<#
.SYNOPSIS
  降级重启 llama-server — 逐级降低 ngl 直到启动成功
  用于 VRAM 不足时手动恢复

.DESCRIPTION
  从 ngl=41 开始尝试，失败则降到 30、20、15，全部失败则用 CPU-only。
  每次尝试会先 kill 所有 llama-server 残存进程。
  最后输出实际生效的 ngl 值。

.PARAMETER ForceNG
  强制使用指定的 ngl 值，跳过逐级尝试

.EXAMPLE
  .\restart_llama_degraded.ps1
  .\restart_llama_degraded.ps1 -ForceNG 20
#>
param(
  [int]$ForceNG = -1
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

# ========== 路径 — 从 config.yaml 读取 ==========
$scriptRoot = $PSScriptRoot
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $scriptRoot)
if ($workspaceRoot -match 'skills$') { $workspaceRoot = Split-Path -Parent $workspaceRoot }

$configPath = Join-Path $workspaceRoot 'config.yaml'
if (-not (Test-Path $configPath)) {
  Write-Host "config.yaml not found at $configPath" -ForegroundColor Red
  exit 1
}
$configRaw = Get-Content $configPath -Raw -Encoding UTF8

function Get-YamlValue($raw, $key) {
  $pattern = "(?m)^\s*${key}\s*:\s*`"?(.+?)`"?\s*$"
  $m = [regex]::Match($raw, $pattern)
  if ($m.Success) { return $m.Groups[1].Value.Trim('"').Trim() }
  return $null
}

$exe    = Get-YamlValue $configRaw 'llama_exe'
$model  = Get-YamlValue $configRaw 'llama_model'
$logDir = Get-YamlValue $configRaw 'llama_log_dir'
$port   = Get-YamlValue $configRaw 'llama_port'
if (-not $port) { $port = 8080 }

if (-not (Test-Path $exe)) {
  Write-Host "llama-server.exe not found: $exe" -ForegroundColor Red
  exit 1
}
if (-not (Test-Path $model)) {
  Write-Host "Model not found: $model" -ForegroundColor Red
  exit 1
}

# ========== 辅助函数 ==========
function Kill-AllLlama {
  $procs = Get-Process llama-server -ErrorAction SilentlyContinue
  if ($procs) {
    $procs | Stop-Process -Force
    Write-Host "Killed $($procs.Count) llama-server process(es)"
  }
  Start-Sleep -Seconds 2
}

function Test-LlamaReady($timeoutSeconds = 120) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $timeoutSeconds) {
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:${port}/health" `
           -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
      if ($r.StatusCode -eq 200) {
        $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        Write-Host "[OK] llama ready after ${elapsed}s" -ForegroundColor Green
        return $true
      }
    } catch {}
    Start-Sleep -Seconds 3
  }
  $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
  Write-Host "[ERROR] llama not ready after ${elapsed}s" -ForegroundColor Red
  return $false
}

# ========== 主流程 ==========
Write-Host "=== Llama Degraded Restart ===" -ForegroundColor Cyan
Write-Host "Exe:   $exe"
Write-Host "Model: $model"
Write-Host "Port:  $port"
Write-Host ""

# 先杀所有残存进程
Write-Host "Cleaning up existing processes..." -ForegroundColor Yellow
Kill-AllLlama

# 确定 ngl 值
$nglTries = @()
if ($ForceNG -ge 0) {
  $nglTries = @($ForceNG)
  Write-Host "Using forced ngl=$ForceNG"
} else {
  $nglTries = @(41, 30, 20, 10, 5, 0)
}

# 逐级尝试
$started = $false
$finalNgl = -1
foreach ($ngl in $nglTries) {
  Kill-AllLlama

  if ($ngl -eq 0) {
    Write-Host "Trying CPU-only (ngl=0)..." -ForegroundColor Yellow
  } else {
    Write-Host "Trying ngl=$ngl..." -ForegroundColor Yellow
  }

  $logFile = if ($logDir) { Join-Path $logDir "llama_degraded_$(Get-Date -Format 'yyyyMMddHHmm').log" } else { $null }

  $args = @(
    '-m', $model,
    '-c', '120000',
    '--flash-attn', 'on',
    '-ctk', 'q8_0',
    '-ctv', 'q8_0',
    '-ngl', $ngl,
    '--cpu-moe',
    '--batch-size', '4096',
    '--ubatch-size', '2048',
    '--threads', '24',
    '--api-key', '123456',
    '-rea', 'off',
    '--jinja',
    '--cache-ram', '5000',
    '--parallel', '1',
    '--kv-unified',
    '--no-mmap',
    '--no-warmup',
    '--port', $port
  )

  $proc = Start-Process -FilePath $exe -ArgumentList $args -NoNewWindow -PassThru

  if (Test-LlamaReady -timeoutSeconds 120) {
    $started = $true
    $finalNgl = $ngl
    break
  } else {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "ngl=$ngl failed, trying next level..." -ForegroundColor DarkYellow
  }
}

if ($started) {
  Write-Host ""
  Write-Host "=== SUCCESS: ngl=$finalNgl, port=$port ===" -ForegroundColor Green
  # 重启 watchdog
  $watchdog = Join-Path (Split-Path -Parent $scriptRoot) 'llama-watchdog.ps1'
  if (Test-Path $watchdog) {
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$watchdog`"" -WindowStyle Hidden
    Write-Host "Watchdog restarted" -ForegroundColor Green
  }
  exit 0
} else {
  Write-Host ""
  Write-Host "=== FAILED: all ngl levels exhausted ===" -ForegroundColor Red
  Write-Host "Try rebooting or checking GPU status."
  exit 1
}
