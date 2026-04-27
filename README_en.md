# Open-AutoGLM

> Phone Agent - Vision-Language Model powered phone automation

[中文阅读](./README.md)

<div align="center">
<img src=resources/logo.svg width="20%"/>
</div>

<p align="center">
    🐳 <a href="#docker-deployment-recommended">Docker</a> ·
    📡 <a href="#http-api">HTTP API</a> ·
    📱 <a href="#phone-setup">Phone Setup</a> ·
    🤖 <a href="#ai-assisted-installation">AI-Assisted Install</a>
</p>

## Overview

Phone Agent is an intelligent assistant framework that uses vision-language models to understand phone screens and automate tasks.

**How it works**: Screenshot → Vision Model → Action → ADB Execute → Loop until done.

```
User: "Open WeChat, search for John and send 'dinner tonight'"
  → Screenshot: Home screen → Launch WeChat → Screenshot: WeChat home → Tap search
  → Type "John" → Tap contact → Type "dinner tonight" → Tap send → finish ✅
```

This fork adds **Docker deployment**, **HTTP API**, **async task management**, and **thinking mode** on top of the original [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM).

> ⚠️ This project is for research and learning only.

## AI-Assisted Installation

Use Claude Code (or any AI coding agent) with a multimodal-capable model:

```
Access the documentation and install AutoGLM for me
https://raw.githubusercontent.com/bomomoQWQ/Open-AutoGLM/refs/heads/main/README_en.md
```

## Docker Deployment (Recommended 🐳)

### 1. Host Setup

```bash
# Install ADB
sudo apt install adb -y

# Start ADB server
adb start-server

# Connect phone via USB, verify
adb devices
# → Should show:  XXXXXX   device
# Also supports WiFi ADB
```

### 2. Run Container

```bash
docker pull bomomo/phone-agent:latest

docker run -d --network host \
  --name phone-agent \
  --restart unless-stopped \
  -e PYTHONUNBUFFERED=1 \
  -e PHONE_AGENT_PORT=8002 \
  -e PHONE_AGENT_ENABLE_THINKING=true \
  -e PHONE_AGENT_BASE_URL=<MODEL_API_URL> \
  -e PHONE_AGENT_MODEL=<MODEL_NAME> \
  -e PHONE_AGENT_API_KEY=<API_KEY> \
  bomomo/phone-agent:latest
```

`--network host` allows the container's adb client to connect directly to the host's adb server at 127.0.0.1:5037.

### 3. Verify

```bash
curl http://localhost:8002/api/health
# → {"status":"ok","adb_available":true,"device_connected":true,"model_configured":true}
```

## HTTP API

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/tasks` | POST | Start async task (recommended ⭐) |
| `/api/tasks/{id}` | GET | Query task progress |
| `/api/tasks/{id}` | DELETE | Cancel running task |
| `/api/run` | POST | Sync execution (simple tasks) |

See [SKILL.md](SKILL.md) for full API docs and Python examples (also bundled as `Phone_Agent_2.zip`).

### Async Task Example

```bash
# 1. Start → instant response
curl -X POST http://localhost:8002/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"task":"Open WeChat and send dinner tonight to John"}'
# → {"task_id":"a1b2c3d4e5f6","status":"pending","steps":0}

# 2. Poll every 3s
curl http://localhost:8002/api/tasks/a1b2c3d4e5f6
# → {"status":"running","steps":3}

# 3. Done / Cancel
curl http://localhost:8002/api/tasks/a1b2c3d4e5f6
# → {"status":"finished","result":"Message sent","steps":6}

