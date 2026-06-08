param(
    [string]$text,
    [string]$lang = 'ja',
    [string]$mood = 'auto'
)

$ErrorActionPreference = 'Continue'

$taskId = 'tts_' + (Get-Date -Format 'yyyyMMddHHmmss')
$flagDir = 'C:\Users\TK\.openclaw\workspace\.task_flags'
$flagFile = Join-Path $flagDir "$taskId.done"
mkdir $flagDir -Force -ErrorAction SilentlyContinue | Out-Null

$mediaDir = 'C:\Users\TK\.openclaw\media\qqbot\audio'
mkdir $mediaDir -Force -ErrorAction SilentlyContinue | Out-Null

$python = 'C:\Users\TK\Desktop\vllm\GPT-SoVITS-v2pro-20250604-nvidia50\runtime\python.exe'
$script = 'C:\Users\TK\.openclaw\workspace\skills\tts\tts_call.py'

$env:PYTHONIOENCODING = 'utf-8'
$env:HF_ENDPOINT = 'https://hf-mirror.com'

# Run TTS - stderr has [LOCK]/[LLAMA] logs, stdout has the wav path
$rawOutput = & $python $script $text $lang $mood 2>$null
# Extract the path from stdout
$wavPath = ($rawOutput | Where-Object { $_ -match 'C:\\.+\.wav' } | Select-Object -Last 1) -replace '^\s+|\s+$',''

$exitOk = ($LASTEXITCODE -eq 0) -or ($rawOutput -match '\.wav')
if ($exitOk -and $wavPath -and (Test-Path $wavPath)) {
    $mediaFile = Join-Path $mediaDir ('tts_' + (Get-Date -Format 'yyyyMMddHHmmss') + '.wav')
    Copy-Item $wavPath $mediaFile -Force -ErrorAction Stop
    @{status='ok';file=$mediaFile;type='tts'} | ConvertTo-Json -Compress | Set-Content $flagFile

    # Wait for llama to be fully ready
    Write-Output 'TTS done, confirming llama ready...'
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
    Write-Output "<qqmedia>$mediaFile</qqmedia>"
} else {
    Write-Output "FAILED: exit=$LASTEXITCODE path=$wavPath"

    # TTS failed, ensure llama is restarted
    Write-Output 'Restarting llama after failed TTS run...'
    & 'C:\Users\TK\Desktop\vllm\restart-llama.ps1'
}
