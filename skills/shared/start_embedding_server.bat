@echo off
REM ============================================================
REM 本地 Embedding 服务 启动脚本
REM 模型: sentence-transformers/all-MiniLM-L6-v2 (384 维)
REM 端口: http://127.0.0.1:9999
REM ============================================================

set "SCRIPT_DIR=%~dp0"
set "PRJ_ROOT=%SCRIPT_DIR%..\"

REM Python: 优先使用 Sakura runtime，其次用共享 runtime，最后系统 Python
if exist "%PRJ_ROOT%skills\sakura\runtime\python.exe" (
    set "PYTHON_EXE=%PRJ_ROOT%skills\sakura\runtime\python.exe"
) else if exist "%PRJ_ROOT%runtime\python.exe" (
    set "PYTHON_EXE=%PRJ_ROOT%runtime\python.exe"
) else (
    set "PYTHON_EXE=python"
)

REM 设置 HF 缓存到 Sakura runtime（复用缓存，不重复下载）
set "HF_HOME=%PRJ_ROOT%skills\sakura\runtime\hf-cache"
set "SENTENCE_TRANSFORMERS_HOME=%PRJ_ROOT%skills\sakura\runtime\hf-cache"

if not exist "%HF_HOME%" mkdir "%HF_HOME%"

echo [embedding_server] Starting local embedding service...
echo [embedding_server] Model: sentence-transformers/all-MiniLM-L6-v2
echo [embedding_server] Port: 9999
echo [embedding_server] HF cache: %HF_HOME%

cd /d "%SCRIPT_DIR%"
"%PYTHON_EXE%" "%SCRIPT_DIR%embedding_server.py" %*
pause
