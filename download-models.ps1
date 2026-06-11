# download-models.ps1
# AI Girlfriend 四季夏目 — 一键模型下载脚本 (Windows PowerShell)
#
# 从 HuggingFace 下载全部 5 个模型文件 (~31.7 GB)
# 需要: huggingface-cli (pip install huggingface_hub)
#
# 用法:
#   powershell -File download-models.ps1
#   powershell -File download-models.ps1 -BaseDir "D:\models"
#
# 首次使用需登录:
#   huggingface-cli login
#   或设置 $env:HF_TOKEN

param(
    [string]$BaseDir = ".",
    [string]$HFRepo = "TAOTAO777/ai-girlfriend-natsume",
    [switch]$Live2DOnly = $false
)

$ErrorActionPreference = "Stop"

if ($Live2DOnly) {
    Write-Host "Live2D-only mode" -ForegroundColor Cyan
    $Models = @()
}

Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  AI Girlfriend — 四季夏目 · Model Downloader         ║" -ForegroundColor Cyan
Write-Host "║  $HFRepo                                          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 检查 huggingface-cli
$hf = Get-Command huggingface-cli -ErrorAction SilentlyContinue
if (-not $hf) {
    # Try hf CLI
    $hf = Get-Command hf -ErrorAction SilentlyContinue
}
if (-not $hf) {
    Write-Host "[ERROR] huggingface-cli not found. Install: pip install huggingface_hub" -ForegroundColor Red
    exit 1
}

Write-Host "Download tool: $($hf.Source)" -ForegroundColor Gray

# 检查认证
Write-Host "Checking auth..." -ForegroundColor Gray
$auth = & $hf auth whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║  Not logged in to HuggingFace!                       ║" -ForegroundColor Yellow
    Write-Host "║                                                      ║" -ForegroundColor Yellow
    Write-Host "║  Please login first:                                 ║" -ForegroundColor Yellow
    Write-Host "║    huggingface-cli login                             ║" -ForegroundColor Yellow
    Write-Host "║                                                      ║" -ForegroundColor Yellow
    Write-Host "║  Or set environment variable:                        ║" -ForegroundColor Yellow
    Write-Host '║    $env:HF_TOKEN = "hf_xxx..."                       ║' -ForegroundColor Yellow
    Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK: $auth" -ForegroundColor Green

# 创建目标目录
$BaseDir = Resolve-Path $BaseDir
$Dirs = @(
    "$BaseDir\llm",
    "$BaseDir\comfyui-checkpoints",
    "$BaseDir\gpt-sovits-weights\GPT_weights_v2Pro",
    "$BaseDir\gpt-sovits-weights\SoVITS_weights_v2Pro"
)
foreach ($d in $Dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}

Write-Host ""
Write-Host "Download directory: $BaseDir" -ForegroundColor Cyan
Write-Host "Target: $HFRepo" -ForegroundColor Cyan
Write-Host "Total: ~31.7 GB — this may take 30-90 minutes depending on network" -ForegroundColor Cyan
Write-Host ""

# 模型文件清单 (repo_path, local_path, description)
$Models = @(
    @{RepoPath="llm/Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf"; LocalPath="$BaseDir\llm\Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf"; Desc="LLM GGUF (16.11 GB)"},
    @{RepoPath="comfyui-checkpoints/WAI-Nsfw-Illustrious-17.safetensors"; LocalPath="$BaseDir\comfyui-checkpoints\WAI-Nsfw-Illustrious-17.safetensors"; Desc="ComfyUI Checkpoint — WAI (6.46 GB)"},
    @{RepoPath="comfyui-checkpoints/miaomiaoHarem_v20.safetensors"; LocalPath="$BaseDir\comfyui-checkpoints\miaomiaoHarem_v20.safetensors"; Desc="ComfyUI Checkpoint — Miaomiao (6.46 GB)"},
    @{RepoPath="gpt-sovits-weights/GPT_weights_v2Pro/xxx-e30.ckpt"; LocalPath="$BaseDir\gpt-sovits-weights\GPT_weights_v2Pro\xxx-e30.ckpt"; Desc="GPT-SoVITS ckpt (155 MB)"},
    @{RepoPath="gpt-sovits-weights/SoVITS_weights_v2Pro/xxx_e20_s6240.pth"; LocalPath="$BaseDir\gpt-sovits-weights\SoVITS_weights_v2Pro\xxx_e20_s6240.pth"; Desc="GPT-SoVITS pth (135 MB)"}
)

