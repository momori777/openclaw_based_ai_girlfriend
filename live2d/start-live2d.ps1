# Live2D Bridge 启动脚本
# 用法: powershell -File start-live2d.ps1
# 或: powershell -File start-live2d.ps1 -NoBrowser

param(
  [switch]$NoBrowser = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "🎭 Live2D Bridge 启动" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor DarkGray
Write-Host ""

# 1. Check node
try {
  $nodeVer = node --version 2>&1
  Write-Host "✅ Node.js: $nodeVer"
} catch {
  Write-Host "❌ Node.js 未安装或不在 PATH 中" -ForegroundColor Red
  Write-Host "   请先安装: https://nodejs.org/"
  pause
  exit 1
}

# 2. Check ws module
$wsCheck = node -e "require('ws')" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "⚠️  ws 模块未安装，正在安装..." -ForegroundColor Yellow
  npm install ws 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ws 安装失败" -ForegroundColor Red
    pause
    exit 1
  }
  Write-Host "✅ ws 已安装"
} else {
  Write-Host "✅ ws 模块已就绪"
}

# 3. Check model
$modelPath = Join-Path $ScriptDir "model\ren.model3.json"
if (Test-Path $modelPath) {
  Write-Host "✅ Live2D 模型已就绪: $modelPath"
} else {
  Write-Host "❌ 模型文件不存在: $modelPath" -ForegroundColor Red
  Write-Host "   请将 ren_pro_jp/runtime/ 目录复制到 live2d/model/"
  pause
  exit 1
}

# 4. Kill existing bridge processes (port 19200)
Write-Host ""
Write-Host "🔍 检查是否有旧进程..." -ForegroundColor Yellow

# Kill any process on port 19200
$existing = netstat -ano | Select-String "19200" | Select-String "LISTENING"
if ($existing) {
  $pidStr = ($existing -split '\s+')[-1]
  Write-Host "   发现占用 19200 端口的进程 (PID: $pidStr)，正在关闭..."
  taskkill /PID $pidStr /F 2>&1 | Out-Null
  Start-Sleep -Seconds 1
  Write-Host "   已关闭旧进程"
}

# Kill any process on port 19201
$existingWs = netstat -ano | Select-String "19201" | Select-String "LISTENING"
if ($existingWs) {
  $pidStr = ($existingWs -split '\s+')[-1]
  Write-Host "   发现占用 19201 端口的进程 (PID: $pidStr)，正在关闭..."
  taskkill /PID $pidStr /F 2>&1 | Out-Null
  Start-Sleep -Seconds 1
}

Write-Host ""

# 5. Start bridge
Write-Host "🚀 启动 Live2D Bridge..." -ForegroundColor Green
$bridgePath = Join-Path $ScriptDir "live2d-bridge.mjs"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "node"
$psi.Arguments = "`"$bridgePath`""
$psi.WorkingDirectory = $ScriptDir
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $false
$psi.RedirectStandardError = $false

$process = [System.Diagnostics.Process]::Start($psi)

Write-Host "   Bridge PID: $($process.Id)"
Write-Host "   HTTP:  http://localhost:19200"
Write-Host "   WS:    ws://localhost:19201"
Write-Host ""

# Wait for bridge to be ready
Write-Host "⏳ 等待启动完成..."
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Milliseconds 500
  try {
    $r = Invoke-WebRequest -Uri "http://localhost:19200/api/status" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) {
      $ready = $true
      break
    }
  } catch {
    # Not ready yet
  }
}

if ($ready) {
  Write-Host "✅ Live2D Bridge 运行中!" -ForegroundColor Green
} else {
  Write-Host "⚠️  Bridge 进程已启动但 HTTP 尚未响应，可能需要等待几秒" -ForegroundColor Yellow
}

# 6. Open browser
if (-not $NoBrowser) {
  Write-Host ""
  Write-Host "🌐 正在打开浏览器..."
  Start-Process "http://localhost:19200"
}

# 7. Print useful commands
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "📋 快速测试命令:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  表情:  curl http://localhost:19200/api/expression?name=happy"
Write-Host "  动作:  curl http://localhost:19200/api/motion?name=mtn_01"
Write-Host "  消息:  curl http://localhost:19200/api/message?text=こんにちは"
Write-Host "  说话:  curl http://localhost:19200/api/speak?action=start&text=おはよう"
Write-Host "  组合:  curl http://localhost:19200/api/emotion?expression=happy&text=好き"
Write-Host "  重置:  curl http://localhost:19200/api/reset"
Write-Host "  状态:  curl http://localhost:19200/api/status"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
Write-Host "按任意键可关闭 Bridge (Ctrl+C 也可)..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup
Write-Host ""
Write-Host "🛑 关闭 Live2D Bridge..." -ForegroundColor Yellow
$process.Kill()
Write-Host "   已关闭"
