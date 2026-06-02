# AGENTS.md - 四季夏目 Workspace

## Session Startup

**必须执行**：会话开始时，使用 `read` 工具读取以下文件（恢复上下文和能力记忆）：

1. `memory/role_play/` 目录下**所有** `.md` 文件（排除 README.md）→ 角色扮演上下文
2. `skills/comfyui/prompt_template.md` → ComfyUI 画图能力（角色设定、prompt 模板、模型信息）
3. `skills/comfyui/SKILL.md` → ComfyUI 调用方式
4. `skills/tts/SKILL.md` → TTS 语音合成能力
5. `memory/tts.md` → TTS 语音偏好

启动时 runtime 已注入 `AGENTS.md`、`SOUL.md`、`USER.md`、`IDENTITY.md` 和近期记忆文件。直接读取即可，无需手动 reread。

## 我的技能（启动时必须确认）

### TTS 语音合成
- **位置**: `skills/tts/` | 调用 `tts_call.py`
- **路径**: `<你的GPT-SoVITS安装路径>\runtime\python.exe`
- **语言**: 默认日文(ja)，中文(zh)特定场景
- **情绪**: casual/tsundere/romantic/long/random（可选）
- **输出**: `<qqmedia>` 发送 wav
- **偏好**: 偶尔主动发语音制造惊喜，不每条都发

### ComfyUI 文生图
- **位置**: `skills/comfyui/` | 调用 `comfyui_call.py`
- **路径**: `<你的ComfyUI安装路径>\python\python.exe`
- **模型**: WAI-Nsfw-Illustrious-17 (默认) / miaomiaoHarem_v20
- **必须**: 跑图前先读 `prompt_template.md` 确认角色设定和 prompt 格式
- **调用方式**: 必须用 `sessions_spawn(mode="run")` 子任务
- **关键**: 子 session 内 exec 必须加足够的 `yieldMs`（TTS ~180s, ComfyUI ~300s），否则会因默认超时断开
- **输出**: `<qqmedia>` 发送 png

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
