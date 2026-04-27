# Open-AutoGLM Quick Start for Coding Agent

<div align="center">
<img src=resources/logo.svg width="20%"/>
</div>

> **本文专为 AI 助手（如 Claude Code）阅读，用于自动化部署 Open-AutoGLM（Docker 版）。**
>
> **This document is designed for AI assistants (such as Claude Code) to automate the deployment of Open-AutoGLM (Docker edition).**
>
> 如果你是人类读者，可以跳过本文，按照 [README.md](README.md) 操作即可。
>
> If you are a human reader, you can skip this document and follow [README.md](README.md) instead.

---

## Table of Contents / 目录

- [English](#english)
- [中文](#中文)

---

# English

## Overview

Open-AutoGLM is a phone automation agent. The user says "Open WeChat and send a message to John", and the agent controls the Android phone to complete the task.

**Architecture**: Screenshot → Vision Model → Action (Tap/Swipe/Type) → ADB Execute → Loop

This fork adds Docker support and HTTP API, making it suitable as a skill/tool for upstream AI agents.

## Deployment Steps

### 1. Pre-flight Checklist

Ask the user to confirm:

- [ ] An Android phone (7.0+) with USB cable (data-capable, not charge-only)
- [ ] Developer Mode enabled (Settings → About → tap Build Number 7x)
- [ ] USB Debugging enabled (Settings → Developer Options → USB Debugging)
- [ ] USB Debugging (Security Settings) enabled (some devices)
- [ ] ADB Keyboard installed: https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk
- [ ] A vision-language model API endpoint (any OpenAI-compatible VLM: GPT-4o, qwen-vl, AutoGLM-Phone-9B, etc.)

### 2. Host Machine Setup (Linux)

```bash
# Install ADB
sudo apt install adb -y

# Start ADB server
adb start-server

# Connect phone via USB, verify
adb devices
# Expected:  XXXXXXXX    device

# Enable ADB Keyboard
adb shell ime enable com.android.adbkeyboard/.AdbIME
```

### 3. Run Container

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

### 4. Verify

```bash
curl http://localhost:8002/api/health
# → {"status":"ok","adb_available":true,"device_connected":true,"model_configured":true}
```

### 5. Run a Task

```bash
# Async (recommended for complex tasks)
curl -X POST http://localhost:8002/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"task":"打开微信给文件传输助手发消息：部署成功"}'

# Sync (quick tasks)
curl -X POST http://localhost:8002/api/run \
  -H "Content-Type: application/json" \
  -d '{"task":"打开微信给文件传输助手发消息：部署成功"}'
```

## API Reference

See [SKILL.md](SKILL.md) for full API documentation and Python integration examples.

## Environment Variables

| Variable | Required | Description | Default |
|---|---|---|---|
| `PHONE_AGENT_BASE_URL` | Yes | Model API URL | `http://localhost:8000/v1` |
| `PHONE_AGENT_MODEL` | Yes | Model name | `autoglm-phone-9b` |
| `PHONE_AGENT_API_KEY` | No | API key | `EMPTY` |
| `PHONE_AGENT_PORT` | No | HTTP port | `8000` |
| `PHONE_AGENT_ENABLE_THINKING` | No | Thinking mode for qwen | `false` |
| `PHONE_AGENT_MAX_STEPS` | No | Max steps per task | `100` |
| `PHONE_AGENT_LANG` | No | Language (`cn`/`en`) | `cn` |

## Troubleshooting

| Issue | Solution |
|---|---|
| `adb devices` empty | Check USB cable, USB Debugging enabled, tap "Allow" on phone |
| Can open apps but can't tap | Enable "USB Debugging (Security Settings)" |
| Text input not working | Install & enable ADB Keyboard: `adb shell ime enable com.android.adbkeyboard/.AdbIME` |
| Screenshot black | Sensitive page (payment/bank) — normal, agent handles it |
| Container keeps restarting | Check port conflict: `docker logs phone-agent`, change `PHONE_AGENT_PORT` |
| API call timeout | Use async `/api/tasks` endpoints instead of `/api/run` |

## Deployment Checklist

1. ✅ `adb devices` shows a device
2. ✅ ADB Keyboard installed and enabled
3. ✅ `curl /api/health` returns `"status":"ok"`
4. ✅ A task completes: "打开微信给文件传输助手发消息：部署成功"

---

# 中文

## 概述

Open-AutoGLM 是一个手机自动化 Agent。用户说"打开微信给张三发消息"，Agent 自动操作安卓手机完成任务。

**原理**：截图 → 视觉模型理解界面 → 输出操作 → ADB 执行 → 循环

本分支增加了 Docker 支持和 HTTP API，适合作为上游 AI Agent 的 skill/tool 使用。

## 部署步骤

### 1. 前置检查

逐项向用户确认：

- [ ] 安卓手机 (7.0+)，支持数据传输的 USB 数据线（非仅充电线）
- [ ] 开发者模式已开启（设置 → 关于手机 → 连续点击版本号 7 次）
- [ ] USB 调试已开启（设置 → 开发者选项 → USB 调试）
- [ ] USB 调试（安全设置）已开启（部分机型需要）
- [ ] ADB Keyboard 已安装：https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk
- [ ] 有一个可用的视觉语言模型 API（任意 OpenAI 兼容 VLM：GPT-4o、qwen-vl、AutoGLM-Phone-9B 等）

### 2. 宿主机配置（Linux）

```bash
# 安装 ADB
sudo apt install adb -y

# 启动 ADB server
adb start-server

# USB 连接手机，验证
adb devices
# 应显示:  XXXXXXXX    device

# 启用 ADB Keyboard
adb shell ime enable com.android.adbkeyboard/.AdbIME
```

### 3. 启动容器

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

### 4. 验证

```bash
curl http://localhost:8002/api/health
# → {"status":"ok","adb_available":true,"device_connected":true,"model_configured":true}
```

### 5. 执行任务

```bash
# 异步（推荐，复杂任务用）
curl -X POST http://localhost:8002/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"task":"打开微信给文件传输助手发消息：部署成功"}'

# 同步（快速任务用）
curl -X POST http://localhost:8002/api/run \
  -H "Content-Type: application/json" \
  -d '{"task":"打开微信给文件传输助手发消息：部署成功"}'
```

## API 参考

详见 [SKILL.md](SKILL.md)，包含完整 API 文档和 Python 集成示例。

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|---|---|---|---|
| `PHONE_AGENT_BASE_URL` | 是 | 模型 API 地址 | `http://localhost:8000/v1` |
| `PHONE_AGENT_MODEL` | 是 | 模型名称 | `autoglm-phone-9b` |
| `PHONE_AGENT_API_KEY` | 否 | API 密钥 | `EMPTY` |
| `PHONE_AGENT_PORT` | 否 | HTTP 端口 | `8000` |
| `PHONE_AGENT_ENABLE_THINKING` | 否 | 千问思考模式 | `false` |
| `PHONE_AGENT_MAX_STEPS` | 否 | 每任务最大步数 | `100` |
| `PHONE_AGENT_LANG` | 否 | 语言 (`cn`/`en`) | `cn` |

## 常见问题

| 问题 | 解决 |
|---|---|
| `adb devices` 无输出 | 检查数据线、USB 调试是否开启、手机上点「允许」 |
| 能打开应用但无法点击 | 开启「USB 调试（安全设置）」 |
| 文本输入不工作 | 安装并启用 ADB Keyboard |
| 截图黑屏 | 敏感页面（支付/银行）正常现象 |
| 容器反复重启 | 检查端口冲突，改 `PHONE_AGENT_PORT` |
| API 调用超时 | 改用异步 `/api/tasks` 端点 |

## 部署验收标准

1. ✅ `adb devices` 能看到设备
2. ✅ ADB Keyboard 已安装启用
3. ✅ `curl /api/health` 返回 `"status":"ok"`
4. ✅ 一个任务完整执行成功："打开微信给文件传输助手发消息：部署成功"
