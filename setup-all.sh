#!/usr/bin/env bash
# setup-all.sh
# ╔═══════════════════════════════════════════════════════════════════╗
# ║  AI Girlfriend — 四季夏目 · All-in-One Setup (Linux / macOS)       ║
# ║  One command: Models → llama.cpp → OpenClaw → Ready             ║
# ╚═══════════════════════════════════════════════════════════════════╝
#
# 用法:
#   bash setup-all.sh                           # 全部自动
#   bash setup-all.sh --skip-model-download     # 跳过模型下载
#   bash setup-all.sh --dry-run                 # 只检查不执行
#   bash setup-all.sh --model-base-dir /mnt/models  # 自定义模型目录
#   bash setup-all.sh --gpt-sovits-dir /opt/GPT-SoVITS  # 指定路径

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_TIME=$(date +%s)

# ═══════════════════════════════════════════════════════════════════
# Args
# ═══════════════════════════════════════════════════════════════════
MODEL_BASE_DIR=""
SKIP_MODEL_DOWNLOAD=false
SKIP_LLAMA_SETUP=false
SKIP_OPENCLAW_SETUP=false
WORKSPACE_PATH=""
GPT_SOVITS_DIR=""
COMFYUI_DIR=""
DRY_RUN=false
NO_START=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model-base-dir)   MODEL_BASE_DIR="$2"; shift 2 ;;
        --skip-model-download) SKIP_MODEL_DOWNLOAD=true; shift ;;
        --skip-llama-setup) SKIP_LLAMA_SETUP=true; shift ;;
        --skip-openclaw-setup) SKIP_OPENCLAW_SETUP=true; shift ;;
        --workspace)        WORKSPACE_PATH="$2"; shift 2 ;;
        --gpt-sovits-dir)   GPT_SOVITS_DIR="$2"; shift 2 ;;
        --comfyui-dir)      COMFYUI_DIR="$2"; shift 2 ;;
        --dry-run)          DRY_RUN=true; shift ;;
        --no-start)         NO_START=true; shift ;;
        --skip-bot-config)  SKIP_BOT_CONFIG=true; shift ;;
        --qq-app-id)        QQ_APP_ID="$2"; shift 2 ;;
        --qq-client-secret) QQ_CLIENT_SECRET="$2"; shift 2 ;;
        --tg-bot-token)     TG_BOT_TOKEN="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: bash setup-all.sh [options]"
            echo ""
            echo "Options:"
            echo "  --model-base-dir DIR    Model download root directory"
            echo "  --skip-model-download   Skip model download step"
            echo "  --skip-llama-setup      Skip llama.cpp setup step"
            echo "  --skip-openclaw-setup   Skip OpenClaw install step"
            echo "  --workspace PATH        OpenClaw workspace directory"
            echo "  --gpt-sovits-dir DIR    GPT-SoVITS install directory"
            echo "  --comfyui-dir DIR       ComfyUI install directory"
            echo "  --dry-run               Check only, no changes"
            echo "  --no-start              Don't start services"
            echo "  --skip-bot-config       Skip QQ/Telegram Bot config"
            echo "  --qq-app-id ID          QQ Bot AppID"
            echo "  --qq-client-secret SEC  QQ Bot ClientSecret"
            echo "  --tg-bot-token TOKEN    Telegram Bot Token"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ═══════════════════════════════════════════════════════════════════
# Colors & helpers
# ═══════════════════════════════════════════════════════════════════
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; WHITE='\033[1;37m'
GRAY='\033[0;90m'; NC='\033[0m'

ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()   { echo -e "  ${RED}✗${NC} $1"; }
info()  { echo -e "  ${GRAY}$1${NC}"; }
step()  { echo -e "${YELLOW}[$1/8]${NC} $2"; }

