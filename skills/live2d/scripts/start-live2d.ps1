# Live2D Bridge 鍚姩鑴氭湰
# 鐢ㄦ硶: powershell -File start-live2d.ps1
# 鎴? powershell -File start-live2d.ps1 -NoBrowser

param(
  [switch]$NoBrowser = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "馃幁 Live2D Bridge 鍚姩" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor DarkGray
Write-Host ""

# 1. Check node
try {
  $nodeVer = node --version 2>&1
  Write-Host "鉁?Node.js: $nodeVer"
} catch {
  Write-Host "鉂?Node.js 鏈畨瑁呮垨涓嶅湪 PATH 涓? -ForegroundColor Red
  Write-Host "   璇峰厛瀹夎: https://nodejs.org/"
  pause
  exit 1
}

# 2. Check ws module
$wsCheck = node -e "require('ws')" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "鈿狅笍  ws 妯″潡鏈畨瑁咃紝姝ｅ湪瀹夎..." -ForegroundColor Yellow
  npm install ws 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "鉂?ws 瀹夎澶辫触" -ForegroundColor Red
    pause
    exit 1
  }
  Write-Host "鉁?ws 宸插畨瑁?
} else {
  Write-Host "鉁?ws 妯″潡宸插氨缁?
}

# 3. Check model
$modelPath = Join-Path $ScriptDir "model\shiki_natsume\final\shiki_natsume.model3.json"
if (Test-Path $modelPath) {
  Write-Host "鉁?Live2D 妯″瀷宸插氨缁? $modelPath"
} else {
  Write-Host "鉂?妯″瀷鏂囦欢涓嶅瓨鍦? $modelPath" -ForegroundColor Red
  Write-Host "   璇峰皢 hack/decrypt_shiki.py 鐩綍澶嶅埗鍒?live2d/model/"
  pause
  exit 1
}

# 4. Kill existing bridge processes (port 19200)
Write-Host ""
Write-Host "馃攳 妫€鏌ユ槸鍚︽湁鏃ц繘绋?.." -ForegroundColor Yellow

# Kill any process on port 19200
$existing = netstat -ano | Select-String "19200" | Select-String "LISTENING"
if ($existing) {
  $pidStr = ($existing -split '\s+')[-1]
  Write-Host "   鍙戠幇鍗犵敤 19200 绔彛鐨勮繘绋?(PID: $pidStr)锛屾鍦ㄥ叧闂?.."
  taskkill /PID $pidStr /F 2>&1 | Out-Null
  Start-Sleep -Seconds 1
  Write-Host "   宸插叧闂棫杩涚▼"
}

# Kill any process on port 19201
$existingWs = netstat -ano | Select-String "19201" | Select-String "LISTENING"
if ($existingWs) {
  $pidStr = ($existingWs -split '\s+')[-1]
  Write-Host "   鍙戠幇鍗犵敤 19201 绔彛鐨勮繘绋?(PID: $pidStr)锛屾鍦ㄥ叧闂?.."
  taskkill /PID $pidStr /F 2>&1 | Out-Null
  Start-Sleep -Seconds 1
}

Write-Host ""

# 5. Start bridge
Write-Host "馃殌 鍚姩 Live2D Bridge..." -ForegroundColor Green
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
Write-Host "鈴?绛夊緟鍚姩瀹屾垚..."
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
  Write-Host "鉁?Live2D Bridge 杩愯涓?" -ForegroundColor Green
} else {
  Write-Host "鈿狅笍  Bridge 杩涚▼宸插惎鍔ㄤ絾 HTTP 灏氭湭鍝嶅簲锛屽彲鑳介渶瑕佺瓑寰呭嚑绉? -ForegroundColor Yellow
}

# 6. Open browser
if (-not $NoBrowser) {
  Write-Host ""
  Write-Host "馃寪 姝ｅ湪鎵撳紑娴忚鍣?.."
  Start-Process "http://localhost:19200"
}

# 7. Print useful commands
Write-Host ""
Write-Host "鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣" -ForegroundColor DarkGray
Write-Host "馃搵 蹇€熸祴璇曞懡浠?" -ForegroundColor Cyan
Write-Host ""
Write-Host "  琛ㄦ儏:  curl http://localhost:19200/api/expression?name=happy"
Write-Host "  鍔ㄤ綔:  curl http://localhost:19200/api/motion?name=mtn_01"
Write-Host "  娑堟伅:  curl http://localhost:19200/api/message?text=銇撱倱銇仭銇?
Write-Host "  璇磋瘽:  curl http://localhost:19200/api/speak?action=start&text=銇娿伅銈堛亞"
Write-Host "  缁勫悎:  curl http://localhost:19200/api/emotion?expression=happy&text=濂姐亶"
Write-Host "  閲嶇疆:  curl http://localhost:19200/api/reset"
Write-Host "  鐘舵€?  curl http://localhost:19200/api/status"
Write-Host "鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣" -ForegroundColor DarkGray
Write-Host ""
Write-Host "鎸変换鎰忛敭鍙叧闂?Bridge (Ctrl+C 涔熷彲)..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup
Write-Host ""
Write-Host "馃洃 鍏抽棴 Live2D Bridge..." -ForegroundColor Yellow
$process.Kill()
Write-Host "   宸插叧闂?
