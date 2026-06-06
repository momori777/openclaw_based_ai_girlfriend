# AI 女友 — 四季夏目 (Shiki Natsume)

**100% 本地部署 · 完全私有化 · 零 API 依赖**

> 所有对话、语音、图片都在你自己的电脑上生成。没有云服务器，没有第三方 API，没有数据泄露风险。你的 AI 女友，只属于你。

---

基于 OpenClaw + QQ Bot + llama.cpp + GPT-SoVITS + ComfyUI 的 AI 女友项目，完全运行在你自己的电脑上。

角色：**四季夏目**（Shiki Natsume），出自《星月咖啡馆与死之蝶》。高挑、冷淡，外冷内热。设定为「女友体验」角色扮演 — 她来主导。

## ✨ 为什么选这个项目？

| 对比 | 云端 AI 女友 | 本项目 |
|------|-------------|--------|
| 🛡️ **隐私** | 聊天记录、语音、图片全在厂商服务器 | **一切都在你本地**，没有任何数据离开你的电脑 |
| 💰 **费用** | 按月订阅 / token 计费，长期不菲 | **免费**，一次部署永久使用（自备硬件） |
| 🌐 **网络** | 依赖网络，服务器宕机就无法使用 | **断网也能聊**，睡前一键关闭 WiFi 更安心 |
| 🎛️ **可控性** | prompt/template 由厂商掌控，随时被改 | **你完全控制**所有模型、参数、角色设定 |
| 🔞 **内容** | 审查严格，动不动封号 | **无审查**，你想聊什么就聊什么 |
| 🎨 **扩展性** | 只能使用厂商提供的模型和功能 | **自由组合** — 换 LLM、换画图模型、换语音模型 |

## 🎬 演示

![QQ Bot Demo](media/demo_qqbot.gif)

> 👆 QQ Bot 实机演示：文字聊天 + TTS 语音 + ComfyUI 画图 + 角色记忆

## 硬件配置

| 组件 | 型号 |
|------|------|
| GPU | NVIDIA GeForce RTX 5070 Laptop (8 GB VRAM) |
| CPU | Intel Core i9-14900HX (24 核, 32 线程) |
| 内存 | 32 GB DDR5 |
| 系统 | Windows 11 |

## 功能特性

- 💬 **QQ + Telegram 双通道** — 通过 OpenClaw Gateway 集成 QQ Bot + Telegram Bot
- 🎤 **TTS 语音合成** — 本地 GPT-SoVITS 推理，日语语音（14 条参考音频）
- 🎨 **AI 图片生成** — 本地 ComfyUI 推理，SDXL/Illustrious 模型
- 🧠 **显存调度** — 8 GB 显存下自动协调 llama-server ↔ TTS/ComfyUI
- 💾 **角色记忆** — 对话摘要持久化到 `memory/role_play/`

## 模型