# ═══════════════════════════════════════════════════════════════════
# Banner
# ═══════════════════════════════════════════════════════════════════
clear 2>/dev/null || true
echo ""
echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  AI Girlfriend — 四季夏目 · All-in-One Setup (Linux/macOS)         ║${NC}"
echo -e "${MAGENTA}║  Models → llama.cpp → OpenClaw → Workspace → Start → Verify      ║${NC}"
echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# 0. Environment check
# ═══════════════════════════════════════════════════════════════════
step 0 "Environment check"

# Disk space
if command -v df &>/dev/null; then
    free_gb=$(df -BG . 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ -n "$free_gb" ]]; then
        info "Disk free: ${free_gb} GB"
        if [[ "$free_gb" -lt 50 ]]; then
            warn "Less than 50 GB free — models + tools need ~35 GB"
        fi
    fi
fi

# Memory
if command -v free &>/dev/null; then
    mem_gb=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}')
    info "RAM: ${mem_gb} GB"
    if [[ -n "$mem_gb" && "$mem_gb" -lt 16 ]]; then
        warn "RAM < 16 GB — model inference may be slow or OOM-prone"
    fi
elif [[ "$(uname)" == "Darwin" ]]; then
    mem_gb=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1073741824}')
    info "RAM: ${mem_gb} GB"
fi

# Network
if command -v curl &>/dev/null; then
    if curl -s --connect-timeout 5 https://huggingface.co >/dev/null 2>&1; then
        ok "Network: huggingface.co reachable"
    else
        warn "Cannot reach huggingface.co — model download may fail"
        info "  Tip: export HF_ENDPOINT=https://hf-mirror.com"
    fi
fi

# git
if command -v git &>/dev/null; then
    ok "git: $(git --version 2>&1)"
else
    warn "git not installed — needed for llama.cpp build"
fi

# python3
if command -v python3 &>/dev/null; then
    ok "python3: $(python3 --version 2>&1)"
elif command -v python &>/dev/null; then
    ok "python: $(python --version 2>&1)"
else
    warn "python3 not installed — needed for huggingface-cli"
fi

# Build tools (for llama.cpp)
if command -v g++ &>/dev/null || command -v clang++ &>/dev/null; then
    ok "C++ compiler found"
else
    warn "C++ compiler not found — install build-essential (Linux) or Xcode CLI tools (macOS)"
fi

# Check for CUDA / Metal
if command -v nvidia-smi &>/dev/null; then
    ok "GPU: NVIDIA CUDA detected"
    # Check CUDA toolkit version for RTX 50xx warning
    if command -v nvcc &>/dev/null; then
        CUDA_TK=$(nvcc --version 2>/dev/null | grep -oP 'release \K[0-9]+\.[0-9]+' || echo "")
        CUDA_MAJOR=$(echo "$CUDA_TK" | cut -d. -f1 2>/dev/null || echo 0)
        if [[ "$CUDA_MAJOR" -ge 13 ]]; then
            warn "CUDA Toolkit $CUDA_TK detected — RTX 50xx (Blackwell) may crash with 'munmap_chunk(): invalid pointer'"
            info "  Fix: use pre-built CUDA 12.4 llama.cpp binary instead of self-compiling"
            info "  https://github.com/ggml-org/llama.cpp/releases → cudart-llama-bin-linux-cuda-12.4-x64.tar.gz"
        fi
    fi
elif [[ "$(uname)" == "Darwin" ]]; then
    ok "GPU: Apple Silicon / Metal (auto-detected by llama.cpp)"
elif command -v rocminfo &>/dev/null; then
    ok "GPU: AMD ROCm detected"
else
    info "No GPU detected — will use CPU-only inference"
fi

echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  DRY RUN complete. No changes made.                               ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════
# 1. Model download
# ═══════════════════════════════════════════════════════════════════
step 1 "Download models (~29 GB)"

if [[ "$SKIP_MODEL_DOWNLOAD" == "true" ]]; then
    info "Skipped (--skip-model-download)"
