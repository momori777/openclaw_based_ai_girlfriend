#!/usr/bin/env bash
# setup-llama.sh
# AI Girlfriend — 四季夏目 · llama.cpp Auto Setup (Linux / macOS)
#
# Auto-detects GPU/CPU/RAM and generates optimized llama-server config.
# Optionally clones and builds llama.cpp from source.
#
# Usage:
#   bash setup-llama.sh
#   bash setup-llama.sh --model /path/to/model.gguf
#   bash setup-llama.sh --build  # also clone & compile llama.cpp
#
# Prerequisites:
#   1. Model downloaded via download-models.sh
#   2. Default model path: ./llm/ Qwen GGUF

set -euo pipefail

# ============================================================================
# Args
# ============================================================================
MODEL_PATH=""
CONTEXT_SIZE=120000
API_KEY="llama-key-change-me"
PORT=8080
BUILD_LLAMA=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL_PATH="$2"; shift 2 ;;
        --context) CONTEXT_SIZE="$2"; shift 2 ;;
        --api-key) API_KEY="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --build) BUILD_LLAMA=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; GRAY='\033[0;90m'; NC='\033[0m'

# ============================================================================
# Banner
# ============================================================================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  AI Girlfriend — 四季夏目 · llama.cpp Auto Setup           ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# System Detection
# ============================================================================
echo -e "${YELLOW}[1/5] Detecting hardware...${NC}"

# OS
OS_NAME="$(uname -s)"
OS_VER="$(uname -r)"
echo -e "  OS:       ${GRAY}${OS_NAME} ${OS_VER}${NC}"

# CPU
if command -v nproc &>/dev/null; then
    CPU_CORES=$(nproc)
elif [[ "$OS_NAME" == "Darwin" ]]; then
    CPU_CORES=$(sysctl -n hw.logicalcpu 2>/dev/null || echo 4)
else
    CPU_CORES=$(grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 4)
fi
echo -e "  CPU:      ${GRAY}${CPU_CORES} logical cores${NC}"

# RAM (GB)
if [[ "$OS_NAME" == "Darwin" ]]; then
    TOTAL_RAM_GB=$(echo "$(sysctl -n hw.memsize) / 1073741824" | bc 2>/dev/null || echo 8)
elif [[ "$OS_NAME" == "Linux" ]]; then
    TOTAL_RAM_GB=$(awk '/MemTotal/ {printf "%.1f", $2/1048576}' /proc/meminfo 2>/dev/null || echo 8)
else
    TOTAL_RAM_GB=8
fi
echo -e "  RAM:      ${GRAY}${TOTAL_RAM_GB} GB${NC}"

# GPU detection
VRAM_GB=0
GPU_NAME="No GPU detected"
GPU_DETECTED=false

# Try nvidia-smi
if command -v nvidia-smi &>/dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "")
    if [[ -n "$GPU_NAME" ]]; then
        VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ' || echo 0)
        VRAM_GB=$(echo "scale=1; $VRAM_MB / 1024" | bc 2>/dev/null || echo 0)
        GPU_DETECTED=true
        echo -e "  GPU:      ${GRAY}${GPU_NAME} (${VRAM_GB} GB VRAM)${NC}"
        # CUDA driver version
        CUDA_DRV=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || echo "")
        if [[ -n "$CUDA_DRV" ]]; then
            echo -e "  CUDA Drv: ${GRAY}${CUDA_DRV}${NC}"
        fi
    fi
fi

# Check nvcc (CUDA toolkit) version
CUDA_TK=""
CUDA_WARN=false
if command -v nvcc &>/dev/null; then
    CUDA_TK=$(nvcc --version 2>/dev/null | grep -oP 'release \K[0-9]+\.[0-9]+' || echo "")
    if [[ -n "$CUDA_TK" ]]; then
        echo -e "  CUDA TK:  ${GRAY}${CUDA_TK}${NC}"
        # CUDA 13.x has known issues with llama.cpp on Blackwell (RTX 50xx)
        CUDA_MAJOR=$(echo "$CUDA_TK" | cut -d. -f1)
        if [[ "$CUDA_MAJOR" -ge 13 ]]; then
            echo -e "  ${YELLOW}⚠️  CUDA 13.x may cause 'munmap_chunk(): invalid pointer' crashes!${NC}"
            echo -e "  ${YELLOW}   RTX 50xx (Blackwell) + CUDA 13.x = known llama.cpp memory bug.${NC}"
            echo -e "  ${YELLOW}   Solution: use pre-built CUDA 12.x llama.cpp binary instead:${NC}"
            echo -e "  ${YELLOW}   https://github.com/ggml-org/llama.cpp/releases${NC}"
            echo -e "  ${YELLOW}   Download: cudart-llama-bin-linux-cuda-12.4-x64.tar.gz${NC}"
            CUDA_WARN=true
        fi
    fi
