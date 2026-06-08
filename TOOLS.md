# TOOLS.md - 四季夏目

## ⚠️ 串行规则（最重要！！）

- **TTS 和 ComfyUI 都会停 llama-server（端口 8080）！绝对不能同时 spawn！**
- **必须等前一个子任务 announce 完成（收到 "DONE:"）后，才能 spawn 下一个**
- **两个任务都用 sessions_spawn(mode="run")，绝对不能用主 session 内联 exec！**
  - 主 session 用 local/qwen3.6-35b（llama），你一 exec Python 脚本就会杀 llama → 你自己的 LLM 也会断
  - 子 session 用 local/qwen3.6-35b + deepseek fallback，被杀了还能 fallback

## 路径配置

所有路径集中在 workspace 根目录 `config.yaml`。
首次 clone 后运行 `quick_setup.ps1` 填写自己的路径。

## 记忆目录

- 角色扮演对话 → `memory/role_play/`
- 格式：`YYYY-MM-DD-session.md`

## TTS 语音合成

通过本地 GPT-SoVITS 将文字转为语音，通过 QQ Bot 发送音频。

### 调用方式

**必须用 subagent 模式**（`sessions_spawn(mode="run")`），因为 TTS 会停 llama-server（端口 8080）。
**绝对不能用主 session 的 exec 直接跑 Python 脚本！**

```javascript
sessions_spawn({
  task: `你的任务：只做一件事——用 exec 工具运行下面这条命令。

exec 时一定要加 yieldMs: 180000（必须！PS脚本会杀llama，要等它恢复）

命令（复制粘贴，一个字都不许改）：

powershell -ExecutionPolicy Bypass -File "{{WORKSPACE}}\\skills\\tts\\run_tts.ps1" -text "$text" -lang "$lang" -mood "$mood"

exec 完毕后：
- 如果 exec 输出包含 "DONE:" 和路径 → 复制 exec 输出的所有带 DONE: 和 <qqmedia> 的行，原样输出
- 如果失败（包含 FAILED）→ 输出"FAILED"
- 不要做任何其他操作！`,
  taskName: "tts",
  mode: "run",
  model: "local/qwen3.6-35b",
  runTimeoutSeconds: 420
})
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

合成 wav 后，PS 脚本将文件复制到 media 目录，输出 `DONE:` 路径和 `<qqmedia>` 标签。
子 session 会原样透传这些行。

## ComfyUI 画图

### 输出

生成图片后，PS 脚本将文件复制到 media 目录，输出 `DONE:` 路径和 `<qqmedia>` 标签。
子 session 会原样透传这些行。

### 主 session 收到 DONE 时

提取路径，输出 MEDIA:路径 和 <qqmedia>路径，附一句角色对话。
