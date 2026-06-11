# start.ps1 — 一键启动全部 Shiki 服务
# Usage: .\start.ps1
# 
# 启动顺序:
#   1. llama-server (从 config.yaml 读取路径, ngl=41 batch=1024/512)
#   2. Live2D Bridge (localhost:19200)
#   3. OpenClaw Gateway

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$scriptRoot = $PSScriptRoot

# ========== 读取 config.yaml ==========
$configPath = Join-Path $scriptRoot "config.yaml"
if (-not (Test-Path $configPath)) {
    Write-Host "ERROR: config.yaml not found at $configPath" -ForegroundColor Red
    Write-Host "Run quick_setup.ps1 first, or copy config.example.yaml → config.yaml" -ForegroundColor Yellow
    exit 1
}
$configRaw = Get-Content $configPath -Raw -Encoding UTF8

function Get-YamlValue($raw, $key) {
    $pattern = "(?m)^\s*${key}\s*:\s*`"?(.+?)`"?\s*$"
    $m = [regex]::Match($raw, $pattern)
    if ($m.Success) { return $m.Groups[1].Value.Trim('"').Trim() }
    return $null
}

$llamaExe   = Get-YamlValue $configRaw 'llama_exe'
$llamaModel = Get-YamlValue $configRaw 'llama_model'
$llamaPort  = Get-YamlValue $configRaw 'llama_port'
if (-not $llamaPort) { $llamaPort = 8080 }
$llamaLogDir = Get-YamlValue $configRaw 'llama_log_dir'
$workspace  = Get-YamlValue $configRaw 'workspace'

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  四季夏目 — Shiki Natsume Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ========== 1. Llama Server ==========
Write-Host "[1/3] llama-server" -ForegroundColor Yellow

function Test-Online($port, $label) {
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:${port}/health" -TimeoutSec 2 -UseBasicParsing
        Write-Host "  ${label} already online (port ${port})" -ForegroundColor Green
        return $true
    } catch {
        return $false
    }
}

if (Test-Online $llamaPort "llama-server") {
    # already up — skip
} else {
    # Validate paths
    if (-not (Test-Path $llamaExe)) {
        Write-Host "  ERROR: llama-server.exe not found: $llamaExe" -ForegroundColor Red
        Write-Host "  Check config.yaml → llama_exe" -ForegroundColor Yellow
        exit 1
    }
    if (-not (Test-Path $llamaModel)) {
        Write-Host "  ERROR: Model not found: $llamaModel" -ForegroundColor Red
        Write-Host "  Check config.yaml → llama_model" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "  Starting llama-server (ngl=41, batch=1024/512)..."

    # Kill stale processes
    Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1

    $llamaArgs = @(
        '-m', $llamaModel,
        '-c', '120000',
        '--flash-attn', 'on',
        '-ctk', 'q8_0',
        '-ctv', 'q8_0',
        '-ngl', '41',
        '--cpu-moe',
        '--batch-size', '1024',
        '--ubatch-size', '512',
        '--threads', '24',
        '--api-key', '***',
        '-rea', 'off',
        '--jinja',
        '--cache-ram', '5000',
        '--parallel', '1',
        '--kv-unified',
        '--no-mmap',
        '--port', $llamaPort
    )

    $null = Start-Process -FilePath $llamaExe -ArgumentList $llamaArgs -WindowStyle Hidden

    # Wait for ready
    Write-Host "  Waiting for llama-server to load model..."
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $maxWait = 300
    $ready = $false
    while ($sw.Elapsed.TotalSeconds -lt $maxWait) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:${llamaPort}/health" -TimeoutSec 3 -UseBasicParsing
            if ($r.StatusCode -eq 200) {
                $took = [math]::Round($sw.Elapsed.TotalSeconds, 1)
                Write-Host "  llama-server ready! (${took}s)" -ForegroundColor Green
                $ready = $true
                break
            }
        } catch {}
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        Write-Host "  WARNING: llama-server not responding after ${maxWait}s — continuing anyway" -ForegroundColor Yellow
    }
}

# ========== 2. Live2D Bridge ==========
Write-Host "[2/3] Live2D Bridge" -ForegroundColor Yellow

if (Test-Online 19200 "Live2D Bridge") {
    # already up — skip
} else {
    $live2dDir = Join-Path $scriptRoot "live2d"
    if (-not (Test-Path (Join-Path $live2dDir "live2d-bridge.mjs"))) {
        Write-Host "  WARNING: live2d-bridge.mjs not found in $live2dDir" -ForegroundColor Yellow
    } else {
        Write-Host "  Starting Live2D Bridge..."
        $null = Start-Process -FilePath node -ArgumentList "live2d-bridge.mjs" -WorkingDirectory $live2dDir -WindowStyle Hidden
        Start-Sleep -Seconds 2

        $sw2 = [Diagnostics.Stopwatch]::StartNew()
        $ready2 = $false
        while ($sw2.Elapsed.TotalSeconds -lt 10) {
            try {
                $null = Invoke-WebRequest -Uri "http://localhost:19200/api/status" -TimeoutSec 2 -UseBasicParsing
                Write-Host "  Live2D Bridge ready! (port 19200)" -ForegroundColor Green
                $ready2 = $true
                break
            } catch {}
            Start-Sleep -Seconds 1
        }
        if (-not $ready2) {
            Write-Host "  WARNING: Bridge not responding after 10s" -ForegroundColor Yellow
        }
    }
}

# ========== 3. OpenClaw Gateway ==========
Write-Host "[3/3] OpenClaw Gateway" -ForegroundColor Yellow

try {
    $gwStatus = openclaw gateway status 2>&1
    if ($gwStatus -match 'running') {
        Write-Host "  Gateway already running" -ForegroundColor Green
    } else {
        Write-Host "  Starting gateway..."
        openclaw gateway start
        Start-Sleep -Seconds 2
        Write-Host "  Gateway started" -ForegroundColor Green
    }
} catch {
    Write-Host "  WARNING: Could not check/start gateway: $($_.Exception.Message)" -ForegroundColor Yellow
}

# ========== Done ==========
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  All services ready!" -ForegroundColor Green
Write-Host "  llama-server : http://127.0.0.1:${llamaPort}" -ForegroundColor Green
Write-Host "  Live2D Bridge: http://localhost:19200" -ForegroundColor Green
Write-Host "  Gateway      : http://127.0.0.1:18789" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
