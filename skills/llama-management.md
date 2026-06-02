# Llama 显存管理方案

## 背景

RTX 5070 只有 12GB 显存。llama-server（local/qwen3.6-35b）占用约 6GB。
TTS（GPT-SoVITS）需要约 2-3GB。ComfyUI 需要约 4-7GB。
三者同时跑必 OOM。

## 架构：主 session 写 prompt → 子 session exec → announce 回主 session

### 职责分-工

| 主 session（qqbot, local/qwen） | 子 session（DeepSeek） |
|-------------------------------|----------------------|
| 读模板/TTS文本、写英文 prompt | exec PowerShell |
| sessions_spawn 子 session | 跑 Python 脚本（停llama→推理→起llama） |
| 回复用户"正在处理" | 复制媒体文件到 media/qqbot/ |
| 收 announce → 包装发用户 | 写 .task_flags ({"status":"ok","file":"<path>","type":"tts|comfyui"}) |
| ❌ 不 exec Python 脚本 | announce 结果回主 session |

### 为什么这样分

- **主 session 用 local/qwen3.6-35b** —— 停 llama 就死，不能自己做 GPU 推理
- **子 session 用 deepseek/deepseek-v4-flash** —— 不依赖本地 llama，停 llama 不影响
- **主 session 写好 prompt** —— 所有"思考"工作在停 llama 前完成
- **子 session 只 exec** —— 不需要判断、不需要写 prompt，只跑命令

### 流程

```
主 session (qqbot, local/qwen)    子 session (DeepSeek)         Python 脚本           Windows Task Scheduler
    │                                   │                          │                      │
    ├── 读 prompt 模板                   │                          │                      │
    ├── 用英文写好正/负向 prompt          │                          │                      │
    ├── sessions_spawn ────────────────► │                          │                      │
    │   task: 完整 PS 命令（参数已就位）   │                          │                      │
    │   model: deepseek                  │                          │                      │
    │                                   │                          │                      │
    ├── 回复"正在画图/合成"               │                          │                      │
    │   (正常结束 turn)                   │                          │                      │
    │                                   │                          │                      │
    │                                   ├── exec PowerShell ─────► │                      │
    │                                   │                          ├── stop_llama()      │
    │                                   │                          │   (主session LLM断) │
    │                                   │                          ├── GPU 推理          │
    │                                   │                          ├── start_llama()     │
    │                                   │                          ├── 复制到media/qqbot │
    │                                   │                          ├── 写.task_flags     │
    │                                   │                          ├── "DONE: path"      │
    │                                   │    ← exec 完成 ─────────│                      │
    │                                   │                          │                      │
    │    ← announce ("DONE: path") ────│                          │                      │
    │                                   │                          │                      │
    │   回复用户: <qqmedia>path</>       │                          │                      │
    │                                   │                          │              llama-watchdog
    │                                   │                          │              (每10分钟保底重启)
```

## 关键约束

1. **主 session 不要 sessions_yield** — yield 持锁，和子 session 的 announce 抢死锁
2. **主 session 不要 exec Python 脚本** — SKILL.md 写得再清楚也可能被忽视，但必须强调
3. **子 session 模型必须是 deepseek/deepseek-v4-flash** — sessions_spawn 的 model 参数
4. **子 session 的 task 是完整 PS 命令** — 不需要子 session 自己思考，只 exec

## Windows Task Scheduler（零 LLM API 消耗）

| 任务名 | 频率 | 脚本 | 作用 |
|------|------|------|------|
| `llama-watchdog` | 每10分钟 | `qqbot/skills/llama-watchdog.ps1` | llama 健康检查，宕机重启 |
| `cleanup-qqbot-orphans` | 每小时 | `qqbot/skills/cleanup_orphans.ps1` | 清理孤儿进程、锁文件、过期 .task_flags |