elif command -v nvidia-smi &>/dev/null; then
    echo -e "  CUDA TK:  ${GRAY}[nvcc not found — using pre-built binaries is fine]${NC}"
fi

# Try AMD ROCm
if ! $GPU_DETECTED && command -v rocminfo &>/dev/null; then
    GPU_NAME=$(rocminfo 2>/dev/null | grep "Marketing Name" | head -1 | cut -d: -f2 | xargs || echo "AMD GPU")
    VRAM_GB=0
    GPU_DETECTED=true
    echo -e "  GPU:      ${GRAY}${GPU_NAME} (VRAM unknown — using CPU fallback)${NC}"
fi

# macOS Metal
if ! $GPU_DETECTED && [[ "$OS_NAME" == "Darwin" ]]; then
    GPU_NAME="Apple Silicon (Metal)"
    VRAM_GB=$(echo "scale=1; $TOTAL_RAM_GB * 0.75" | bc 2>/dev/null || echo 4)
    GPU_DETECTED=true
    echo -e "  GPU:      ${GRAY}${GPU_NAME} (~${VRAM_GB} GB unified memory)${NC}"
fi

if ! $GPU_DETECTED; then
    echo -e "  GPU:      ${YELLOW}[UNKNOWN — CPU-only mode]${NC}"
fi

# ============================================================================
# Model detection
# ============================================================================
echo -e "${YELLOW}[2/5] Detecting model...${NC}"

if [[ -z "$MODEL_PATH" ]]; then
    for p in \
        "./llm/Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf" \
        "./models/llm/Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf" \
        "llm/Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf"; do
        if [[ -f "$p" ]]; then
            MODEL_PATH="$(realpath "$p")"
            break
        fi
    done
fi

if [[ -z "$MODEL_PATH" ]] || [[ ! -f "$MODEL_PATH" ]]; then
    echo -e "  ${YELLOW}No model found. Search paths:${NC}"
    echo -e "    - ./llm/Qwen3.6-35B-A3B-APEX-I-Compact.gguf"
    echo -e "    - ./models/llm/"
    echo -e "    - ./llm/"
    echo ""
    echo -e "  ${YELLOW}Run download-models.sh first, or specify --model <path>.${NC}"
    exit 1
fi

MODEL_SIZE_GB=$(echo "scale=2; $(stat -f%z "$MODEL_PATH" 2>/dev/null || stat -c%s "$MODEL_PATH") / 1073741824" | bc 2>/dev/null || echo "?")
echo -e "  Model:    ${GRAY}${MODEL_PATH}${NC}"
echo -e "  Size:     ${GRAY}${MODEL_SIZE_GB} GB${NC}"

# ============================================================================
# Configuration Generation
# ============================================================================
echo -e "${YELLOW}[3/5] Generating optimal configuration...${NC}"

# Convert to numbers for comparison
VRAM_INT=$(echo "$VRAM_GB" | cut -d. -f1)
RAM_INT=$(echo "$TOTAL_RAM_GB" | cut -d. -f1)

if [[ "$VRAM_INT" -le 0 ]]; then
    # CPU-only
    NGL=0
    KV_CACHE_GB=$(echo "scale=1; if ($TOTAL_RAM_GB * 0.15 > 8) 8 else $TOTAL_RAM_GB * 0.15" | bc)
    GPU_MODE="CPU-ONLY"
    echo ""
    echo -e "  ${CYAN}VRAM Budget:${NC}"
    echo -e "    ${GRAY}No GPU — CPU-only mode${NC}"
    echo -e "    ${YELLOW}→ Only suitable for small models (<3B params).${NC}"
    echo -e "    ${YELLOW}→ Qwen 35B MoE requires 16+ GB RAM just to load.${NC}"

elif [[ "$VRAM_INT" -le 4 ]]; then
    NGL=$(echo "$VRAM_GB / 0.5" | bc | cut -d. -f1)
    KV_CACHE_GB=1
    GPU_MODE="HYBRID (minimal GPU offload)"
    echo ""
    echo -e "  ${CYAN}VRAM Budget (${VRAM_GB} GB):${NC}"
    echo -e "    ${GRAY}GPU offload: $NGL layers (~${VRAM_GB} GB)${NC}"
    echo -e "    ${GRAY}Rest on CPU + system RAM${NC}"

