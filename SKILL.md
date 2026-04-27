# Phone Agent Skill

Phone Agent 是一个手机自动化任务执行器。上级 AI Agent 通过 HTTP API 下发**手机操作任务**，Phone Agent 自动操控手机完成并返回结果。

## ⚠️ 核心原理（必读）

> Phone Agent **不是截图工具**，不是文件管理器，不是系统命令执行器。
> 
> Phone Agent 的工作方式：截图 → VLM 看图 → 输出点击/滑动/打字 → ADB 执行 → 循环。
> 
> 截图是 Agent **内部用来分析画面的**，不是对外输出。它**无法**像 `adb screencap` 那样把截图文件返回给调用方。

### ✅ 正确的任务（自然语言手机操作）

| 任务 | 效果 |
|---|---|
| `打开微信给张三发消息：晚上吃饭` | 自动化操作手机完成 |
| `打开淘宝搜索无线耳机加入购物车` | 自动化操作手机完成 |
| `打开设置连接 WiFi 名为 guest-2.4G` | 自动化操作手机完成 |
| `打开小红书搜索成都美食攻略` | 自动化操作手机完成 |
| `帮我打开Chrome` | 自动化操作手机完成 |

### ❌ 错误的用法（这些做不到）

| 错误任务 | 为什么不行 |
|---|---|
| `截图`、`截取屏幕`、`返回桌面并截屏` | 这不是截图工具，截图是内部用的 |
| `获取截图文件保存到 /sdcard/xx.png` | 没有文件保存能力 |
| `列出桌面上的应用图标` | 这是描述任务，应改为手机操作如 `看看桌面上有什么应用` |
| `adb shell screencap` | 不能执行 ADB 命令 |
| `调用某某 API` | 没有 API 调用功能，但通过 `Call_API` 可总结当前页面 |

### 任务公式

```
打开{App名} 做{具体操作}
```

任务必须是**用户想让手机做的事**。VLM 能看懂屏幕内容（如"桌面上有什么应用"它可以播报），但这不是截图 API——上级 Agent 拿不到图片。

### 任务必须明确终止条件

⚠️ **不要下发开放式任务**，如"向下滑动看看还有没有更多"、"一直翻找"。这会导致 Agent 陷入无限循环。

✅ 好的范例（有明确边界）：

| ✅ 好任务 | ❌ 差任务 |
|---|---|
| `在蜜雪冰城页面往下滑5次，列出看到的饮品种类` | `在蜜雪冰城页面往下滑动看看还有什么` |
| `打开设置连接WiFi名为xxx` | `打开设置看看WiFi` |
| `打开淘宝搜索无线耳机，看前3个结果的价格` | `打开淘宝搜无线耳机看看` |
| `打开小红书刷3条笔记后总结` | `打开小红书刷一下` |

**公式：操作 + 次数上限 + 要获取的信息**

## ⚠️ 地址配置（重要）

Phone Agent 使用 `--network host`，占宿主机端口。上级 Agent 连 Phone Agent 的地址取决于部署环境：

| 上级 Agent 在哪 | 用的地址 |
|---|---|
| Docker 同宿主机 | `172.17.0.1:8002`（默认 bridge 网关）或宿主机内网 IP |
| Docker（自定义网络） | `docker inspect bridge | grep Gateway` 查网关 IP |
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

### 异步任务（推荐 ⭐）

长任务不会超时，可随时取消。

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
{"task_id": "a1b2c3d4e5f6", "status": "running", "steps": 3, "result": null}
```
```json
{"task_id": "a1b2c3d4e5f6", "status": "finished", "steps": 6, "result": "消息已发送"}
```

**3. 取消任务（死循环或不对劲时）**

```bash
curl -X DELETE http://<host>:8002/api/tasks/a1b2c3d4e5f6
```

状态枚举：`pending` → `running` → `finished` / `error` / `cancelled`

### 同步执行（简单任务可用）

```bash
curl -X POST http://<host>:8002/api/run \
  -H "Content-Type: application/json" \
  -d '{"task": "打开设置", "max_steps": 10}'
```

```json
{"success": true, "result": "已打开设置", "steps": 2}
```

⚠️ 任务超过 HTTP 超时会断开，建议只用快速任务。

### Python 调用示例

```python
import requests
import time
import os

def _get_base_url():
    if os.path.exists("/.dockerenv"):
        return "http://172.17.0.1:8002"
    return "http://localhost:8002"

BASE_URL = os.getenv("PHONE_AGENT_URL", _get_base_url())

def run_phone_task(task: str, max_steps: int = 50,
                   poll_interval: float = 3.0) -> dict:
    """异步执行手机任务，轮询等待完成。"""
    r = requests.post(f"{BASE_URL}/api/tasks",
                      json={"task": task, "max_steps": max_steps},
                      timeout=10)
    r.raise_for_status()
    task_id = r.json()["task_id"]

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

1. 任务描述用自然语言，说清楚要打开什么 App、做什么操作
2. Phone Agent **不是截图工具**——不要发截图、截屏、获取屏幕、保存文件类任务
3. 登录、支付等敏感操作会触发人工接管，无人响应时会失败
4. 任务间串行执行，不要并发调用
5. 上级 Agent 检测到步骤长时间无进展可主动 DELETE 取消
