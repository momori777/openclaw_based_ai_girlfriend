# setup-llama.ps1
# AI Girlfriend — 四季夏目 · llama.cpp 一键部署 (Windows)
#
# 自动检测硬件: GPU/VRAM, CPU cores, RAM
# 自动推荐并生成最优 llama-server 启动配置
# 自动下载/编译 llama.cpp (可选)
#
# 用法:
#   powershell -File setup-llama.ps1
#   powershell -File setup-llama.ps1 -ModelPath "D:\models\my-model.gguf"
#   powershell -File setup-llama.ps1 -BuildLlama   # 也编译 llama.cpp
#
# 前置:
#   1. 已通过 download-models.ps1 下载模型
#   2. 模型路径默认为 ./llm/ 下的 Qwen GGUF

param(
    [string]$ModelPath = "",
    [int]$ContextSize = 120000,
    [string]$ApiKey = "llama-key-change-me",
    [int]$Port = 8080,
    [switch]$BuildLlama,
    [switch]$DryRun,
    [switch]$SkipPrompt
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Banner
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  AI Girlfriend — 四季夏目 · llama.cpp Auto Setup           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# System Detection
# ============================================================================
Write-Host "[1/5] Detecting hardware..." -ForegroundColor Yellow

$cpuCores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
$totalRamGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
$osName = (Get-CimInstance Win32_OperatingSystem).Caption

# GPU detection via WMI
$gpus = @()
try {
    $wmiGpus = Get-CimInstance Win32_VideoController | Where-Object { $_.AdapterRAM -gt 0 -or $_.Name -match "NVIDIA|AMD|Intel" }
    foreach ($g in $wmiGpus) {
        $vramMB = if ($g.AdapterRAM) { [math]::Round($g.AdapterRAM / 1MB, 0) } else { 0 }
        $gpus += @{ Name = $g.Name; VRAM_GB = [math]::Round($vramMB / 1024, 1); VRAM_MB = $vramMB }
    }
} catch {
    # Fallback: nvidia-smi
    try {
        $nvidiaSmi = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
        if ($nvidiaSmi) {
            foreach ($line in $nvidiaSmi) {
                $parts = $line -split ", "
                if ($parts.Count -ge 2) {
                    $vramMB = [int]($parts[1] -replace '\D', '')
                    $gpus += @{ Name = $parts[0].Trim(); VRAM_GB = [math]::Round($vramMB / 1024, 1); VRAM_MB = $vramMB }
                }
            }
        }
    } catch {}
}

Write-Host "  OS:       $osName" -ForegroundColor Gray
Write-Host "  CPU:      $cpuCores logical cores" -ForegroundColor Gray
Write-Host "  RAM:      $totalRamGB GB" -ForegroundColor Gray

if ($gpus.Count -gt 0) {
    foreach ($g in $gpus) {
        Write-Host "  GPU:      $($g.Name) ($($g.VRAM_GB) GB VRAM)" -ForegroundColor Gray
    }
} else {
    Write-Host "  GPU:      [UNKNOWN — no NVIDIA/AMD GPU detected via WMI]" -ForegroundColor Yellow
    $gpus = @(@{ Name = "Unknown Intel iGPU"; VRAM_GB = 0; VRAM_MB = 0 })
}

# CUDA version detection (for compatibility warnings)
$cudaVersion = ""
$cudaWarning = $false
try {
    $nvccOut = & nvcc --version 2>$null
    if ($nvccOut -match "release (\d+\.\d+)") {
        $cudaVersion = $Matches[1]
        Write-Host "  CUDA:     $cudaVersion" -ForegroundColor Gray
        # CUDA 13.x has known compatibility issues with llama.cpp on Blackwell GPUs
        if ([version]$cudaVersion -ge [version]"13.0") {
            Write-Host "  ⚠️  WARNING: CUDA 13.x may cause 'munmap_chunk(): invalid pointer' crashes!" -ForegroundColor Yellow
            Write-Host "     RTX 50xx (Blackwell) + CUDA 13.x is known to break llama.cpp memory management." -ForegroundColor Yellow
            Write-Host "     Recommend: use pre-built llama.cpp CUDA 12.8 binaries instead of self-compiling." -ForegroundColor Yellow
            Write-Host "     Download from: https://github.com/ggml-org/llama.cpp/releases" -ForegroundColor Yellow
            Write-Host "     Look for: llama-bXXXX-bin-win-cuda-cu12.8-x64.zip" -ForegroundColor Yellow
            $cudaWarning = $true
        }
    }
} catch {
    Write-Host "  CUDA:     [nvcc not found — if using pre-built llama.cpp binaries, this is fine]" -ForegroundColor Gray
}

# Pick primary GPU (first discrete)
$primaryGpu = $gpus | Where-Object { $_.VRAM_GB -gt 2 } | Select-Object -First 1
if (-not $primaryGpu) { $primaryGpu = $gpus[0] }

$vramGB = $primaryGpu.VRAM_GB

# ============================================================================
# Model detection
# ============================================================================
Write-Host "[2/5] Detecting model..." -ForegroundColor Yellow

if (-not $ModelPath) {
    $defaults = @(
        ".\llm\Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf",
        ".\models\llm\Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf",
        "llm\Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf"
    )
    foreach ($p in $defaults) {
        if (Test-Path $p) {
            $ModelPath = (Resolve-Path $p).Path
            break
        }
    }
}

if (-not $ModelPath -or -not (Test-Path $ModelPath)) {
    Write-Host "  No model found. Search paths:" -ForegroundColor Yellow
    foreach ($p in $defaults) { Write-Host "    - $p" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "  Run download-models.ps1 first, or specify -ModelPath." -ForegroundColor Yellow
    Write-Host "  Example: setup-llama.ps1 -ModelPath 'D:\models\qwen.gguf'" -ForegroundColor Yellow
    exit 1
}

$modelSizeGB = [math]::Round((Get-Item $ModelPath).Length / 1GB, 2)
Write-Host "  Model:    $ModelPath" -ForegroundColor Gray
Write-Host "  Size:     $modelSizeGB GB" -ForegroundColor Gray

# ============================================================================
# Configuration Generation
# ============================================================================
Write-Host "[3/5] Generating optimal configuration..." -ForegroundColor Yellow

# ── VRAM budget analysis ──
Write-Host ""
Write-Host "  VRAM Budget Analysis ($($primaryGpu.Name)):" -ForegroundColor Cyan

if ($vramGB -le 0) {
    # CPU-only
    $ngl = 0
    $kvCacheGB = [math]::Min([math]::Floor($totalRamGB * 0.15), 8)
    $ramBudgetGB = $modelSizeGB + $kvCacheGB + 2
    $gpuMode = "CPU-ONLY"
    Write-Host "    Total VRAM:   N/A (no GPU detected)" -ForegroundColor Gray
    Write-Host "    → CPU-only mode" -ForegroundColor Yellow
} elseif ($vramGB -le 4) {
    # Tiny GPU — offload what we can, rest CPU
    $ngl = [math]::Floor($vramGB / 0.5)  # rough: ~500MB per layer
    $kvCacheGB = [math]::Min([math]::Floor($totalRamGB * 0.15), 6)
    $ramBudgetGB = $modelSizeGB + $kvCacheGB + 2
    $gpuMode = "HYBRID (GPU offload limited)"
    Write-Host "    Total VRAM:   $vramGB GB" -ForegroundColor Gray
    Write-Host "    Model fits?   NO — CPU offload needed for $(($modelSizeGB - $vramGB).ToString('F1')) GB" -ForegroundColor Yellow
} elseif ($vramGB -le 8) {
    # 6-8 GB — RTX 2060/3060/4060/5070 laptop range
    $ngl = 41  # ~5GB for model, ~3GB headroom for KV+OS
    $kvCacheGB = 1.5
    $ramBudgetGB = $modelSizeGB - $vramGB + $kvCacheGB + 4
    $gpuMode = "HYBRID (MoE experts on CPU)"
    Write-Host "    Total VRAM:   $vramGB GB" -ForegroundColor Gray
    Write-Host "    Model on GPU: ~$($vramGB - 3) GB (41 layers)" -ForegroundColor Gray
    Write-Host "    MoE experts:  CPU offload" -ForegroundColor Gray
    Write-Host "    KV Cache:     $kvCacheGB GB" -ForegroundColor Gray
    Write-Host "    Free VRAM:    ~$($vramGB - 5.6) GB (for TTS/ComfyUI to fill)" -ForegroundColor Gray
} elseif ($vramGB -le 16) {
    # 12-16 GB — RTX 4070/4080/5080 range
    $ngl = 99  # all layers
    $kvCacheGB = 3
    $ramBudgetGB = 8  # system + overhead
    $gpuMode = "FULL GPU (all layers on GPU)"
    Write-Host "    Total VRAM:   $vramGB GB" -ForegroundColor Gray
    Write-Host "    Model fits?   YES — full GPU offload" -ForegroundColor Green
    Write-Host "    KV Cache:     $kvCacheGB GB" -ForegroundColor Gray
} else {
    # 24+ GB — RTX 4090/5090
    $ngl = 99
    $kvCacheGB = 6
    $ramBudgetGB = 8
    $gpuMode = "FULL GPU BEAST MODE"
    Write-Host "    Total VRAM:   $vramGB GB 🚀" -ForegroundColor Gray
    Write-Host "    Model fits?   EASILY — full GPU + generous KV cache" -ForegroundColor Green
}

# ── Thread configuration ──
if ($cpuCores -le 8) {
    $threads = $cpuCores - 2
    $batchSize = 2048
    $ubatch = 1024
} elseif ($cpuCores -le 24) {
    $threads = [math]::Min($cpuCores, 16)  # More than 16 doesn't help much
    $batchSize = 4096
    $ubatch = 2048
} else {
    $threads = 24
    $batchSize = 8192
    $ubatch = 4096
}
if ($threads -lt 2) { $threads = 2 }

# ── Context / Cache ──
$realContext = if ($kvCacheGB -le 0) {
    [math]::Min($ContextSize, 32768)
} else {
    $ContextSize
}

# ── MoE strategy ──
$cpuMoe = if ($vramGB -le 8) { "--cpu-moe --cpu-mask 0xFFFFFFFF" } else { "" }

# ── Model loading strategy ──
$noMmap = if ($totalRamGB -lt 32) { "" } else { "--no-mmap" }  # no-mmap needs lots of RAM
$q4Offload = $true  # Q4 cache for VRAM efficiency

# ── Build llama-server args ──
$llamaArgs = @(
    '-m', "`"$ModelPath`"",
    '-c', $realContext.ToString(),
    '--flash-attn', 'on',
    '-ngl', $ngl.ToString(),
    '--batch-size', $batchSize.ToString(),
    '--ubatch-size', $ubatch.ToString(),
    '--threads', $threads.ToString(),
    '--api-key', "`"$ApiKey`"",
    '-rea', 'off',
    '--jinja',
    '--cache-ram', '2048',
    '--parallel', '1',
    '--kv-unified'
)

if ($q4Offload) {
    $llamaArgs += @('-ctk', 'q8_0', '-ctv', 'q8_0')
}

if ($cpuMoe) {
    $llamaArgs += $cpuMoe -split ' '
}

if ($noMmap) {
    $llamaArgs += '--no-mmap'
}

# ============================================================================
# Check llama.cpp
# ============================================================================
Write-Host "[4/5] Checking llama.cpp..." -ForegroundColor Yellow

$llamaExe = Get-Command llama-server.exe -ErrorAction SilentlyContinue

if (-not $llamaExe) {
    # Search common paths
    $searchPaths = @(
        ".\llama.cpp\build\bin\Release\llama-server.exe",
        "..\llama.cpp\build\bin\Release\llama-server.exe",
        "$env:USERPROFILE\Desktop\vllm\llama.cpp\build\bin\Release\llama-server.exe",
        "$env:LOCALAPPDATA\llama.cpp\llama-server.exe"
    )
    foreach ($p in $searchPaths) {
        if (Test-Path $p) {
            $llamaExe = Get-Command $p
            break
        }
    }
}

$vllmDir = ""

if (-not $llamaExe) {
    Write-Host ""
    Write-Host "  llama.cpp not found on PATH!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Choose how to install:" -ForegroundColor Cyan
    Write-Host "  1. Let this script clone & build llama.cpp from source" -ForegroundColor White
    Write-Host "  2. Download pre-built release from GitHub" -ForegroundColor White
    Write-Host "  3. Specify path manually" -ForegroundColor White
    Write-Host ""
    
    if (-not $SkipPrompt) {
        $choice = Read-Host "  Enter choice [1/2/3] (default: 2)"
        if (-not $choice) { $choice = "2" }
    } else {
        $choice = if ($BuildLlama) { "1" } else { "2" }
    }
    
    switch ($choice) {
        "1" {
            # Build from source
            $vllmDir = Join-Path $env:USERPROFILE "Desktop\vllm"
            Write-Host ""
            Write-Host "  Cloning llama.cpp to $vllmDir..." -ForegroundColor Yellow
            
            if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
                Write-Host "  [ERROR] cmake not found!" -ForegroundColor Red
                Write-Host "  Install: winget install Kitware.CMake" -ForegroundColor Yellow
                Write-Host "  Or choose option 2 (pre-built release)" -ForegroundColor Yellow
                exit 1
            }
            
            if (-not (Test-Path "$vllmDir\llama.cpp")) {
                git clone https://github.com/ggml-org/llama.cpp.git "$vllmDir\llama.cpp" 2>&1 | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  [ERROR] Clone failed. Check git + network." -ForegroundColor Red
                    exit 1
                }
            }
            
            Write-Host "  Building llama.cpp (this may take 10-20 min)..." -ForegroundColor Yellow
            
            $buildDir = "$vllmDir\llama.cpp\build"
            New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
            
            Push-Location $buildDir
            try {
                cmake .. -G "Visual Studio 17 2022" -A x64 -DGGML_CUDA=ON 2>&1 | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    # Try without CUDA
                    Write-Host "  CUDA build failed, trying CPU-only..." -ForegroundColor Yellow
                    cmake .. -G "Visual Studio 17 2022" -A x64 2>&1 | Out-Null
                }
                cmake --build . --config Release --parallel $threads 2>&1 | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  [ERROR] Build failed." -ForegroundColor Red
                    Write-Host "  Try pre-built release: https://github.com/ggml-org/llama.cpp/releases" -ForegroundColor Yellow
                    exit 1
                }
            }
            finally {
                Pop-Location
            }
            
            $llamaExe = "$buildDir\bin\Release\llama-server.exe"
            Write-Host "  Build complete: $llamaExe" -ForegroundColor Green
            
            # Add to PATH
            $llamaBin = Split-Path $llamaExe -Parent
            Write-Host ""
            Write-Host "  Add to PATH (recommended):" -ForegroundColor Cyan
            Write-Host "    [System.Environment]::SetEnvironmentVariable('Path', `$env:Path + ';$llamaBin', 'User')" -ForegroundColor White
            
            # Create restart script
            $restartScript = "$vllmDir\restart-llama.ps1"
            Write-Host "  Creating restart script: $restartScript" -ForegroundColor Gray
            $restartContent = @"
# restart-llama.ps1 — Auto-generated by setup-llama.ps1
# Kills existing llama-server and starts a new one

`$exe = "$llamaExe"
`$args = @(
$(($llamaArgs | ForEach-Object { "    $_" }) -join ",`n")
)

Write-Host "[llama-restart] Starting llama-server..."
Start-Process -FilePath `$exe -ArgumentList `$args -WindowStyle Hidden
Write-Host "[llama-restart] Done"
"@
            
        }
        "2" {
            # Pre-built release
            Write-Host ""
            Write-Host "  Download from: https://github.com/ggml-org/llama.cpp/releases" -ForegroundColor Cyan
            Write-Host "  Choose the CUDA build (e.g. llama-bXXXX-bin-win-cuda-cuXX.X-x64.zip)" -ForegroundColor Cyan
            Write-Host "  Extract to a folder, add to PATH." -ForegroundColor Cyan
            Write-Host ""
            
            if (-not $SkipPrompt) {
                $manualPath = Read-Host "  Enter llama-server.exe path (or press Enter to skip)"
            } else { $manualPath = "" }
            
            if ($manualPath -and (Test-Path $manualPath)) {
                $llamaExe = $manualPath
            }
            
            if (-not $llamaExe) {
                Write-Host "  No llama.cpp found. Exiting." -ForegroundColor Yellow
                Write-Host "  Re-run after installing llama.cpp, or use -BuildLlama flag." -ForegroundColor Yellow
                exit 0
            }
        }
        "3" {
            if (-not $SkipPrompt) {
                $manualPath = Read-Host "  Enter full path to llama-server.exe"
            }
            if ($manualPath -and (Test-Path $manualPath)) {
                $llamaExe = $manualPath
            } else {
                Write-Host "  Invalid path." -ForegroundColor Red
                exit 1
            }
        }
    }
}

