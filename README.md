# Phone Agent

基于视觉语言模型的手机自动化 Agent，通过 HTTP API 为上游 AI Agent 提供手机操控能力。

```
上游 Agent ── HTTP ──► Phone Agent (Docker) ── ADB ──► 手机
```

## 快速开始

### 1. 宿主机准备

```bash
# Linux: 安装 ADB（USB 驱动需要在内核层）
sudo apt install adb -y

# 启动 ADB server，手机 USB 连接
adb start-server
adb devices  # 应看到设备
```

手机上需要安装 [ADB Keyboard](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk)（文本输入用）。

### 2. 启动容器

```bash
docker pull bomomo/phone-agent:latest

docker run -d --network host \
  --name phone-agent \
  --restart unless-stopped \
  -e PYTHONUNBUFFERED=1 \
  -e PHONE_AGENT_PORT=8002 \
  -e PHONE_AGENT_ENABLE_THINKING=true \
  -e PHONE_AGENT_BASE_URL=<模型地址> \
  -e PHONE_AGENT_MODEL=<模型名> \
  -e PHONE_AGENT_API_KEY=<API密钥> \
  bomomo/phone-agent:latest
```

`--network host` 使容器内 adb 客户端直连宿主机 adb server (127.0.0.1:5037)。

### 3. 验证

```bash
curl http://localhost:8002/api/health
# → {"status":"ok","adb_available":true,"device_connected":true}
```

## API 文档

详细接口文档见 [SKILL.md](SKILL.md)。

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | 健康检查 |
| `/api/run` | POST | 同步执行任务 |
| `/api/tasks` | POST | 启动异步任务（推荐） |
| `/api/tasks/{id}` | GET | 查询任务进度 |
| `/api/tasks/{id}` | DELETE | 取消运行中任务 |

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|---|---|---|---|
| `PHONE_AGENT_BASE_URL` | 是 | VLM 模型 API 地址 | `http://localhost:8000/v1` |
| `PHONE_AGENT_MODEL` | 是 | 模型名称 | `autoglm-phone-9b` |
| `PHONE_AGENT_API_KEY` | 否 | API 密钥 | `EMPTY` |
| `PHONE_AGENT_PORT` | 否 | HTTP 监听端口 | `8000` |
| `PHONE_AGENT_ENABLE_THINKING` | 否 | 启用思考模式（千问等） | `false` |
| `PHONE_AGENT_MAX_STEPS` | 否 | 每任务最大步数 | `100` |
| `PHONE_AGENT_LANG` | 否 | 语言: `cn` / `en` | `cn` |
| `PHONE_AGENT_DEVICE_ID` | 否 | ADB 设备 ID | 自动检测 |
| `PHONE_AGENT_DEVICE_TYPE` | 否 | 设备类型: `adb` / `hdc` / `ios` | `adb` |

## 特性

- **异步任务 + 取消**：长任务不超时，可随时取消死循环
- **思考模式**：支持千问 `enable_thinking`，实时显示推理过程
- **死循环检测**：连续 3 步相同操作且画面无变化时自动注入警告
- **熄屏唤醒**：执行任务前自动唤醒手机屏幕
- **ADB 分离部署**：容器只装 adb 客户端，连宿主机 adb server
- **端口可配**：通过 `PHONE_AGENT_PORT` 避免端口冲突

## 开发

### 本地运行

```bash
pip install -r requirements.txt
pip install -e .

# CLI 模式
python main.py --base-url <URL> --model <MODEL> "打开设置"

# HTTP 服务
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 构建镜像

```bash
docker build -t phone-agent .
```

## 项目结构

```
├── server.py              # FastAPI HTTP 入口
├── main.py                # CLI 入口
├── Dockerfile             # Docker 构建
├── SKILL.md               # 上游 Agent 集成文档
├── config.yaml.example    # YAML 配置示例
├── phone_agent/
│   ├── agent.py           # Agent 主循环 + 死循环检测
│   ├── model/client.py    # OpenAI 兼容 VLM 客户端
│   ├── actions/handler.py # 操作解析与执行
│   ├── adb/               # ADB 操作（截图/点击/输入）
│   └── config/            # 提示词/应用列表/配置加载
```

## License

本项目基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 构建。仅供研究和学习使用。