else
    if [[ -z "$MODEL_BASE_DIR" ]]; then
        MODEL_BASE_DIR="$SCRIPT_DIR/models"
    fi

    # Ensure huggingface-cli
    if ! command -v huggingface-cli &>/dev/null && ! command -v hf &>/dev/null; then
        info "Installing huggingface_hub..."
        pip3 install huggingface_hub 2>&1 | tail -1 || pip install huggingface_hub 2>&1 | tail -1
    fi

    DL_SCRIPT="$SCRIPT_DIR/download-models.sh"
    if [[ -f "$DL_SCRIPT" ]]; then
        info "Running download-models.sh..."
        bash "$DL_SCRIPT" "$MODEL_BASE_DIR" && ok "Models downloaded → $MODEL_BASE_DIR" || warn "Model download may have incomplete items"
    else
        err "download-models.sh not found"
    fi
fi
echo ""

# ═══════════════════════════════════════════════════════════════════
# 2. llama.cpp setup
# ═══════════════════════════════════════════════════════════════════
step 2 "Configure llama.cpp (auto-detect hardware)"

if [[ "$SKIP_LLAMA_SETUP" == "true" ]]; then
    info "Skipped (--skip-llama-setup)"
else
    SL_SCRIPT="$SCRIPT_DIR/setup-llama.sh"
    if [[ -f "$SL_SCRIPT" ]]; then
        info "Running setup-llama.sh..."
        bash "$SL_SCRIPT" && {
            ok "llama.cpp configured"
            [[ -f "$SCRIPT_DIR/llama-config/launch-llama.sh" ]] && ok "Launch script: llama-config/launch-llama.sh"
        } || warn "llama.cpp setup had issues"
    else
        err "setup-llama.sh not found"
    fi
fi
echo ""

# ═══════════════════════════════════════════════════════════════════
# 3. OpenClaw install
# ═══════════════════════════════════════════════════════════════════
step 3 "Install OpenClaw"

if [[ "$SKIP_OPENCLAW_SETUP" == "true" ]]; then
    info "Skipped (--skip-openclaw-setup)"
else
    SO_SCRIPT="$SCRIPT_DIR/setup-openclaw.sh"
    if [[ -f "$SO_SCRIPT" ]]; then
        info "Running setup-openclaw.sh..."
        OC_ARGS="--skip-deploy"
        [[ -n "$WORKSPACE_PATH" ]] && OC_ARGS="$OC_ARGS --workspace $WORKSPACE_PATH"
        bash "$SO_SCRIPT" $OC_ARGS && ok "OpenClaw installed" || warn "OpenClaw install had issues"
    else
        err "setup-openclaw.sh not found"
    fi
fi
echo ""

# ═══════════════════════════════════════════════════════════════════
# 4. Workspace deploy + paths
# ═══════════════════════════════════════════════════════════════════
step 4 "Deploy workspace + path config"

if [[ -z "$WORKSPACE_PATH" ]]; then
    WORKSPACE_PATH="${HOME}/.openclaw/workspace"
fi
WORKSPACE_PATH="$(cd "$(dirname "$WORKSPACE_PATH")" 2>/dev/null && pwd)/$(basename "$WORKSPACE_PATH")" || WORKSPACE_PATH="${HOME}/.openclaw/workspace"
info "Target: $WORKSPACE_PATH"

# Interactive path collection
if [[ -z "$GPT_SOVITS_DIR" ]]; then
    echo -e "  ${CYAN}── GPT-SoVITS path ──${NC}"
    echo -n "  GPT-SoVITS install directory (enter to skip): "
    read -r GPT_SOVITS_DIR
fi
if [[ -z "$COMFYUI_DIR" ]]; then
    echo -e "  ${CYAN}── ComfyUI path ──${NC}"
    echo -n "  ComfyUI install directory (enter to skip): "
    read -r COMFYUI_DIR
fi

# Create workspace dir
mkdir -p "$WORKSPACE_PATH"

# Copy files (skip existing)
FILES=("AGENTS.md" "SOUL.md" "IDENTITY.md" "USER.md" "HEARTBEAT.md" "TOOLS.md" "config-patch.json" "models.yaml" ".gitignore")
for f in "${FILES[@]}"; do
    src="$SCRIPT_DIR/$f"
    dst="$WORKSPACE_PATH/$f"
    if [[ -f "$src" && ! -f "$dst" ]]; then
        cp "$src" "$dst"
        ok "$f"
    elif [[ -f "$dst" ]]; then
        info "$f (exists, skipped)"
    fi
