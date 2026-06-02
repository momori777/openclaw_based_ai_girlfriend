#!/usr/bin/env bash
# setup-openclaw.sh
# AI Girlfriend — 四季夏目 · OpenClaw 一键部署 (Linux / macOS / WSL2)
#
# 自动完成:
#   1. 检测 Node.js → 缺失则安装
#   2. 安装 OpenClaw Gateway (via 官方安装脚本)
#   3. 部署 AI Girlfriend 工作区到 OpenClaw workspace
#   4. 应用 config-patch.json (本地 LLM 上下文窗口配置)
#   5. 启动 OpenClaw Gateway daemon
#   6. 验证安装
#
# 用法:
#   bash setup-openclaw.sh
#   bash setup-openclaw.sh --workspace /path/to/workspace
#   bash setup-openclaw.sh --skip-node --skip-deploy --no-onboard
#
# 前置:
#   - 已运行 download-models.sh 下载模型
#   - (可选) 已运行 setup-llama.sh 配置 llama.cpp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_PATH=""
SKIP_NODE=false
SKIP_DEPLOY=false
NO_ONBOARD=false
SKIP_DAEMON=false

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --workspace) WORKSPACE_PATH="$2"; shift 2 ;;
        --skip-node) SKIP_NODE=true; shift ;;
        --skip-deploy) SKIP_DEPLOY=true; shift ;;
        --no-onboard) NO_ONBOARD=true; shift ;;
        --skip-daemon) SKIP_DAEMON=true; shift ;;
        -h|--help)
            echo "Usage: bash setup-openclaw.sh [options]"
            echo ""
            echo "Options:"
            echo "  --workspace PATH    Target OpenClaw workspace directory"
            echo "  --skip-node         Skip Node.js installation check"
            echo "  --skip-deploy       Skip workspace file deployment"
            echo "  --no-onboard        Skip OpenClaw onboarding wizard"
            echo "  --skip-daemon       Skip Gateway daemon setup"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m'
WHITE='\033[0;37m'
NC='\033[0m'

# ============================================================================
# Banner
# ============================================================================
echo ""
echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  AI Girlfriend — 四季夏目 · OpenClaw 一键部署              ║${NC}"
echo -e "${MAGENTA}║  Setup OpenClaw Gateway + Deploy AI Girlfriend Workspace   ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Step 1: Check / Install Node.js
# ============================================================================
if $SKIP_NODE; then
    echo -e "${GRAY}[1/5] Skipping Node.js check (--skip-node)${NC}"
