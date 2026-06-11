# llama-watchdog.ps1
# 纯 PowerShell watchdog，不依赖任何 LLM
# 由 Windows Task Scheduler 每 10 分钟触发
# 作用: 检查 llama-server 健康，宕机则自动重启
# 路径: 从 workspace 根目录的 config.yaml 读取

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# ========== 从 config.yaml 读取路径 ==========
$configPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'config.yaml'
if (Test-Path $configPath) {
    $configRaw = Get-Content $configPath -Raw -Encoding UTF8
    function Get-YamlValue($raw, $key) {
        $pattern = "(?m)^\s*${key}\s*:\s*`"?(.+?)`"?\s*$"
        $m = [regex]::Match($raw, $pattern)
        if ($m.Success) { return $m.Groups[1].Value.Trim('"').Trim() }
        return $null
    }
    $logDir = Get-YamlValue $configRaw 'llama_log_dir'
    $restartScript = Get-YamlValue $configRaw 'restart_script'
} else {
    # Fallback 默认路径
    $logDir = "C:\Users\TK\Desktop\vllm\restart-logs"
    $restartScript = "C:\Users\TK\Desktop\vllm\restart-llama.ps1"
}

$logFile = "$logDir\watchdog.log"
$null = New-Item -ItemType Directory -Path $logDir -Force -ErrorAction SilentlyContinue

function Write-WatchdogLog {
    param([string]$Message)
    $elapsed = $stopwatch.ElapsedMilliseconds
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [+${elapsed}ms] $Message"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Write-WatchdogLog "=== watchdog check ==="

# 1. 检查 llama-server 进程
$llamaProc = Get-Process llama-server -ErrorAction SilentlyContinue
if (-not $llamaProc) {
    Write-WatchdogLog "llama-server not running, starting..."
    if ($restartScript -and (Test-Path $restartScript)) {
        & $restartScript
    } else {
        Write-WatchdogLog "no restart script configured"
    }
    Write-WatchdogLog "done"
    exit 0
}

# 2. 检查端口健康
$healthy = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) {
        $healthy = $true
        Write-WatchdogLog "healthy (PID=$($llamaProc.Id))"
    }
}
catch {
    Write-WatchdogLog "port 8080 check failed: $_"
}

if ($healthy) {
    exit 0
}

# 3. 进程在但端口不通 → 重启
Write-WatchdogLog "process alive but port dead, restarting..."
Stop-Process -Id $llamaProc.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
if ($restartScript -and (Test-Path $restartScript)) {
        & $restartScript
    } else {
        Write-WatchdogLog "no restart script configured"
    }
Write-WatchdogLog "done"
exit 0
