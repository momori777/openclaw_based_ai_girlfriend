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

# Must be Continue - comfyui_call.py writes [LOCK]/[LLAMA] to stderr, and Stop would abort

$taskId = 'comfyui_' + (Get-Date -Format 'yyyyMMddHHmmss')
$flagDir = 'C:\Users\TK\.openclaw\workspace\.task_flags'
$flagFile = Join-Path $flagDir "$taskId.done"
mkdir $flagDir -Force -ErrorAction SilentlyContinue | Out-Null

$mediaDir = 'C:\Users\TK\.openclaw\media\qqbot\images'
mkdir $mediaDir -Force -ErrorAction SilentlyContinue | Out-Null

$python = 'E:\comfyui\ComfyUI-aki-v3\python\python.exe'
$script = 'C:\Users\TK\.openclaw\workspace\skills\comfyui\comfyui_call.py'

# Run ComfyUI - stderr has [LOCK]/[LLAMA] logs, stdout has the image path
$rawOutput = & $python $script $positive $negative $seed $width $height $steps $cfg $checkpoint 2>$null
# Extract the path from stdout (may have tqdm mixed in)
$imgPath = ($rawOutput | Where-Object { $_ -match 'C:\\.+\.png' } | Select-Object -Last 1) -replace '^\s+|\s+$',''

$exitOk = ($LASTEXITCODE -eq 0) -or ($rawOutput -match '\.png')
if ($exitOk -and $imgPath -and (Test-Path $imgPath)) {
    $mediaFile = Join-Path $mediaDir ('comfyui_' + (Get-Date -Format 'yyyyMMddHHmmss') + '.png')
    Copy-Item $imgPath $mediaFile -Force -ErrorAction Stop
    @{status='ok';file=$mediaFile;type='comfyui'} | ConvertTo-Json -Compress | Set-Content $flagFile

    # Wait for llama to be fully ready
    # Python script internally does start_llama + 3-stage check, this is secondary safety
    Write-Output 'ComfyUI done, confirming llama ready...'
    for ($i = 0; $i -lt 180; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/health' -TimeoutSec 2 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                Write-Output "LLAMA_READY after $i seconds"
                break
            }
        } catch {}
        Start-Sleep 1
    }

    Write-Output "DONE: $mediaFile"
} else {
    Write-Output "FAILED: exit=$LASTEXITCODE path=$imgPath"
}
