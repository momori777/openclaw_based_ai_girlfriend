# Live2D 桌面宠物控制 Skill

## 概述

通过 HTTP API 控制屏幕上的 Live2D 四季夏目模型，支持切换表情、播放动作、显示对话气泡。

Live2D Bridge 已在 `localhost:19200`（HTTP）+ `19201`（WebSocket）持续运行。
**本项目为纯 HTTP 调用，不杀 llama-server，不需要 spawn 子 session。**

## 先决条件

- Bridge 已由 sakura 项目自动启动
- 前端 `index.html` 已在浏览器中打开
- 模型: Shiki Natsume (四季夏目)

若 bridge 未运行：
```powershell
Start-Process node -ArgumentList "live2d-bridge.mjs" -WorkingDirectory "{{PROJECT_ROOT}}/live2d" -WindowStyle Hidden
```

## API 接口

所有接口为 `GET http://localhost:19200/api/<endpoint>?<params>`

### 切换表情 `/api/expression`
```
GET /api/expression?name=<expression_name>
```
可用值: `neutral`（默认）, `happy`, `sad`, `angry`, `surprised`, `exp_01` ~ `exp_05`

### 播放动作 `/api/motion`
```
GET /api/motion?name=<motion_name>
```
可用值: `idle`（默认待机）, `mtn_01`, `mtn_02`, `mtn_03`

### 显示对话气泡 `/api/message`
```
GET /api/message?text=<URL编码文本>&duration=<毫秒>
```
duration 默认 5000ms。气泡在模型上方显示。

### 口型同步 `/api/speak`
```
GET /api/speak?action=start&text=<文本>
GET /api/speak?action=end
```
控制嘴部开合动画。`start` 开始说话口型，`end` 关闭。

### 组合控制 `/api/emotion`
```
GET /api/emotion?expression=<>&motion=<>&text=<>
```
一次调用同时设置表情、动作和文本。参数均为可选。

### 重置 `/api/reset`
```
GET /api/reset
```
恢复默认表情动作，清除气泡。

### 状态检查 `/api/status`
```
GET /api/status
```
返回 `{"ok":true,"clients":<N>,"uptime":<seconds>}`。clients≥1 表示前端已连接。

## 调用方式

直接用 `exec` 的 `curl` 或 PowerShell Invoke-WebRequest：

```powershell
# 表情
Invoke-WebRequest -Uri "http://localhost:19200/api/expression?name=happy" -Method GET | Out-Null

# 动作 + 文本
Invoke-WebRequest -Uri "http://localhost:19200/api/emotion?motion=mtn_01&text=おかえりなさい" -Method GET | Out-Null
```

**不需要 sessions_spawn！** Live2D bridge 是独立进程，不影响 llama-server。

## 流式 TTS 联动

当同时需要 TTS + Live2D 口型时：
1. 先 HTTP GET `/api/speak?action=start&text=<文本>` — 开启口型
2. 正常 spawn TTS 子 session 合成语音
3. TTS 播放完成后 HTTP GET `/api/speak?action=end` — 关闭口型

## 项目文件

```
{{PROJECT_ROOT}}/live2d/
├── index.html           # Live2D 前端页面
├── live2dcubismcore.min.js  # Cubism Core 4 (207KB) — 必须用此版本！
├── plid-v5-bundle.js    # pixi-live2d-display v0.5.0 bundle
├── live2d-bridge.mjs    # HTTP + WebSocket bridge
├── pixi-shim.js         # PIXI UMD shim
├── model/shiki_natsume/ # 四季夏目模型
└── core/                # SDK 源码（参考用）

D:\skills_backup\live2d\browser\  # 验证通过的文件备份
├── index.html
├── live2dcubismcore.min.js  # Core 4 CDN: cubism.live2d.com/sdk-web/cubismcore/
└── plid-v5-bundle.js
```

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 模型图层错乱/缺失 | Core 版本 6.0.1 不兼容 | 用 Core 4 (207KB)，从 CDN 下载 |
| /api/status 返回 0 clients | 前端未打开 | 浏览器打开 index.html |
| Bridge 进程不在 | sakura 未启动 | 手动 `node live2d-bridge.mjs` |
