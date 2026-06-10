# start-all.ps1 — Launch Live2D bridge + Sakura Desktop Pet
# Usage: .\start-all.ps1
# 
# Prerequisites:
#   1. Live2D model decrypted: D:\AI_Girlfriend\live2d\model\shiki_natsume\final\
#   2. Node.js installed
#   3. Sakura character.json has live2d.enabled = true

$ErrorActionPreference = "Stop"
$projectRoot = "D:\AI_Girlfriend"

Write-Host "=== Starting Live2D + Sakura ===" -ForegroundColor Cyan

# ── 1. Kill old processes ──
Write-Host "[1/3] Cleaning up old processes..."
$oldNode = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq "" }
$oldPython = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*sakura*" }

# ── 2. Start Live2D Bridge ──
Write-Host "[2/3] Starting Live2D Bridge..."
$live2dDir = Join-Path $projectRoot "live2d"
$bridgeProcess = Start-Process -FilePath "node" -ArgumentList "live2d-bridge.mjs" -WorkingDirectory $live2dDir -PassThru -WindowStyle Hidden

# Wait for bridge to come online
Write-Host "  Waiting for bridge on http://localhost:19200..."
$maxWait = 10
for ($i = 0; $i -lt $maxWait; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:19200/api/status" -TimeoutSec 2 -UseBasicParsing
        Write-Host "  Bridge online!" -ForegroundColor Green
        break
    } catch {
        if ($i -eq $maxWait - 1) {
            Write-Host "  WARNING: Bridge not responding after ${maxWait}s" -ForegroundColor Yellow
        }
    }
}

# ── 3. Start Sakura Desktop Pet ──
Write-Host "[3/3] Starting Sakura Desktop Pet..."
$sakuraDir = Join-Path $projectRoot "skills\sakura"
$sakuraProcess = Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $sakuraDir -WindowStyle Normal

Write-Host ""
Write-Host "=== All processes started ===" -ForegroundColor Green
Write-Host "  Live2D Bridge: http://localhost:19200 (node PID: $($bridgeProcess.Id))"
Write-Host "  Sakura: PID $($sakuraProcess.Id)"
Write-Host ""
Write-Host "To stop: Ctrl+C in this window, or:"
Write-Host "  Stop-Process -Id $($bridgeProcess.Id) -Force"
Write-Host "  Stop-Process -Id $($sakuraProcess.Id) -Force"
