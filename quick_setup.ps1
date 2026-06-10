# AI Girlfriend 四季夏目 — 一键路径配置脚本
# 自动检测已安装的工具路径，没找到的交互式填写，最终生成 config.yaml
#
# 用法: powershell -ExecutionPolicy Bypass -File quick_setup.ps1

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Girlfriend 四季夏目 — 一键路径向导" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "正在扫描已安装的工具……" -ForegroundColor Yellow
Write-Host ""

# ============================================================
# 辅助函数
# ============================================================
function Find-Exe($name, $searchPaths) {
    foreach ($dir in $searchPaths) {
        $candidate = Join-Path $dir $name
        if (Test-Path $candidate) { return $candidate }
        # 也递归一层
        try {
            $found = Get-ChildItem $dir -Filter $name -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) { return $found.FullName }
        } catch {}
    }
    return $null
}

function Find-Dir($name, $searchRoots) {
    foreach ($root in $searchRoots) {
        try {
            $found = Get-ChildItem $root -Directory -Filter $name -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) { return $found.FullName }
        } catch {}
    }
    return $null
}

function Prompt-Path($label, $default, $hint) {
    if ($hint) { Write-Host "  $hint" -ForegroundColor DarkGray }
    $val = Read-Host "$label"
    if (-not $val) { $val = $default }
    if ($val) { Write-Host "    -> $val" -ForegroundColor Green }
    else { Write-Host "    -> (未设置)" -ForegroundColor DarkGray }
    return $val
}