else
    echo -e "${YELLOW}[1/5] Checking Node.js...${NC}"

    NODE_VERSION=""
    if command -v node &>/dev/null; then
        NODE_VERSION=$(node --version 2>/dev/null || echo "")
    fi

    NEEDS_NODE=false
    if [[ -z "$NODE_VERSION" ]]; then
        NEEDS_NODE=true
    else
        MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d. -f1)
        if [[ "$MAJOR" -lt 22 ]]; then
            echo -e "  ${YELLOW}Node $NODE_VERSION found, but needs v22.16+ (v24 recommended)${NC}"
            NEEDS_NODE=true
        fi
    fi

    if ! $NEEDS_NODE; then
        echo -e "  ${GREEN}Node.js $NODE_VERSION — OK${NC}"
    else
        echo -e "  ${YELLOW}Installing Node.js via nvm / fnm...${NC}"

        # Detect OS
        OS_TYPE="$(uname -s)"

        # Try fnm (cross-platform, fast)
        if command -v fnm &>/dev/null; then
            echo -e "  ${GRAY}fnm found, installing Node 24...${NC}"
            fnm install 24
            fnm use 24
        elif command -v nvm &>/dev/null; then
            echo -e "  ${GRAY}nvm found, installing Node 24...${NC}"
            nvm install 24
            nvm use 24
        else
            # Install fnm
            echo -e "  ${GRAY}Installing fnm (Fast Node Manager)...${NC}"
            if [[ "$OS_TYPE" == "Darwin" ]]; then
                # macOS
                if command -v brew &>/dev/null; then
                    brew install fnm
                else
                    curl -fsSL https://fnm.vercel.app/install | bash
                fi
            else
                # Linux / WSL2
                curl -fsSL https://fnm.vercel.app/install | bash
            fi

            # Source fnm
            export FNM_DIR="${HOME}/.fnm"
            if [[ -f "$FNM_DIR/fnm" ]]; then
                eval "$(fnm env)"
            elif [[ -f "$HOME/.local/share/fnm/fnm" ]]; then
                export FNM_DIR="$HOME/.local/share/fnm"
                eval "$(fnm env)"
            fi

            if command -v fnm &>/dev/null; then
                fnm install 24
                fnm use 24
            else
                echo -e "  ${RED}[ERROR] Cannot install Node.js automatically.${NC}"
                echo -e "  ${RED}Please install manually: https://nodejs.org/ (v22+ or v24+)${NC}"
                echo -e "  ${YELLOW}After installing, re-run this script.${NC}"
                exit 1
            fi
        fi

        echo -e "  ${GREEN}Node.js installed!${NC}"
        echo ""
        echo -e "  ${YELLOW}⚠️  You may need to restart your shell and re-run this script.${NC}"
        echo -e "  ${YELLOW}   Or run: source ~/.bashrc (or ~/.zshrc)${NC}"

        # If we can continue in this session
        if command -v node &>/dev/null; then
            echo -e "  ${GREEN}Node.js is available in this session.${NC}"
        else
            echo -e "  ${YELLOW}Please restart your shell, then run: bash setup-openclaw.sh${NC}"
            exit 0
        fi
    fi
fi

# ============================================================================
# Step 2: Install OpenClaw
# ============================================================================
echo -e "${YELLOW}[2/5] Installing OpenClaw...${NC}"

if command -v openclaw &>/dev/null; then
    OC_VERSION=$(openclaw --version 2>&1 || echo "unknown")
    OC_PATH=$(which openclaw)
    echo -e "  ${GREEN}OpenClaw already installed: $OC_VERSION${NC}"
    echo -e "  ${GRAY}Path: $OC_PATH${NC}"
else
    echo -e "  ${YELLOW}Downloading and installing OpenClaw...${NC}"
    echo -e "  ${GRAY}Using official install script: https://openclaw.ai/install.sh${NC}"

    if $NO_ONBOARD; then
        curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
    else
        curl -fsSL https://openclaw.ai/install.sh | bash
    fi

    # Verify
    if command -v openclaw &>/dev/null; then
        OC_VERSION=$(openclaw --version 2>&1)
        echo -e "  ${GREEN}OpenClaw installed successfully!${NC}"
        echo -e "  ${GRAY}Version: $OC_VERSION${NC}"
    else
        echo -e "  ${RED}[ERROR] openclaw CLI not found after install.${NC}"
        echo -e "  ${YELLOW}Try restarting your terminal and running: openclaw --version${NC}"
        echo -e "  ${YELLOW}If still not found, add npm global bin to PATH:${NC}"
        echo -e "  ${WHITE}  export PATH=\"\$(npm prefix -g)/bin:\$PATH\"${NC}"
        exit 1
    fi
fi

# ============================================================================
# Step 3: Deploy AI Girlfriend Workspace
# ============================================================================
if $SKIP_DEPLOY; then
    echo -e "${GRAY}[3/5] Skipping workspace deployment (--skip-deploy)${NC}"