所有模型托管在 HuggingFace：**[TAOTAO777/ai-girlfriend-natsume](https://huggingface.co/TAOTAO777/ai-girlfriend-natsume)**

详见 [`models.yaml`](models.yaml)。

| 模型 | 用途 | 大小 |
|------|------|------|
| **Qwen3.6-35B-A3B-APEX-I-Compact** (Q4_K GGUF) | 聊天 LLM | 16.11 GB |
| **WAI-Nsfw-Illustrious-17** | ComfyUI 生图（默认） | 6.46 GB |
| **miaomiaoHarem_v20** | ComfyUI 生图（备用） | 6.46 GB |
| **GPT-SoVITS 语音权重** | TTS 语音合成 | ~303 MB |

### 一键下载

```powershell
# 安装 huggingface-cli：pip install huggingface_hub
huggingface-cli login

# 下载全部模型
huggingface-cli download TAOTAO777/ai-girlfriend-natsume --local-dir ./models

# 或者按组件单独下载：
huggingface-cli download TAOTAO777/ai-girlfriend-natsume llm/ --local-dir ./models
huggingface-cli download TAOTAO777/ai-girlfriend-natsume comfyui-checkpoints/ --local-dir ./checkpoints
huggingface-cli download TAOTAO777/ai-girlfriend-natsume gpt-sovits-weights/ --local-dir ./gpt-sovits-weights
```

如果 HuggingFace 被墙，可以去度盘下载：https://pan.baidu.com/s/1sLeSyVp76yzWcR3Q4pX0kA?pwd=0721

### 本地路径

按照 `models.yaml` 放置下载好的文件。脚本中的绝对路径需要改成你自己的路径。

> ⚠️ **免责声明**：所有模型均为社区开源模型。本项目仅提供镜像分发，非盈利性质。版权归原作者所有。

## 本地 LLM 性能

通过 llama.cpp (b8851-b9222) 运行 Qwen3.6-35B-A3B (MoE, Q4_K, 16.10 GiB, 34.66B 参数)。

### 启动命令

```powershell
llama-server.exe `
  -m "Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf" `
  -c 120000 `
  --flash-attn on -ctk q8_0 -ctv q8_0 `
  -ngl 41 --cpu-moe --cpu-mask 0xFFFFFFFF `
  --batch-size 4096 --ubatch-size 2048 --threads 24 `
  --api-key *** -rea off --jinja `
  --cache-ram 2048 --parallel 1 `
  --kv-unified --no-mmap
```

### 关键指标

| 指标 | 数值 | 备注 |
|------|------|------|
| 显存占用 | ~4.6 GiB（模型）+ ~1.2 GiB（KV 缓存） | 8 GB 显存下约剩 2 GB |
| 预填充速度 | **960 ~ 1390 t/s** | 120K 上下文，batch-size 4096 |
| 生成速度 | **31 ~ 39 t/s** | MoE 架构，8/256 专家 |
| 上下文长度 | 120K（约 12 万 token） | 处理 5.9 万 token 约需 55 秒 |
| 模型加载时间 | ~12 秒 | --no-mmap，需充足内存 |

### 长上下文稳定性

Qwen3.6 MoE 使用 SSM（门控 Delta 网络）混合注意力，配合 `--kv-unified`。

⚠️ **已知限制**：不支持跨轮 prompt 缓存复用（SSM 架构限制）。每次请求会触发完整上下文重处理。对话越长 → 首 token 延迟越高（5.9 万 token 约 55 秒）。

**缓解措施**：
- 定期 `/reset`（夏目会在重置前将角色扮演摘要写入 `memory/role_play/`）
- 启动时从摘要恢复上下文，将实际 token 数控制在 5K–20K 范围
- `config-patch.json` 将 OpenClaw contextWindow 设为 262144 以匹配模型容量

### 显存预算

```
8 GB 总显存
├── llama-server 常驻：~5.8 GB（模型 4.6G + KV 缓存 1.2G）
├── 空闲：~2.2 GB
│
├── TTS 推理：停止 llama → ~8 GB 空闲 → 恢复 llama（~70 秒）
└── ComfyUI 生图：停止 llama → ~8 GB 空闲 → 恢复 llama（~120 秒）
```

## 目录结构

```
AI_Girlfriend/                        # OpenClaw 工作区根目录
├── configure.ps1                     # 🛠 交互式路径配置向导（自动替换所有路径）
├── config.json                       # configure.ps1 生成的配置文件
├── download-models.ps1               # 一键模型下载（Windows）
├── download-models.sh                # 一键模型下载（Linux/macOS）
├── setup-llama.ps1                   # 自动检测硬件 + 配置 llama.cpp（Win）
├── setup-llama.sh                    # 自动检测硬件 + 配置 llama.cpp（Linux/macOS）
├── setup-openclaw.ps1                # 一键 OpenClaw 安装 + 部署（Win）
├── setup-openclaw.sh                 # 一键 OpenClaw 安装 + 部署（Linux/macOS）
├── setup-all.ps1                     # 🚀 一键全家桶脚本（Windows）
├── setup-all.sh                      # 🚀 一键全家桶脚本（Linux/macOS）
├── config-qqbot.json                 # QQ Bot 配置补丁
├── config-telegram.json              # Telegram Bot 配置补丁
├── config-patch.json                 # OpenClaw LLM 配置补丁
├── AGENTS.md                         # 代理行为规则
├── SOUL.md                           # 角色性格设定
├── IDENTITY.md                       # 角色身份
├── USER.md                           # 用户信息（请修改成你自己的）
├── HEARTBEAT.md                      # 心跳配置
├── TOOLS.md                          # 工具速查
├── models.yaml                       # 模型目录 + 下载链接
├── README.md                         # 项目说明（英文版）
├── README_zh.md                      # 本文件（中文版）
├── .gitignore
├── live2d/                           # 🚧 Live2D 角色可视化（尚未正式实装）
├── ren_pro_jp/                       # Ren'Py 对话引擎（配套 Live2D，未实装）
├── memory/                           # [.gitignore] 运行时记忆
│   └── role_play/                    # 角色扮演对话记录
├── media/qqbot/                      # [.gitignore] 生成的媒体文件
│   ├── audio/                        # TTS 语音输出
│   └── images/                       # ComfyUI 图片输出
├── docs/
│   ├── telegram-setup.md             # Telegram Bot 配置指南
│   └── qqbot-setup.md                # QQ Bot 配置指南
└── skills/
    ├── tts/
    │   ├── SKILL.md                  # TTS 调用指南
    │   ├── run_tts.ps1               # TTS 启动脚本
    │   ├── tts_call.py               # GPT-SoVITS 推理（含 llama 启停）
    │   └── ref_wavs/                 # 参考音频（14 条按情绪分类，请自备）
    ├── comfyui/
    │   ├── SKILL.md                  # ComfyUI 调用指南
    │   ├── run_comfyui.ps1           # ComfyUI 启动脚本
    │   ├── comfyui_call.py           # ComfyUI 推理（含 llama 启停）
    │   ├── prompt_template.md        # 角色 prompt 模板
    │   ├── custom_prompt.txt         # 自定义额外 prompt
    │   ├── apron_negative.txt        # 围裙场景负面 prompt
    │   └── apron_prompt.txt          # 围裙场景正面 prompt
    ├── llama-management.md           # 显存管理架构文档
    ├── llama-watchdog.ps1            # Llama 健康检查
    └── cleanup_orphans.ps1           # 孤儿进程/锁/会话清理
```

## 环境依赖

| 组件 | 版本 / 来源 | 用途 |
|------|------------|------|
| [OpenClaw](https://docs.openclaw.ai) | 最新版 | AI 代理网关 |
| QQ Bot | OpenClaw qqbot channel | QQ 消息中转 |
| Telegram Bot | OpenClaw telegram channel | Telegram 消息中转 |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | b9222 | 本地 LLM 推理服务 |
| [GPT-SoVITS v2](https://github.com/RVC-Boss/GPT-SoVITS) | v2pro-20250604 | TTS 语音合成 |
| [ComfyUI](https://github.com/comfyanonymous/ComfyUI) | aki-v3 | 图片生成引擎 |

## 快速开始

### 🚀 一键全家桶（推荐）

**一行命令，从零到跑通所有 AI 女友功能：**

**Windows：**
```powershell
powershell -File setup-all.ps1
```

**Linux / macOS：**
```bash
bash setup-all.sh
```

自动串行执行：环境检查 → 模型下载 → llama.cpp 配置 → OpenClaw 安装 → 工作区部署 → 路径检查 → 启动 → 验证。

> 支持断点续传。可选参数：`--skip-model-download`、`--skip-llama-setup`、`--skip-openclaw-setup`、`--dry-run`、`--no-start`

---

### 分步执行（如果你想手动控制每一环）

### 0. 安装 OpenClaw

一键安装 OpenClaw Gateway 并部署 AI 女友工作区：

**Windows：**
```powershell
powershell -File setup-openclaw.ps1
```

**Linux / macOS：**
```bash
bash setup-openclaw.sh
```

脚本会自动：
- 安装 Node.js（如未安装）
- 通过官方脚本安装 OpenClaw Gateway
- 部署所有工作区文件（AGENTS.md、SOUL.md、skills 等）到你的 OpenClaw 工作区
- 安装 Gateway 守护进程实现自启动
- 应用本地 LLM 上下文窗口配置补丁

> **可选参数：** `--skip-node`、`--skip-deploy`、`--skip-daemon`、`--no-onboard`

### 1. 下载模型

使用提供的一键下载脚本：

**Windows：**
```powershell
# 安装依赖
pip install huggingface_hub
huggingface-cli login  # 首次使用需登录

# 运行下载器
powershell -File download-models.ps1

# 或指定目标目录
powershell -File download-models.ps1 -BaseDir "D:\models"
```

**Linux / macOS：**
```bash
pip install huggingface_hub
huggingface-cli login  # 首次使用需登录

bash download-models.sh
# 或：bash download-models.sh /path/to/models
```

脚本会从 HuggingFace 下载全部 5 个模型文件（约 29 GB），自动跳过已存在文件，并显示进度。

如果 HuggingFace 被墙，去度盘下载：https://pan.baidu.com/s/1sLeSyVp76yzWcR3Q4pX0kA?pwd=0721

详见 [`models.yaml`](models.yaml) 了解完整模型详情和手动下载命令。

### 2. 配置 llama.cpp

自动检测你的硬件并生成优化后的 llama-server 配置：

**Windows：**
```powershell
# 基础：检测硬件，生成配置
powershell -File setup-llama.ps1

# 自动编译（克隆 + 从源码编译 llama.cpp）
powershell -File setup-llama.ps1 -BuildLlama

# 自定义模型路径
powershell -File setup-llama.ps1 -ModelPath "D:\my-models\custom.gguf"
```

**Linux / macOS：**
```bash
# 基础
bash setup-llama.sh

# 自动编译
bash setup-llama.sh --build

# 自定义模型
bash setup-llama.sh --model /path/to/custom.gguf
```

脚本自动检测：
- **GPU** — NVIDIA (nvidia-smi)、AMD (rocminfo)、Apple Silicon (Metal)，或降级方案
- **显存** — 决定 GPU 卸载层数、批次大小、KV 缓存预算
- **CPU 核心** — 配置线程数和批次大小
- **内存** — 检查 --no-mmap 是否安全（需 32 GB+）

输出到 `llama-config/`：
- `launch-llama.ps1` / `launch-llama.sh` — 启动服务器
- `llama-watchdog.ps1` / `llama-watchdog.sh` — 健康检查（任务计划器 / cron）
- `hardware-report.md` — 你机器的检测配置
- 外加 systemd 服务（Linux）或 launchd plist（macOS）实现自启动

### 3. 配置路径 ⚡ 推荐用交互式向导

**一键搞定所有路径替换：**

`powershell
powershell -File configure.ps1
`

交互式配置向导会问你本地路径，然后自动替换所有脚本中的硬编码路径。
支持 \-DryRun\ 参数先预览不写入。

> 配置自动保存到 \config.json\，下次运行会自动读取。

---

<details>
<summary>📝 手动配置（点击展开）</summary>

以下文件中所有绝对路径需要改成你自己的环境：

| 文件 | 关键变量 |
|------|---------|
| \skills/tts/tts_call.py\ | \WEBUI_DIR\、\OUTPUT_DIR\、\LLAMA_EXE_PATH\、\LLAMA_MODEL_PATH\、\RESTART_SCRIPT\ |
| \skills/tts/run_tts.ps1\ | \\、\\、\\、\\ |
| \skills/comfyui/comfyui_call.py\ | \COMFYUI_ROOT\、\PYTHON_PATH\、\CHECKPOINTS_DIR\、\OUTPUT_DIR\、\LLAMA_*\ |
| \skills/comfyui/run_comfyui.ps1\ | \\、\\、\\、\\ |
| \skills/llama-watchdog.ps1\ | llama-server 路径、重启脚本路径 |
| \skills/cleanup_orphans.ps1\ | 项目目录、task_flags 目录 |

</details>

### 4. 部署到 OpenClaw

如果你还没运行 `setup-openclaw.ps1` / `setup-openclaw.sh`，可以手动把 `AI_Girlfriend/` 当作 OpenClaw 工作区使用。配置 qqbot channel 指向此目录即可。

### 5. Windows 任务计划器

```powershell
# Llama 健康检查（每 10 分钟）
schtasks /create /tn "llama-watchdog" `
  /tr "powershell -File C:\Users\<你>\.openclaw\workspace\qqbot\skills\llama-watchdog.ps1" `
  /sc minute /mo 10

# 孤儿进程清理（每小时）
schtasks /create /tn "cleanup-qqbot-orphans" `
  /tr "powershell -File C:\Users\<你>\.openclaw\workspace\qqbot\skills\cleanup_orphans.ps1" `
  /sc hourly /mo 1
```

### 6. 应用配置补丁

通过 OpenClaw 应用 `config-patch.json`：`gateway config.patch.apply`。

## QQ Bot 配置

参见 [`docs/qqbot-setup.md`](docs/qqbot-setup.md)。

快速配置：

1. 前往 [QQ 开放平台](https://q.qq.com/) 创建私域机器人，获取 **AppID** + **ClientSecret**
2. 编辑 `config-qqbot.json`，替换 `<YOUR_QQ_APP_ID>` 和 `<YOUR_QQ_CLIENT_SECRET>`
3. 应用配置：`openclaw gateway call config.patch.apply --json --params (Get-Content config-qqbot.json -Raw)`
4. QQ Bot channel 支持热更新，无需重启

## Telegram 配置

参见 [`docs/telegram-setup.md`](docs/telegram-setup.md)。

快速配置：

1. 通过 [@BotFather](https://t.me/BotFather) 创建 Bot，获取 Token
2. 编辑 `config-telegram.json`，替换 `<YOUR_BOT_TOKEN>`
3. 应用配置：`openclaw gateway call config.patch.apply --json --params (Get-Content config-telegram.json -Raw)`
4. 重启：`openclaw gateway restart`

参考了 [arlanrakh/talk-to-girlfriend-ai](https://github.com/arlanrakh/talk-to-girlfriend-ai) 的 Telegram 集成设计。

## 架构

```
用户（QQ / Telegram）
  │
  ▼
OpenClaw Gateway（qqbot + telegram channel）
  │
  ├── 主会话（local/qwen3.6-35b）
  │   ├── 角色扮演对话（QQ + Telegram）
  │   ├── Prompt / TTS 文本生成
  │   └── sessions_spawn → 子会话
  │
  ├── 子会话（local/qwen3.6-35b，deepseek 作为 fallback）
      ├── exec run_tts.ps1 → 停止 llama → GPT-SoVITS → 启动 llama → 通知
      └── exec run_comfyui.ps1 → 停止 llama → ComfyUI → 启动 llama → 通知
```

**显存调度流程**：
1. 主会话收到用户请求 → 组装 PS 命令
2. `sessions_spawn(mode="run")` 创建本地模型子会话（DeepSeek 作为 fallback）
3. 子会话 exec PS 脚本 → `stop_llama()` 停止 llama-server
4. 8 GB 显存全部释放 → 执行 TTS/ComfyUI 推理
5. `start_llama()` 重启 llama-server（~12 秒加载 + ~3 秒预热）
6. 子会话写入 `.task_flags` → announce 回主会话
7. 主会话读取媒体文件 → 通过 `<qqmedia>` (QQ) + `MEDIA:` (Telegram) 发送给用户

## ⚠️ 重要提示

- TTS/ComfyUI 推理期间 llama-server 离线约 60–120 秒 — 对话会暂停
- 子会话使用**本地模型**（与主会话相同），DeepSeek 作为可选 fallback — 无需网络也可独立运行
- llama-server 不支持跨轮 prompt 缓存复用（SSM 架构限制）— 请定期使用 `/reset`
- 所有模型文件受 `.gitignore` 保护，不会提交到 git
- GPT-SoVITS 权重为自己训练的，此处不提供 — 请用你自己的语音数据训练