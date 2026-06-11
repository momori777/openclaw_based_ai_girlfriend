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
    [switch]$SkipSakuraSetup,
    [switch]$SkipBotConfig,
    [string]$QQAppId = "",
    [string]$QQClientSecret = "",
    [string]$TGBotToken = "",
    [string]$WorkspacePath = "",
    [string]$GPTSoVitsDir = "",
    [string]$ComfyUIDir = "",
    [string]$SakuraReleaseUrl = "",
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
function step { param($n,$t) Write-Host "[$n/9] $t" -ForegroundColor Yellow }

Clear-Host 2>$null
Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║  AI Girlfriend — 四季夏目 · 全自动一键部署                        ║" -ForegroundColor Magenta
Write-Host "║  模型下载 → llama.cpp → OpenClaw → Sakura → 工作区 → 验证       ║" -ForegroundColor Magenta
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
# config.yaml (路径配置)
# 注意: config.yaml 由 quick_setup.ps1 生成，此处仅创建目录结构
wok "工作区部署完成"
Write-Host ""

# ═══ 5. Bot Token 配置 ═══
step 5 "配置 QQ Bot + Telegram Bot Token"

if ($SkipBotConfig) {
    info "已跳过 (--skip-bot-config)"
} else {
    $qqbotConfigFile = Join-Path $ScriptDir "config-qqbot.json"
    $tgConfigFile = Join-Path $ScriptDir "config-telegram.json"

    # QQ Bot
    if (-not $QQAppId) {
        Write-Host "  ── QQ Bot 凭证 ──" -ForegroundColor Cyan
        Write-Host "  (去 https://q.qq.com/ 创建机器人获取 AppID 和 ClientSecret)" -ForegroundColor Gray
        $QQAppId = Read-Host "  QQ AppID (留空跳过)"
    }
    $qqSecret = $QQClientSecret
    if ($QQAppId -and -not $qqSecret) {
        $qqSecret = Read-Host "  QQ ClientSecret"
    }

    # Telegram Bot
    if (-not $TGBotToken) {
        Write-Host "  ── Telegram Bot Token ──" -ForegroundColor Cyan
        Write-Host "  (去 https://t.me/BotFather 发 /newbot 创建 Bot 获取 Token)" -ForegroundColor Gray
        $TGBotToken = Read-Host "  Telegram Bot Token (留空跳过)"
    }

    # 应用 QQ Bot 配置
    if ($QQAppId -and $qqSecret) {
        info "应用 QQ Bot 配置..."
        try {
            $qqPatch = @(
                @{path="channels.qqbot.enabled"; value=$true},
                @{path="channels.qqbot.name"; value="四季夏目"},
                @{path="channels.qqbot.appId"; value=$QQAppId},
                @{path="channels.qqbot.clientSecret"; value=$qqSecret},
                @{path="channels.qqbot.dmPolicy"; value="open"},
                @{path="channels.qqbot.groupPolicy"; value="open"},
                @{path="channels.qqbot.markdownSupport"; value=$true},
                @{path="channels.qqbot.streaming.mode"; value="partial"},
                @{path="channels.qqbot.urlDirectUpload"; value=$true}
            )
            $qqParams = @{patch=$qqPatch} | ConvertTo-Json -Depth 5 -Compress
            & openclaw gateway call config.patch.apply --json --params $qqParams 2>&1 | Out-Null
            wok "QQ Bot 配置已应用"
        } catch { warn "QQ Bot 配置失败，请稍后手动: config-qqbot.json" }
    } else { info "QQ Bot 已跳过" }

    # 应用 Telegram Bot 配置
    if ($TGBotToken) {
        info "应用 Telegram Bot 配置..."
        try {
            $tgPatch = @(
                @{path="channels.telegram.enabled"; value=$true},
                @{path="channels.telegram.botToken"; value=$TGBotToken},
                @{path="channels.telegram.dmPolicy"; value="pairing"},
                @{path="channels.telegram.replyToMode"; value="first"},
                @{path="channels.telegram.historyLimit"; value=50},
                @{path="channels.telegram.streaming"; value="partial"},
                @{path="channels.telegram.linkPreview"; value=$true},
                @{path="channels.telegram.mediaMaxMb"; value=100},
                @{path="channels.telegram.actions.reactions"; value=$true},
                @{path="channels.telegram.actions.sendMessage"; value=$true},
                @{path="channels.telegram.reactionNotifications"; value="own"}
            )
            $tgParams = @{patch=$tgPatch} | ConvertTo-Json -Depth 5 -Compress
            & openclaw gateway call config.patch.apply --json --params $tgParams 2>&1 | Out-Null
            wok "Telegram Bot 配置已应用"
        } catch { warn "Telegram Bot 配置失败，请稍后手动: config-telegram.json" }
    } else { info "Telegram Bot 已跳过" }
}
Write-Host ""