# ============================================================
# 搜索根目录
# ============================================================
$desktop = [Environment]::GetFolderPath("Desktop")
$searchRoots = @("C:\", "D:\", "E:\", $desktop, $env:USERPROFILE, "$env:USERPROFILE\Desktop\vllm")
$defaultWorkspace = "$env:USERPROFILE\.openclaw\workspace"
$defaultMediaAudio = "$env:USERPROFILE\.openclaw\media\qqbot\audio"
$defaultMediaImages = "$env:USERPROFILE\.openclaw\media\qqbot\images"
$defaultComfyuiTemp = "$defaultWorkspace\comfyui"
$defaultTtsTemp = $defaultMediaAudio
$defaultLlamaLogDir = "$desktop\vllm\restart-logs"

# ============================================================
# 1. OpenClaw workspace（自动检测）
# ============================================================
Write-Host "--- OpenClaw Workspace ---" -ForegroundColor Green
$workspace = $defaultWorkspace
if (-not (Test-Path $workspace)) {
    # 尝试在当前项目目录上两级找
    $workspace = Split-Path -Parent (Split-Path -Parent $scriptDir)
    if ($workspace -notmatch 'workspace') { $workspace = $defaultWorkspace }
}
Write-Host "  workspace: $workspace" -ForegroundColor $(if (Test-Path $workspace) { 'Green' } else { 'Red' })

# 媒体目录
$mediaAudio = $defaultMediaAudio
$mediaImages = $defaultMediaImages
# 确保存在
New-Item -ItemType Directory -Force -Path $mediaAudio -ErrorAction SilentlyContinue | Out-Null
New-Item -ItemType Directory -Force -Path $mediaImages -ErrorAction SilentlyContinue | Out-Null
Write-Host "  audio out: $mediaAudio" -ForegroundColor Green
Write-Host "  image out: $mediaImages" -ForegroundColor Green

# ============================================================
# 2. ComfyUI（自动检测 + 手动补填）
# ============================================================
Write-Host ""
Write-Host "--- ComfyUI ---" -ForegroundColor Green

$comfyuiRoot = Find-Dir "ComfyUI" $searchRoots
$comfyuiPython = Find-Exe "python.exe" @("$comfyuiRoot\..\python", "$comfyuiRoot\python", "E:\comfyui\ComfyUI-aki-v3\python")
$comfyuiCheckpoints = if ($comfyuiRoot) { Join-Path $comfyuiRoot "models\checkpoints" } else { $null }
$comfyuiConfigure = Find-Exe "A绘世启动器.exe" @("$comfyuiRoot\..", "$comfyuiRoot\..\..", "E:\comfyui\ComfyUI-aki-v3")

if (-not $comfyuiRoot) {
    Write-Host "  未自动检测到 ComfyUI，请手动填写：" -ForegroundColor Yellow
    $comfyuiRoot = Prompt-Path "  ComfyUI 根目录 (含 models/checkpoints/)" $null ""
    $comfyuiPython = Prompt-Path "  Python 路径 (秋叶整合包: .../python/python.exe)" $null ""
    $comfyuiCheckpoints = Prompt-Path "  checkpoints 目录" $null ""
    $comfyuiConfigure = Prompt-Path "  A绘世启动器.exe (秋叶整合包一键启动)" $null ""
} else {
    $comfyuiCheckpoints = if ($comfyuiRoot) { Join-Path $comfyuiRoot "models\checkpoints" } else { $null }
    Write-Host "  root:      $comfyuiRoot" -ForegroundColor $(if (Test-Path $comfyuiRoot) { 'Green' } else { 'Yellow' })
    Write-Host "  python:    $comfyuiPython" -ForegroundColor $(if (Test-Path $comfyuiPython) { 'Green' } else { 'Yellow' })
    Write-Host "  ckpt dir:  $comfyuiCheckpoints" -ForegroundColor $(if (Test-Path $comfyuiCheckpoints) { 'Green' } else { 'Yellow' })
    Write-Host "  launcher:  $comfyuiConfigure" -ForegroundColor $(if ($comfyuiConfigure -and (Test-Path $comfyuiConfigure)) { 'Green' } else { 'DarkGray' })
    # 没找到的单独问
    if (-not $comfyuiConfigure) {
        $comfyuiConfigure = Prompt-Path "  A绘世启动器.exe (秋叶整合包一键启动，可跳过)" $null ""
    }
}

# ============================================================
# 3. GPT-SoVITS v2 Pro（自动检测 + 手动补填）
# ============================================================
Write-Host ""
Write-Host "--- GPT-SoVITS v2 Pro (TTS) ---" -ForegroundColor Green

$sovitsRoot = Find-Dir "GPT-SoVITS-v2pro*" $searchRoots
if (-not $sovitsRoot) { $sovitsRoot = Find-Dir "GPT-SoVITS*" $searchRoots }
$sovitsPython = if ($sovitsRoot) { Join-Path $sovitsRoot "runtime\python.exe" } else { $null }

if (-not $sovitsRoot) {
    Write-Host "  未自动检测到 GPT-SoVITS，请手动填写：" -ForegroundColor Yellow
    $sovitsRoot = Prompt-Path "  GPT-SoVITS 安装目录" $null ""
    $sovitsPython = Prompt-Path "  runtime/python.exe 完整路径" $null ""
} else {
    Write-Host "  root:   $sovitsRoot" -ForegroundColor $(if (Test-Path $sovitsRoot) { 'Green' } else { 'Yellow' })
    Write-Host "  python: $sovitsPython" -ForegroundColor $(if (Test-Path $sovitsPython) { 'Green' } else { 'Yellow' })
}

# ============================================================
# 4. llama.cpp（自动检测 + 手动补填）
# ============================================================
Write-Host ""
Write-Host "--- llama.cpp (本地 LLM) ---" -ForegroundColor Green

$llamaExe = Find-Exe "llama-server.exe" $searchRoots
$llamaModel = Find-Exe "*.gguf" $searchRoots  # 可能有多个，取第一个

# 如果有 vllm 目录
$vllmDir = Find-Dir "vllm" $searchRoots
if (-not $vllmDir) { $vllmDir = Find-Dir "vllm" @($desktop) }
$llamaLogDir = if ($vllmDir) { Join-Path $vllmDir "restart-logs" } else { $defaultLlamaLogDir }
$restartScript = Find-Exe "restart-llama.ps1" @($vllmDir, "$defaultWorkspace\skills\shared")

if (-not $llamaExe) {
    Write-Host "  未自动检测到 llama.cpp，请手动填写：" -ForegroundColor Yellow
    $llamaExe = Prompt-Path "  llama-server.exe 路径" $null ""
    $llamaModel = Prompt-Path "  GGUF 模型文件路径" $null ""
    $llamaLogDir = Prompt-Path "  日志目录" $defaultLlamaLogDir ""
    $restartScript = Prompt-Path "  restart-llama.ps1 路径" $null ""
} else {
    Write-Host "  exe:     $llamaExe" -ForegroundColor $(if (Test-Path $llamaExe) { 'Green' } else { 'Yellow' })
    Write-Host "  model:   $llamaModel" -ForegroundColor $(if ($llamaModel -and (Test-Path $llamaModel)) { 'Green' } else { 'Yellow' })
    Write-Host "  log dir: $llamaLogDir" -ForegroundColor Green
    Write-Host "  restart: $restartScript" -ForegroundColor $(if ($restartScript -and (Test-Path $restartScript)) { 'Green' } else { 'DarkGray' })
    # 模型可能有多个
    if ($llamaModel -and (Test-Path $llamaModel)) {
        # 只取第一个
    } else {
        # 让用户选
        $llamaModel = Prompt-Path "  GGUF 模型文件路径 (检测到多个或路径不对)" $llamaModel ""
    }
    if (-not $restartScript) {
        $restartScript = Prompt-Path "  restart-llama.ps1 路径 (可跳过，使用内置降级重启)" $null ""
    }
}

# ============================================================
# 5. 生成 config.yaml
# ============================================================
Write-Host ""
Write-Host "生成 config.yaml..." -ForegroundColor Cyan

# 确保路径用双反斜杠
$esc = { param($p) if ($p) { $p.Replace('\', '\\') } else { '' } }

$yaml = @"
# AI Girlfriend 四季夏目 - 路径配置文件
# 由 quick_setup.ps1 自动生成 $(Get-Date -Format 'yyyy-MM-dd HH:mm')
# 重新运行 quick_setup.ps1 可修改路径

# ============================================================
# OpenClaw workspace (agent 工作区)
# ============================================================
workspace: "$(& $esc $workspace)"

# ============================================================
# 媒体输出目录 (qqbot channel 的发文件目录)
# ============================================================
media_qqbot_audio: "$(& $esc $mediaAudio)"
media_qqbot_images: "$(& $esc $mediaImages)"

# ============================================================
# ComfyUI 文生图
# ============================================================
comfyui_root: "$(& $esc $comfyuiRoot)"
comfyui_python: "$(& $esc $comfyuiPython)"
comfyui_checkpoints_dir: "$(& $esc $comfyuiCheckpoints)"
comfyui_temp_output_dir: "$(& $esc $defaultComfyuiTemp)"
comfyui_launcher: "$(& $esc $comfyuiConfigure)"

# ============================================================
# GPT-SoVITS v2 Pro (TTS)
# ============================================================
sovits_root: "$(& $esc $sovitsRoot)"
sovits_python: "$(& $esc $sovitsPython)"
tts_temp_output_dir: "$(& $esc $defaultTtsTemp)"

# ============================================================
# llama.cpp (本地 LLM)
# ============================================================
llama_exe: "$(& $esc $llamaExe)"
llama_model: "$(& $esc $llamaModel)"
llama_log_dir: "$(& $esc $llamaLogDir)"
restart_script: "$(& $esc $restartScript)"
llama_port: 8080
"@

$configPath = Join-Path $scriptDir "config.yaml"
Set-Content -Path $configPath -Value $yaml -Encoding UTF8

# ============================================================
# 6. 验证总结
# ============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  config.yaml 已生成: $configPath" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$checks = @(
    @{Label="ComfyUI root";    Path=$comfyuiRoot},
    @{Label="ComfyUI python";  Path=$comfyuiPython},
    @{Label="ComfyUI ckpt";    Path=$comfyuiCheckpoints},
    @{Label="ComfyUI launcher";Path=$comfyuiConfigure},
    @{Label="SovITS root";     Path=$sovitsRoot},
    @{Label="SovITS python";   Path=$sovitsPython},
    @{Label="llama exe";       Path=$llamaExe},
    @{Label="llama model";     Path=$llamaModel},
    @{Label="workspace";       Path=$workspace},
    @{Label="media audio";     Path=$mediaAudio},
    @{Label="media images";    Path=$mediaImages},
    @{Label="llama log dir";   Path=$llamaLogDir}
)

$ok = 0
$bad = 0
Write-Host "路径验证:" -ForegroundColor Yellow
foreach ($c in $checks) {
    if ($c.Path -and (Test-Path $c.Path)) {
        Write-Host "  [OK]   $($c.Label)" -ForegroundColor Green
        $ok++
    } elseif ($c.Path) {
        Write-Host "  [MISS] $($c.Label): $($c.Path)" -ForegroundColor Red
        $bad++
    } else {
        Write-Host "  [SKIP] $($c.Label) (未设置)" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "结果: $ok 个就绪, $bad 个缺失" -ForegroundColor $(if ($bad -eq 0) { 'Green' } else { 'Yellow' })

if ($bad -gt 0) {
    Write-Host ""
    Write-Host "缺失路径请手动编辑 config.yaml 补充。" -ForegroundColor Yellow
    Write-Host "或重新运行: powershell -ExecutionPolicy Bypass -File quick_setup.ps1" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "所有路径验证通过！" -ForegroundColor Green
    Write-Host "下一步: 运行 download-models.ps1 下载模型" -ForegroundColor White
}

Write-Host ""
Write-Host "降级重启 llama: .\skills\shared\restart_llama_degraded.ps1" -ForegroundColor DarkGray
