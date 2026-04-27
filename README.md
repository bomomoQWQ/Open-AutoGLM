# Open-AutoGLM

> Phone Agent - 基于视觉语言模型的手机自动化 Agent

[Readme in English](README_en.md)

<div align="center">
<img src=resources/logo.svg width="20%"/>
</div>

<p align="center">
    🐳 <a href="#docker-部署推荐">Docker 部署</a> ·
    📡 <a href="#http-api">HTTP API</a> ·
    📱 <a href="#手机端配置">手机配置</a> ·
    🤖 <a href="#懒人版快速安装">AI 辅助安装</a>
</p>

## 项目介绍

Phone Agent 是一个基于视觉语言模型的手机端智能助理框架，能够以多模态方式理解手机屏幕内容，并通过自动化操作帮助用户完成任务。

**工作原理**：截图 → 视觉模型理解界面 → 输出操作指令 → ADB 执行 → 循环，直到任务完成。

```
用户: "打开微信给张三发消息：晚上吃饭"
  → Agent: 截图 → 看到桌面 → Launch 微信 → 截图 → 看到微信首页 → Tap 搜索框
  → Type "张三" → Tap 联系人 → Type "晚上吃饭" → Tap 发送 → finish ✅
```

本项目在原生 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 基础上增加了 **Docker 容器化部署**、**HTTP API 服务**、**异步任务管理**、**思考模式** 等特性，使其更适合作为上游 AI Agent 的 skill/tool 使用。

> ⚠️ 本项目仅供研究和学习使用。严禁用于非法获取信息、干扰系统或任何违法活动。

## 懒人版快速安装

