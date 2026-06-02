# setup-openclaw.ps1
# AI Girlfriend — 四季夏目 · OpenClaw 一键部署 (Windows PowerShell)
#
# 自动完成:
#   1. 检测 Node.js → 缺失则安装
#   2. 安装 OpenClaw Gateway (via 官方安装脚本)
#   3. 部署 AI Girlfriend 工作区到 OpenClaw workspace
#   4. 应用 config-patch.json (本地 LLM 上下文窗口配置)
#   5. 启动 OpenClaw Gateway daemon
#   6. 验证安装
#
# 用法:
#   powershell -File setup-openclaw.ps1
#   powershell -File setup-openclaw.ps1 -WorkspacePath "D:\my-gf-workspace"
#   powershell -File setup-openclaw.ps1 -SkipNodeInstall -SkipDeploy
#
# 前置:
#   - 已运行 download-models.ps1 下载模型
#   - (可选) 已运行 setup-llama.ps1 配置 llama.cpp

param(
    [string]$WorkspacePath = "",
    [switch]$SkipNodeInstall,
    [switch]$SkipDeploy,
    [switch]$NoOnboard,
    [switch]$SkipDaemon
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ============================================================================
# Banner
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║  AI Girlfriend — 四季夏目 · OpenClaw 一键部署              ║" -ForegroundColor Magenta
Write-Host "║  Setup OpenClaw Gateway + Deploy AI Girlfriend Workspace   ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# ============================================================================
# Step 1: Check / Install Node.js
# ============================================================================
if ($SkipNodeInstall) {
    Write-Host "[1/5] Skipping Node.js check (--SkipNodeInstall)" -ForegroundColor DarkGray
} else {
    Write-Host "[1/5] Checking Node.js..." -ForegroundColor Yellow

    $nodeVersion = $null
    try {
        $nodeVersion = & node --version 2>$null
    } catch {}

    $needsNode = $false
    if (-not $nodeVersion) {
        $needsNode = $true
    } else {
        $ver = [Version]($nodeVersion -replace '^v', '')
        if ($ver.Major -lt 22) {
            Write-Host "  Node $nodeVersion found, but needs v22.16+ (v24 recommended)" -ForegroundColor Yellow
            $needsNode = $true
        }
    }

    if (-not $needsNode) {
        Write-Host "  Node.js $nodeVersion — OK" -ForegroundColor Green
    } else {
        Write-Host "  Installing Node.js..." -ForegroundColor Yellow

        # Try winget first (Windows package manager)
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Host "  Installing via winget..." -ForegroundColor Gray
            winget install OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements
            Write-Host "  Node.js installed via winget." -ForegroundColor Green
            Write-Host ""
            Write-Host "  ⚠️  IMPORTANT: Restart your PowerShell window, then re-run this script." -ForegroundColor Yellow
            Write-Host "     Node was just installed and won't be available in this session." -ForegroundColor Yellow
            exit 0
        }

        # Fallback: fnm (Fast Node Manager) via PowerShell
        Write-Host "  winget not found. Installing via fnm (Fast Node Manager)..." -ForegroundColor Gray
        try {
            winget install Schniz.fnm --silent --accept-source-agreements --accept-package-agreements
        } catch {
            Write-Host "  [ERROR] Cannot install Node.js automatically." -ForegroundColor Red
            Write-Host "  Please install manually: https://nodejs.org/ (v22+ or v24+)" -ForegroundColor Red
            Write-Host "  After installing, re-run this script." -ForegroundColor Yellow
            exit 1
        }

        Write-Host "  Node.js installed via fnm." -ForegroundColor Green
        Write-Host ""
        Write-Host "  ⚠️  IMPORTANT: Restart your PowerShell window, then re-run this script." -ForegroundColor Yellow
        exit 0
    }
}

# ============================================================================
# Step 2: Install OpenClaw
# ============================================================================
Write-Host "[2/5] Installing OpenClaw..." -ForegroundColor Yellow

$openclawExe = Get-Command openclaw -ErrorAction SilentlyContinue

