#configure.ps1 — AI Girlfriend 路径配置向导
#交互式输入你的本地路径，自动替换所有脚本中的 {{PLACEHOLDER}} 占位符

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  四季夏目 AI Girlfriend — 路径配置向导" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  这个脚本会引导你输入本地路径，" -ForegroundColor Gray
Write-Host "  然后自动替换所有脚本中的 {{PLACEHOLDER}} 占位符。" -ForegroundColor Gray
Write-Host ""

# ========== 路径配置 ==========
Write-Host "--- 路径配置 ---" -ForegroundColor Yellow
Write-Host ""

# OpenClaw 工作区
$userHome = $env:USERPROFILE
$defaultWorkspace = Join-Path $userHome ".openclaw\workspace"
$Workspace = Read-Host "OpenClaw 工作区目录"
if (-not $Workspace) { $Workspace = $defaultWorkspace }
Write-Host "  ✓ 工作区: $Workspace" -ForegroundColor Green
Write-Host ""

# llama.cpp
Write-Host "--- llama.cpp ---" -ForegroundColor Yellow
$defaultLlamaExe = Join-Path $userHome "Desktop\vllm\llama-b9222-bin-win-cuda-12.4-x64\llama-server.exe"
$LlamaExe = Read-Host "llama-server.exe 完整路径"
if (-not $LlamaExe) { $LlamaExe = $defaultLlamaExe }
Write-Host "  ✓ llama-server: $LlamaExe" -ForegroundColor Green

$defaultLlamaModel = Join-Path $userHome "Desktop\vllm\models\Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf"
$LlamaModel = Read-Host "LLM 模型 (.gguf) 完整路径"
if (-not $LlamaModel) { $LlamaModel = $defaultLlamaModel }
Write-Host "  ✓ 模型: $LlamaModel" -ForegroundColor Green

$defaultLlamaLogDir = Join-Path $userHome "Desktop\vllm\restart-logs"
$LlamaLogDir = Read-Host "llama 日志目录"
if (-not $LlamaLogDir) { $LlamaLogDir = $defaultLlamaLogDir }
Write-Host "  ✓ 日志: $LlamaLogDir" -ForegroundColor Green

$defaultRestartScript = Join-Path $userHome "Desktop\vllm\restart-llama.ps1"
$RestartScript = Read-Host "restart-llama.ps1 完整路径"
if (-not $RestartScript) { $RestartScript = $defaultRestartScript }
Write-Host "  ✓ 重启脚本: $RestartScript" -ForegroundColor Green
Write-Host ""

# ComfyUI
Write-Host "--- ComfyUI ---" -ForegroundColor Yellow
$defaultComfyRoot = "E:\comfyui\ComfyUI-aki-v3\ComfyUI"
$ComfyRoot = Read-Host "ComfyUI 根目录"
if (-not $ComfyRoot) { $ComfyRoot = $defaultComfyRoot }
Write-Host "  ✓ ComfyUI 根: $ComfyRoot" -ForegroundColor Green

$defaultComfyPython = (Split-Path $ComfyRoot -Parent) + "\python\python.exe"
$ComfyPython = Read-Host "ComfyUI Python 解释器路径"
if (-not $ComfyPython) { $ComfyPython = $defaultComfyPython }
Write-Host "  ✓ Python: $ComfyPython" -ForegroundColor Green

$defaultCheckpoints = Join-Path $ComfyRoot "models\checkpoints"
$CheckpointsDir = Read-Host "Checkpoints 目录"
if (-not $CheckpointsDir) { $CheckpointsDir = $defaultCheckpoints }
Write-Host "  ✓ Checkpoints: $CheckpointsDir" -ForegroundColor Green

$defaultComfyOutput = Join-Path $Workspace "comfyui_output"
$ComfyOutput = Read-Host "ComfyUI 图片输出目录"
if (-not $ComfyOutput) { $ComfyOutput = $defaultComfyOutput }
Write-Host "  ✓ 输出: $ComfyOutput" -ForegroundColor Green
Write-Host ""

