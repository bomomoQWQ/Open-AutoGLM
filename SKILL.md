# Phone Agent Skill

Phone Agent 是一个手机自动化工具。上级 AI Agent 通过 HTTP API 下发自然语言任务，Phone Agent 接管手机完成操作后返回结果。

> **推荐使用异步任务 API**，避免复杂任务因超时中断。

## ⚠️ 地址配置（重要）

Phone Agent 使用 `--network host`，占宿主机端口。上级 Agent 连 Phone Agent 的地址取决于部署环境：

| 上级 Agent 在哪 | 用的地址 |
|---|---|
| Docker 同宿主机 | `172.17.0.1:8002`（默认 bridge 网关）或宿主机内网 IP |
| Docker（自定义网络） | `docker inspect bridge \| grep Gateway` 查网关 IP |
| 非 Docker / 同机 | `localhost:8002` |
| 远程 | 宿主机内网 IP，如 `192.168.1.100:8002` |

### 快速检测

```bash
# 在上级 Agent 所在的容器里执行
curl http://172.17.0.1:8002/api/health
# 不通就试宿主机内网 IP
curl http://192.168.1.xxx:8002/api/health
```

## API 文档

### 健康检查

```bash
curl http://<host>:8002/api/health
```

```json
{"status": "ok", "adb_available": true, "device_connected": true, "model_configured": true}
```

`status` 为 `ok` 时可执行任务，`degraded` 表示组件异常。

### 异步任务（推荐 ⭐）

复杂任务走走停停可能要几分钟，同步阻塞容易超时。异步 API 三步解决：

**1. 启动任务 → 秒回 task_id**

```bash
curl -X POST http://<host>:8002/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"task": "打开微信给张三发消息：晚上吃饭", "max_steps": 20}'
```

```json
{"task_id": "a1b2c3d4e5f6", "status": "pending", "steps": 0}
```

**2. 轮询进度（建议每 3 秒一次）**

```bash
curl http://<host>:8002/api/tasks/a1b2c3d4e5f6
```

```json
// 进行中
{"task_id": "a1b2c3d4e5f6", "status": "running", "steps": 3, "result": null}

// 完成
{"task_id": "a1b2c3d4e5f6", "status": "finished", "steps": 6, "result": "消息已发送"}
```

**3. 取消任务（死循环或不对劲时）**

```bash
curl -X DELETE http://<host>:8002/api/tasks/a1b2c3d4e5f6
```

```json
{"task_id": "a1b2c3d4e5f6", "status": "cancelling"}
```

任务状态枚举：`pending` → `running` → `finished` / `error` / `cancelled`

### 同步执行（简单任务可用）

```bash
curl -X POST http://<host>:8002/api/run \
  -H "Content-Type: application/json" \
  -d '{"task": "打开设置", "max_steps": 10}'
```

```json
{"success": true, "result": "已打开设置", "steps": 2}
```

⚠️ 任务超过 HTTP 超时时间会断开，建议只在快速任务使用。

### Python 调用示例

```python
import requests
import time
import os

# 自动检测地址：Docker 环境用 bridge 网关，否则用 localhost
def _get_base_url():
    if os.path.exists("/.dockerenv"):
        return "http://172.17.0.1:8002"   # Docker bridge 网关
    return "http://localhost:8002"

BASE_URL = os.getenv("PHONE_AGENT_URL", _get_base_url())

def run_phone_task(task: str, max_steps: int = 50,
                   poll_interval: float = 3.0) -> dict:
    """异步执行手机任务，轮询等待完成。"""
    # 1. 启动
    r = requests.post(f"{BASE_URL}/api/tasks",
                      json={"task": task, "max_steps": max_steps},
                      timeout=10)
    r.raise_for_status()
    task_id = r.json()["task_id"]

    # 2. 轮询
    try:
        while True:
            r = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)
            r.raise_for_status()
            data = r.json()
            if data["status"] in ("finished", "error", "cancelled"):
                return data
            time.sleep(poll_interval)
    except Exception:
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}")
        raise
```

也可通过环境变量 `PHONE_AGENT_URL` 显式指定地址。

## 任务示例

| 场景 | task |
|---|---|
| 社交 | `打开微信给张三发消息：晚上吃饭` |
| 购物 | `打开淘宝搜索无线耳机加入购物车` |
| 外卖 | `打开美团搜索附近的火锅店` |
| 内容 | `打开小红书搜索成都美食攻略` |
| 设置 | `打开设置连接 WiFi 名称为 guest-2.4G` |
| 通用 | `打开{App名称}做{具体操作}` |

## 注意事项

1. 任务描述尽量具体，包含目标 App 和期望操作
2. 登录、支付等敏感操作会触发人工接管，无人响应时会失败
3. 任务间串行执行，不要并发调用
4. 上级 Agent 检测到步骤长时间无进展可主动 DELETE 取消