else
    echo -e "${YELLOW}[3/5] Deploying AI Girlfriend workspace...${NC}"

    # Determine OpenClaw workspace directory
    if [[ -z "$WORKSPACE_PATH" ]]; then
        WORKSPACE_PATH="$HOME/.openclaw/workspace"
    fi
    WORKSPACE_PATH="$(cd "$WORKSPACE_PATH" 2>/dev/null && pwd || echo "$WORKSPACE_PATH")"

    echo -e "  ${GRAY}Target workspace: $WORKSPACE_PATH${NC}"

    # Create workspace directory if needed
    mkdir -p "$WORKSPACE_PATH"

    # Copy workspace files (non-destructive — won't overwrite existing user-modified files)
    deploy_files=(
        "AGENTS.md"
        "SOUL.md"
        "IDENTITY.md"
        "USER.md"
        "HEARTBEAT.md"
        "TOOLS.md"
        "config-patch.json"
        "models.yaml"
        ".gitignore"
    )

    echo -e "  ${GRAY}Copying workspace config files...${NC}"
    for file in "${deploy_files[@]}"; do
        src="$SCRIPT_DIR/$file"
        dst="$WORKSPACE_PATH/$file"

        if [[ -f "$src" ]]; then
            if [[ -f "$dst" ]]; then
                echo -e "    ${GRAY}⏭  $file (already exists, skipped)${NC}"
            else
                cp "$src" "$dst"
                echo -e "    ${GREEN}✓  $file${NC}"
            fi
        else
            echo -e "    ${YELLOW}✗  $file (source not found)${NC}"
        fi
    done

    # Copy skill directories
    skill_dirs=("skills")
    echo -e "  ${GRAY}Copying skill directories...${NC}"
    for dir in "${skill_dirs[@]}"; do
        src="$SCRIPT_DIR/$dir"
        dst="$WORKSPACE_PATH/$dir"

        if [[ -d "$src" ]]; then
            mkdir -p "$dst"
            cp -r "$src/"* "$dst/" 2>/dev/null || true
            echo -e "    ${GREEN}✓  $dir/${NC}"
        else
            echo -e "    ${YELLOW}✗  $dir/ (source not found)${NC}"
        fi
    done

    # Create runtime directories
    runtime_dirs=(
        "$WORKSPACE_PATH/memory"
        "$WORKSPACE_PATH/memory/role_play"
        "$WORKSPACE_PATH/media/qqbot/audio"
        "$WORKSPACE_PATH/media/qqbot/images"
    )
    echo -e "  ${GRAY}Creating runtime directories...${NC}"
    for dir in "${runtime_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            echo -e "    ${GREEN}✓  $dir${NC}"
        fi
    done

    echo -e "  ${GREEN}Workspace deployed to: $WORKSPACE_PATH${NC}"
    echo ""
    echo -e "  ${YELLOW}⚠️  IMPORTANT — Paths to update in your workspace:${NC}"
    echo -e "  ${WHITE}  $WORKSPACE_PATH/skills/tts/tts_call.py${NC}"
    echo -e "  ${WHITE}  $WORKSPACE_PATH/skills/tts/SKILL.md${NC}"
    echo -e "  ${WHITE}  $WORKSPACE_PATH/skills/comfyui/comfyui_call.py${NC}"
    echo -e "  ${WHITE}  $WORKSPACE_PATH/skills/comfyui/SKILL.md${NC}"
    echo -e "  ${YELLOW}  Update PYTHON_PATH, WEBUI_DIR, COMFYUI_ROOT, LLAMA_MODEL_PATH etc.${NC}"
fi

# ============================================================================
# Step 4: Apply Config Patch
# ============================================================================
echo -e "${YELLOW}[4/5] Applying configuration...${NC}"

# Check if Gateway is running
GATEWAY_RUNNING=false
if openclaw gateway status &>/dev/null; then
    GATEWAY_RUNNING=true
    echo -e "  ${GREEN}Gateway is running.${NC}"
else
    echo -e "  ${YELLOW}Gateway is not running.${NC}"
fi

if $GATEWAY_RUNNING; then
    # Apply config patch via gateway
    patch_file="$WORKSPACE_PATH/config-patch.json"
    if [[ -f "$patch_file" ]]; then
        echo -e "  ${GRAY}Applying config-patch.json...${NC}"
        if openclaw gateway config.patch.apply --file "$patch_file" &>/dev/null; then
            echo -e "  ${GREEN}Config patch applied.${NC}"
        else
            echo -e "  ${YELLOW}⚠️  Could not auto-apply patch. Manual command:${NC}"
            echo -e "  ${WHITE}     openclaw gateway config.patch.apply${NC}"
        fi
    else
        echo -e "  ${YELLOW}config-patch.json not found at $patch_file${NC}"
    fi