Write-Host "  llama-server: $($llamaExe.Source)" -ForegroundColor Green

# ============================================================================
# Generate output files
# ============================================================================
Write-Host "[5/5] Generating configuration files..." -ForegroundColor Yellow

$outputDir = Join-Path $PWD "llama-config"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

# ── Hardware report ──
$report = @"
# llama.cpp Auto-Generated Configuration
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# Machine: $($env:COMPUTERNAME)

## Hardware Detection
- OS: $osName
- CPU: $cpuCores logical cores
- RAM: $totalRamGB GB
- GPU: $($primaryGpu.Name) ($($primaryGpu.VRAM_GB) GB VRAM)
- Mode: $gpuMode

## Model
- Path: $ModelPath
- Size: $modelSizeGB GB

## Generated Parameters
| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| -ngl       | $ngl   | Based on $vramGB GB VRAM |
| --threads  | $threads | $cpuCores logical cores |
| --batch-size | $batchSize | Balanced for CPU + GPU |
| --ubatch-size | $ubatch | Half batch-size |
| -c         | $realContext | Context window |
| VRAM free  | ~$([math]::Max(0, $vramGB - 5.6).ToString('F1')) GB | After model + KV cache |
"@

$reportPath = Join-Path $outputDir "hardware-report.md"
Set-Content -Path $reportPath -Value $report -Encoding UTF8
Write-Host "  Hardware report: $reportPath" -ForegroundColor Gray