# Cancel anytime
curl -X DELETE http://localhost:8002/api/tasks/a1b2c3d4e5f6
```

### Address Configuration

Phone Agent uses `--network host`. Access from other containers/machines:

| Caller Location | Address |
|---|---|
| Same host | `localhost:8002` / `127.0.0.1:8002` |
| Docker container | `172.17.0.1:8002` (bridge gateway) |
| LAN machine | Host IP, e.g. `192.168.1.100:8002` |

## Enhanced Features

- **Async Tasks + Cancel**: Long tasks never timeout. Cancel dead loops anytime.
- **Dead-Loop Detection**: Auto-injects warning after 3+ identical actions with no screen change.
- **Thinking Mode**: Supports qwen `enable_thinking` with real-time streaming reasoning.
- **Screen Wake**: Auto-wakes device before task execution (`adb shell input keyevent 224`).
- **ADB Split Deployment**: Container only runs adb client, connects to host's adb server.
- **Configurable Port**: `PHONE_AGENT_PORT` env var to avoid conflicts.
- **YAML Config**: `config.yaml.example` with priority: CLI > env > yaml > default.

## Phone Setup

### 1. Enable Developer Mode

Settings → About Phone → Tap Build Number 7x until "Developer mode enabled".

### 2. Enable USB Debugging

Settings → Developer Options → USB Debugging → ON.
Some devices also need **USB Debugging (Security Settings)**.
Connect with USB cable, tap "Allow" on phone.

### 3. Install ADB Keyboard

Download [ADB Keyboard APK](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk) and install.

Enable it:

```bash
adb shell ime enable com.android.adbkeyboard/.AdbIME
```

## Model Configuration

### Third-Party Services (any vision-capable model)

| Provider | base-url | model |
|---|---|---|
| Zhipu BigModel | `https://open.bigmodel.cn/api/paas/v4` | `autoglm-phone` |
| ModelScope | `https://api-inference.modelscope.cn/v1` | `ZhipuAI/AutoGLM-Phone-9B` |
| Alibaba Bailian | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` etc. |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| Any OpenAI-compatible | Custom | Custom |

### Self-Hosted (vLLM)

```shell
python3 -m vllm.entrypoints.openai.api_server \
  --served-model-name autoglm-phone-9b \
  --allowed-local-media-path / \
  --mm-encoder-tp-mode data \
  --mm_processor_cache_type shm \
  --mm_processor_kwargs "{\"max_pixels\":5000000}" \
  --max-model-len 25480 \
  --chat-template-content-format string \
  --limit-mm-per-prompt "{\"image\":10}" \
  --model zai-org/AutoGLM-Phone-9B \
  --port 8000
```

## Environment Variables

| Variable | Required | Description | Default |
|---|---|---|---|
| `PHONE_AGENT_BASE_URL` | Yes | Model API URL | `http://localhost:8000/v1` |
| `PHONE_AGENT_MODEL` | Yes | Model name | `autoglm-phone-9b` |
| `PHONE_AGENT_API_KEY` | No | API key | `EMPTY` |
| `PHONE_AGENT_PORT` | No | HTTP port | `8000` |
| `PHONE_AGENT_ENABLE_THINKING` | No | Thinking mode | `false` |
| `PHONE_AGENT_MAX_STEPS` | No | Max steps | `100` |
| `PHONE_AGENT_LANG` | No | Language (`cn`/`en`) | `cn` |
| `PHONE_AGENT_DEVICE_ID` | No | ADB device ID | auto-detect |
| `PHONE_AGENT_DEVICE_TYPE` | No | `adb`/`hdc`/`ios` | `adb` |
| `PHONE_AGENT_UNLOCK_PIN` | No | Lock screen PIN | empty |

## CLI Usage

```bash
pip install -r requirements.txt
pip install -e .

python main.py --base-url http://localhost:8000/v1 --model autoglm-phone-9b
python main.py --base-url http://localhost:8000/v1 "Open Chrome and search for OpenAI"
python main.py --lang en --base-url http://localhost:8000/v1 "Open Chrome browser"
python main.py --list-apps
```

### Python API

```python
from phone_agent import PhoneAgent
from phone_agent.model import ModelConfig

model_config = ModelConfig(
    base_url="http://localhost:8000/v1",
    model_name="autoglm-phone-9b",
)
agent = PhoneAgent(model_config=model_config)
result = agent.run("Open eBay and search for wireless earbuds")
print(result)
```

## Troubleshooting

### Device not found

```bash
adb kill-server && adb start-server
adb devices
```

Check: USB debugging on, data-capable cable, authorized on phone.

### Can open apps but can't tap

Enable both **USB Debugging** and **USB Debugging (Security Settings)**.

### Text input not working

Install ADB Keyboard and run: `adb shell ime enable com.android.adbkeyboard/.AdbIME`

### Windows encoding issues

```bash
PYTHONIOENCODING=utf-8 python main.py ...
```

## Build Image

```bash
docker build -t phone-agent .
```

## Citation

```bibtex
@article{liu2024autoglm,
  title={Autoglm: Autonomous foundation agents for guis},
  author={Liu, Xiao and Qin, Bo and Liang, Dongzhu and Dong, Guang and Lai, Hanyu
          and Zhang, Hanchen and Zhao, Hanlin and Iong, Iat Long and Sun, Jiadai
          and Wang, Jiaqi and others},
  journal={arXiv preprint arXiv:2411.00820},
  year={2024}
}
```

## License

Based on [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM). For research and learning only.
