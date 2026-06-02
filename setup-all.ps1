# setup-all.ps1
# ╔═══════════════════════════════════════════════════════════════════╗
# ║  AI Girlfriend — 四季夏目 · 全自动一键部署                          ║
# ║  One command: Models → llama.cpp → OpenClaw → Ready             ║
# ╚═══════════════════════════════════════════════════════════════════╝
#
# 用法:
#   powershell -File setup-all.ps1                          # 全部自动
#   powershell -File setup-all.ps1 -SkipModelDownload       # 跳过下载
#   powershell -File setup-all.ps1 -DryRun                  # 只检查不执行
#   powershell -File setup-all.ps1 -ModelBaseDir "D:\models" # 自定义目录

param(
    [string]$ModelBaseDir = "",
    [switch]$SkipModelDownload,
    [switch]$SkipLlamaSetup,
    [switch]$SkipOpenClawSetup,
    [string]$WorkspacePath = "",
    [string]$GPTSoVitsDir = "",
    [string]$ComfyUIDir = "",
    [switch]$DryRun,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartTime = Get-Date

function wok { param($t) Write-Host "  ✓ $t" -ForegroundColor Green }
function warn { param($t) Write-Host "  ⚠ $t" -ForegroundColor Yellow }
function err { param($t) Write-Host "  ✗ $t" -ForegroundColor Red }
function info { param($t) Write-Host "  $t" -ForegroundColor Gray }
function step { param($n,$t) Write-Host "[$n/7] $t" -ForegroundColor Yellow }

Clear-Host 2>$null
Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║  AI Girlfriend — 四季夏目 · 全自动一键部署                        ║" -ForegroundColor Magenta
Write-Host "║  模型下载 → llama.cpp → OpenClaw → 工作区 → 启动 → 验证          ║" -ForegroundColor Magenta
Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# ═══ 0. 环境检查 ═══
step 0 "环境检查"
$disk = Get-PSDrive -Name ((Get-Location).Drive.Name) -ErrorAction SilentlyContinue
if ($disk) {
    $freeGB = [math]::Round($disk.Free/1GB,1)
    info "磁盘剩余: $freeGB GB"
    if ($freeGB -lt 50) { warn "磁盘空间不足50GB！模型+工具需要~35GB" }
}
try { Test-Connection huggingface.co -Count 1 -Quiet -Timeout 5 | Out-Null; wok "网络 OK" } catch { warn "网络不通 huggingface.co" }
if (Get-Command git -ErrorAction SilentlyContinue) { wok "git: $(git --version 2>&1)" } else { warn "未安装 git" }
if (Get-Command python -ErrorAction SilentlyContinue) { wok "python: $(python --version 2>&1)" } else { warn "未安装 Python" }
Write-Host ""

if ($DryRun) { Write-Host "DRY RUN 完成。" -ForegroundColor Cyan; exit 0 }

# ═══ 1. 模型下载 ═══
step 1 "下载模型 (~29 GB)"
if ($SkipModelDownload) { info "已跳过" }
else {
    if (-not $ModelBaseDir) { $ModelBaseDir = "$ScriptDir\models" }
    if (-not (Get-Command huggingface-cli -ErrorAction SilentlyContinue)) {
        pip install huggingface_hub 2>&1 | Out-Null
    }
    $dl = Join-Path $ScriptDir "download-models.ps1"
    if (Test-Path $dl) {
        info "调用 download-models.ps1..."
        & powershell -File $dl -BaseDir $ModelBaseDir
        if ($LASTEXITCODE -eq 0) { wok "模型下载完成 → $ModelBaseDir" } else { warn "部分失败" }
    } else { err "找不到 download-models.ps1" }
}
Write-Host ""

# ═══ 2. llama.cpp 配置 ═══
step 2 "配置 llama.cpp (自动检测硬件)"
if ($SkipLlamaSetup) { info "已跳过" }
else {
    $sl = Join-Path $ScriptDir "setup-llama.ps1"
    if (Test-Path $sl) {
        info "调用 setup-llama.ps1..."
        & powershell -File $sl -SkipPrompt
        if ($LASTEXITCODE -eq 0) {
            wok "llama.cpp 配置完成"
            if (Test-Path "$ScriptDir\llama-config\launch-llama.ps1") { wok "启动脚本: llama-config\launch-llama.ps1" }
        } else { warn "部分失败" }
    } else { err "找不到 setup-llama.ps1" }
}
Write-Host ""

# ═══ 3. OpenClaw 安装 ═══
step 3 "安装 OpenClaw"
if ($SkipOpenClawSetup) { info "已跳过" }
else {
    $so = Join-Path $ScriptDir "setup-openclaw.ps1"
    if (Test-Path $so) {
        info "调用 setup-openclaw.ps1..."
        $ocArgs = @("-File", $so, "-SkipDeploy")
        if ($WorkspacePath) { $ocArgs += @("-WorkspacePath", $WorkspacePath) }
        & powershell @ocArgs
        if ($LASTEXITCODE -eq 0) { wok "OpenClaw 已安装" } else { warn "部分失败" }
    } else { err "找不到 setup-openclaw.ps1" }
}
Write-Host ""

# ═══ 4. 工作区部署 + 路径 ═══
step 4 "部署工作区 + 路径配置"
if (-not $WorkspacePath) { $WorkspacePath = "$env:USERPROFILE\.openclaw\workspace" }
$WorkspacePath = [IO.Path]::GetFullPath($WorkspacePath)
info "目标: $WorkspacePath"

# 交互式收集路径
if (-not $GPTSoVitsDir) {
    Write-Host "  ── GPT-SoVITS 路径 ──" -ForegroundColor Cyan
    $GPTSoVitsDir = Read-Host "  GPT-SoVITS 安装目录 (留空跳过)"
}
if (-not $ComfyUIDir) {
    Write-Host "  ── ComfyUI 路径 ──" -ForegroundColor Cyan
    $ComfyUIDir = Read-Host "  ComfyUI 安装目录 (留空跳过)"
}

# 复制文件 (不覆盖已存在)
$files = @("AGENTS.md","SOUL.md","IDENTITY.md","USER.md","HEARTBEAT.md","TOOLS.md","config-patch.json","models.yaml",".gitignore")
foreach ($f in $files) {
    $dst = Join-Path $WorkspacePath $f
    if (Test-Path (Join-Path $ScriptDir $f) -and -not (Test-Path $dst)) {
        Copy-Item (Join-Path $ScriptDir $f) $dst -Force
    }
}
# skills
$sd = Join-Path $WorkspacePath "skills"
if (-not (Test-Path $sd)) { New-Item -ItemType Directory $sd -Force | Out-Null }
Copy-Item "$ScriptDir\skills\*" $sd -Recurse -Force
# runtime dirs
foreach ($d in @("$WorkspacePath\memory\role_play","$WorkspacePath\media\qqbot\audio","$WorkspacePath\media\qqbot\images")) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }
}
# path map
@{gpt_sovits_dir=$GPTSoVitsDir;comfyui_dir=$ComfyUIDir;workspace=$WorkspacePath;created_at=(Get-Date -Format "o")} | ConvertTo-Json | Set-Content (Join-Path $WorkspacePath "path-map.json") -Encoding UTF8
wok "工作区部署完成"
Write-Host ""