elif [[ "$VRAM_INT" -le 8 ]]; then
    NGL=41
    KV_CACHE_GB=1.5
    GPU_MODE="HYBRID (MoE experts on CPU)"
    echo ""
    echo -e "  ${CYAN}VRAM Budget (${VRAM_GB} GB):${NC}"
    echo -e "    ${GRAY}Model on GPU: ~$(echo "$VRAM_GB - 3" | bc) GB ($NGL layers)${NC}"
    echo -e "    ${GRAY}MoE experts: CPU offload${NC}"
    echo -e "    ${GRAY}KV Cache: ${KV_CACHE_GB} GB${NC}"
    echo -e "    ${GRAY}Free VRAM: ~$(echo "$VRAM_GB - 5.6" | bc) GB${NC}"

elif [[ "$VRAM_INT" -le 16 ]]; then
    NGL=99
    KV_CACHE_GB=3
    GPU_MODE="FULL GPU"
    echo ""
    echo -e "  ${CYAN}VRAM Budget (${VRAM_GB} GB):${NC}"
    echo -e "    ${GREEN}Model fits fully on GPU${NC}"
    echo -e "    ${GRAY}KV Cache: ${KV_CACHE_GB} GB${NC}"

else
    NGL=99
    KV_CACHE_GB=6
    GPU_MODE="FULL GPU BEAST MODE"
    echo ""
    echo -e "  ${CYAN}VRAM Budget (${VRAM_GB} GB):${NC}"
    echo -e "    ${GREEN}Model fits easily — generous KV cache${NC}"
fi

# Threads
if [[ "$CPU_CORES" -le 8 ]]; then
    THREADS=$((CPU_CORES - 2))
    BATCH_SIZE=2048
    UBATCH=1024
elif [[ "$CPU_CORES" -le 24 ]]; then
    THREADS=$((CPU_CORES > 16 ? 16 : CPU_CORES))
    BATCH_SIZE=4096
    UBATCH=2048
else
    THREADS=24
    BATCH_SIZE=8192
    UBATCH=4096
fi
[[ "$THREADS" -lt 2 ]] && THREADS=2

# Context
if (( $(echo "$KV_CACHE_GB <= 0" | bc -l) )); then
    REAL_CONTEXT=$((CONTEXT_SIZE < 32768 ? CONTEXT_SIZE : 32768))
else
    REAL_CONTEXT=$CONTEXT_SIZE
fi

# MoE
CPU_MOE=""
if (( $(echo "$VRAM_GB <= 8" | bc -l) )); then
    CPU_MOE="--cpu-moe --cpu-mask 0xFFFFFFFF"
fi

# No-mmap
NO_MMAP=""
if (( $(echo "$TOTAL_RAM_GB >= 32" | bc -l) )); then
    NO_MMAP="--no-mmap"
fi

echo -e "  Mode:     ${WHITE}${GPU_MODE}${NC}"
echo -e "  Threads:  ${GRAY}${THREADS}${NC}"
echo -e "  Context:  ${GRAY}${REAL_CONTEXT}${NC}"
echo -e "  Batch:    ${GRAY}${BATCH_SIZE}/${UBATCH}${NC}"

# ============================================================================
# Check llama.cpp
# ============================================================================
echo -e "${YELLOW}[4/5] Checking llama.cpp...${NC}"

LLAMA_EXE=""
if command -v llama-server &>/dev/null; then
    LLAMA_EXE="llama-server"
elif [[ -f "./llama.cpp/build/bin/llama-server" ]]; then
    LLAMA_EXE="$(realpath ./llama.cpp/build/bin/llama-server)"
elif [[ -f "../llama.cpp/build/bin/llama-server" ]]; then
    LLAMA_EXE="$(realpath ../llama.cpp/build/bin/llama-server)"
fi

