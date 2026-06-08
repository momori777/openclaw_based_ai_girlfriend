# AI Girlfriend 四季夏目 — 一键路径配置脚本
# 运行此脚本，交互式填写各工具的安装路径，自动生成 config.yaml
#
# 用法: powershell -ExecutionPolicy Bypass -File quick_setup.ps1

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Girlfriend 四季夏目 — 路径配置向导" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "请按提示填写各工具的安装路径。" -ForegroundColor Yellow
Write-Host "留空则使用默认值（基于当前用户的 OpenClaw workspace）。" -ForegroundColor Yellow
Write-Host ""

# ============================================================
# 默认值
# ============================================================
$defaultWorkspace = "$env:USERPROFILE\.openclaw\workspace"
$defaultMediaAudio = "$env:USERPROFILE\.openclaw\media\qqbot\audio"
$defaultMediaImages = "$env:USERPROFILE\.openclaw\media\qqbot\images"
$defaultComfyuiTemp = "$defaultWorkspace\comfyui"
$defaultTtsTemp = $defaultMediaAudio

# ============================================================
# 交互式填写
# ============================================================

Write-Host "--- OpenClaw ---" -ForegroundColor Green
$workspace = Read-Host "OpenClaw workspace 目录 [$defaultWorkspace]"
if (-not $workspace) { $workspace = $defaultWorkspace }

$mediaAudio = Read-Host "QQBot 音频输出目录 [$defaultMediaAudio]"
if (-not $mediaAudio) { $mediaAudio = $defaultMediaAudio }

$mediaImages = Read-Host "QQBot 图片输出目录 [$defaultMediaImages]"
if (-not $mediaImages) { $mediaImages = $defaultMediaImages }

Write-Host ""
Write-Host "--- ComfyUI 文生图 ---" -ForegroundColor Green
Write-Host "(秋叶整合包: 安装目录下有 ComfyUI/ 和 python/ 子目录)" -ForegroundColor DarkGray
$comfyuiRoot = Read-Host "ComfyUI 根目录 (如 E:\comfyui\ComfyUI-aki-v3\ComfyUI)"
$comfyuiPython = Read-Host "ComfyUI 对应 Python (如 E:\comfyui\ComfyUI-aki-v3\python\python.exe)"
$comfyuiCheckpoints = Read-Host "ComfyUI checkpoints 目录 (如 E:\comfyui\ComfyUI-aki-v3\ComfyUI\models\checkpoints)"

Write-Host ""
Write-Host "--- GPT-SoVITS v2 Pro (TTS) ---" -ForegroundColor Green
Write-Host "(安装目录下有 runtime/python.exe 和 GPT_SoVITS/ 子目录)" -ForegroundColor DarkGray
$sovitsRoot = Read-Host "GPT-SoVITS 安装目录 (如 D:\GPT-SoVITS-v2pro)"
$sovitsPython = Read-Host "GPT-SoVITS 对应 Python (如 D:\GPT-SoVITS-v2pro\runtime\python.exe)"

Write-Host ""
Write-Host "--- llama.cpp (本地 LLM) ---" -ForegroundColor Green
$llamaExe = Read-Host "llama-server.exe 路径 (如 D:\vllm\llama-b9222-bin-win-cuda-12.4-x64\llama-server.exe)"
$llamaModel = Read-Host "GGUF 模型文件路径 (如 D:\vllm\models\qwen3.6-35b.gguf)"
$llamaLogDir = Read-Host "llama 重启日志目录 [$env:USERPROFILE\Desktop\vllm\restart-logs]"
if (-not $llamaLogDir) { $llamaLogDir = "$env:USERPROFILE\Desktop\vllm\restart-logs" }
$restartScript = Read-Host "restart-llama.ps1 路径 (如 $env:USERPROFILE\Desktop\vllm\restart-llama.ps1)"

# ============================================================
# 生成 config.yaml
# ============================================================
$yaml = @"
# AI Girlfriend 四季夏目 - 本地路径配置
# 由 quick_setup.ps1 自动生成，不会被 git 提交
# 如需修改路径，重新运行 quick_setup.ps1 或直接编辑此文件

workspace: "$workspace"
media_qqbot_audio: "$mediaAudio"
media_qqbot_images: "$mediaImages"

comfyui_root: "$comfyuiRoot"
comfyui_python: "$comfyuiPython"
comfyui_checkpoints_dir: "$comfyuiCheckpoints"
comfyui_temp_output_dir: "$defaultComfyuiTemp"

sovits_root: "$sovitsRoot"
sovits_python: "$sovitsPython"
tts_temp_output_dir: "$defaultTtsTemp"

llama_exe: "$llamaExe"
llama_model: "$llamaModel"
llama_log_dir: "$llamaLogDir"
restart_script: "$restartScript"
llama_port: 8080
"@

$configPath = Join-Path $scriptDir "config.yaml"
Set-Content -Path $configPath -Value $yaml -Encoding UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  config.yaml 已生成: $configPath" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 检查 config.yaml 路径是否正确" -ForegroundColor White
Write-Host "  2. 运行 download-models.ps1 下载模型" -ForegroundColor White
Write-Host "  3. 按 docs/quick-start.md 启动" -ForegroundColor White