# Live2D 模型单独处理（tar.gz 需要解压）
$Live2D = @{
    RepoPath = "live2d-model/shiki_natsume.tar.gz"
    ArchivePath = "$BaseDir\live2d-model\shiki_natsume.tar.gz"
    ExtractDir = "$BaseDir\live2d\model"
    Desc = "Live2D Model — Shiki Natsume (~209 MB)"
}

$total = $Models.Count
$current = 0
$failed = @()

foreach ($m in $Models) {
    $current++
    
    # 检查是否已存在
    if (Test-Path $m.LocalPath) {
        $existingSize = (Get-Item $m.LocalPath).Length
        Write-Host "[$current/$total] $($m.Desc) — already exists, skipping" -ForegroundColor DarkGray
        continue
    }
    
    Write-Host "[$current/$total] Downloading $($m.Desc)..." -ForegroundColor Yellow
    Write-Host "         From: $($m.RepoPath)" -ForegroundColor Gray
    Write-Host "         To:   $($m.LocalPath)" -ForegroundColor Gray
    
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    
    $output = & $hf download $HFRepo $m.RepoPath --local-dir $BaseDir 2>&1
    $exitCode = $LASTEXITCODE
    
    $sw.Stop()
    $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    
    if ($exitCode -eq 0) {
        Write-Host "         OK ($elapsed s)" -ForegroundColor Green
    } else {
        Write-Host "         FAILED ($elapsed s) — exit code $exitCode" -ForegroundColor Red
        $failed += $m.Desc
    }
    Write-Host ""
}

# ============================================
# Live2D 模型下载 (tar.gz 需要解压)
# ============================================
$current++
$total++

$live2dMarker = Join-Path $Live2D.ExtractDir "shiki_natsume\final\shiki_natsume.model3.json"
if (Test-Path $live2dMarker) {
    Write-Host "[$current/$total] $($Live2D.Desc) — already exists, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "[$current/$total] Downloading $($Live2D.Desc)..." -ForegroundColor Yellow
    Write-Host "         From: $($Live2D.RepoPath)" -ForegroundColor Gray
    
    $null = New-Item -ItemType Directory -Path (Split-Path $Live2D.ArchivePath) -Force
    $null = New-Item -ItemType Directory -Path $Live2D.ExtractDir -Force
    
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $output = & $hf download $HFRepo $Live2D.RepoPath --local-dir $BaseDir 2>&1
    $exitCode = $LASTEXITCODE
    $sw.Stop()
    $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    
    if ($exitCode -eq 0) {
        Write-Host "         Downloaded ($elapsed s)" -ForegroundColor Green
        Write-Host "         Extracting to $($Live2D.ExtractDir)..." -ForegroundColor Gray
        tar -xzf $Live2D.ArchivePath -C $Live2D.ExtractDir
        if ($LASTEXITCODE -eq 0) {
            Write-Host "         Extracted OK" -ForegroundColor Green
        } else {
            Write-Host "         Extract FAILED" -ForegroundColor Yellow
            $failed += $Live2D.Desc
        }
    } else {
        Write-Host "         FAILED ($elapsed s) — exit code $exitCode" -ForegroundColor Red
        $failed += $Live2D.Desc
    }
}
Write-Host ""

# 汇总
Write-Host "══════════════════════════════════════════════════════" -ForegroundColor Cyan
$finalTotal = $total
$finalSuccess = $finalTotal - $failed.Count
Write-Host "Done: $finalSuccess / $finalTotal items" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "Failed models (re-run to retry):" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
}

if ($finalSuccess -eq $finalTotal) {
    Write-Host ""
    Write-Host "All models downloaded to:" -ForegroundColor Green
    Write-Host "  $BaseDir" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next step: open models.yaml and update local_path fields" -ForegroundColor Cyan
    Write-Host "to match your directory structure." -ForegroundColor Cyan
}