if [[ -z "$LLAMA_EXE" ]]; then
    echo ""
    echo -e "  ${YELLOW}llama.cpp not found on PATH!${NC}"
    echo ""
    echo -e "  ${CYAN}Options:${NC}"
    echo -e "  ${WHITE}1. Let this script clone & build llama.cpp from source${NC}"
    echo -e "  ${WHITE}2. Download pre-built release from GitHub${NC}"
    echo -e "  ${WHITE}3. Specify path manually${NC}"
    echo ""

    if [[ "$BUILD_LLAMA" == true ]]; then
        CHOICE=1
    else
        read -rp "  Enter choice [1/2/3] (default: 2): " CHOICE
        CHOICE=${CHOICE:-2}
    fi

    case "$CHOICE" in
        1)
            BUILD_DIR="${HOME}/llama.cpp"
            echo ""
            echo -e "  ${YELLOW}Cloning llama.cpp to ${BUILD_DIR}...${NC}"

            if ! command -v cmake &>/dev/null; then
                echo -e "  ${RED}[ERROR] cmake not found!${NC}"
                echo -e "  ${YELLOW}Install: apt install cmake (Ubuntu) / brew install cmake (macOS)${NC}"
                exit 1
            fi

            if [[ ! -d "$BUILD_DIR" ]]; then
                git clone https://github.com/ggml-org/llama.cpp.git "$BUILD_DIR"
            fi

            echo -e "  ${YELLOW}Building with CUDA support...${NC}"
            mkdir -p "$BUILD_DIR/build"
            cd "$BUILD_DIR/build"

            BUILD_OK=false
            if command -v nvcc &>/dev/null; then
                cmake .. -DGGML_CUDA=ON && BUILD_OK=true
            elif command -v rocminfo &>/dev/null; then
                cmake .. -DGGML_HIPBLAS=ON && BUILD_OK=true
            elif [[ "$OS_NAME" == "Darwin" ]]; then
                cmake .. -DGGML_METAL=ON && BUILD_OK=true
            fi

            if ! $BUILD_OK; then
                echo -e "  ${YELLOW}No GPU SDK found, falling back to CPU-only...${NC}"
                cmake ..
            fi

            cmake --build . --config Release -j "$THREADS"

            if [[ $? -ne 0 ]]; then
                echo -e "  ${RED}[ERROR] Build failed.${NC}"
                echo -e "  ${YELLOW}Try pre-built release: https://github.com/ggml-org/llama.cpp/releases${NC}"
                exit 1
            fi

            LLAMA_EXE="$BUILD_DIR/build/bin/llama-server"
            echo -e "  ${GREEN}Build complete: ${LLAMA_EXE}${NC}"
            ;;

        2)
            echo ""
            echo -e "  ${CYAN}Download pre-built from:${NC}"
            echo -e "  ${WHITE}https://github.com/ggml-org/llama.cpp/releases${NC}"
            echo -e "  ${GRAY}Linux:   cudart-llama-bin-linux-cuda-12.4-x64.tar.gz (NVIDIA)${NC}"
            echo -e "  ${GRAY}Linux:   llama-bXXXX-bin-linux-x64.tar.gz (CPU-only)${NC}"
            echo -e "  ${GRAY}macOS:   llama-bXXXX-bin-macos-arm64.tar.gz (Apple Silicon)${NC}"
            echo -e "  ${GRAY}Extract and add llama-server to PATH.${NC}"
            echo ""
            read -rp "  Enter llama-server path (or Enter to skip): " manual_path
            if [[ -n "$manual_path" ]] && [[ -x "$manual_path" ]]; then
                LLAMA_EXE="$manual_path"
            fi
            ;;

        3)
            read -rp "  Enter full path to llama-server: " manual_path
            if [[ -n "$manual_path" ]] && [[ -x "$manual_path" ]]; then
                LLAMA_EXE="$manual_path"
            else
                echo -e "  ${RED}Invalid path.${NC}"
                exit 1
            fi
            ;;
    esac
fi

if [[ -z "$LLAMA_EXE" ]]; then
    echo ""
    echo -e "  ${YELLOW}No llama.cpp found. Re-run after installing, or use --build flag.${NC}"
    exit 0
fi

echo -e "  llama-server: ${GREEN}${LLAMA_EXE}${NC}"

# ============================================================================
# Generate output files
# ============================================================================
echo -e "${YELLOW}[5/5] Generating configuration files...${NC}"

OUTPUT_DIR="./llama-config"
mkdir -p "$OUTPUT_DIR"

# Build args array
LLAMA_ARGS=(
    '-m' "\"${MODEL_PATH}\""
    '-c' "${REAL_CONTEXT}"
    '--flash-attn' 'on'
    '-ngl' "${NGL}"
    '--batch-size' "${BATCH_SIZE}"
    '--ubatch-size' "${UBATCH}"
    '--threads' "${THREADS}"
    '--api-key' "\"${API_KEY}\""
    '-rea' 'off'
    '--jinja'
    '--cache-ram' '2048'
    '--parallel' '1'
    '--kv-unified'
)

