"""Phone Agent HTTP API Server.

Provides REST endpoints for an upstream AI agent (e.g. in a separate Docker
container) to run phone automation tasks.

Usage:
    python server.py
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

import os
import subprocess
import threading
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.device_factory import set_device_type, DeviceType
from phone_agent.model import ModelConfig


# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

_model_config = ModelConfig(
    base_url=os.getenv("PHONE_AGENT_BASE_URL", "http://localhost:8000/v1"),
    model_name=os.getenv("PHONE_AGENT_MODEL", "autoglm-phone-9b"),
    api_key=os.getenv("PHONE_AGENT_API_KEY", "EMPTY"),
    lang=os.getenv("PHONE_AGENT_LANG", "cn"),
    temperature=float(os.getenv("PHONE_AGENT_TEMPERATURE", "0.0")),
    max_tokens=int(os.getenv("PHONE_AGENT_MAX_TOKENS", "3000")),
    extra_body={"enable_thinking": os.getenv("PHONE_AGENT_ENABLE_THINKING", "").lower() in ("1", "true", "yes")} or {},
)

_default_max_steps = int(os.getenv("PHONE_AGENT_MAX_STEPS", "100"))
_device_id = os.getenv("PHONE_AGENT_DEVICE_ID")
_device_type_raw = os.getenv("PHONE_AGENT_DEVICE_TYPE", "adb")

set_device_type(DeviceType(_device_type_raw))

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Phone Agent API", version="0.1.0")

# ---------------------------------------------------------------------------
# Task store (async task management)
# ---------------------------------------------------------------------------

_task_store: dict[str, dict[str, Any]] = {}
_task_lock = threading.Lock()


def _cleanup_old_tasks() -> None:
    """Remove finished/cancelled tasks older than 5 minutes."""
    now = time.time()
    with _task_lock:
        stale = [
            tid
            for tid, t in _task_store.items()
            if t["status"] in ("finished", "error", "cancelled")
            and now - t.get("finished_at", now) > 300
        ]
        for tid in stale:
            del _task_store[tid]


def _run_task_background(task_id: str, agent: PhoneAgent, task: str) -> None:
    """Background thread: execute agent step-by-step, check cancel flag."""
    task_info = _task_store.get(task_id)
    if not task_info:
        return

    cancel = task_info["cancel"]
    task_info["status"] = "running"

    try:
        # First step
        result = agent.step(task)
        task_info["steps"] = agent.step_count

        if result.finished:
            task_info["status"] = "finished"
            task_info["result"] = result.message or "Done"
            task_info["finished_at"] = time.time()
            return

        # Continue step by step until finished, cancelled, or max steps
        while not cancel.is_set() and agent.step_count < task_info["max_steps"]:
            result = agent.step()
            task_info["steps"] = agent.step_count

            if result.finished:
                task_info["status"] = "finished"
                task_info["result"] = result.message or "Done"
                task_info["finished_at"] = time.time()
                return

        if cancel.is_set():
            task_info["status"] = "cancelled"
            task_info["result"] = "Task cancelled by user"
        else:
            task_info["status"] = "finished"
            task_info["result"] = "Max steps reached"

    except Exception as exc:
        task_info["status"] = "error"
        task_info["result"] = str(exc)

    task_info["finished_at"] = time.time()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    task: str = Field(..., description="Natural language task description")
    max_steps: int = Field(
        default_factory=lambda: _default_max_steps,
    )


class RunResponse(BaseModel):
    success: bool
    result: str
    steps: int


class TaskResponse(BaseModel):
    task_id: str
    status: str
    steps: int
    result: str | None = None


class HealthResponse(BaseModel):
    status: str
    adb_available: bool
    device_connected: bool
    model_configured: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_unlock_pin = os.getenv("PHONE_AGENT_UNLOCK_PIN", "")


def _check_adb() -> tuple[bool, bool]:
    adb_available = False
    device_connected = False
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=5
        )
        adb_available = result.returncode == 0
        for line in result.stdout.strip().split("\n")[1:]:
            if "\tdevice" in line:
                device_connected = True
                break
    except Exception:
        pass
    return adb_available, device_connected


def _wake_device() -> None:
    subprocess.run(
        ["adb", "shell", "input", "keyevent", "224"],
        capture_output=True, timeout=5,
    )
    if _unlock_pin:
        subprocess.run(["adb", "shell", "input", "keyevent", "82"], capture_output=True, timeout=5)
        subprocess.run(["adb", "shell", "input", "text", _unlock_pin], capture_output=True, timeout=5)
        subprocess.run(["adb", "shell", "input", "keyevent", "66"], capture_output=True, timeout=5)


def _build_agent(max_steps: int) -> PhoneAgent:
    agent_config = AgentConfig(
        max_steps=max_steps,
        device_id=_device_id,
        lang=_model_config.lang,
        verbose=False,
    )
    return PhoneAgent(model_config=_model_config, agent_config=agent_config)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health", response_model=HealthResponse)
def health():
    adb_available, device_connected = _check_adb()
    return HealthResponse(
        status="ok" if adb_available and device_connected else "degraded",
        adb_available=adb_available,
        device_connected=device_connected,
        model_configured=bool(_model_config.base_url and _model_config.model_name),
    )


@app.post("/api/run", response_model=RunResponse)
def run_task(request: RunRequest):
    """Synchronous run. Blocks until task completes. For simple integrations."""
    _wake_device()
    agent = _build_agent(request.max_steps)
    try:
        result = agent.run(request.task)
        return RunResponse(success=True, result=result, steps=agent.step_count)
    except Exception as exc:
        return RunResponse(success=False, result=str(exc), steps=0)


@app.post("/api/tasks", response_model=TaskResponse)
def create_task(request: RunRequest):
    """Create an async task. Returns immediately with task_id."""
    _cleanup_old_tasks()
    _wake_device()

    task_id = uuid.uuid4().hex[:12]
    agent = _build_agent(request.max_steps)
    cancel = threading.Event()

    with _task_lock:
        _task_store[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "steps": 0,
            "result": None,
            "max_steps": request.max_steps,
            "cancel": cancel,
            "created_at": time.time(),
        }

    thread = threading.Thread(
        target=_run_task_background,
        args=(task_id, agent, request.task),
        daemon=True,
    )
    _task_store[task_id]["thread"] = thread
    thread.start()

    return TaskResponse(task_id=task_id, status="pending", steps=0)


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    """Get task status and progress."""
    with _task_lock:
        task_info = _task_store.get(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        task_id=task_id,
        status=task_info["status"],
        steps=task_info["steps"],
        result=task_info.get("result"),
    )


@app.delete("/api/tasks/{task_id}", response_model=TaskResponse)
def cancel_task(task_id: str):
    """Cancel a running task."""
    with _task_lock:
        task_info = _task_store.get(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task_info["status"] not in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Task already finished")

    task_info["cancel"].set()
    return TaskResponse(
        task_id=task_id,
        status="cancelling",
        steps=task_info["steps"],
        result=None,
    )