# GPT-SoVITS
Write-Host "--- GPT-SoVITS TTS ---" -ForegroundColor Yellow
$defaultSovitsDir = Join-Path $userHome "Desktop\vllm\GPT-SoVITS-v2pro-20250604-nvidia50"
$SovitsDir = Read-Host "GPT-SoVITS 根目录"
if (-not $SovitsDir) { $SovitsDir = $defaultSovitsDir }
Write-Host "  ✓ GPT-SoVITS: $SovitsDir" -ForegroundColor Green

$defaultSovitsPython = Join-Path $SovitsDir "runtime\python.exe"
$SovitsPython = Read-Host "GPT-SoVITS Python 解释器路径"
if (-not $SovitsPython) { $SovitsPython = $defaultSovitsPython }
Write-Host "  ✓ Python: $SovitsPython" -ForegroundColor Green

$LlamaModelDir = Split-Path $LlamaModel -Parent

$defaultTtsOutput = Join-Path $Workspace "qqbot\audio"
$TtsOutput = Read-Host "TTS 音频输出目录"
if (-not $TtsOutput) { $TtsOutput = $defaultTtsOutput }
Write-Host "  ✓ 输出: $TtsOutput" -ForegroundColor Green

$defaultRefDir = Join-Path $Workspace "skills\tts\ref_wavs"
$RefDir = Read-Host "TTS 参考音频目录"
if (-not $RefDir) { $RefDir = $defaultRefDir }
Write-Host "  ✓ 参考音频: $RefDir" -ForegroundColor Green
Write-Host ""

# 媒体输出
Write-Host "--- 媒体输出 ---" -ForegroundColor Yellow
$defaultMediaImages = Join-Path $userHome ".openclaw\media\qqbot\images"
$MediaImages = Read-Host "媒体-图片目录 (QQ/Telegram 发送用)"
if (-not $MediaImages) { $MediaImages = $defaultMediaImages }
Write-Host "  ✓ 图片: $MediaImages" -ForegroundColor Green

$defaultMediaAudio = Join-Path $userHome ".openclaw\media\qqbot\audio"
$MediaAudio = Read-Host "媒体-音频目录 (QQ/Telegram 发送用)"
if (-not $MediaAudio) { $MediaAudio = $defaultMediaAudio }
Write-Host "  ✓ 音频: $MediaAudio" -ForegroundColor Green

$defaultTaskFlags = Join-Path $Workspace ".task_flags"
$TaskFlags = Read-Host ".task_flags 目录"
if (-not $TaskFlags) { $TaskFlags = $defaultTaskFlags }
Write-Host "  ✓ .task_flags: $TaskFlags" -ForegroundColor Green
Write-Host ""

# 额外路径
$AgentsRoot = Join-Path $userHome ".openclaw\agents"

# ========== 确认 ==========
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  配置汇总" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""
$config = @{
    Workspace       = $Workspace
    LlamaExe        = $LlamaExe
    LlamaModel      = $LlamaModel
    LlamaModelDir   = $LlamaModelDir
    LlamaLogDir     = $LlamaLogDir
    RestartScript   = $RestartScript
    ComfyRoot       = $ComfyRoot
    ComfyPython     = $ComfyPython
    CheckpointsDir  = $CheckpointsDir
    ComfyOutput     = $ComfyOutput
    SovitsDir       = $SovitsDir
    SovitsPython    = $SovitsPython
    TtsOutput       = $TtsOutput
    RefDir          = $RefDir
    MediaImages     = $MediaImages
    MediaAudio      = $MediaAudio
    TaskFlags       = $TaskFlags
    AgentsRoot      = $AgentsRoot
}
foreach ($k in $config.Keys | Sort-Object) {
    Write-Host ("  {0,-20} = {1}" -f $k, $config[$k]) -ForegroundColor Gray
}
Write-Host ""

$confirm = Read-Host "确认以上配置？按 Enter 开始应用，输入 N 取消"
if ($confirm -eq "N" -or $confirm -eq "n") {
    Write-Host "取消。" -ForegroundColor Red
    exit 0
}

