# GPT-SoVITS TTS 执行手册（qqbot 主 session 专用）

## ⚠️ 核心规则：你不能 exec TTS！你要 spawn 子 session！

TTS 推理会杀 llama-server（腾显存）。你用的是 local/qwen3.6-35b——llama 一死你也会死。
所以你必须把 exec 任务交给子 session，子 session 不依赖LLM，出错会fallback到deepseek 模型（不依赖本地 llama）。

# 子 session 用本地 qwen3.6-35b 也能正常执行

## 执行步骤

### STEP 1: 准备好参数

```
确定要合成的文本（默认日文 ja）。
确定情绪模式（casual/tsundere/romantic/long），不指定则自动匹配。
```

### STEP 2: 用 sessions_spawn 创建子 session

用下面这个命令，把 **$text、$lang、$mood 替换好后** 传给子 session：

```javascript
sessions_spawn({
  task: `你的任务：执行下面这个 PowerShell 命令。
完成后把输出告诉我就行，不需要额外处理。

用 exec 工具运行：

powershell -ExecutionPolicy Bypass -Command "
$taskId = '生成一个随机ID'
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
    Write-Output \"DONE: $mediaFile\"
} else {
    Write-Output 'FAILED'
}
"`,
  taskName: "tts",
  mode: "run",
  model: "deepseek/deepseek-v4-flash",
  runTimeoutSeconds: 120,
  timeoutSeconds: 180
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
| text_language | ja=日文, zh=中文, en=英文 |
| mood | casual=日常温柔, tsundere=傲娇, romantic=深情, long=长句 |
| 自动匹配 | 无 mood 时根据关键词自动选情绪 |

## 参数速查

| 参数 | 默认值 |
|------|--------|
| 语言 | ja (日文) |
| 情绪 | 自动匹配 |

## 你的职责 vs 子 session 的职责

| 你（qqbot 主 session） | 子 session（DeepSeek） |
|------------------------|----------------------|
| ✅ 写日文/中文文本 | ✅ 执行 exec 命令 |
| ✅ 选情绪模式 | ✅ 复制 wav 到 media/qqbot/audio |
| ✅ sessions_spawn 子 session | ✅ 写 .task_flags |
| ✅ 回复用户"正在合成" | ✅ announce 结果 |
| ❌ 不要 exec Python 脚本！ | |

## .task_flags 文件

- 路径: `C:\Users\TK\.openclaw\workspace\qqbot\.task_flags\`
- 格式: `{"status":"ok","file":"<path>","type":"tts"}` 或 `{"status":"fail"}`
- 由 Windows Task Scheduler `cleanup-qqbot-orphans` 每小时自动清理

## 常见问题

### Q: 子 session 报 `503 Loading model` 怎么办？
**A**: 这是因为 exec 的 `yieldMs` 太短，子进程还没跑完（TTS 推理 + llama 重启 ≈ 60s），60s 后 exec 超时，子 agent 需要 `process poll` 但 llama 还没恢复。
**解决**: 确保 exec 调用时 `yieldMs: 180000`（180秒），给 llama 足够时间重启。
