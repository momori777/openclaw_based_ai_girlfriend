# Live2D 角色显示 — 夏目

> **当前状态：升级到 pixi-live2d-display v0.5.0-beta + Cubism SDK 5-r.5。mask 渲染由官方 Cubism 5 ClippingManager 处理，理论正常。待浏览器端肉眼验证。**
> 表情切换 API 正常，WS 通信正常，动画（眨眼/呼吸/鼠标追踪）正常。

## 架构

```
OpenClaw ──HTTP(GET)──→ bridge :19200 ──broadcast WS──→ 浏览器 :19200
                              :19201 ←────────connected────────┘
```

- Bridge: `D:\AI_Girlfriend\live2d\live2d-bridge.mjs` (Node.js)
- 前端: `D:\AI_Girlfriend\live2d\index.html`
- 模型: `D:\AI_Girlfriend\live2d\model-hack\ren.model3.json` (moc3 ver6→ver5 hacked)
- 启动: `D:\AI_Girlfriend\live2d\start-live2d.ps1`

## 启动 / 检查

```powershell
# 启动 bridge（后台运行）
Start-Process -WindowStyle Hidden -FilePath "node" -ArgumentList "live2d-bridge.mjs" -WorkingDirectory "D:\AI_Girlfriend\live2d"

# 检查状态
curl http://localhost:19200/api/status
# → {"ok":true,"clients":1,"uptime":123.45}

# 打开浏览器看模型
# 浏览器访问 http://localhost:19200
```

## API 参考

**所有接口 HTTP GET，参数通过 query string。**

### 表情切换

```
GET /api/expression?name=<name>
```

| 参数名 | 可用值 |
|--------|--------|
| exp_01 / neutral | 中性（默认） |
| exp_02 / happy | 微笑 |
| exp_03 / sad | 闭眼/悲伤 |
| exp_04 / angry | 生气 |
| exp_05 / surprised | 惊讶 |

```powershell
curl "http://localhost:19200/api/expression?name=happy"
curl "http://localhost:19200/api/expression?name=angry"
```

### 情绪 + 文字组合（最常用）

```
GET /api/emotion?expression=<name>&text=<文字>&motion=<动作>
```

```powershell
curl "http://localhost:19200/api/emotion?expression=happy&text=いいね！"
curl "http://localhost:19200/api/emotion?expression=angry&text=バカ！"
curl "http://localhost:19200/api/emotion?expression=surprised&text=えっ！？"
```

### 说话（嘴型同步）

```
GET /api/speak?action=start&text=<显示文字>   # 开始嘴型动画
GET /api/speak?action=end                     # 停止
```

```powershell
curl "http://localhost:19200/api/speak?action=start&text=おはよう"
# 等语音播完...
curl "http://localhost:19200/api/speak?action=end"
```

### 纯文字消息（无嘴型）

```
GET /api/message?text=<文字>&duration=<毫秒>
```

### 动作

```
GET /api/motion?name=<name>
```

### 重置

```
GET /api/reset   # 回中性表情 + 清文字 + 停嘴型
```

## 和 TTS 联动

```
1. curl /api/emotion?expression=<情绪>&text=<显示文字>    # 设表情
2. curl /api/speak?action=start&text=<文字>               # 开始嘴型
3. sessions_spawn tts 子 session                          # 执行 TTS
4. 发 MEDIA: 语音文件                                      # 发送语音
5. 等待 TTS 时长后 curl /api/speak?action=end             # 停嘴型
```

## 和 ComfyUI 联动

```
1. curl /api/emotion?expression=happy&text=ちょっと待ってて…
2. sessions_spawn comfyui 子 session
3. 图片生成完毕
4. curl /api/emotion?expression=surprised&text=これ、どう？
```

## 调用原则

| ✅ 应该用 | ❌ 不该用 |
|-----------|----------|
| 情绪转折点 | 每条消息都切表情 |
| 发 TTS 语音时 | 普通聊天中间频繁切 |
| 撒娇/亲昵时刻 | 和角色性格不符的夸张表情 |
| 用户刚连上时 | 沉默场景 |

## 已知问题

1. **renderer.doDrawModel 偶尔报 `Cannot read properties of undefined (reading '0')`** — v0.5 的 Cubism4 渲染器在处理某些 drawable 顶点数据时可能读取失败，但不影响整体渲染
2. **Motion API 待验证** — v0.5 beta 的 motion API 与 v0.3 可能不完全兼容
3. **不需要 moc3 hack** — Cubism SDK 5-r.5 原生支持 ver6 moc3；当前 model-hack 是 ver5 降级版

## 构建流程

1. 确保 `node_modules/pixi-live2d-display@0.5.0-beta` 已安装
2. 运行 `node build-bundle.cjs` 生成 `plid-v5-bundle.js`
3. `index.html` 加载顺序: PixiJS → Cubism2Shim → CubismCore5 → PIXI-bridge → plid-v5-bundle

## 技术栈

```
浏览器端:
  PIXI.js v7.4.2 (CDN)
  pixi-live2d-display v0.5.0-beta (本地 bundle, esbuild IIFE)
  Cubism Core 5-r.5 (本地 SDK)
  Cubism 2 Shim (内联 <script>)
  @pixi/* proxy → window.PIXI bridge (内联 <script>)

构建:
  esbuild: umd-entry.mjs → plid-v5-bundle.js
  入口: node build-bundle.cjs

Bridge:
  Node.js + ws
  HTTP static serve + API routing
  WS broadcast
```
