# QQ Bot 配置指南

AI Girlfriend (四季夏目) 的 QQ Bot 集成，基于 OpenClaw Gateway QQ Bot Channel。

## 前置要求

- 一个 QQ 账号
- 在 [QQ 开放平台](https://q.qq.com/) 创建 QQ Bot 应用

## 配置步骤

### 1. 获取 QQ Bot 凭证

1. 打开 [QQ 开放平台](https://q.qq.com/)
2. 登录后进入「应用管理」→「创建机器人」
3. 选择**私域机器人**（支持论坛、帖子等完整功能）
4. 创建完成后，在应用详情页获取：
   - **AppID**（机器人 ID）
   - **ClientSecret**（机器人密钥）

### 2. 配置机器人权限

在 QQ 开放平台的应用管理页面：

1. **基本配置** → 填写机器人名称（如「四季夏目」）、头像、简介
2. **频道权限** → 申请需要的 API 权限：

| 权限 | 用途 |
|------|------|
| 获取频道信息 | 读取频道/子频道列表 |
| 发送消息 | 发送文字/图片/语音消息 |
| 获取成员信息 | 读取用户昵称、头像 |
| 论坛操作 | 发帖/评论（私域专属） |
| 消息反应 | Emoji reaction |

3. 将机器人添加到你的 QQ 频道中

### 3. 应用 QQ Bot 配置

项目根目录下的 `config-qqbot.json` 已提供配置模板。

**方式一：使用 config-qqbot.json 补丁**

```powershell
# 1. 修改 config-qqbot.json 中的占位符
#    <YOUR_QQ_APP_ID>         → 你的 AppID
#    <YOUR_QQ_CLIENT_SECRET>  → 你的 ClientSecret

# 2. 应用补丁（PowerShell）
$patch = Get-Content .\config-qqbot.json -Raw | ConvertFrom-Json
$params = @{ patch = @($patch) } | ConvertTo-Json -Depth 10 -Compress
$escaped = $params -replace '"','\"'
openclaw gateway call config.patch.apply --json --params $escaped

# 3. QQ Bot channel 配置热更新，无需重启
```

**方式二：手动编辑配置文件**

编辑 `~/.openclaw/openclaw.json`，在 `channels` 下添加：

```json5
{
  channels: {
    qqbot: {
      enabled: true,
      name: "四季夏目",             // 机器人名称
      appId: "123456789",           // 你的 AppID
      clientSecret: "your-secret",  // 你的 ClientSecret
      dmPolicy: "open",             // 私聊策略：open=全部允许, allowlist=白名单
      groupPolicy: "open",          // 群组/频道策略
      markdownSupport: true,        // Markdown 渲染
      streaming: {
        mode: "partial",            // 流式输出
      },
      urlDirectUpload: true,        // URL 直接上传媒体
      audioFormatPolicy: {
        sttDirectFormats: ["wav"],  // 语音识别支持的格式
        uploadDirectFormats: ["wav"], // 直接上传的音频格式
        transcodeEnabled: true,     // 音频转码
      },
      voiceDirectUploadFormats: ["wav"], // 语音直接上传格式
    },
  },
}
```

### 4. 验证配置

QQ Bot channel 支持热更新，配置保存后自动生效：

```powershell
# 查看 channel 状态
openclaw gateway status

# 应该看到 qqbot channel 状态为 healthy
```

在 QQ 频道中给机器人发消息测试。

## 进阶配置

### 群组/频道访问控制

```json5
{
  channels: {
    qqbot: {
      dmPolicy: "open",              // 允许所有私聊
      allowFrom: ["123456789"],      // 白名单用户（dmPolicy=allowlist 时生效）
      groupPolicy: "allowlist",      // 群组白名单模式
      groupAllowFrom: ["987654321"], // 允许响应的群组 ID
    },
  },
}
```

### 消息流式输出

```json5
{
  channels: {
    qqbot: {
      streaming: {
        mode: "partial",           // partial=流式输出, off=关闭
        c2cStreamApi: true,        // 私聊启用流式 API
      },
    },
  },
}
```

### 自定义命令

```json5
{
  channels: {
    qqbot: {
      customCommands: [
        { command: "reset", description: "重置对话 / 角色扮演上下文" },
        { command: "generate", description: "AI 生成图片" },
        { command: "voice", description: "TTS 语音合成" },
      ],
    },
  },
}
```

### 语音识别 (STT)

```json5
{
  channels: {
    qqbot: {
      stt: {
        enabled: true,
        provider: "openai",          // 或 deepseek / local
        model: "whisper-1",
      },
    },
  },
}
```

### 私域 vs 公域机器人

| 特性 | 私域机器人 | 公域机器人 |
|------|-----------|-----------|
| 论坛操作 | ✅ 支持 | ❌ 不支持 |
| 频道数量 | 不限 | 需审核 |
| 受众 | 仅自己的频道 | 可被其他频道添加 |
| 推荐 | **本项目推荐私域** | 如需公开使用 |

## 与 Telegram Bot 并存

QQ Bot 和 Telegram Bot 共享同一套角色设定（SOUL.md / AGENTS.md），夏目在两个平台上有相同的性格和行为。

配置互不冲突：
- `channels.qqbot.*` — QQ Bot 专属
- `channels.telegram.*` — Telegram Bot 专属
- 两者可同时启用，独立运行

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| 401 鉴权失败 | 检查 AppID 和 ClientSecret 是否正确 |
| 11241 无权限 | 前往 QQ 开放平台申请对应 API 权限 |
| 11242 非私域 | 将机器人切换为私域模式 |
| 11243 无管理权限 | 确保机器人在频道中有管理权限 |
| 机器人不回复 | 检查 `openclaw gateway status`，确认 qqbot channel 状态 |
| 群组不响应 | 检查 `groupPolicy` 和 `groupAllowFrom` 配置 |
