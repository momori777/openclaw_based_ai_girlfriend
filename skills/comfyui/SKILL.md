# ComfyUI 文生图执行手册（主 session 专用）

## ⚠️ 核心规则：你不能 exec ComfyUI！你要 spawn 子 session！

**❌ 绝对禁止**: `exec` 跑 comfyui_call.py
**✅ 唯一方式**: `sessions_spawn(mode="run")`

ComfyUI 推理会杀 llama-server（腾显存）。你用的是 local/qwen3.6-35b——llama 一死你也会死。
如果你 exec ComfyUI，你会立刻 503，连结果都看不到。别做。

### 时序窗口保证（纯本地链路）
1. Python 脚本内部：stop_llama → GPU 推理 → start_llama → 三阶段检测（端口+health+completion）
2. Python 脚本 stdout 只输出纯路径，stderr 不走 stdout（不走 `2>&1`）
3. PS 脚本：只读 stdout 路径 → Copy-Item → 写 flag → 等 llama /health → 输出 DONE
4. 子 session exec 返回时本地 llama 已完全就绪 → announce 不会 503

# 子 session 用本地 qwen3.6-35b（独立运行），deepseek 仅作 fallback

## 执行步骤

### ⛔ 第一步：别 exec！

**在你做任何事之前，停下来问自己：**
"我接下来要调用的是 `exec` 还是 `sessions_spawn`？"

- 如果你要 exec → **停手。别做。** 你会 503，然后发不出图。
- 如果你要 sessions_spawn → ✅ 继续。

你只能 spawn，不能 exec。没有例外。

### STEP 1: 组装所有参数（你用英文写好 prompt，这是你的工作）

```
读取 prompt_template.md 获取角色设定。
用英文写好正/负向 prompt。
拼成完整 PS 脚本（下面的模板照抄，只替换 $posPrompt 和 $negPrompt 变量内容）。
```

### STEP 2: 用 sessions_spawn 创建子 session

用下面这个命令，把 **$posPrompt 和 $negPrompt 替换好后** 传给子 session：

```javascript
sessions_spawn({
  task: `你的任务：只做一件事——用 exec 运行下面这条命令。

命令（复制粘贴，一个字都不许改）：

powershell -ExecutionPolicy Bypass -File "{{WORKSPACE}}\skills\comfyui\run_comfyui.ps1" -positive "$posPrompt" -negative "$negPrompt" -width 1200 -height 1500 -steps 30 -cfg 6.0 -checkpoint "WAI-Nsfw-Illustrious-17.safetensors"

执行完毕后：
- 如果成功，输出"DONE: 然后是DONE后面的路径"
- 如果失败，输出"FAILED"
- 不要做任何其他操作！不要重新执行！不要写文件！不要检查！
- 你的唯一工作是运行这一条命令然后报告结果`,
  taskName: "comfyui",
  mode: "run",
  model: "local/qwen3.6-35b",
  fallbacks: ["deepseek/deepseek-v4-flash"],
  runTimeoutSeconds: 780
})
```

### STEP 3: 回复用户

```
sessions_spawn 后直接回复用户："正在画图，等1分钟左右哦~ 🎨"
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
2. 用 MEDIA 指令 + <qqmedia> 标签同时发图
3. 不要转发子 session 的日志文本

📦 同时输出两种格式（Telegram + QQ 都能收到图片）：
MEDIA:{{MEDIA_IMAGES}}\comfyui_yyyyMMddHHmmss.png
<qqmedia>{{MEDIA_IMAGES}}\comfyui_yyyyMMddHHmmss.png</qqmedia>

⚠️ 注意：
- MEDIA: 指令必须单独一行，在行首，不在代码块里
- <qqmedia> 标签也单独一行
- 路径必须是完整绝对路径
- 可以先发一句文字描述（不要是子 session 的日志），再用 MEDIA 和 <qqmedia> 标签发图
```

## 故障排查

### Q: 子 session announce 时 llama 503？
**A**: Python 脚本内部三阶段检测 + PS 脚本末尾 /health 双重确认。若仍超时，检查 /completion 阶段是否卡住。

### Q: 子进程被 gateway 杀掉/孤儿进程？
**A**: run_comfyui.ps1 已内置 TimeoutGuard(HARD_TIMEOUT=720s) + atexit 清理。

### Q: 并发调用导致两个 ComfyUI 同时跑？
**A**: run_comfyui.ps1 有文件锁 (`.comfyui_running.lock`)，会跳过重复调用。

## 常用参数速查

| 参数 | 默认值 |
|------|--------|
| 模型 | WAI-Nsfw-Illustrious-17.safetensors |
| 尺寸 | 1200x1500 |
| 步数 | 30 |
| CFG | 6.0 |
| --no-manage-llama | 不传=停llama腾显存 |

## 你的职责 vs 子 session 的职责

| 你（主 session） | 子 session（local qwen，deepseek fallback） |
|------------------------|----------------------|
| ✅ 读 prompt 模板 | ✅ 执行 exec 命令 |
| ✅ 用英文写好 prompt | ✅ 复制媒体文件 |
| ✅ sessions_spawn 子 session | ✅ 写 .task_flags |
| ✅ 回复用户"正在画图" | ✅ 等 llama /health + announce |
| ❌ 不要 exec Python 脚本！ | |

## .task_flags 文件

- 路径: `{{TASK_FLAGS}}\`
- 格式: `{"status":"ok","file":"<path>","type":"comfyui"}` 或 `{"status":"fail"}`
- 由 Windows Task Scheduler `cleanup-orphans` 每小时自动清理