# Q4 cache offload
LLAMA_ARGS+=('-ctk' 'q8_0' '-ctv' 'q8_0')

# MoE
if [[ -n "$CPU_MOE" ]]; then
    IFS=' ' read -ra MOE_ARGS <<< "$CPU_MOE"
    LLAMA_ARGS+=("${MOE_ARGS[@]}")
fi

# no-mmap
if [[ -n "$NO_MMAP" ]]; then
    LLAMA_ARGS+=("$NO_MMAP")
fi

# ── Hardware report ──
cat > "$OUTPUT_DIR/hardware-report.md" << EOF
# llama.cpp Auto-Generated Configuration
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# Machine: $(hostname)

## Hardware Detection
- OS: ${OS_NAME} ${OS_VER}
- CPU: ${CPU_CORES} logical cores
- RAM: ${TOTAL_RAM_GB} GB
- GPU: ${GPU_NAME} (${VRAM_GB} GB VRAM)
- Mode: ${GPU_MODE}

## Model
- Path: ${MODEL_PATH}
- Size: ${MODEL_SIZE_GB} GB

## Generated Parameters
| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| -ngl       | ${NGL}   | Based on ${VRAM_GB} GB VRAM |
| --threads  | ${THREADS} | ${CPU_CORES} logical cores |
| --batch-size | ${BATCH_SIZE} | Balanced for CPU + GPU |
| --ubatch-size | ${UBATCH} | Half batch-size |
| -c         | ${REAL_CONTEXT} | Context window |
EOF
echo -e "  Hardware report: ${GRAY}${OUTPUT_DIR}/hardware-report.md${NC}"

# ── Launch script ──
cat > "$OUTPUT_DIR/launch-llama.sh" << 'SHELLHEAD'
#!/usr/bin/env bash
# launch-llama.sh — Auto-generated by setup-llama.sh
# Start llama-server with optimized parameters
set -euo pipefail
SHELLHEAD

cat >> "$OUTPUT_DIR/launch-llama.sh" << EOF
# Generated for: ${GPU_NAME}, ${VRAM_GB} GB VRAM, ${CPU_CORES} cores, ${TOTAL_RAM_GB} GB RAM
# Mode: ${GPU_MODE}
# $(date '+%Y-%m-%d %H:%M:%S')

LLAMA_EXE="${LLAMA_EXE}"

echo "============================================"
echo " AI Girlfriend — llama-server"
echo " GPU: ${GPU_NAME} | VRAM: ${VRAM_GB} GB"
echo " Mode: ${GPU_MODE}"
echo " Port: ${PORT}"
echo "============================================"
echo ""

ARGS=(
EOF

for arg in "${LLAMA_ARGS[@]}"; do
    echo "    ${arg}" >> "$OUTPUT_DIR/launch-llama.sh"
done

cat >> "$OUTPUT_DIR/launch-llama.sh" << 'SHELLTAIL'
)

echo "Starting llama-server..."
"$LLAMA_EXE" "${ARGS[@]}" &
LLAMA_PID=$!
echo "PID: $LLAMA_PID"
echo ""

# Wait for health endpoint
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8080/health > /dev/null 2>&1; then
        echo "Server ready!"
        echo "Endpoint: http://127.0.0.1:8080"
        break
    fi
    sleep 1
    if [[ "$i" -eq 30 ]]; then
        echo "Timeout — server may still be loading. Check http://127.0.0.1:8080/health"
    fi
done

echo "Server running. Press Ctrl+C to stop."
trap "kill $LLAMA_PID 2>/dev/null; exit 0" INT TERM
wait $LLAMA_PID
SHELLTAIL

chmod +x "$OUTPUT_DIR/launch-llama.sh"
echo -e "  Launch script:  ${GREEN}${OUTPUT_DIR}/launch-llama.sh${NC}"

# ── Systemd service (Linux only) ──
if [[ "$OS_NAME" == "Linux" ]]; then
    cat > "$OUTPUT_DIR/llama-server.service" << EOF
# Place in: ~/.config/systemd/user/llama-server.service
# Enable: systemctl --user enable --now llama-server.service
[Unit]
Description=llama.cpp Server — AI Girlfriend
After=network.target