done

# Copy skills
SKILL_SRC="$SCRIPT_DIR/skills"
SKILL_DST="$WORKSPACE_PATH/skills"
mkdir -p "$SKILL_DST"
if [[ -d "$SKILL_SRC" ]]; then
    cp -r "$SKILL_SRC"/* "$SKILL_DST"/
    ok "skills/ directory"
fi

# Create runtime dirs
mkdir -p "$WORKSPACE_PATH/memory/role_play"
mkdir -p "$WORKSPACE_PATH/media/qqbot/audio"
mkdir -p "$WORKSPACE_PATH/media/qqbot/images"

# Write path-map.json
cat > "$WORKSPACE_PATH/path-map.json" << PATHMAPEOF
{
    "gpt_sovits_dir": "${GPT_SOVITS_DIR}",
    "comfyui_dir": "${COMFYUI_DIR}",
    "workspace": "${WORKSPACE_PATH}",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
PATHMAPEOF
ok "path-map.json (path config)"

ok "Workspace deployed"
echo ""

# ═══════════════════════════════════════════════════════════════════
# 5. Bot Token Configuration
# ═══════════════════════════════════════════════════════════════════
step 5 "Configure QQ Bot + Telegram Bot Token"

if [[ "$SKIP_BOT_CONFIG" == "true" ]]; then
    info "Skipped (--skip-bot-config)"
else
    # QQ Bot
    if [[ -z "$QQ_APP_ID" ]]; then
        echo -e "  ${CYAN}── QQ Bot Credentials ──${NC}"
        echo -e "  ${GRAY}(Go to https://q.qq.com/ to create a bot and get AppID + ClientSecret)${NC}"
        echo -n "  QQ AppID (enter to skip): "
        read -r QQ_APP_ID
    fi
    if [[ -n "$QQ_APP_ID" && -z "$QQ_CLIENT_SECRET" ]]; then
        echo -n "  QQ ClientSecret: "
        read -r QQ_CLIENT_SECRET
    fi

    # Telegram Bot
    if [[ -z "$TG_BOT_TOKEN" ]]; then
        echo -e "  ${CYAN}── Telegram Bot Token ──${NC}"
        echo -e "  ${GRAY}(Send /newbot to https://t.me/BotFather to create a bot)${NC}"
        echo -n "  Telegram Bot Token (enter to skip): "
        read -r TG_BOT_TOKEN
    fi

    # Apply QQ Bot config
    if [[ -n "$QQ_APP_ID" && -n "$QQ_CLIENT_SECRET" ]]; then
        info "Applying QQ Bot config..."
        if command -v openclaw &>/dev/null; then
            QQ_PATCH='[{"path":"channels.qqbot.enabled","value":true},{"path":"channels.qqbot.name","value":"四季夏目"},{"path":"channels.qqbot.appId","value":"'"$QQ_APP_ID"'"},{"path":"channels.qqbot.clientSecret","value":"'"$QQ_CLIENT_SECRET"'"},{"path":"channels.qqbot.dmPolicy","value":"open"},{"path":"channels.qqbot.groupPolicy","value":"open"},{"path":"channels.qqbot.markdownSupport","value":true},{"path":"channels.qqbot.streaming.mode","value":"partial"},{"path":"channels.qqbot.urlDirectUpload","value":true}]'
            openclaw gateway call config.patch.apply --json --params "$QQ_PATCH" 2>/dev/null && ok "QQ Bot configured" || warn "QQ Bot config failed — apply config-qqbot.json manually"
        else
            warn "openclaw CLI not found — apply config-qqbot.json manually"
        fi
    else
        info "QQ Bot skipped"
    fi

    # Apply Telegram Bot config
    if [[ -n "$TG_BOT_TOKEN" ]]; then
        info "Applying Telegram Bot config..."
        if command -v openclaw &>/dev/null; then
            TG_PATCH='[{"path":"channels.telegram.enabled","value":true},{"path":"channels.telegram.botToken","value":"'"$TG_BOT_TOKEN"'"},{"path":"channels.telegram.dmPolicy","value":"pairing"},{"path":"channels.telegram.replyToMode","value":"first"},{"path":"channels.telegram.historyLimit","value":50},{"path":"channels.telegram.streaming","value":"partial"},{"path":"channels.telegram.linkPreview","value":true},{"path":"channels.telegram.mediaMaxMb","value":100},{"path":"channels.telegram.actions.reactions","value":true},{"path":"channels.telegram.actions.sendMessage","value":true},{"path":"channels.telegram.reactionNotifications","value":"own"}]'
            openclaw gateway call config.patch.apply --json --params "$TG_PATCH" 2>/dev/null && ok "Telegram Bot configured" || warn "Telegram Bot config failed — apply config-telegram.json manually"
        else
            warn "openclaw CLI not found — apply config-telegram.json manually"
        fi
    else
        info "Telegram Bot skipped"
    fi
fi
echo ""

# ═══════════════════════════════════════════════════════════════════
# 6. Path audit
# ═══════════════════════════════════════════════════════════════════
step 6 "Path audit & fix checklist"
echo ""
echo -e "  ${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${YELLOW}║  ⚠️  Edit config.yaml to set your local paths:            ║${NC}"
echo -e "  ${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

EDITS=(
    "config.yaml|llama_model_path, comfyui_root, gpt_sovits_dir, ref_wav_dir, output_dir"
    "skills/tts/tts_call.py|all paths now read from config.yaml — just verify"
    "skills/comfyui/comfyui_call.py|all paths now read from config.yaml — just verify"
)

for entry in "${EDITS[@]}"; do
    file="${entry%%|*}"
    vars="${entry#*|}"
    echo -e "  ${WHITE}📄 $WORKSPACE_PATH/$file${NC}"
    IFS=',' read -ra VAR_LIST <<< "$vars"
    for v in "${VAR_LIST[@]}"; do
        echo -e "     ${YELLOW}→ $v${NC}"
    done
    echo ""
done

echo -e "  ${CYAN}💡 Use sed or VS Code to find/replace hardcoded paths${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# 7. Start services
# ═══════════════════════════════════════════════════════════════════
step 7 "Start services"

if [[ "$NO_START" == "true" ]]; then
    info "Skipped (--no-start)"
else
    # Start llama-server
    LAUNCH_SCRIPT="$SCRIPT_DIR/llama-config/launch-llama.sh"
    if [[ -f "$LAUNCH_SCRIPT" ]]; then
        info "Starting llama-server..."
        # Check if already running
        if pgrep -f "llama-server" >/dev/null 2>&1; then
            ok "llama-server already running"
        else
            bash "$LAUNCH_SCRIPT" &
            ok "llama-server started (PID $!)"
            info "  Wait ~12s for model load"
        fi
    else
        warn "launch-llama.sh not found — run setup-llama.sh first"
    fi

    # Start OpenClaw Gateway
    info "Starting OpenClaw Gateway..."
    if command -v openclaw &>/dev/null; then
        openclaw gateway start 2>&1 && ok "Gateway started" || warn "Gateway start failed — try: openclaw gateway start"
    else
        warn "openclaw CLI not found"
    fi
fi
echo ""

# ═══════════════════════════════════════════════════════════════════
# 8. Verification
# ═══════════════════════════════════════════════════════════════════
step 8 "Verification"

# llama-server health
if curl -s --connect-timeout 5 http://127.0.0.1:8080/health >/dev/null 2>&1; then
    ok "llama-server: healthy ✅"
else
    warn "llama-server: not responding (may still be loading)"
fi

# OpenClaw Gateway
if command -v openclaw &>/dev/null; then
    if openclaw gateway status &>/dev/null; then
        ok "OpenClaw Gateway: running ✅"
    else
        warn "OpenClaw Gateway: status unknown"
    fi
else
    warn "OpenClaw Gateway: CLI not found"
fi

# Workspace
if [[ -f "$WORKSPACE_PATH/AGENTS.md" ]]; then
    ok "Workspace: complete ✅"
else
    err "Workspace: missing files"
fi

# Model GGUF
GGUF=$(find "$MODEL_BASE_DIR" "$SCRIPT_DIR/models" "$SCRIPT_DIR/llm" -name "*.gguf" -type f 2>/dev/null | head -1)
if [[ -n "$GGUF" ]]; then
    ok "LLM model: $(basename "$GGUF") ✅"
else
    warn "LLM model: no .gguf found"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════
# Done
# ═══════════════════════════════════════════════════════════════════
ELAPSED=$(( ($(date +%s) - START_TIME) / 60 ))
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           🎉 AI Girlfriend — 四季夏目 · Setup Complete!           ║${NC}"
echo -e "${GREEN}║           Time: ${ELAPSED}min | Workspace: $WORKSPACE_PATH${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${YELLOW}📋 Must-do checklist:${NC}"
echo -e "    ${WHITE}1. Edit config.yaml — set all local paths (see Step 6)${NC}"
echo -e "    ${WHITE}2. Edit USER.md (your name/handle)${NC}"
echo -e "    ${WHITE}3. (If you skipped Step 5) Manually configure QQ/Telegram Bot tokens${NC}"
echo -e "    ${WHITE}4. ⚠️ RTX 50xx users: use pre-built CUDA 12.4 llama.cpp binary!${NC}"
echo ""
echo -e "  ${CYAN}🚀 Daily startup:${NC}"
echo -e "    ${WHITE}bash start-girlfriend.sh${NC}"
echo -e "    ${WHITE}openclaw gateway --open  # Open Web Chat${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Generate start-girlfriend.sh (daily quick-start)
# ═══════════════════════════════════════════════════════════════════
cat > "$SCRIPT_DIR/start-girlfriend.sh" << 'STARTSCRIPT'
#!/usr/bin/env bash
# start-girlfriend.sh — AI Girlfriend daily quick-start (auto-generated)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; MAGENTA='\033[0;35m'; NC='\033[0m'

echo -e "${MAGENTA}🌸 Starting AI Girlfriend — 四季夏目...${NC}"

# Start llama-server
LAUNCH="$SCRIPT_DIR/llama-config/launch-llama.sh"
if [[ -f "$LAUNCH" ]]; then
    if pgrep -f "llama-server" >/dev/null 2>&1; then
        echo -e "  ${GREEN}llama-server already running${NC}"
    else
        bash "$LAUNCH" &
        echo -e "  ${GREEN}llama-server starting (PID $!)...${NC}"
    fi
else
    echo -e "  ${YELLOW}launch-llama.sh not found — skip${NC}"
fi

# Start Gateway
if command -v openclaw &>/dev/null; then
    if openclaw gateway status &>/dev/null; then
        echo -e "  ${GREEN}Gateway already running${NC}"
    else
        openclaw gateway start 2>/dev/null && echo -e "  ${GREEN}Gateway started${NC}" || echo -e "  ${YELLOW}Gateway start failed${NC}"
    fi
else
    echo -e "  ${YELLOW}openclaw CLI not found${NC}"
fi

echo -e "${GREEN}✅ Ready. Open: http://127.0.0.1:18789${NC}"
STARTSCRIPT

chmod +x "$SCRIPT_DIR/start-girlfriend.sh"
ok "Generated start-girlfriend.sh (daily one-click start)"
echo ""
echo -e "  ${GRAY}Project: https://github.com/momori777/openclaw_based_ai_girlfriend${NC}"
echo -e "  ${GRAY}Models:  https://huggingface.co/TAOTAO777/ai-girlfriend-natsume${NC}"
echo -e "  ${GRAY}Docs:    https://docs.openclaw.ai${NC}"
echo ""