# ═══ 5. 路径检查 ═══
step 5 "路径检查 & 修复清单"
Write-Host "  ╔════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "  ║  ⚠️ 以下文件有硬编码路径，需手动修改！                  ║" -ForegroundColor Yellow
Write-Host "  ╚════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

$edits = @(
    @{F="$WorkspacePath\skills\tts\tts_call.py"; V=@("WEBUI_DIR","OUTPUT_DIR","LLAMA_EXE_PATH","LLAMA_MODEL_PATH","RESTART_SCRIPT")}
    @{F="$WorkspacePath\skills\comfyui\comfyui_call.py"; V=@("COMFYUI_ROOT","PYTHON_PATH","CHECKPOINTS_DIR","OUTPUT_DIR","LLAMA_EXE_PATH","LLAMA_MODEL_PATH","RESTART_SCRIPT")}
    @{F="$WorkspacePath\skills\tts\SKILL.md"; V=@("PS命令中的所有路径")}
    @{F="$WorkspacePath\skills\comfyui\SKILL.md"; V=@("PS命令中的所有路径")}
    @{F="$WorkspacePath\skills\llama-watchdog.ps1"; V=@("restart-llama.ps1路径","日志目录")}
    @{F="$WorkspacePath\skills\cleanup_orphans.ps1"; V=@("workspace路径","task_flags目录")}
)
foreach ($e in $edits) {
    Write-Host "  📄 $($e.F)" -ForegroundColor White
    foreach ($v in $e.V) { Write-Host "     → $v" -ForegroundColor Yellow }
    Write-Host ""
}
Write-Host "  💡 用 VS Code 全局替换: Ctrl+Shift+H → C:\Users\TK → 你的用户名" -ForegroundColor Cyan
Write-Host ""