# ═══ 6. Sakura 桌宠部署 ═══
step 6 "Sakura 桌宠 (下载 Release + 安装依赖)"
if ($SkipSakuraSetup) { info "已跳过" }
else {
    $sakuraDir = Join-Path $ScriptDir "skills\sakura"

    # 检查是否已有 Sakura 源码
    if ((Test-Path "$sakuraDir\main.py") -and (Test-Path "$sakuraDir\requirements.txt")) {
        info "检测到 Sakura 源码 ($sakuraDir)"
    } else {
        warn "未找到 Sakura 源码，正在 Git Clone..."
        if (-not (Test-Path $sakuraDir)) { New-Item -ItemType Directory $sakuraDir -Force | Out-Null }
        git clone https://github.com/Rvosy/Sakura.git $sakuraDir 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { wok "Sakura 源码已克隆" } else { warn "Clone 失败 (可能被墙)，请手动下载: https://github.com/Rvosy/Sakura" }
    }

    # 下载 runtime Release（内置 Python 环境）
    $runtimeDir = "$sakuraDir\runtime"
    if (Test-Path "$runtimeDir\python.exe") {
        wok "runtime (内置 Python) 已就绪"
    } else {
        info "需要下载 Sakura Release 包 (含内置 python.exe)..."
        # 尝试获取最新 Release URL，否则使用用户指定的
        if (-not $SakuraReleaseUrl) {
            try {
                $ghApi = "https://api.github.com/repos/Rvosy/Sakura/releases/latest"
                $release = Invoke-RestMethod $ghApi -Timeout 10 -ErrorAction Stop
                $asset = $release.assets | Where-Object { $_.name -match "windows-x64\.zip" } | Select-Object -First 1
                if ($asset) { $SakuraReleaseUrl = $asset.browser_download_url }
                info "最新 Release: $($release.tag_name)"
            } catch {
                warn "无法获取 GitHub Release (可能被墙)"
            }
        }

        if ($SakuraReleaseUrl) {
            $zipPath = "$env:TEMP\sakura-release.zip"
            info "下载: $SakuraReleaseUrl"
            try {
                Invoke-WebRequest $SakuraReleaseUrl -OutFile $zipPath -Timeout 600
                wok "下载完成 ($([math]::Round((Get-Item $zipPath).Length/1MB,1)) MB)"
                info "解压 runtime..."
                Expand-Archive $zipPath -DestinationPath $env:TEMP\sakura-extract -Force
                $extractedRuntime = Get-ChildItem "$env:TEMP\sakura-extract" -Directory -Filter "runtime" -Recurse -Depth 1 | Select-Object -First 1
                if ($extractedRuntime) {
                    Copy-Item $extractedRuntime.FullName $runtimeDir -Recurse -Force
                    wok "runtime 已部署到 $runtimeDir"
                } else {
                    warn "Release 包中未找到 runtime 目录"
                }
                Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
                Remove-Item "$env:TEMP\sakura-extract" -Recurse -Force -ErrorAction SilentlyContinue
            } catch {
                err "下载 Sakura Release 失败: $_"
                warn "请手动从 https://github.com/Rvosy/Sakura/releases 下载 windows-x64.zip 并解压 runtime/ 到 $runtimeDir"
            }
        } else {
            warn "无 Release URL。请手动下载: https://github.com/Rvosy/Sakura/releases"
            warn "解压后把 runtime/ 文件夹放到 $runtimeDir"
        }
    }

    # 安装 Python 依赖
    if (Test-Path "$sakuraDir\requirements.txt") {
        info "安装 Sakura Python 依赖..."
        $pyExe = if (Test-Path "$runtimeDir\python.exe") { "$runtimeDir\python.exe" } else { "python" }
        & $pyExe -m pip install -r "$sakuraDir\requirements.txt" -i https://mirrors.aliyun.com/pypi/simple --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple --extra-index-url https://pypi.org/simple 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { wok "Sakura 依赖安装完成" } else { warn "部分依赖安装失败，请在 Sakura 目录手动运行 install.bat" }
    }

    # Playwright 浏览器
    $pyExe = if (Test-Path "$runtimeDir\python.exe") { "$runtimeDir\python.exe" } else { "python" }
    info "安装 Playwright 浏览器..."
    & $pyExe -m playwright install chromium 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { wok "Playwright Chromium 已安装" } else { warn "Playwright 安装失败，部分功能不可用" }
}
Write-Host ""

# ═══ 7. 路径检查 ═══
step 7 "路径检查 & 修复清单"
Write-Host "  ╔════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "  ║  ⚠️ 以下文件有硬编码路径，需手动修改！                  ║" -ForegroundColor Yellow
Write-Host "  ╚════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

$edits = @(
    @{F="$WorkspacePath\skills\tts\tts_call.py"; V=@("从 config.yaml 读取路径")}
    @{F="$WorkspacePath\skills\comfyui\comfyui_call.py"; V=@("从 config.yaml 读取路径")}
    @{F="$WorkspacePath\skills\tts\run_tts.ps1"; V=@("从 config.yaml 读取路径")}
    @{F="$WorkspacePath\skills\comfyui\run_comfyui.ps1"; V=@("从 config.yaml 读取路径")}
    @{F="$WorkspacePath\skills\llama-watchdog.ps1"; V=@("已改为从 config.yaml 读取")}
    @{F="$WorkspacePath\skills\cleanup_orphans.ps1"; V=@("锁文件路径已修正")}
    @{F="$WorkspacePath\start.ps1"; V=@("从 config.yaml 读取路径")}
)
foreach ($e in $edits) {
    Write-Host "  📄 $($e.F)" -ForegroundColor White
    foreach ($v in $e.V) { Write-Host "     → $v" -ForegroundColor Yellow }
    Write-Host ""
}
Write-Host "  💡 用 VS Code 全局替换: Ctrl+Shift+H → C:\Users\TK → 你的用户名" -ForegroundColor Cyan
Write-Host ""

# ═══ 8. 启动服务 ═══
step 8 "启动服务"
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

# ═══ 9. 验证 ═══
step 9 "验证"
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
Write-Host "    1. 修改 skills/*.py + SKILL.md 中的硬编码路径 (见Step 6)" -ForegroundColor White
Write-Host "    2. 修改 USER.md (你的名字/称呼)" -ForegroundColor White
Write-Host "    3. (如跳过Step 5) 手动配置 QQ/Telegram Bot Token" -ForegroundColor White
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