if ($openclawExe) {
    $ocVersion = & openclaw --version 2>&1
    Write-Host "  OpenClaw already installed: $ocVersion" -ForegroundColor Green
    Write-Host "  Path: $($openclawExe.Source)" -ForegroundColor Gray
} else {
    Write-Host "  Downloading and installing OpenClaw..." -ForegroundColor Yellow
    Write-Host "  Using official install script: https://openclaw.ai/install.ps1" -ForegroundColor Gray

    try {
        if ($NoOnboard) {
            & ([scriptblock]::Create((iwr -useb https://openclaw.ai/install.ps1))) -NoOnboard
        } else {
            iwr -useb https://openclaw.ai/install.ps1 | iex
        }
    } catch {
        Write-Host "  [ERROR] OpenClaw installation failed: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Manual install options:" -ForegroundColor Yellow
        Write-Host "    npm:  npm install -g openclaw@latest && openclaw onboard --install-daemon" -ForegroundColor White
        Write-Host "    docs: https://docs.openclaw.ai/zh-CN/install" -ForegroundColor White
        exit 1
    }

    # Verify
    $openclawExe = Get-Command openclaw -ErrorAction SilentlyContinue
    if (-not $openclawExe) {
        Write-Host "  [ERROR] openclaw CLI not found after install." -ForegroundColor Red
        Write-Host "  Try restarting your terminal and running: openclaw --version" -ForegroundColor Yellow
        Write-Host "  If still not found, add npm global bin to PATH:" -ForegroundColor Yellow
        Write-Host '    $npmPrefix = npm prefix -g' -ForegroundColor White
        Write-Host '    [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$npmPrefix", "User")' -ForegroundColor White
        exit 1
    }

    Write-Host "  OpenClaw installed successfully!" -ForegroundColor Green
    $ocVersion = & openclaw --version 2>&1
    Write-Host "  Version: $ocVersion" -ForegroundColor Gray
}

# ============================================================================
# Step 3: Deploy AI Girlfriend Workspace
# ============================================================================
if ($SkipDeploy) {
    Write-Host "[3/5] Skipping workspace deployment (--SkipDeploy)" -ForegroundColor DarkGray
} else {
    Write-Host "[3/5] Deploying AI Girlfriend workspace..." -ForegroundColor Yellow

    # Determine OpenClaw workspace directory
    if (-not $WorkspacePath) {
        $WorkspacePath = "$env:USERPROFILE\.openclaw\workspace"
    }
    $WorkspacePath = [System.IO.Path]::GetFullPath($WorkspacePath)

    Write-Host "  Target workspace: $WorkspacePath" -ForegroundColor Gray

    # Create workspace directory if needed
    if (-not (Test-Path $WorkspacePath)) {
        New-Item -ItemType Directory -Path $WorkspacePath -Force | Out-Null
    }

    # Copy workspace files (non-destructive — won't overwrite existing user-modified files)
    $deployFiles = @(
        "AGENTS.md",
        "SOUL.md",
        "IDENTITY.md",
        "USER.md",
        "HEARTBEAT.md",
        "TOOLS.md",
        "config-patch.json",
        "models.yaml",
        ".gitignore"
    )

    Write-Host "  Copying workspace config files..." -ForegroundColor Gray
    foreach ($file in $deployFiles) {
        $src = Join-Path $ScriptDir $file
        $dst = Join-Path $WorkspacePath $file

        if (Test-Path $src) {
            if (Test-Path $dst) {
                Write-Host "    ⏭  $file (already exists, skipped)" -ForegroundColor DarkGray
            } else {
                Copy-Item -Path $src -Destination $dst -Force
                Write-Host "    ✓  $file" -ForegroundColor Green
            }
        } else {
            Write-Host "    ✗  $file (source not found)" -ForegroundColor Yellow
        }
    }

    # Copy skill directories
    $skillDirs = @("skills")
    Write-Host "  Copying skill directories..." -ForegroundColor Gray
    foreach ($dir in $skillDirs) {
        $src = Join-Path $ScriptDir $dir
        $dst = Join-Path $WorkspacePath $dir

        if (Test-Path $src) {
            if (-not (Test-Path $dst)) {
                New-Item -ItemType Directory -Path $dst -Force | Out-Null
            }
            Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force
            Write-Host "    ✓  $dir/" -ForegroundColor Green
        } else {
            Write-Host "    ✗  $dir/ (source not found)" -ForegroundColor Yellow
        }
    }

    # Create runtime directories
    $runtimeDirs = @(
        "$WorkspacePath\memory",
        "$WorkspacePath\memory\role_play",
        "$WorkspacePath\media\qqbot\audio",
        "$WorkspacePath\media\qqbot\images"
    )
    Write-Host "  Creating runtime directories..." -ForegroundColor Gray
    foreach ($dir in $runtimeDirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "    ✓  $dir" -ForegroundColor Green
        }
    }

    Write-Host "  Workspace deployed to: $WorkspacePath" -ForegroundColor Green
    Write-Host ""
    Write-Host "  ⚠️  IMPORTANT — Paths to update in your workspace:" -ForegroundColor Yellow
    Write-Host "    $WorkspacePath\skills\tts\tts_call.py" -ForegroundColor White
    Write-Host "    $WorkspacePath\skills\tts\SKILL.md" -ForegroundColor White
    Write-Host "    $WorkspacePath\skills\comfyui\comfyui_call.py" -ForegroundColor White
    Write-Host "    $WorkspacePath\skills\comfyui\SKILL.md" -ForegroundColor White
    Write-Host "    $WorkspacePath\skills\llama-watchdog.ps1" -ForegroundColor White
    Write-Host "  Update PYTHON_PATH, WEBUI_DIR, COMFYUI_ROOT, LLAMA_MODEL_PATH etc." -ForegroundColor Yellow
}

# ============================================================================
# Step 4: Apply Config Patch
# ============================================================================
Write-Host "[4/5] Applying configuration..." -ForegroundColor Yellow

# Check if Gateway is running
$gatewayRunning = $false
try {
    $status = & openclaw gateway status 2>&1
    if ($LASTEXITCODE -eq 0) {
        $gatewayRunning = $true
        Write-Host "  Gateway is running." -ForegroundColor Green
    } else {
        Write-Host "  Gateway is not running." -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Could not check Gateway status (may need to start first)." -ForegroundColor Yellow
}

if ($gatewayRunning) {
    # Apply config patch via gateway
    $patchFile = Join-Path $WorkspacePath "config-patch.json"
    if (Test-Path $patchFile) {
        Write-Host "  Applying config-patch.json..." -ForegroundColor Gray
        try {
            & openclaw gateway config.patch.apply --file $patchFile 2>&1 | Out-Null
            Write-Host "  Config patch applied." -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️  Could not auto-apply patch. Manual command:" -ForegroundColor Yellow
            Write-Host "     openclaw gateway config.patch.apply" -ForegroundColor White
        }
    } else {
        Write-Host "  config-patch.json not found at $patchFile" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "  ⚠️  Gateway not running. After starting the Gateway, apply the config patch:" -ForegroundColor Yellow
    Write-Host "     1. Start Gateway:  openclaw gateway start" -ForegroundColor White
    Write-Host "     2. Apply patch:    openclaw gateway config.patch.apply" -ForegroundColor White
}

# ============================================================================
# Step 5: Install Gateway Daemon & Start
# ============================================================================
Write-Host "[5/5] Configuring Gateway daemon..." -ForegroundColor Yellow

if (-not $SkipDaemon) {
    # On Windows, OpenClaw uses Task Scheduler or Startup folder
    Write-Host "  Installing Gateway daemon (auto-start on login)..." -ForegroundColor Gray
    try {
        & openclaw gateway install 2>&1 | Out-Null
        Write-Host "  Gateway daemon installed." -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  Could not install daemon automatically." -ForegroundColor Yellow
        Write-Host "     Manual: openclaw gateway install" -ForegroundColor White
    }

    # Start Gateway
    Write-Host "  Starting Gateway..." -ForegroundColor Gray
    try {
        & openclaw gateway start 2>&1 | Out-Null
        Write-Host "  Gateway started!" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  Could not start Gateway." -ForegroundColor Yellow
        Write-Host "     Manual: openclaw gateway start" -ForegroundColor White
    }
} else {
    Write-Host "  Skipping daemon setup (--SkipDaemon)" -ForegroundColor DarkGray
}

# ============================================================================
# Verification
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ OpenClaw + AI Girlfriend Setup Complete!               ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "  Verification commands:" -ForegroundColor Cyan
Write-Host "    openclaw --version        # Check CLI" -ForegroundColor White
Write-Host "    openclaw doctor           # Check configuration" -ForegroundColor White
Write-Host "    openclaw gateway status   # Check Gateway status" -ForegroundColor White
Write-Host ""

Write-Host "  Workspace: $WorkspacePath" -ForegroundColor Cyan
Write-Host ""

# Final checklist
Write-Host "  📋 Post-setup Checklist:" -ForegroundColor Yellow
Write-Host "    ☐ 1. Update paths in skills/tts/tts_call.py" -ForegroundColor White
Write-Host "    ☐ 2. Update paths in skills/comfyui/comfyui_call.py" -ForegroundColor White
Write-Host "    ☐ 3. Verify llama-server is running: http://127.0.0.1:8080/health" -ForegroundColor White
Write-Host "    ☐ 4. Apply config-patch.json: openclaw gateway config.patch.apply" -ForegroundColor White
Write-Host "    ☐ 5. Configure QQ Bot channel (see README.md)" -ForegroundColor White
Write-Host "    ☐ 6. Test: send a message through your QQ Bot" -ForegroundColor White
Write-Host ""

# Print next steps
Write-Host "  🚀 Quick Start:" -ForegroundColor Cyan
Write-Host "    # Start llama-server (in a separate window)" -ForegroundColor Gray
Write-Host "    Start-Process powershell -ArgumentList '-File $ScriptDir\llama-config\launch-llama.ps1' -WindowStyle Hidden" -ForegroundColor White
Write-Host ""
Write-Host "    # Check everything is running" -ForegroundColor Gray
Write-Host "    openclaw gateway status" -ForegroundColor White
Write-Host "    curl http://127.0.0.1:8080/health" -ForegroundColor White
Write-Host ""

Write-Host "  文档: https://docs.openclaw.ai/zh-CN" -ForegroundColor DarkGray
Write-Host "  项目: https://github.com/momori777/openclaw_based_ai_girlfriend" -ForegroundColor DarkGray
Write-Host "  模型: https://huggingface.co/TAOTAO777/ai-girlfriend-natsume" -ForegroundColor DarkGray
Write-Host ""
