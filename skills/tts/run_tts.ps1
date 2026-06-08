param(
    [string]$text,
    [string]$lang = 'ja',
    [string]$mood = 'auto'
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

$sovitsPython = Get-YamlValue $configRaw 'sovits_python'
$ttsScript = Join-Path $PSScriptRoot 'tts_call.py'  # always alongside this script
$mediaDir = Get-YamlValue $configRaw 'media_qqbot_audio'
if (-not $mediaDir) { $mediaDir = Join-Path $workspaceRoot 'media\qqbot\audio' }

$taskId = 'tts_' + (Get-Date -Format 'yyyyMMddHHmmss') + '_' + (Get-Random -Minimum 1000 -Maximum 9999)
$flagDir = Join-Path $workspaceRoot '.task_flags'
$flagFile = Join-Path $flagDir "$taskId.done"
mkdir $flagDir -Force -ErrorAction SilentlyContinue | Out-Null
mkdir $mediaDir -Force -ErrorAction SilentlyContinue | Out-Null

$env:PYTHONIOENCODING = 'utf-8'
$env:HF_ENDPOINT = 'https://hf-mirror.com'

# Run TTS - stderr has [LOCK]/[LLAMA] logs, stdout has the wav path
$rawOutput = & $sovitsPython $ttsScript $text $lang $mood 2>$null
# Extract the path from stdout
$wavPath = ($rawOutput | Where-Object { $_ -match '\.wav' } | Select-Object -Last 1) -replace '^\s+|\s+$',''

$exitOk = ($LASTEXITCODE -eq 0) -or ($rawOutput -match '\.wav')
if ($exitOk -and $wavPath -and (Test-Path $wavPath)) {
    $mediaFile = Join-Path $mediaDir ('tts_' + (Get-Date -Format 'yyyyMMddHHmmss') + '.wav')
    Copy-Item $wavPath $mediaFile -Force -ErrorAction Stop
    @{status='ok';file=$mediaFile;type='tts'} | ConvertTo-Json -Compress | Set-Content $flagFile

    # Python script internally does start_llama + 3-stage check
    Write-Output "DONE: $mediaFile"
    Write-Output "<qqmedia>$mediaFile</qqmedia>"
} else {
    Write-Output "FAILED: exit=$LASTEXITCODE path=$wavPath"

    # TTS failed, ensure llama is restarted
    Write-Output 'Restarting llama after failed TTS run...'
    $restartScript = Get-YamlValue $configRaw 'restart_script'
    if ($restartScript -and (Test-Path $restartScript)) {
        & $restartScript
    }
}