[Service]
Type=simple
ExecStart=${LLAMA_EXE} \\
$(printf '    %s \\\n' "${LLAMA_ARGS[@]}")
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF
    echo -e "  Systemd unit:   ${GRAY}${OUTPUT_DIR}/llama-server.service${NC}"

    cat > "$OUTPUT_DIR/llama-watchdog.sh" << 'WATCHDOGHEAD'
#!/usr/bin/env bash
# llama-watchdog.sh — Health check for cron
WATCHDOGHEAD
    cat >> "$OUTPUT_DIR/llama-watchdog.sh" << WATCHDOGEOF

LOG_FILE="${OUTPUT_DIR}/watchdog.log"
mkdir -p "\$(dirname "\$LOG_FILE")"

log() { echo "[\$(date '+%Y-%m-%d %H:%M:%S')] \$1" >> "\$LOG_FILE"; }

log "=== watchdog check ==="

if curl -sf http://127.0.0.1:${PORT}/health > /dev/null 2>&1; then
    log "healthy"
    exit 0
fi

log "llama-server down — restarting..."
systemctl --user restart llama-server.service 2>/dev/null || \
    nohup bash "${OUTPUT_DIR}/launch-llama.sh" > /dev/null 2>&1 &
log "restart triggered"
WATCHDOGEOF
    chmod +x "$OUTPUT_DIR/llama-watchdog.sh"
    echo -e "  Watchdog:       ${GRAY}${OUTPUT_DIR}/llama-watchdog.sh${NC}"

    # Cron hint
    cat > "$OUTPUT_DIR/setup-cron.txt" << EOF
# Add to crontab (crontab -e):
# */10 * * * * ${OUTPUT_DIR}/llama-watchdog.sh
EOF
    echo -e "  Cron config:    ${GRAY}${OUTPUT_DIR}/setup-cron.txt${NC}"
fi

# ── macOS launchd plist ──
if [[ "$OS_NAME" == "Darwin" ]]; then
    PLIST_PATH="${OUTPUT_DIR}/com.ai-girlfriend.llama-server.plist"
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai-girlfriend.llama-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>${LLAMA_EXE}</string>
$(printf '        <string>%s</string>\n' "${LLAMA_ARGS[@]}")
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${OUTPUT_DIR}/llama-server.log</string>
    <key>StandardErrorPath</key>
    <string>${OUTPUT_DIR}/llama-server.err</string>
</dict>
</plist>
EOF
    echo -e "  Launchd plist:  ${GRAY}${PLIST_PATH}${NC}"
    echo -e "  ${GRAY}Install: cp ${PLIST_PATH} ~/Library/LaunchAgents/${NC}"
    echo -e "  ${GRAY}Start:   launchctl load ~/Library/LaunchAgents/com.ai-girlfriend.llama-server.plist${NC}"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete!                                           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${WHITE}Hardware:    ${GPU_NAME} — ${VRAM_GB} GB VRAM${NC}"
echo -e "  ${WHITE}CPU:         ${CPU_CORES} cores | RAM: ${TOTAL_RAM_GB} GB${NC}"
echo -e "  ${WHITE}Mode:        ${GPU_MODE}${NC}"
echo -e "  ${WHITE}Model:       ${MODEL_SIZE_GB} GB GGUF${NC}"
echo ""
echo -e "  ${CYAN}Generated files in: ${OUTPUT_DIR}/${NC}"
echo -e "    ${WHITE}launch-llama.sh       — Start llama-server${NC}"
if [[ "$OS_NAME" == "Linux" ]]; then
    echo -e "    ${WHITE}llama-watchdog.sh     — Health check (cron)${NC}"
    echo -e "    ${WHITE}llama-server.service  — systemd unit${NC}"
elif [[ "$OS_NAME" == "Darwin" ]]; then
    echo -e "    ${WHITE}*.plist               — launchd service${NC}"
fi
echo -e "    ${WHITE}hardware-report.md    — Your machine specs${NC}"
echo ""
echo -e "  ${CYAN}Quick Start:${NC}"
echo -e "    ${WHITE}1. bash ${OUTPUT_DIR}/launch-llama.sh${NC}"
echo -e "    ${WHITE}2. Wait for http://127.0.0.1:${PORT}/health to return 200${NC}"
echo -e "    ${WHITE}3. Configure OpenClaw to use http://127.0.0.1:${PORT}/v1${NC}"
echo ""
