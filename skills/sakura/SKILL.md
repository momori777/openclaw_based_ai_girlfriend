# Sakura Desktop Pet — AI 桌宠 Agent 框架

## 概述

Sakura 是一个开源的桌面宠物 Agent 框架，由 [Rvosy](https://github.com/Rvosy) 开发。
项目地址：https://github.com/Rvosy/Sakura
当前版本：v0.9.6-dev
已获作者授权引用（Issue #38，momori777/TK 询问，Rvosy 回复"可以的"）。

**核心概念：** Sakura 不是传统聊天机器人（需要你先开口），而是**会主动找你的桌宠**。
她会在角落里观察你的屏幕，偶尔觉得该说点什么的时候自己开口——比如看到你打游戏死了三次，凑过来问"要不要帮你查攻略？"

**技术架构：**
- UI 层：PySide6（Qt for Python）桌宠窗口、立绘动画、字幕气泡、设置面板
- Agent 层：AgentRuntime 决策引擎，使用 OpenAI 兼容接口原生 `tool_calls` 协议
- **LLM 层（已改造）**：默认使用本地 llama-server (Qwen3.6-35B)，带 llama 生命周期感知重试 + 远程 fallback
- **本地 LLM 适配器**：`app/llm/local_llama_client.py` — 当 TTS/ComfyUI 杀死 llama 时自动指数退避重试（最长 126s），重试耗尽后自动切换远程 fallback
- 语音层：GPT-SoVITS TTS，支持声线切换和语气联动
- 记忆层：mem0 长期记忆 + Qdrant 向量存储 + sentence-transformers 嵌入
- 插件层：原生 Python 插件系统 + MCP Server 支持
- 工具层：待办/提醒/笔记/记忆/浏览器/桌面/屏幕观察等内置工具

**分段双语回复协议：** 模型输出分段 JSON，每段包含日文原文、中文字幕、语气标签和立绘标识。
UI 同步驱动字幕、表情和语音。

## 项目结构

```
D:\AI_Girlfriend\skills\sakura\
├── main.py                    # 应用入口（QApplication + 启动流程）
├── install.bat                # Windows 依赖安装脚本
├── start.bat                  # Windows 一键启动脚本
├── requirements.txt           # Python 依赖
├── app/
│   ├── agent/                 # Agent 决策层
│   │   ├── runtime.py         # AgentRuntime：核心决策 + tool_calls 循环
│   │   ├── builtin_tools.py   # 内置工具（todo/reminder/notes/memory/screen）
│   │   ├── memory.py          # 长期记忆（mem0 + Qdrant）
│   │   ├── reminders.py       # 提醒调度
│   │   ├── proactive_care.py  # 主动关怀（周期性观察 + 主动搭话）
│   │   ├── screen_policy.py   # 屏幕观察策略
│   │   ├── screen_tools.py    # 屏幕截图/观察工具
│   │   ├── screen_observation.py  # 屏幕观察入口
│   │   ├── desktop_tools.py   # 桌面操作（打开URL/文件夹）
│   │   ├── tool_policy.py     # 工具路由/权限策略
│   │   ├── tools/             # 统一工具注册系统
│   │   └── mcp/               # MCP 工具桥接/配置
│   ├── core/                  # 应用核心
│   │   ├── app_context.py     # AppContext 依赖容器
│   │   ├── bootstrap.py       # 启动装配
│   │   ├── chat_pipeline.py   # 对话编排管线
│   │   ├── chat_worker.py     # Qt 后台线程 Worker
│   │   └── debug_log.py       # 调试日志（自动脱敏 API Key）
│   ├── config/                # 配置管理（YAML 读写、角色包加载、迁移）
│   ├── llm/                   # LLM 客户端
│   │   ├── api_client.py      # OpenAI 兼容客户端
│   │   ├── chat_reply.py      # 分段回复 JSON 解析
│   │   ├── prompts/           # 提示词模板/渲染
│   │   └── prompt_templates.py
│   ├── plugins/               # 原生插件系统
│   │   ├── manager.py         # 插件管理器
│   │   ├── discovery.py       # 插件发现
│   │   └── adapters.py        # SDK 兼容适配
│   ├── storage/               # 存储层（聊天历史 JSONL、视觉观察记录）
│   ├── ui/                    # UI 组件
│   │   ├── pet_window.py      # 桌宠主窗口（150KB+，最复杂的UI组件）
│   │   ├── settings_dialog.py # 设置对话框（125KB+）
│   │   ├── history_window.py  # 聊天历史回看
│   │   ├── portrait_controller.py  # 立绘切换控制
│   │   ├── subtitle_controller.py  # 字幕气泡显示
│   │   ├── tool_confirmation_panel.py  # 工具权限确认面板
│   │   └── tray_menu.py       # 系统托盘菜单
│   └── voice/                 # 语音服务
│       ├── tts.py             # GPT-SoVITS TTS Provider
│       ├── tts_bundle.py      # TTS 整合包管理
│       └── playback_controller.py  # 语音播放控制
├── sdk/                       # 插件 SDK
│   ├── plugin.py              # PluginBase 基类
│   ├── register.py            # PluginCapabilityRegistry
│   ├── types.py               # 贡献点类型定义
│   └── tool_registry.py       # 工具注册器
├── plugins/                   # 本地插件目录
│   ├── playwright_browser/    # Playwright 浏览器自动化插件
│   └── example_plugin/        # 示例插件
├── data/
│   └── config/                # YAML 配置文件
│       ├── api.yaml           # API Key / Base URL / 模型配置
│       ├── system_config.yaml # 系统配置（UI、主动关怀、调试等）
│       ├── characters.yaml    # 角色选择
│       ├── mcp.yaml           # MCP Server 配置
│       └── plugins.yaml       # 插件启停/优先级
├── scripts/                   # 安装/启动脚本（macOS/Linux）
├── tests/                     # pytest 测试（unit / integration / ui）
├── tools/mcp/                 # MCP Server 运行时
│   └── Windows-MCP-0.8.0/     # Windows MCP Server
├── third_party/mem0/          # 第三方 mem0 分支
├── docs/                      # 文档
│   ├── TECHNICAL_README.md    # 技术讲解
│   ├── SAKURA_PLUGIN_SDK.md   # 插件开发 SDK 文档
│   └── README.zh.md / README.en.md
└── assets/                    # 项目预览图
```

## 核心功能详解

### 1. 角色包驱动

角色通过 `characters/<id>/character.json` 定义，包含：
- **角色卡** (`card.md`)：人格设定、对话风格、世界观
- **立绘** (`portraits/`)：多表情立绘图片
- **语音** (`voice/`)：GPT-SoVITS 声线权重（`.ckpt` / `.pth`）+ 参考音频

角色包通过设置页导入/导出。

### 2. Agent 决策引擎 (AgentRuntime)

`app/agent/runtime.py` 是核心。使用 OpenAI 兼容接口的 `tool_calls` 协议：

```
用户输入/主动事件 → ChatPipeline → AgentRuntime
  → LLM 决策（文本回复 or 调用工具）
  → 工具执行 + 结果回填
  → LLM 最终回复（分段 JSON）
  → UI 同步驱动字幕 + 立绘 + TTS
```

回复格式（分段 JSON）：
```json
{
  "segments": [
    {
      "text_ja": "日文原文",
      "text_zh": "中文字幕",
      "tone": "casual|tsundere|romantic|...",
      "portrait": "portrait_id"
    }
  ]
}
```

### 3. 主动关怀 (Proactive Care)

定时检查上下文，主动发起对话：
- 屏幕观察结果
- 时间/日期变化
- 用户行为模式
- 通过 `data/config/system_config.yaml` 配置间隔和冷却

### 4. 屏幕观察

- 按需截图（用户说"看屏幕"/"观察屏幕"）
- 自主屏幕观察（Agent 认为需要时）
- 支持手动框选截图
- 视觉摘要纳入对话上下文

### 5. 工具系统

内置工具（`app/agent/builtin_tools.py`）：

| 工具名 | 功能 |
|--------|------|
| `observe_screen` | 屏幕截图观察 |
| `get_current_time` | 获取当前时间 |
| `add_todo` / `list_todos` / `complete_todo` | 待办事项管理 |
| `add_reminder` / `list_reminders` / `cancel_reminder` | 提醒管理 |
| `create_note` / `update_note` / `delete_note` | 笔记管理 |
| `memory_find` / `memory_add` / `memory_list` | 长期记忆操作 |
| `open_url` | 打开浏览器 URL |

MCP 工具：
- **Web Search**：内置 Web 搜索 MCP Server
- **Windows MCP**：桌面自动化（截图、点击、输入等）

插件工具：通过 `plugins/` 目录加载（如 Playwright 浏览器插件）

**权限确认：** 高风险工具（如桌面操作）需要用户确认后才执行。

### 6. 长期记忆

使用 mem0 + Qdrant 向量存储：
- 记忆先进入候选区
- 确认后写入正式记忆
- 支持自动整理（`memory_curator.py`）
- 通过 `HF_HOME` 环境变量缓存嵌入模型到 `runtime/hf-cache/`

### 7. TTS 语音

GPT-SoVITS 服务架构：
```
Sakura → POST /tts → GPT-SoVITS API → WAV 音频 → PyAudio 播放
```

支持：
- Windows 内置整合包一键下载
- macOS/Linux 自定义 GPT-SoVITS 路径
- 声线权重切换（按角色加载不同模型）
- 语气联动参考音频选择

### 8. 插件系统

插件是进程内运行的 Python 扩展，贡献点包括：
- **工具注册**：为 Agent 添加可调用工具
- **设置页面**：自定义设置面板
- **聊天 UI Widget**：输入栏扩展组件
- **提示词补丁**：修改系统提示词和回复协议
- **工具页签**：设置窗口的"工具"页

见 `docs/SAKURA_PLUGIN_SDK.md` 了解完整插件开发方式。

## LLM 后端架构（已改造为本地优先）

### 改造动机

上游 Sakura 默认调用远程 API（如 GemAI Gemini Flash）。为与 AI_Girlfriend 项目整体风格一致——**所有技能共用一颗大脑（llama-server Qwen3.6-35B）**——已将默认 LLM 后端改为本地 llama-server。

### 改造内容

1. **`app/llm/local_llama_client.py`** — 新增本地 LLM 适配器：
   - 默认 URL：`http://localhost:8080/v1`（llama-server）
   - 默认模型：`qwen3.6-35b`
   - llama 不可用时指数退避重试（2s→4s→8s→16s→32s→64s，总计 ~126s）
   - 检测到 TTS/ComfyUI 杀死 llama 时不报错，静默等待重试
   - 重试耗尽后自动切换远程 fallback API
   - 重试间 llama 恢复后自动切回本地

2. **`app/config/settings_service.py`** — 默认配置改为本地：
   - `base_url` 默认值：`http://localhost:8080/v1`（原为 `https://api.openai.com/v1`）
   - `model` 默认值：`qwen3.6-35b`（原为 `gpt-4.1-mini`）
   - `timeout_seconds` 默认值：120（原为 60，给 llama 推理更长时间）

3. **`app/core/bootstrap.py`** — 启动时创建 `LocalLlamaClient` 而非原始 `OpenAICompatibleClient`
   - 若 `api.yaml` 配置了非本地 URL，自动设为远程 fallback
   - MemoryStore/MemoryCurator/AgentRuntime 仍然使用相同的 `.chat()/.complete_raw()/.complete_with_tools()` 接口

### 数据流

```
┌─────────────────────────────────────────────────────┐
│ Sakura (PySide6 GUI)                                 │
│                                                       │
│  AgentRuntime ──→ LocalLlamaClient ──→ llama-server  │
│       │                    │           :8080/v1        │
│       │                    │  ┌─ fail (TTS running)   │
│       │                    │  │  retry 2s, 4s, 8s...  │
│       │                    │  └─ llama back → success  │
│       │                    │                           │
│       │              fallback (if >126s)               │
│       │                    └──→ remote API (GemAI)     │
│       │                                                │
│  ┌────┴─────── TTS GPU 推理 ────────┐                 │
│  │ Sakura 自己的 TTS 也杀 llama    │                 │
│  │ 但 LocalLlamaClient 会自动等    │                 │
│  └────────────────────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

### 共用 llm-server 的三方协调

| 组件 | 何时占用 llama | 协调方式 |
|------|---------------|---------|
| OpenClaw Agent | 持续占用 | 主 session 的 LLM |
| TTS/ComfyUI | 需要 GPU 推理时 kill llama | `run_tts.ps1` / `run_comfyui.ps1` 停/启 llama |
| Sakura | 发送对话请求 | `LocalLlamaClient` 自动重试等待 llama 恢复 |

Sakura 的 `LocalLlamaClient` 不需要自己 kill/restart llama —— 它只是被动等待。
当 TTS/ComfyUI 正在运行时，Sakura 的 LLM 请求会排队等待（指数退避），llama 恢复后自动继续。

### 回退到纯远程 API

若想用回远程 API（不通过本地 llama）：编辑 `data/config/api.yaml`：
```yaml
llm:
  base_url: https://api.gemai.cc/v1
  api_key: your_key_here
  model: gemini-2.0-flash
```
此时 `LocalLlamaClient` 检测到非本地 URL，自动将远程 API 作为唯一后端（不经过 llama）。

## 配置说明

所有配置在 `D:\AI_Girlfriend\skills\sakura\data\config\` 下：

### api.yaml
```yaml
llm:
  # 默认不配置 → 自动使用本地 llama-server (http://localhost:8080/v1, qwen3.6-35b)
  # 配置远程 API 后 → 本地 llama 不可用时自动 fallback
  base_url: http://localhost:8080/v1    # 本地 llama-server
  api_key: local                        # llama-server 不需要 key
  model: qwen3.6-35b                    # 本地模型
  timeout_seconds: 120                  # 本地推理较慢，给足时间
tts:
  enabled: true
  provider: gpt-sovits
  gpt_sovits:
    api_url: http://127.0.0.1:9880/tts
```

### system_config.yaml
```yaml
ui:
  subtitle_language: zh        # 字幕语言 ja/zh
  portrait_scale_percent: 100  # 立绘缩放
proactive_care:
  enabled: true                 # 主动关怀开关
  check_interval_minutes: 20   # 检查间隔
  cooldown_minutes: 10         # 冷却时间
mcp:
  windows_enabled: false        # Windows 桌面自动化 MCP
debug:
  enabled: false                # 调试日志（自动脱敏 API Key）
```

## 在 AI_Girlfriend 项目中的位置

Sakura 是 AI_Girlfriend 项目的三个核心 skill 之一：

| Skill | 位置 | 功能 |
|-------|------|------|
| **comfyui** | `D:\AI_Girlfriend\skills\comfyui\` | 文生图（WAII 模型 + ComfyUI API） |
| **tts** | `D:\AI_Girlfriend\skills\tts\` | 语音合成（GPT-SoVITS + 14种情绪参考音频） |
| **sakura** | `D:\AI_Girlfriend\skills\sakura\` | 桌宠 Agent 框架（完整 AI 女友客户端） |

Sakura 提供了一个完整的 GUI 桌面宠物体验，集成了 LLM 对话、TTS 语音、屏幕观察、长期记忆等功能。AI_Girlfriend 项目可以：
1. 直接使用 Sakura 作为 AI 女友的桌面客户端
2. 参考 Sakura 的 Agent 架构（AgentRuntime、工具系统、分段回复协议）来构建自己的 Agent
3. 复用 Sakura 的 TTS 整合（GPT-SoVITS 服务管理、声线切换）
4. 学习 Sakura 的主动关怀和屏幕观察机制

## 快速启动（Windows）

```powershell
# 1. 安装依赖
cd D:\AI_Girlfriend\skills\sakura
.\install.bat

# 2. 编辑 API 配置
notepad data\config\api.yaml

# 3. 启动
.\start.bat
```

## 注意事项

1. **路径要求：** PySide6 不支持非 ASCII 路径。Sakura 当前路径 `D:\AI_Girlfriend\skills\sakura` 符合要求（全英文）。
2. **Python 环境：** `start.bat` 会优先使用 `runtime\python.exe`，不存在时使用系统 Python。Release 完整包自带 `runtime/`。
3. **模型要求：** 必须使用多模态模型（如 Gemini Flash）。DeepSeek 系列不支持视觉，会导致屏幕观察等功能失效。
4. **HF 缓存：** `start.bat` 设置 `HF_HOME` 和 `SENTENCE_TRANSFORMERS_HOME` 到 `runtime/hf-cache/`，避免重复下载嵌入模型。
5. **角色包：** 需要从 GitHub Releases 或百度网盘下载角色包（含立绘和声线权重），通过设置页导入。
6. **Git 子模块：** 本项目是 `sakura` 源码的完整克隆（非 git submodule），放在 `D:\AI_Girlfriend\skills\sakura\` 下。
7. **授权状态：** 作者 Rvosy 已在 Issue #38 中同意引用（"可以的，这段时间太忙没时间加开源协议，之后会给项目加一个相对宽松一点的开源协议"）。

## 致谢

- **原作者/贡献者**：[@Rvosy](https://github.com/Rvosy) — Sakura Desktop Pet 项目创建者，已授权本项目引用（Issue #38）
- **LLM 本地化改造**：TK (momori777) — 将默认 LLM 后端改为本地 llama-server，使 Sakura 与 AI_Girlfriend 项目共用同一颗大脑

## 相关链接

- 项目主页：https://github.com/Rvosy/Sakura
- Releases 下载：https://github.com/Rvosy/Sakura/releases
- 角色包网盘：https://pan.baidu.com/s/5ZXvAi6n6i7-OJAYeWDpprg
- API 中转站推荐：https://api.gemai.cc/register?aff=rwbQ
- Issue #38（授权记录）：https://github.com/Rvosy/Sakura/issues/38
- AI_Girlfriend 项目：https://github.com/momori777/openclaw_based_ai_girlfriend