# ── Launch script ──
$launchContent = @"
# launch-llama.ps1 — Auto-generated by setup-llama.ps1
# Start llama-server with optimized parameters
#
# Generated for: $($primaryGpu.Name), $($primaryGpu.VRAM_GB) GB VRAM, $cpuCores cores, $totalRamGB GB RAM
# Mode: $gpuMode
# $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
#
# CRITICAL: Do NOT run this script in the same PowerShell window as OpenClaw.
# It runs a persistent background server. Use:
#   Start-Process powershell -ArgumentList '-File launch-llama.ps1' -WindowStyle Hidden

`$exe = "$($llamaExe.Source)"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " AI Girlfriend — llama-server" -ForegroundColor Cyan
Write-Host " GPU: $($primaryGpu.Name) | VRAM: $($primaryGpu.VRAM_GB) GB" -ForegroundColor Cyan
Write-Host " Mode: $gpuMode" -ForegroundColor Cyan
Write-Host " Port: $Port" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

`$cmdArgs = @(
$(($llamaArgs | ForEach-Object { "    $_" }) -join ",`n")
)

Write-Host "Starting llama-server..."
`$proc = Start-Process -FilePath `$exe -ArgumentList @(`$cmdArgs) -WindowStyle Hidden -PassThru
Write-Host "PID: `$(`$proc.Id)" -ForegroundColor Green
Write-Host ""
Write-Host "Waiting for server to start..." -ForegroundColor Yellow

# Wait for health endpoint
for (`$i = 1; `$i -le 30; `$i++) {
    try {
        `$r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -TimeoutSec 2
        if (`$r.StatusCode -eq 200) {
            Write-Host "Server ready!" -ForegroundColor Green
            Write-Host "Endpoint: http://127.0.0.1:8080" -ForegroundColor Green
            break
        }
    } catch {
        Start-Sleep -Seconds 1
        if (`$i -eq 30) {
            Write-Host "Timeout — server may still be loading. Check http://127.0.0.1:8080/health" -ForegroundColor Yellow
        }
    }
}

# Keep running
Write-Host "Server running. Press Ctrl+C to stop." -ForegroundColor Gray
try { Wait-Process -Id `$proc.Id } catch {}
"@

$launchPath = Join-Path $outputDir "launch-llama.ps1"
Set-Content -Path $launchPath -Value $launchContent -Encoding UTF8
Write-Host "  Launch script:  $launchPath" -ForegroundColor Green

# ── Watchdog ──
$watchdogContent = @"
# llama-watchdog.ps1 — Auto-generated by setup-llama.ps1
# Health check for llama-server. Configure in Windows Task Scheduler to run every 10 min.

`$logFile = "$outputDir\watchdog.log"
`$null = New-Item -ItemType Directory -Path (Split-Path `$logFile -Parent) -Force -ErrorAction SilentlyContinue

function log { param([string]`$m) Add-Content -Path `$logFile -Value "[`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] `$m" -Encoding UTF8 }

log "=== watchdog check ==="

`$proc = Get-Process llama-server -ErrorAction SilentlyContinue
if (-not `$proc) {
    log "llama-server not running — restarting..."
    Start-Process powershell -ArgumentList '-File', '$launchPath' -WindowStyle Hidden
    log "restart triggered"
    exit 0
}

try {
    `$r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -TimeoutSec 5
    if (`$r.StatusCode -eq 200) {
        log "healthy (PID=`$(`$proc.Id))"
        exit 0
    }
} catch {
    log "health check failed: `$_"
}

# Process alive but port dead → kill and restart
log "process alive but dead port — forcing restart..."
Stop-Process -Id `$proc.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList '-File', '$launchPath' -WindowStyle Hidden
log "forced restart done"
exit 0
"@

$watchdogPath = Join-Path $outputDir "llama-watchdog.ps1"
Set-Content -Path $watchdogPath -Value $watchdogContent -Encoding UTF8
Write-Host "  Watchdog:       $watchdogPath" -ForegroundColor Gray

# ── Task Scheduler setup ──
$taskSched = @"
# Run these in an elevated PowerShell to set up auto-restart:

# Llama health check (every 10 minutes)
schtasks /create /tn "llama-watchdog" `
  /tr "powershell -File '$watchdogPath'" `
  /sc minute /mo 10

# Orphan cleanup (hourly — only if you have cleanup_orphans.ps1)
# schtasks /create /tn "cleanup-llama-orphans" `
#   /tr "powershell -File '.\skills\cleanup_orphans.ps1'" `
#   /sc hourly /mo 1
"@

$schedPath = Join-Path $outputDir "setup-task-scheduler.ps1"
Set-Content -Path $schedPath -Value $taskSched -Encoding UTF8
Write-Host "  Task Scheduler: $schedPath" -ForegroundColor Gray

# ============================================================================
# Summary
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Setup Complete!                                           ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Hardware:    $($primaryGpu.Name) — $($primaryGpu.VRAM_GB) GB VRAM" -ForegroundColor White
Write-Host "  CPU:         $cpuCores cores | RAM: $totalRamGB GB" -ForegroundColor White
Write-Host "  Mode:        $gpuMode" -ForegroundColor White
Write-Host "  Model:       $modelSizeGB GB GGUF" -ForegroundColor White
Write-Host ""
Write-Host "  Generated files in: $outputDir\" -ForegroundColor Cyan
Write-Host "    launch-llama.ps1      — Start llama-server" -ForegroundColor White
Write-Host "    llama-watchdog.ps1    — Health check (Task Scheduler)" -ForegroundColor White
Write-Host "    setup-task-scheduler.ps1 — Register watchdog task" -ForegroundColor White
Write-Host "    hardware-report.md    — Your machine specs" -ForegroundColor White
Write-Host ""
Write-Host "  Quick Start:" -ForegroundColor Cyan
Write-Host "    1. Run .\llama-config\launch-llama.ps1" -ForegroundColor White
Write-Host "    2. Wait for http://127.0.0.1:$Port/health to return 200" -ForegroundColor White
Write-Host "    3. Configure OpenClaw to use http://127.0.0.1:$Port/v1" -ForegroundColor White
Write-Host ""
Write-Host "  ⚠️  IMPORTANT: Start llama-server in a SEPARATE window:" -ForegroundColor Yellow
Write-Host "    Start-Process powershell -ArgumentList '-File $launchPath' -WindowStyle Hidden" -ForegroundColor White
