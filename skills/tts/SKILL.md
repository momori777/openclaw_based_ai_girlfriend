# GPT-SoVITS TTS 执行手册（主 session 专用）

## ⚠️ 核心规则：你不能 exec TTS！你要 spawn 子 session！

**❌ 绝对禁止**: `exec` 跑 tts_call.py
**✅ 唯一方式**: `sessions_spawn(mode="run")`

TTS 推理会杀 llama-server（腾显存）。你用的是 local/qwen3.6-35b——llama 一死你也会死。
如果你 exec TTS，你会立刻 503，连结果都看不到。别做。

### 时序窗口保证（纯本地链路）
1. Python 脚本内部：stop_llama → TTS 推理 → start_llama → 三阶段检测（端口+health+completion）
2. Python 脚本 stdout 只输出纯路径，stderr 不走 stdout（不走 `2>&1`）
3. PS 脚本：只读 stdout 路径 → Copy-Item → 写 flag → 等 llama /health → 输出 DONE
4. 子 session exec 返回时本地 llama 已完全就绪 → announce 不会 503

# 子 session 用本地 qwen3.6-35b（独立运行），deepseek 仅作 fallback

## 执行步骤

### ⛔ 第一步：别 exec！

**在你做任何事之前，停下来问自己：**
"我接下来要调用的是 `exec` 还是 `sessions_spawn`？"

- 如果你要 exec → **停手。别做。** 你会 503，然后发不出语音。
- 如果你要 sessions_spawn → ✅ 继续。

你只能 spawn，不能 exec。没有例外。

### STEP 1: 组装参数（你负责写文本、选情绪、选语言）

```
根据上下文写好要合成的文本。
选语言（默认 ja=日文）。
选情绪模式（casual/tsundere/romantic/long），不指定则自动匹配。
```

### STEP 2: 用 sessions_spawn 创建子 session

用下面这个命令，把 **$text、$lang、$mood 替换好后** 传给子 session：

```javascript
sessions_spawn({
  task: `你的任务：只做一件事——用 exec 运行下面这条命令。

命令（复制粘贴，一个字都不许改）：

powershell -ExecutionPolicy Bypass -File "{{WORKSPACE}}\skills\tts\run_tts.ps1" -text "$text" -lang "$lang" -mood "$mood"

执行完毕后：
- 如果成功，输出"DONE: 然后是DONE后面的路径"
- 如果失败，输出"FAILED"
- 不要做任何其他操作！不要重新执行！不要写文件！不要检查！
- 你的唯一工作是运行这一条命令然后报告结果`,
  taskName: "tts",
  mode: "run",
  model: "local/qwen3.6-35b",
  fallbacks: ["deepseek/deepseek-v4-flash"],
  runTimeoutSeconds: 540
})
```

### STEP 3: 回复用户

```
sessions_spawn 后直接回复用户："正在合成语音，稍等哦~ 🎤"
然后正常结束当前 turn。别 sessions_yield。
```

### STEP 4: 收到 announce 后（重要！）

```
子 session 跑完会自动 announce 回来。announce 里会有 "DONE: <path>"。

⚠️ announce 可能包含两段文本：
1) 子 session 总结的长日志（模型信息、耗时等）—— 忽略它，不要转发！
2) "DONE: <path>" —— 只有这行有用！

你必须：
1. 从 announce 文本中提取 "DONE: 后的文件路径"
2. 用 MEDIA 指令 + <qqmedia> 标签同时发语音
3. 不要转发子 session 的日志文本

📦 同时输出两种格式（Telegram + QQ 都能收到语音）：
MEDIA:{{MEDIA_AUDIO}}\tts_yyyyMMddHHmmss.wav
<qqmedia>{{MEDIA_AUDIO}}\tts_yyyyMMddHHmmss.wav</qqmedia>

⚠️ 注意：
- MEDIA: 指令必须单独一行，在行首，不在代码块里
- <qqmedia> 标签也单独一行
- 路径必须是完整绝对路径
- 可以先说一句话，再用 MEDIA 和 <qqmedia> 发语音
```

## 参数速查

| 参数 | 说明 |
|------|------|
| text | 要合成的文本 |
| text_language | ja=日文, zh=中文, en=英文 |
| mood | casual=日常温柔, tsundere=傲娇, romantic=深情, long=长句 |
| 默认值 | lang=ja, mood=自动匹配 |

## 你的职责 vs 子 session 的职责

| 你（主 session） | 子 session（local qwen，deepseek fallback） |
|------------------------|---------------------------------------------|
| ✅ 写好待合成的文本 | ✅ 执行 exec 命令 |
| ✅ 选语言和情绪模式 | ✅ 复制 wav 到 media/qqbot/audio |
| ✅ sessions_spawn 子 session | ✅ 写 .task_flags |
| ✅ 回复用户"正在合成" | ✅ 等 llama /health + announce |
| ❌ 不要 exec Python 脚本！ | |

## .task_flags 文件

- 路径: `{{TASK_FLAGS}}\`
- 格式: `{"status":"ok","file":"<path>","type":"tts"}` 或 `{"status":"fail"}`
- 由 Windows Task Scheduler `cleanup-orphans` 每小时自动清理

## 故障排查

### Q: 子 session announce 时 llama 503？
**A**: Python 脚本内部三阶段检测 + PS 脚本末尾 /health 双重确认。若仍超时，检查 /completion 阶段是否卡住。

### Q: 子进程被 gateway 杀掉/孤儿进程？
**A**: tts_call.py 已内置 TimeoutGuard(HARD_TIMEOUT=420s) + atexit 清理。

### Q: 并发调用导致两个 TTS 同时跑？
**A**: tts_call.py 有文件锁 (`.tts_running.lock`)，会跳过重复调用。