else
    echo ""
    echo -e "  ${YELLOW}⚠️  Gateway not running. After starting the Gateway, apply the config patch:${NC}"
    echo -e "  ${WHITE}     1. Start Gateway:  openclaw gateway start${NC}"
    echo -e "  ${WHITE}     2. Apply patch:    openclaw gateway config.patch.apply${NC}"
fi

# ============================================================================
# Step 5: Install Gateway Daemon & Start
# ============================================================================
echo -e "${YELLOW}[5/5] Configuring Gateway daemon...${NC}"

if ! $SKIP_DAEMON; then
    # Install daemon (systemd on Linux, launchd on macOS)
    echo -e "  ${GRAY}Installing Gateway daemon (auto-start on login)...${NC}"
    if openclaw gateway install &>/dev/null; then
        echo -e "  ${GREEN}Gateway daemon installed.${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Could not install daemon automatically.${NC}"
        echo -e "  ${WHITE}     Manual: openclaw gateway install${NC}"
    fi

    # Start Gateway
    echo -e "  ${GRAY}Starting Gateway...${NC}"
    if openclaw gateway start &>/dev/null; then
        echo -e "  ${GREEN}Gateway started!${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Could not start Gateway.${NC}"
        echo -e "  ${WHITE}     Manual: openclaw gateway start${NC}"
    fi
else
    echo -e "  ${GRAY}Skipping daemon setup (--skip-daemon)${NC}"
fi

# ============================================================================
# Verification
# ============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ OpenClaw + AI Girlfriend Setup Complete!               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "  ${CYAN}Verification commands:${NC}"
echo -e "  ${WHITE}  openclaw --version        # Check CLI${NC}"
echo -e "  ${WHITE}  openclaw doctor           # Check configuration${NC}"
echo -e "  ${WHITE}  openclaw gateway status   # Check Gateway status${NC}"
echo ""

echo -e "  ${CYAN}Workspace: $WORKSPACE_PATH${NC}"
echo ""

# Final checklist
echo -e "  ${YELLOW}📋 Post-setup Checklist:${NC}"
echo -e "  ${WHITE}  ☐ 1. Update paths in skills/tts/tts_call.py${NC}"
echo -e "  ${WHITE}  ☐ 2. Update paths in skills/comfyui/comfyui_call.py${NC}"
echo -e "  ${WHITE}  ☐ 3. Verify llama-server is running: http://127.0.0.1:8080/health${NC}"
echo -e "  ${WHITE}  ☐ 4. Apply config-patch.json: openclaw gateway config.patch.apply${NC}"
echo -e "  ${WHITE}  ☐ 5. Configure QQ Bot channel (see README.md)${NC}"
echo -e "  ${WHITE}  ☐ 6. Test: send a message through your QQ Bot${NC}"
echo ""

# Print next steps
echo -e "  ${CYAN}🚀 Quick Start:${NC}"
echo -e "  ${GRAY}  # Start llama-server (in a separate terminal)${NC}"
echo -e "  ${WHITE}  bash llama-config/launch-llama.sh${NC}"
echo ""
echo -e "  ${GRAY}  # Check everything is running${NC}"
echo -e "  ${WHITE}  openclaw gateway status${NC}"
echo -e "  ${WHITE}  curl http://127.0.0.1:8080/health${NC}"
echo ""

echo -e "  ${GRAY}文档: https://docs.openclaw.ai/zh-CN${NC}"
echo -e "  ${GRAY}项目: https://github.com/momori777/openclaw_based_ai_girlfriend${NC}"
echo -e "  ${GRAY}模型: https://huggingface.co/TAOTAO777/ai-girlfriend-natsume${NC}"
echo ""