# ═══ 6. 启动服务 ═══
step 6 "启动服务"
if ($NoStart) { info "已跳过" }
else {
    $ls = "$ScriptDir\llama-config\launch-llama.ps1"
    if (Test-Path $ls) {
        info "启动 llama-server..."
        Start-Process powershell -ArgumentList '-File',$ls -WindowStyle Minimized
        wok "llama-server 已启动 (约12s加载)"
    } else { warn "找不到 launch-llama.ps1" }
    info "启动 OpenClaw Gateway..."
    try { & openclaw gateway start 2>&1 | Out-Null; wok "Gateway 已启动" } catch { warn "手动: openclaw gateway start" }
}
Write-Host ""

# ═══ 7. 验证 ═══
step 7 "验证"
try { $h = Invoke-RestMethod "http://127.0.0.1:8080/health" -Timeout 5; wok "llama-server ✅" } catch { warn "llama-server 未就绪" }
try { & openclaw gateway status 2>&1 | Out-Null; if ($LASTEXITCODE -eq 0) { wok "Gateway ✅" } else { warn "Gateway 未知" } } catch { warn "Gateway 未检测到" }
if (Test-Path "$WorkspacePath\AGENTS.md") { wok "工作区完整 ✅" } else { err "工作区缺失" }
$gguf = Get-ChildItem "$ModelBaseDir\llm\*.gguf","$ScriptDir\models\llm\*.gguf","$ScriptDir\llm\*.gguf" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($gguf) { wok "LLM模型: $($gguf.Name) ✅" } else { warn "未找到 .gguf" }
Write-Host ""

# ═══ 完成 ═══
$elapsed = [math]::Round(((Get-Date)-$StartTime).TotalMinutes,1)
Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           🎉 AI Girlfriend — 四季夏目 · 部署完成！               ║" -ForegroundColor Green
Write-Host "║           总耗时: ${elapsed}min | 工作区: $WorkspacePath" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  📋 必做清单:" -ForegroundColor Yellow
Write-Host "    1. 修改 skills/*.py + SKILL.md 中的硬编码路径 (见Step 5)" -ForegroundColor White
Write-Host "    2. 修改 USER.md (你的名字/称呼)" -ForegroundColor White
Write-Host "    3. 配置 QQ Bot 通道" -ForegroundColor White
Write-Host ""
Write-Host "  🚀 日常启动:" -ForegroundColor Cyan
Write-Host "    powershell -File start-girlfriend.ps1" -ForegroundColor White
Write-Host "    openclaw gateway --open  # 打开 Web Chat" -ForegroundColor White
Write-Host ""

# 生成快捷启动脚本
@"
# start-girlfriend.ps1 — AI Girlfriend 快速启动 (由 setup-all.ps1 生成)
Write-Host "🌸 启动 AI Girlfriend..." -ForegroundColor Magenta
`$launch = "$ScriptDir\llama-config\launch-llama.ps1"
if ((Test-Path `$launch) -and -not (Get-Process llama-server -EA 0)) {
    Start-Process powershell -ArgumentList '-File',`$launch -WindowStyle Minimized
    Write-Host "llama-server 启动中..." -ForegroundColor Green
} else { Write-Host "llama-server 已在运行" -ForegroundColor Green }
try { openclaw gateway start 2>`$null; Write-Host "Gateway 已启动" -ForegroundColor Green } catch { Write-Host "请手动: openclaw gateway start" -ForegroundColor Yellow }
Write-Host "✅ 准备就绪。打开浏览器: http://127.0.0.1:18789" -ForegroundColor Green
"@ | Set-Content (Join-Path $ScriptDir "start-girlfriend.ps1") -Encoding UTF8
wok "已生成 start-girlfriend.ps1 (日常一键启动)"
