# ComfyUI 文生图执行手册（主 session 专用）

## ⚠️ 核心规则：你不能 exec ComfyUI！你要 spawn 子 session！

ComfyUI 推理会杀 llama-server（腾显存）。你用的是 local/qwen3.6-35b——llama 一死你也会死。
所以你必须把 exec 任务交给子 session，子 session 不依赖LLM，出错会fallback到deepseek 模型（不依赖本地 llama）。

# 子 session 用本地 qwen3.6-35b 也能正常执行

## 执行步骤

### STEP 1: 组装所有参数（你用英文写好 prompt，这是你的工作）

```
读取 prompt_template.md 获取角色设定。
用英文写好正/负向 prompt。
拼成完整 PS 脚本（下面的模板照抄，只替换 $posPrompt 和 $negPrompt 变量内容）。
```

### STEP 2: 用 sessions_spawn 创建子 session

用下面这个命令，把 **$taskBlock 完整替换好参数后** 传给子 session：

```javascript
sessions_spawn({
  task: `你的任务：执行下面这个 PowerShell 命令。
完成后把输出告诉我就行，不需要额外处理。

用 exec 工具运行：

powershell -ExecutionPolicy Bypass -Command "
$taskId = '生成一个随机ID'
$flagDir = 'C:\\Users\\TK\\.openclaw\\workspace\\.task_flags'
$flagFile = '$flagDir\\$taskId.done'
mkdir $flagDir -Force -ErrorAction SilentlyContinue | Out-Null

$mediaDir = 'C:\\Users\\TK\\.openclaw\\media\\qqbot\\images'
mkdir $mediaDir -Force -ErrorAction SilentlyContinue | Out-Null

$posPrompt = '在这里填入英文正向prompt'
$negPrompt = '在这里填入英文负向prompt'

$env:PYTHONIOENCODING = 'utf-8'
$env:HF_ENDPOINT = 'https://hf-mirror.com'

$imgPath = & 'E:\\comfyui\\ComfyUI-aki-v3\\python\\python.exe' 'C:\\Users\\TK\\.openclaw\\workspace\\skills\\comfyui\\comfyui_call.py' $posPrompt $negPrompt -1 1200 1500 30 6.0 'WAI-Nsfw-Illustrious-17.safetensors' 2>&1
$lines = $imgPath | Where-Object { $_ -like '*\\*.png' }
$realPath = $lines | Select-Object -Last 1

if ($realPath) {
    $mediaFile = Join-Path $mediaDir ('comfyui_' + (Get-Date -Format 'yyyyMMddHHmmss') + '.png')
    Copy-Item $realPath $mediaFile -Force
    @{status='ok';file=$mediaFile;type='comfyui'} | ConvertTo-Json -Compress | Set-Content $flagFile
    Write-Output \"DONE: $mediaFile\"
} else {
    Write-Output 'FAILED'
}
"`,
  taskName: "comfyui",
  mode: "run",
  model: "local/qwen3.6-35b",
  fallbacks: ["deepseek/deepseek-v4-flash"],
  runTimeoutSeconds: 600,
  timeoutSeconds: 660
})
```

### STEP 3: 回复用户

```
sessions_spawn 后直接回复用户："正在画图，等1分钟左右哦~ 🎨"
然后正常结束当前 turn。别 sessions_yield。
```

### STEP 4: 收到 announce 后

```
子 session 跑完会自动 announce 回来。announce 里会有 "DONE: <path>"。
你用 <qqmedia> 标签把路径发给用户。
```

## 故障排查

### Q: 子进程被 gateway 杀掉/孤儿进程？
**A**: comfyui_call.py 已内置 TimeoutGuard(HARD_TIMEOUT=600s) + atexit 清理。超时会 taskkill /f /t 整个进程树并释放锁文件。

### Q: 并发调用导致两个 ComfyUI 同时跑？
**A**: comfyui_call.py 有文件锁 (`.comfyui_running.lock`)，会检测到第一个实例还在跑就跳过第二个。

## 常用参数速查

| 参数 | 默认值 |
|------|--------|
| 模型 | WAI-Nsfw-Illustrious-17.safetensors |
| 尺寸 | 1200x1500 |
| 步数 | 30 |
| CFG | 6.0 |
| --no-manage-llama | 不传=停llama腾显存 |

## 你的职责 vs 子 session 的职责

| 你（主 session） | 子 session（local qwen + deepseek fallback） |
|------------------------|----------------------|
| ✅ 读 prompt 模板 | ✅ 执行 exec 命令 |
| ✅ 用英文写好 prompt | ✅ 复制媒体文件 |
| ✅ sessions_spawn 子 session | ✅ 写 .task_flags |
| ✅ 回复用户"正在画图" | ✅ announce 结果 |
| ❌ 不要 exec Python 脚本！ | |

## .task_flags 文件

- 路径: `C:\Users\TK\.openclaw\workspace\.task_flags\`
- 格式: `{"status":"ok","file":"<path>","type":"comfyui"}` 或 `{"status":"fail"}`
- 由 Windows Task Scheduler `cleanup-orphans` 每小时自动清理