如果你使用 Claude Code，配置 [GLM Coding Plan](https://bigmodel.cn/glm-coding) 后，输入以下提示词即可快速部署：

```
访问文档，为我安装 AutoGLM
https://raw.githubusercontent.com/bomomoQWQ/Open-AutoGLM/refs/heads/main/README.md
```

## Docker 部署（推荐 🐳）

### 1. 宿主机准备

```bash
# Linux: 安装 ADB
sudo apt install adb -y

# 启动 ADB server
adb start-server

# 手机 USB 连接后确认
adb devices
# → 应看到设备:  xxxxxx   device
```

### 2. 启动容器

```bash
docker pull bomomo/phone-agent:latest

docker run -d --network host \
  --name phone-agent \
  --restart unless-stopped \
  -e PYTHONUNBUFFERED=1 \
  -e PHONE_AGENT_PORT=8002 \
  -e PHONE_AGENT_ENABLE_THINKING=true \
  -e PHONE_AGENT_BASE_URL=<模型API地址> \
  -e PHONE_AGENT_MODEL=<模型名称> \
  -e PHONE_AGENT_API_KEY=<API密钥> \
  bomomo/phone-agent:latest
```

`--network host` 使容器内 adb 客户端直连宿主机 adb server（127.0.0.1:5037），无需额外配置。

### 3. 验证

```bash
curl http://localhost:8002/api/health
# → {"status":"ok","adb_available":true,"device_connected":true,"model_configured":true}
```

## HTTP API

### 端点总览

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | 健康检查 |
| `/api/tasks` | POST | 启动异步任务（推荐⭐） |
| `/api/tasks/{id}` | GET | 查询任务进度 |
| `/api/tasks/{id}` | DELETE | 取消运行中任务 |
| `/api/run` | POST | 同步执行（简单任务用） |

详细接口文档和 Python 集成示例见 [SKILL.md](SKILL.md)。

### 异步任务示例

```bash
# 1. 启动 → 秒回
curl -X POST http://localhost:8002/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"task":"打开微信给张三发消息：晚上吃饭"}'
# → {"task_id":"a1b2c3d4e5f6","status":"pending","steps":0}

# 2. 轮询（每 3 秒）
curl http://localhost:8002/api/tasks/a1b2c3d4e5f6
# → {"status":"running","steps":3}

# 3. 完成 / 取消
curl http://localhost:8002/api/tasks/a1b2c3d4e5f6
# → {"status":"finished","result":"消息已发送","steps":6}

# 随时取消
curl -X DELETE http://localhost:8002/api/tasks/a1b2c3d4e5f6
```

### 地址说明

Phone Agent 使用 `--network host`，占宿主机端口。其他容器/机器访问时：

| 调用方位置 | 使用的地址 |
|---|---|
| 同宿主机 | `localhost:8002` 或 `127.0.0.1:8002` |
| Docker 容器内 | `172.17.0.1:8002`（bridge 网关） |
| 局域网其他机器 | 宿主机内网 IP，如 `192.168.1.100:8002` |

## 增强特性

除了原生 AutoGLM 的所有能力，本分支额外提供：

- **异步任务 + 取消**：`POST/api/tasks` + `GET/DELETE/api/tasks/{id}`，长任务永不超时
- **死循环检测**：连续 3 步相同操作且画面无变化时自动注入警告
- **思考模式**：支持千问 `enable_thinking`，实时流式显示推理过程
- **熄屏唤醒**：执行任务前自动 `adb shell input keyevent 224` 唤醒屏幕
- **ADB 分离部署**：容器只装 adb 客户端，连宿主机 adb server，手机无需 WiFi
- **端口可配**：`PHONE_AGENT_PORT` 环境变量避免端口冲突
- **YAML 配置**：`config.yaml.example`，优先级 CLI > env > yaml > 默认值

## 手机端配置

### 1. 启用开发者模式

1. 进入 `设置 → 关于手机 → 版本号`
2. 连续快速点击 10 次，直到提示"开发者模式已启用"

### 2. 启用 USB 调试

1. 进入 `设置 → 开发者选项 → USB 调试`，开启
2. 部分机型需同时开启 **USB 调试（安全设置）**
3. 用 USB 数据线连接电脑，手机上点击「允许」

**注意：USB 数据线必须支持数据传输，不能是仅充电线。**

### 3. 安装 ADB Keyboard（文本输入必需）

下载 [ADB Keyboard APK](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk) 并在手机上安装。

安装后启用：

```bash
adb shell ime enable com.android.adbkeyboard/.AdbIME
```

或手动：`设置 → 系统 → 语言和输入法 → 虚拟键盘 → 启用 ADB Keyboard`

## 模型配置

### 使用第三方模型服务

| 服务商 | base-url | model |
|---|---|---|
| 智谱 BigModel | `https://open.bigmodel.cn/api/paas/v4` | `autoglm-phone` |
| ModelScope | `https://api-inference.modelscope.cn/v1` | `ZhipuAI/AutoGLM-Phone-9B` |
| 阿里百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` 等 |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| 任意 OpenAI 兼容 | 自定义 | 自定义 |

### 自行部署模型（vLLM）

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

模型地址（SGLang 同理）：

| Model | 下载 |
|---|---|
| AutoGLM-Phone-9B | [Hugging Face](https://huggingface.co/zai-org/AutoGLM-Phone-9B) / [ModelScope](https://modelscope.cn/models/ZhipuAI/AutoGLM-Phone-9B) |
| AutoGLM-Phone-9B-Multilingual | [Hugging Face](https://huggingface.co/zai-org/AutoGLM-Phone-9B-Multilingual) / [ModelScope](https://modelscope.cn/models/ZhipuAI/AutoGLM-Phone-9B-Multilingual) |

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|---|---|---|---|
| `PHONE_AGENT_BASE_URL` | 是 | 模型 API 地址 | `http://localhost:8000/v1` |
| `PHONE_AGENT_MODEL` | 是 | 模型名称 | `autoglm-phone-9b` |
| `PHONE_AGENT_API_KEY` | 否 | API 密钥 | `EMPTY` |
| `PHONE_AGENT_PORT` | 否 | HTTP 监听端口 | `8000` |
| `PHONE_AGENT_ENABLE_THINKING` | 否 | 千问思考模式 (`true`/`false`) | `false` |
| `PHONE_AGENT_MAX_STEPS` | 否 | 每任务最大步数 | `100` |
| `PHONE_AGENT_LANG` | 否 | 语言 (`cn`/`en`) | `cn` |
| `PHONE_AGENT_DEVICE_ID` | 否 | ADB 设备 ID | 自动检测 |
| `PHONE_AGENT_DEVICE_TYPE` | 否 | `adb`/`hdc`/`ios` | `adb` |
| `PHONE_AGENT_UNLOCK_PIN` | 否 | 锁屏 PIN 码 | 空 |

## 命令行使用

```bash
# 安装
pip install -r requirements.txt
pip install -e .

# 交互模式
python main.py --base-url http://localhost:8000/v1 --model autoglm-phone-9b

# 指定任务
python main.py --base-url http://localhost:8000/v1 "打开美团搜索附近的火锅店"

# 使用 API Key
python main.py --apikey sk-xxxxx

# 英文 prompt
python main.py --lang en --base-url http://localhost:8000/v1 "Open Chrome browser"

# 列出支持的应用
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
result = agent.run("打开淘宝搜索无线耳机")
print(result)
```

## 支持的应用

Phone Agent 支持 50+ 款主流中文应用：

| 分类 | 应用 |
|---|---|
| 社交通讯 | 微信、QQ、微博 |
| 电商购物 | 淘宝、京东、拼多多 |
| 美食外卖 | 美团、饿了么、肯德基 |
| 出行旅游 | 携程、12306、滴滴出行 |
| 视频娱乐 | bilibili、抖音、爱奇艺 |
| 音乐音频 | 网易云音乐、QQ音乐、喜马拉雅 |
| 生活服务 | 大众点评、高德地图、百度地图 |
| 内容社区 | 小红书、知乎、豆瓣 |

运行 `python main.py --list-apps` 查看完整列表。

## 可用操作

| 操作 | 描述 |
|---|---|
| `Launch` | 启动应用 |
| `Tap` | 点击指定坐标 |
| `Type` | 输入文本 |
| `Swipe` | 滑动屏幕 |
| `Back` | 返回上一页 |
| `Home` | 返回桌面 |
| `Long Press` | 长按 |
| `Double Tap` | 双击 |
| `Wait` | 等待页面加载 |
| `Take_over` | 人工接管（登录/验证码） |

## 项目结构

```
├── server.py              # FastAPI HTTP 入口
├── main.py                # CLI 入口
├── Dockerfile             # Docker 镜像构建
├── SKILL.md               # 上游 Agent 集成文档
├── config.yaml.example    # YAML 配置示例
├── phone_agent/
│   ├── agent.py           # Agent 主循环 + 死循环检测
│   ├── model/client.py    # OpenAI 兼容 VLM 客户端
│   ├── actions/handler.py # 操作解析与执行
│   ├── adb/               # ADB 截图/点击/输入
│   └── config/            # 提示词/应用列表/配置
```

## 常见问题

### 设备未找到

```bash
adb kill-server && adb start-server
adb devices
```

检查：USB 调试开启、数据线支持数据传输、手机上已点「允许」授权。

### 能打开应用但无法点击

同时开启 `设置 → 开发者选项` 中的 **USB 调试** 和 **USB 调试（安全设置）**。

### 文本输入不工作

1. 确保 ADB Keyboard 已安装并启用
2. 执行 `adb shell ime enable com.android.adbkeyboard/.AdbIME`

### 截图黑屏

通常出现在支付/密码/银行等敏感页面，Agent 会自动请求人工接管。

### Windows 编码异常

```bash
PYTHONIOENCODING=utf-8 python main.py ...
```

## 构建镜像

```bash
docker build -t phone-agent .
```

## 引用

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

本项目基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 构建。仅供研究和学习使用。
