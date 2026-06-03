# TOOLS.md - 四季夏目

## 记忆目录

- 角色扮演对话 → `memory/role_play/`
- 格式：`YYYY-MM-DD-session.md`

## TTS 语音合成

通过本地 GPT-SoVITS 将文字转为语音，通过 QQ Bot 发送音频。

### 调用方式

**必须用 subagent 模式**（`sessions_spawn(mode="run")`），因为 TTS 会停 llama-server（端口 8080）。

详见 `skills/tts/SKILL.md`。

**语言代码**: ja=日文(默认), zh=中文, en=英文, yue=粤语, ko=韩文
> 日常默认用日文(ja)，训练集是日文拟合效果最好。中文(zh)只在特定场景下用。

**情绪模式**（可选）: casual=日常温柔, tsundere=傲娇强势, romantic=深情, long=长句稳定, random=随机
不传情绪模式时，脚本根据关键词自动匹配。

## ComfyUI 文生图

通过本地 ComfyUI 生成角色图片。详见 `skills/comfyui/SKILL.md` 和 `skills/comfyui/prompt_template.md`。

## 显存管理

RTX 5070 8GB 显存，llama-server + TTS/ComfyUI 不能同时跑。
架构：主 session 写 prompt → 子 session (DeepSeek) exec Python 脚本 → announce 回主 session。
详见 `skills/llama-management.md`。
