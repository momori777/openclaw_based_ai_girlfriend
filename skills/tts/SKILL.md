# GPT-SoVITS TTS 执行手册（qqbot 主 session 专用）

## ⚠️ 核心规则：你不能 exec TTS！你要 spawn 子 session！

TTS 推理会杀 llama-server（腾显存）。你用的是 local/qwen3.6-35b——llama 一死你也会死。
所以你必须把 exec 任务交给子 session，子 session 不依赖LLM，出错会fallback到deepseek 模型（不依赖本地 llama）。

# 子 session 用本地 qwen3.6-35b 也能正常执行

## 执行步骤

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
  task: `你的任务：执行下面这个 PowerShell 命令。
完成后把输出告诉我就行，不需要额外处理。

用 exec 工具运行：

powershell -ExecutionPolicy Bypass -Command "
$taskId = ('tts_' + (Get-Date -Format 'HHmmss') + '_' + [System.Random]::new().Next(1000,9999))
$flagDir = 'C:\\Users\\TK\\.openclaw\\workspace\\qqbot\\.task_flags'
$flagFile = '$flagDir\\$taskId.done'
mkdir $flagDir -Force -ErrorAction SilentlyContinue | Out-Null

$mediaDir = 'C:\\Users\\TK\\.openclaw\\media\\qqbot\\audio'
mkdir $mediaDir -Force -ErrorAction SilentlyContinue | Out-Null

$text = '替换为要合成的文本'
$lang = 'ja'
$mood = 'casual'

$env:PYTHONIOENCODING = 'utf-8'
$env:HF_ENDPOINT = 'https://hf-mirror.com'

$wavPath = & 'C:\\Users\\TK\\Desktop\\vllm\\GPT-SoVITS-v2pro-20250604-nvidia50\\runtime\\python.exe' 'C:\\Users\\TK\\.openclaw\\workspace\\qqbot\\skills\\tts\\tts_call.py' $text $lang $mood 2>&1
$lines = $wavPath | Where-Object { $_ -like '*.wav' }
$realPath = $lines | Select-Object -Last 1

if ($realPath) {
    $mediaFile = Join-Path $mediaDir ('tts_' + (Get-Date -Format 'yyyyMMddHHmmss') + '.wav')
    Copy-Item $realPath $mediaFile -Force
    @{status='ok';file=$mediaFile;type='tts'} | ConvertTo-Json -Compress | Set-Content $flagFile
    Write-Output \\\"DONE: $mediaFile\\\"
} else {
    Write-Output 'FAILED'
}
"`,
  taskName: "tts",
  mode: "run",
  model: "local/qwen3.6-35b",
  fallbacks: ["deepseek/deepseek-v4-flash"],
  runTimeoutSeconds: 300,
  timeoutSeconds: 360
})
```

### STEP 3: 回复用户

```
sessions_spawn 后直接回复用户："正在合成语音，稍等哦~ 🎤"
然后正常结束当前 turn。别 sessions_yield。
```

### STEP 4: 收到 announce 后

```
子 session 跑完会自动 announce 回来。announce 里会有 "DONE: <path>"。
你用 <qqmedia> 标签把路径发给用户。
```

## 参数速查

| 参数 | 说明 |
|------|------|
| text | 要合成的文本 |
| text_language | ja=日文, zh=中文, en=英文 |
| mood | casual=日常温柔, tsundere=傲娇, romantic=深情, long=长句 |
| 默认值 | lang=ja, mood=自动匹配 |

## 你的职责 vs 子 session 的职责

| 你（qqbot 主 session） | 子 session（local qwen + deepseek fallback） |
|------------------------|---------------------------------------------|
| ✅ 写好待合成的文本 | ✅ 执行 exec 命令 |
| ✅ 选语言和情绪模式 | ✅ 复制 wav 到 media/qqbot/audio |
| ✅ sessions_spawn 子 session | ✅ 写 .task_flags |
| ✅ 回复用户"正在合成" | ✅ announce 结果 |
| ❌ 不要 exec Python 脚本！ | |

## .task_flags 文件

- 路径: `C:\Users\TK\.openclaw\workspace\qqbot\.task_flags\`
- 格式: `{"status":"ok","file":"<path>","type":"tts"}` 或 `{"status":"fail"}`
- 由 Windows Task Scheduler `cleanup-qqbot-orphans` 每小时自动清理

## 故障排查

### Q: 子 session 报 `503 Loading model` 怎么办？
**A**: tts_call.py 已经内置了时序窗口管理——stop_llama → TTS 推理 → start_llama（等端口就绪）→ 输出结果。announce 时 llama 应已在线。
如果仍然超时：检查 llama 模型加载时间是否超过 180s（`start_llama()` 的超时值）。

### Q: 子进程被 gateway 杀掉/孤儿进程？
**A**: tts_call.py 已内置 TimeoutGuard(HARD_TIMEOUT=300s) + atexit 清理。超时会 taskkill /f /t 整个进程树并释放锁文件。

### Q: 并发调用导致两个 TTS 同时跑？
**A**: tts_call.py 有文件锁 (`.tts_running.lock`)，会检测到第一个实例还在跑就跳过第二个。