# ========== 保存配置 ==========
$configPath = Join-Path $scriptDir "config.json"
$config | ConvertTo-Json | Set-Content $configPath -Encoding UTF8
Write-Host "✓ 配置已保存到 config.json" -ForegroundColor Green
Write-Host ""

# ========== 占位符映射表 ==========
$placeholders = @{
    '{{WORKSPACE}}'       = $Workspace
    '{{LLAMA_EXE}}'       = $LlamaExe
    '{{LLAMA_MODEL}}'     = $LlamaModel
    '{{LLAMA_MODEL_DIR}}' = $LlamaModelDir
    '{{LLAMA_LOG_DIR}}'   = $LlamaLogDir
    '{{RESTART_SCRIPT}}'  = $RestartScript
    '{{COMFYUI_ROOT}}'    = $ComfyRoot
    '{{COMFYUI_PYTHON}}'  = $ComfyPython
    '{{CHECKPOINTS_DIR}}' = $CheckpointsDir
    '{{COMFY_OUTPUT}}'    = $ComfyOutput
    '{{SOVITS_DIR}}'      = $SovitsDir
    '{{SOVITS_PYTHON}}'   = $SovitsPython
    '{{TTS_OUTPUT}}'      = $TtsOutput
    '{{REF_DIR}}'         = $RefDir
    '{{MEDIA_IMAGES}}'    = $MediaImages
    '{{MEDIA_AUDIO}}'     = $MediaAudio
    '{{TASK_FLAGS}}'      = $TaskFlags
    '{{AGENTS_ROOT}}'    = $AgentsRoot
}

# ========== 替换函数 ==========
function Replace-InFile {
    param(
        [string]$RelativePath,
        [hashtable]$Placeholders
    )
    $fullPath = Join-Path $scriptDir $RelativePath
    if (-not (Test-Path $fullPath)) {
        Write-Host "  ⚠ 跳过 (文件不存在): $RelativePath" -ForegroundColor Yellow
        return
    }
    $content = Get-Content $fullPath -Raw -Encoding UTF8
    $changed = $false
    foreach ($placeholder in $Placeholders.Keys) {
        if ($content.Contains($placeholder)) {
            $content = $content.Replace($placeholder, $Placeholders[$placeholder])
            $changed = $true
        }
    }
    if ($changed -and -not $DryRun) {
        Set-Content $fullPath -Value $content -Encoding UTF8 -NoNewline
        Write-Host "  ✓ 已更新: $RelativePath" -ForegroundColor Green
    } elseif ($changed) {
        Write-Host "  ○ [DRY-RUN] 将更新: $RelativePath" -ForegroundColor Yellow
    } else {
        Write-Host "  - 无变化: $RelativePath" -ForegroundColor Gray
    }
}

# ========== 被处理的所有文件 ==========
Write-Host "--- 开始替换占位符 ---" -ForegroundColor Yellow
Write-Host ""

$files = @(
    "skills\tts\tts_call.py",
    "skills\tts\run_tts.ps1",
    "skills\tts\SKILL.md",
    "skills\comfyui\comfyui_call.py",
    "skills\comfyui\run_comfyui.ps1",
    "skills\comfyui\SKILL.md",
    "skills\comfyui\prompt_template.md",
    "skills\llama-watchdog.ps1",
    "skills\cleanup_orphans.ps1",
    "AGENTS.md",
    "TOOLS.md",
    "models.yaml"
)

foreach ($file in $files) {
    Replace-InFile $file $placeholders
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  ✅ 配置完成！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  已处理的文件:" -ForegroundColor Gray
foreach ($file in $files) {
    Write-Host "    $file" -ForegroundColor Gray
}
Write-Host ""
Write-Host "  配置已保存到 config.json，下次运行会自动读取。" -ForegroundColor Gray
Write-Host "  使用方法: .\configure.ps1           # 交互式输入" -ForegroundColor Gray
Write-Host "            .\configure.ps1 -DryRun   # 预览不写入" -ForegroundColor Gray
Write-Host ""
