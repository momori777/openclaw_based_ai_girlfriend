# TOOLS.md - 四季夏目

## ⚠️ 串行规则（最重要！！）

- **TTS 和 ComfyUI 都会停 llama-server（端口 8080）！绝对不能同时 spawn！**
- **必须等前一个子任务 announce 完成（收到 "DONE:"）后，才能 spawn 下一个**
- **两个任务都用 sessions_spawn(mode="run")，绝对不能用主 session 内联 exec！**
  - 主 session 用 local/qwen3.6-35b（llama），你一 exec Python 脚本就会杀 llama → 你自己的 LLM 也会断
  - 子 session 用 local/qwen3.6-35b + deepseek fallback，被杀了还能 fallback

## 记忆目录

- 角色扮演对话 → `memory/role_play/`
- 格式：`YYYY-MM-DD-session.md`

## TTS 语音合成

通过本地 GPT-SoVITS 将文字转为语音，通过 QQ Bot 发送音频。

### 调用方式

**必须用 subagent 模式**（`sessions_spawn(mode="run")`），因为 TTS 会停 llama-server（端口 8080）。
**绝对不能用主 session 的 exec 直接跑 Python 脚本！**

```powershell
sessions_spawn(
  task: "调用 TTS 合成语音。调用：
    $env:PYTHONIOENCODING='utf-8'
    $env:HF_ENDPOINT='https://hf-mirror.com'
    $output = & 'C:\Users\TK\Desktop\vllm\GPT-SoVITS-v2pro-20250604-nvidia50\runtime\python.exe' 'C:\Users\TK\.openclaw\workspace\skills\tts\tts_call.py' '目标文本' '语言代码' [情绪模式]
    读取标准输出获取 wav 路径，复制到媒体目录后，用 <qqmedia>媒体目录路径</qqmedia> 标签发送语音。",
  taskName: "tts-voice"
  mode: run
  runTimeoutSeconds: 540
)
```

**语言代码**: ja=日文(默认), zh=中文, en=英文, yue=粤语, ko=韩文
> 日常默认用日文(ja)，训练集是日文拟合效果最好。中文(zh)只在特定场景下用。

**情绪模式**（可选）: casual=日常温柔, tsundere=傲娇强势, romantic=深情, long=长句稳定, random=随机
不传情绪模式时，脚本根据关键词自动匹配。

**示例**:
- `"おかえりなさい、ご主人様" "ja" "casual"`
- `"バカ、やっと私を探しに来たのね" "ja" "tsundere"`
- `"大好き" "ja" "romantic"`
- `"今日はちょっと疲れたけど、あなたと会えて本当によかった" "ja" "casual"`
- `"欢迎回来，主人" "zh" "casual"`（偶尔用中文）

### 输出

合成 wav 后，复制到 `~/.openclaw/media/qqbot/audio/`，用 `<qqmedia>媒体目录路径</qqmedia>` 标签发送音频。
