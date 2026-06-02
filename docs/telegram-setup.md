# Telegram 配置指南

AI Girlfriend (四季夏目) 的 Telegram Bot 集成，基于 OpenClaw Gateway Telegram Channel。

## 前置要求

- 一个 Telegram 账号
- 通过 [@BotFather](https://t.me/BotFather) 创建一个 Bot，获取 Bot Token

## 配置步骤

### 1. 获取 Bot Token

1. 在 Telegram 中给 [@BotFather](https://t.me/BotFather) 发 `/start`
2. 发送 `/newbot`，按提示设置 Bot 名称和用户名
3. 复制 BotFather 返回的 Token（格式：`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`）

### 2. 应用 Telegram 配置

通过 OpenClaw Gateway 应用配置补丁。项目根目录下的 `config-telegram.json` 已提供配置模板。

**方式一：使用 config-telegram.json 补丁**

```powershell
# 替换 <YOUR_BOT_TOKEN> 为你的 Bot Token
openclaw gateway call config.patch.apply --json --params '{
  "patch": [
    {"path": "channels.telegram.enabled", "value": true},
    {"path": "channels.telegram.botToken", "value": "<YOUR_BOT_TOKEN>"},
    {"path": "channels.telegram.dmPolicy", "value": "pairing"},
    {"path": "channels.telegram.replyToMode", "value": "first"},
    {"path": "channels.telegram.historyLimit", "value": 50},
    {"path": "channels.telegram.linkPreview", "value": true},
    {"path": "channels.telegram.mediaMaxMb", "value": 100},
    {"path": "channels.telegram.actions.reactions", "value": true},
    {"path": "channels.telegram.actions.sendMessage", "value": true},
    {"path": "channels.telegram.reactionNotifications", "value": "own"},
    {"path": "channels.telegram.streaming", "value": "partial"}
  ]
}'
```

**方式二：手动编辑配置文件**

编辑 `~/.openclaw/openclaw.json`，在 `channels` 下添加：

```json5
{
  channels: {
    // ... 已有 qqbot 配置 ...
    telegram: {
      enabled: true,
      botToken: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz", // 替换为你的 token
      dmPolicy: "pairing",         // pairing: 首次私聊需配对码确认
      replyToMode: "first",        // 回复时引用第一条消息
      historyLimit: 50,            // 每次拉取的历史消息数
      linkPreview: true,           // 链接预览
      mediaMaxMb: 100,             // 媒体文件大小上限
      streaming: "partial",        // 流式输出（partial 模式）
      actions: {
        reactions: true,           // 允许发送 emoji reaction
        sendMessage: true,         // 允许发送消息
      },
      reactionNotifications: "own", // 只通知自己的消息被 reaction
    },
  },
}
```

### 3. 重启 OpenClaw Gateway

配置生效需要重启：

```powershell
openclaw gateway restart
```

### 4. 配对 DM

首次私聊 Bot 时，Bot 会返回一个配对码。在任意 OpenClaw 会话中输入配对码即可完成配对。

## 进阶配置

### 群组配置

```json5
{
  channels: {
    telegram: {
      // ... 基础配置 ...
      groups: {
        "*": { requireMention: true },   // 默认：所有群组需要 @bot 才响应
        "-1001234567890": {               // 特定群组 ID
          requireMention: false,           // 不需要 @ 也响应
          systemPrompt: "Keep answers brief.",
        },
      },
    },
  },
}
```

### 自定义命令

```json5
{
  channels: {
    telegram: {
      customCommands: [
        { command: "reset", description: "重置对话 / 角色扮演上下文" },
        { command: "generate", description: "AI 生成图片" },
        { command: "voice", description: "TTS 语音合成" },
      ],
    },
  },
}
```

### 多账号

```json5
{
  channels: {
    telegram: {
      defaultAccount: "main",
      accounts: {
        main: {
          botToken: "your-main-bot-token",
          dmPolicy: "pairing",
        },
        alt: {
          botToken: "your-alt-bot-token",
          dmPolicy: "open",       // 备用 bot 允许所有 DM
          allowFrom: ["*"],
        },
      },
    },
  },
}
```

### 网络代理

在需要代理的环境下（如中国大陆访问 Telegram API）：

```json5
{
  channels: {
    telegram: {
      apiRoot: "https://api.telegram.org",  // 或自建 Bot API 代理
      proxy: "socks5://127.0.0.1:10808",
      network: {
        autoSelectFamily: true,
        dnsResultOrder: "ipv4first",
      },
    },
  },
}
```

## 与 QQ Bot 并存

Telegram 和 QQ Bot 可以同时运行。两个 channel 配置独立，互不冲突。夏目的角色设定（SOUL.md / AGENTS.md）在所有 channel 下保持一致。

## Reference

参考了 [arlanrakh/talk-to-girlfriend-ai](https://github.com/arlanrakh/talk-to-girlfriend-ai) 的项目结构。该仓库使用 Telethon + FastAPI（User Client 模式），本项目使用 OpenClaw 内建的 Telegram Bot Channel（Bot API 模式），更轻量且与 OpenClaw 生态深度集成。

| 对比 | talk-to-girlfriend-ai | 本项目 |
|------|---------------------|--------|
| 接入方式 | Telethon User Client | OpenClaw Bot Channel |
| 语言栈 | Python FastAPI + TypeScript Agent | OpenClaw Gateway (native) |
| 配置 | .env + session string | openclaw.json (bot token) |
| LLM | Claude Sonnet (外部 API) | 本地 llama.cpp Qwen3.6 |
| TTS | 无 | 本地 GPT-SoVITS |
| 文生图 | 无 | 本地 ComfyUI |

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| Bot 不响应 | 检查 `openclaw gateway status` 查看 channel 状态 |
| 私聊无配对码 | 确认 `dmPolicy` 不为 `disabled`，检查 `openclaw doctor` |
| 群组不响应 | 确认群组 ID 在 `groups` 配置中，检查 `requireMention` |
| 无法访问 Telegram API | 在中国大陆需要配置代理 `proxy` 或自建 Bot API `apiRoot` |
| Token 无效 | 重新通过 @BotFather `/mybots` → API Token 获取 |
