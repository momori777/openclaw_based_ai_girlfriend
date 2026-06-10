<#
.SYNOPSIS
  降级重启 llama-server — ngl 固定 41，逐级降低 batch_size/ubatch_size
  用于 VRAM 不足时手动恢复

.EXAMPLE
  .\restart_llama_degraded.ps1
  .\restart_llama_degraded.ps1 -ForceBatch 1024
#>
param(
  [int]$ForceBatch = -1
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
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:${port}/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
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
Write-Host "=== Llama Degraded Restart (ngl=41, batch downscaling) ===" -ForegroundColor Cyan
Write-Host "Exe:   $exe"
Write-Host "Model: $model"
Write-Host "Port:  $port"
Write-Host ""

# 先杀所有残存进程
Write-Host "Cleaning up existing processes..." -ForegroundColor Yellow
Kill-AllLlama

# 降级表：三个并行数组
$batchSizes    = @(4096, 2048, 1024, 512)
$ubatchSizes   = @(2048, 1024, 512,  256)
$batchLabels   = @('4096/2048', '2048/1024', '1024/512', '512/256')
$startIdx      = 0

if ($ForceBatch -gt 0) {
  $found = $false
  for ($i = 0; $i -lt $batchSizes.Count; $i++) {
    if ($batchSizes[$i] -eq $ForceBatch) {
      $startIdx = $i
      $found = $true
      Write-Host "Using forced batch=$ForceBatch"
      break
    }
  }
  if (-not $found) {
    Write-Host "Invalid batch size $ForceBatch, using full table" -ForegroundColor Yellow
  }
}

$started = $false
$finalBatch = 0
$finalUbatch = 0

for ($i = $startIdx; $i -lt $batchSizes.Count; $i++) {
  Kill-AllLlama
  $bs = $batchSizes[$i]
  $us = $ubatchSizes[$i]
  $lb = $batchLabels[$i]
  Write-Host "Trying batch=$lb..." -ForegroundColor Yellow

  $logFile = if ($logDir) { Join-Path $logDir "llama_degraded_$(Get-Date -Format 'yyyyMMddHHmm').log" } else { $null }

  $llaArgs = @(
    '-m', $model,
    '-c', '120000',
    '--flash-attn', 'on',
    '-ctk', 'q8_0',
    '-ctv', 'q8_0',
    '-ngl', '41',
    '--cpu-moe',
    '--batch-size', "$bs",
    '--ubatch-size', "$us",
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

  $proc = Start-Process -FilePath $exe -ArgumentList $llaArgs -NoNewWindow -PassThru

  if (Test-LlamaReady -timeoutSeconds 120) {
    $started = $true
    $finalBatch = $bs
    $finalUbatch = $us
    break
  } else {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "batch=$lb failed, trying next level..." -ForegroundColor DarkYellow
  }
}

if ($started) {
  Write-Host ""
  Write-Host "=== SUCCESS: ngl=41, batch=$finalBatch/$finalUbatch, port=$port ===" -ForegroundColor Green
  # 重启 watchdog
  $watchdog = Join-Path (Split-Path -Parent $scriptRoot) 'llama-watchdog.ps1'
  if (Test-Path $watchdog) {
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$watchdog`"" -WindowStyle Hidden
    Write-Host "Watchdog restarted" -ForegroundColor Green
  }
  exit 0
} else {
  Write-Host ""
  Write-Host "=== FAILED: all batch levels exhausted ===" -ForegroundColor Red
  Write-Host "Try rebooting or checking GPU status."
  exit 1
}
