param(
    [string]$positive,
    [string]$negative,
    [int]$seed = -1,
    [int]$width = 1200,
    [int]$height = 1500,
    [int]$steps = 30,
    [float]$cfg = 6.0,
    [string]$checkpoint = 'WAI-Nsfw-Illustrious-17.safetensors'
)

$ErrorActionPreference = 'Continue'

# ========== 从 config.yaml 读取路径 ==========
$workspaceRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$configPath = Join-Path $workspaceRoot 'config.yaml'
if (-not (Test-Path $configPath)) {
    Write-Output "FAILED: config.yaml not found at $configPath"
    Write-Output "Please run quick_setup.ps1 first to configure paths."
    exit 1
}
$configRaw = Get-Content $configPath -Raw -Encoding UTF8

# 辅助函数：从 YAML 提取简单标量值
function Get-YamlValue($raw, $key) {
    $pattern = "(?m)^\s*${key}\s*:\s*`"?(.+?)`"?\s*$"
    $m = [regex]::Match($raw, $pattern)
    if ($m.Success) { return $m.Groups[1].Value.Trim('"').Trim() }
    return $null
}

$comfyuiPython = Get-YamlValue $configRaw 'comfyui_python'
$comfyuiScript = Join-Path $PSScriptRoot 'comfyui_call.py'  # always alongside this script
$mediaDir = Get-YamlValue $configRaw 'media_qqbot_images'
if (-not $mediaDir) { $mediaDir = Join-Path $workspaceRoot 'media\qqbot\images' }

$taskId = 'comfyui_' + (Get-Date -Format 'yyyyMMddHHmmss')
$flagDir = Join-Path $workspaceRoot '.task_flags'
$flagFile = Join-Path $flagDir "$taskId.done"
mkdir $flagDir -Force -ErrorAction SilentlyContinue | Out-Null
mkdir $mediaDir -Force -ErrorAction SilentlyContinue | Out-Null

# Run ComfyUI - stderr has [LOCK]/[LLAMA] logs, stdout has the image path
$rawOutput = & $comfyuiPython $comfyuiScript $positive $negative $seed $width $height $steps $cfg $checkpoint 2>$null
# Extract the path from stdout (may have tqdm mixed in)
$imgPath = ($rawOutput | Where-Object { $_ -match '\.png' } | Select-Object -Last 1) -replace '^\s+|\s+$',''

$exitOk = ($LASTEXITCODE -eq 0) -or ($rawOutput -match '\.png')
if ($exitOk -and $imgPath -and (Test-Path $imgPath)) {
    $mediaFile = Join-Path $mediaDir ('comfyui_' + (Get-Date -Format 'yyyyMMddHHmmss') + '.png')
    Copy-Item $imgPath $mediaFile -Force -ErrorAction Stop
    @{status='ok';file=$mediaFile;type='comfyui'} | ConvertTo-Json -Compress | Set-Content $flagFile

    # Python script internally does start_llama + 3-stage check
    # No need to re-verify here — just confirm quickly and output
    Write-Output "DONE: $mediaFile"
    Write-Output "<qqmedia>$mediaFile</qqmedia>"
} else {
    Write-Output "FAILED: exit=$LASTEXITCODE path=$imgPath"

    # ComfyUI failed, ensure llama is restarted
    Write-Output 'Restarting llama after failed ComfyUI run...'
    $restartScript = Get-YamlValue $configRaw 'restart_script'
    if ($restartScript -and (Test-Path $restartScript)) {
        & $restartScript
    }
}
