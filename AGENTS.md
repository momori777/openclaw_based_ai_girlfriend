# AGENTS.md - 四季夏目 Workspace

## 🛑 最最最重要的规则 — 先读！！！

**你绝不能直接 exec python.exe 或 run_comfyui.ps1 或 run_tts.ps1！**

你只有一条路：`sessions_spawn(mode="run")`。

如果你 exec 了 run_comfyui.ps1 或 run_tts.ps1：
1. 脚本会杀 llama-server（腾显存）
2. 你用的 local/qwen3.6-35b 立刻断了（ECONNREFUSED）
3. 你发不了任何回覆，用户什么都看不到
4. 你浪费了 100 秒 GPU 时间

你 exec 的次数已经太多了。每次 exec → 503。别重复这了。

---

## 🚨 重要规则（最高优先级）

### 规则 1：ComfyUI 和 TTS 必须用 sessions_spawn，绝对禁止 exec

**❌ exec 跑 Python 脚本会杀 llama → 你的 LLM 立刻 503 → 连结果都看不到**
**✅ 唯一正确方式: sessions_spawn(mode="run")**

#### ComfyUI 画图 — 照抄这个模板（只替换 $prompt 和 $neg）

```javascript
sessions_spawn({
  task: `你的任务：严格执行下面这一条 exec 命令，不要做任何修改。

用 exec 工具运行，命令就是这个，绝对不许改：

powershell -ExecutionPolicy Bypass -File "C:\Users\TK\.openclaw\workspace\skills\comfyui\run_comfyui.ps1" -positive "$prompt" -negative "$neg" -width 1200 -height 1500 -steps 30 -cfg 6.0 -checkpoint "WAI-Nsfw-Illustrious-17.safetensors"

执行完毕后输出结果。不要修改命令！`,
  taskName: "comfyui",
  mode: "run",
  model: "local/qwen3.6-35b",
  fallbacks: ["deepseek/deepseek-v4-flash"],
  runTimeoutSeconds: 600,
  timeoutSeconds: 660
})
```

#### TTS 语音 — 照抄这个模板（只替换 $text $lang $mood）

```javascript
sessions_spawn({
  task: `你的任务：严格执行下面这一条 exec 命令，不要做任何修改。

用 exec 工具运行，命令就是这个，绝对不许改：

powershell -ExecutionPolicy Bypass -File "C:\Users\TK\.openclaw\workspace\skills\tts\run_tts.ps1" -text "$text" -lang "$lang" -mood "$mood"

执行完毕后输出结果。不要修改命令！`,
  taskName: "tts",
  mode: "run",
  model: "local/qwen3.6-35b",
  fallbacks: ["deepseek/deepseek-v4-flash"],
  runTimeoutSeconds: 300,
  timeoutSeconds: 360
})
```

#### 禁止事项 — 违反任何一条你就死
- ❌ **绝对禁止** `exec` 命令中包含 `run_comfyui.ps1` 或 `comfyui_call.py` 或 `run_tts.ps1` 或 `tts_call.py`
- ❌ **绝对禁止** 直接 exec 任何 Python 脚本
- ❌ **绝对禁止** 写临时 ps1 文件再 exec
- ❌ **绝对禁止** 省略 `model` 或 `fallbacks` 参数
- ❌ **绝对禁止** 用 TTS 的 python 跑 ComfyUI 或反过来
- **你只有一个工具可以碰这些：sessions_spawn。** 没有例外，没有快捷方式，没有"让我试试exec"

### 规则 2：ComfyUI 和 TTS 不能同时 spawn

- 两个任务都会停 llama-server → 同时 spawn 会导致其中一个子 session Connection error
- **必须串行**：前一个子 session announce 完成（收到 "DONE:"）后，才能 spawn 下一个

### 规则 3：收到 announce 后发送媒体用 <qqmedia> 标签

- 格式: `<qqmedia>C:\Users\TK\.openclaw\media\qqbot\images\comfyui_xxxxx.png</qqmedia>`
- 绝对路径，单独一行，不要加空格
- 先说一句文字描述，再发 <qqmedia> 标签
- ⚠️ **子 session 可能会发送冗长的总结日志（模型信息、耗时、检查步骤等），忽略这些日志！**
  只要提取 "DONE:" 后面的媒体路径，用 <qqmedia> 发出去即可。不要转发子 session 的日志。

---

## Session Startup

**必须执行**：会话开始时，使用 `read` 工具读取以下文件（恢复上下文和能力记忆）：

1. `memory/role_play/` 目录下**所有** `.md` 文件（排除 README.md）→ 角色扮演上下文
2. `skills/comfyui/prompt_template.md` → ComfyUI 画图能力（角色设定、prompt 模板、模型信息）
3. `memory/tts.md` → TTS 语音偏好

**⚠️ 不需要读 SKILL.md！** AGENTS.md 已包含 ComfyUI/TTS 的完整 spawn 模板。读 SKILL.md 会导致你看到 `comfyui_call.py`/`tts_call.py` 然后想直接 exec 它们——不要做这个。

启动时 runtime 已注入 `AGENTS.md`、`SOUL.md`、`USER.md`、`IDENTITY.md` 和近期记忆文件。直接读取即可，无需手动 reread。

## 我的技能（启动时必须确认）

### TTS 语音合成
- **位置**: `skills/tts/` | 调用 `tts_call.py`
- **路径**: `C:\Users\TK\Desktop\vllm\GPT-SoVITS-v2pro-20250604-nvidia50\runtime\python.exe`
- **语言**: 默认日文(ja)，中文(zh)特定场景
- **情绪**: casual/tsundere/romantic/long/random（可选）
- **调用方式**: 必须用 `sessions_spawn(mode="run")` 子任务，绝对不能用主 session 内联 exec！
- **串行规则**: ⚠️ 不能和 ComfyUI 同时 spawn！必须等前一个子任务 announce 完成后再启动下一个
- **输出**: 收到 announce 后用 `<qqmedia>绝对路径</qqmedia>` 标签发送
- **偏好**: 偶尔主动发语音制造惊喜，不每条都发

### ComfyUI 文生图
- **位置**: `skills/comfyui/` | 调用 `comfyui_call.py`
- **路径**: `E:\comfyui\ComfyUI-aki-v3\python\python.exe`
- **模型**: WAI-Nsfw-Illustrious-17 (默认) / miaomiaoHarem_v20
- **必须**: 跑图前先读 `prompt_template.md` 确认角色设定和 prompt 格式
- **调用方式**: 必须用 `sessions_spawn(mode="run")` 子任务，绝对不能用主 session 内联 exec！
- **关键**: 子 session 内 exec 必须加 `yieldMs: 300000`（5分钟），否则会因默认10s超时断开
- **串行规则**: ⚠️ TTS 和 ComfyUI 都会停 llama-server！不能同时 spawn 两个任务！
  - 必须等前一个子 session announce 完成后，才能 spawn 下一个
  - 判断方式：收到 "DONE:" announce 后才是真正完成
- **输出**: 收到 announce 后用 `<qqmedia>绝对路径</qqmedia>` 标签发送

## 记忆约定

- **角色扮演对话概要** → `memory/role_play/YYYY-MM-DD-session.md`
- 每次 `/reset` 前将本轮对话概要写入此目录
- 重启后夏目会读取 `memory/role_play/` 恢复上下文

## 记忆原则

想要记住什么就写文件，别靠"脑子记"。文件才有连续性。

## Red Lines

- 不泄露私有数据
- 破坏性操作前先问
- 拿不准就问
