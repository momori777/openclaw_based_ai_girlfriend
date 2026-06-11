#!/usr/bin/env bash
# download-models.sh
# AI Girlfriend 四季夏目 — One-click model download script (Linux / macOS)
#
# Downloads all 5 model files (~31.7 GB) from HuggingFace
# Requires: huggingface-cli (pip install huggingface_hub)
#
# Usage:
#   bash download-models.sh
#   bash download-models.sh /path/to/models
#
# First-time setup:
#   huggingface-cli login
#   or export HF_TOKEN="hf_xxx..."

set -euo pipefail

HF_REPO="TAOTAO777/ai-girlfriend-natsume"
BASE_DIR="${1:-.}"
BASE_DIR="$(cd "$BASE_DIR" && pwd)"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  AI Girlfriend — 四季夏目 · Model Downloader         ║"
echo "║  $HF_REPO                                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check huggingface-cli
if command -v huggingface-cli &>/dev/null; then
    HF_CMD="huggingface-cli"
elif command -v hf &>/dev/null; then
    HF_CMD="hf"
else
    echo "[ERROR] huggingface-cli not found. Install: pip install huggingface_hub"
    exit 1
fi

echo "Download tool: $HF_CMD"

# Check auth
echo -n "Checking auth... "
if $HF_CMD auth whoami &>/dev/null; then
    echo "OK"
else
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  Not logged in to HuggingFace!                       ║"
    echo "║                                                      ║"
    echo "║  Please login first:                                 ║"
    echo "║    huggingface-cli login                             ║"
    echo "║                                                      ║"
    echo "║  Or set environment variable:                        ║"
    echo "║    export HF_TOKEN=\"hf_xxx...\"                      ║"
    echo "╚══════════════════════════════════════════════════════╝"
    exit 1
fi

# Create target directories
mkdir -p "$BASE_DIR/llm"
mkdir -p "$BASE_DIR/comfyui-checkpoints"
mkdir -p "$BASE_DIR/gpt-sovits-weights/GPT_weights_v2Pro"
mkdir -p "$BASE_DIR/gpt-sovits-weights/SoVITS_weights_v2Pro"

echo ""
echo "Download directory: $BASE_DIR"
echo "Target: $HF_REPO"
echo "Total: ~31.7 GB — this may take 30-90 minutes depending on network"
echo ""

# Model file list (repo_path, local_filename, description)
declare -A MODELS=(
    ["llm/Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf"]="llm/Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf|LLM GGUF (16.11 GB)"
    ["comfyui-checkpoints/WAI-Nsfw-Illustrious-17.safetensors"]="comfyui-checkpoints/WAI-Nsfw-Illustrious-17.safetensors|ComfyUI Checkpoint — WAI (6.46 GB)"
    ["comfyui-checkpoints/miaomiaoHarem_v20.safetensors"]="comfyui-checkpoints/miaomiaoHarem_v20.safetensors|ComfyUI Checkpoint — Miaomiao (6.46 GB)"
    ["gpt-sovits-weights/GPT_weights_v2Pro/xxx-e30.ckpt"]="gpt-sovits-weights/GPT_weights_v2Pro/xxx-e30.ckpt|GPT-SoVITS ckpt (155 MB)"
    ["gpt-sovits-weights/SoVITS_weights_v2Pro/xxx_e20_s6240.pth"]="gpt-sovits-weights/SoVITS_weights_v2Pro/xxx_e20_s6240.pth|GPT-SoVITS pth (135 MB)"
)

TOTAL=${#MODELS[@]}
CURRENT=0
FAILED=()

for REPO_PATH in "${!MODELS[@]}"; do
    CURRENT=$((CURRENT + 1))
    IFS='|' read -r LOCAL_PATH DESC <<< "${MODELS[$REPO_PATH]}"
    FULL_LOCAL="$BASE_DIR/$LOCAL_PATH"
    
    # Check if already exists
    if [ -f "$FULL_LOCAL" ]; then
        echo "[$CURRENT/$TOTAL] $DESC — already exists, skipping"
        continue
    fi
    
    echo "[$CURRENT/$TOTAL] Downloading $DESC..."
    echo "         From: $REPO_PATH"
    echo "         To:   $FULL_LOCAL"
    
    START=$(date +%s)
    
    if $HF_CMD download "$HF_REPO" "$REPO_PATH" --local-dir "$BASE_DIR" --local-dir-use-symlinks False; then
        END=$(date +%s)
        ELAPSED=$((END - START))
        echo "         OK (${ELAPSED}s)"
    else
        END=$(date +%s)
        ELAPSED=$((END - START))
        echo "         FAILED (${ELAPSED}s)"
        FAILED+=("$DESC")
    fi
    echo ""
done

# Summary
echo "══════════════════════════════════════════════════════"
SUCCESS=$((TOTAL - ${#FAILED[@]}))
echo "Done: $SUCCESS / $TOTAL models downloaded"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo ""
    echo "Failed models (re-run to retry):"
    for f in "${FAILED[@]}"; do
        echo "  - $f"
    done
fi

if [ "$SUCCESS" -eq "$TOTAL" ]; then
    echo ""
    echo "All models downloaded to:"
    echo "  $BASE_DIR"
    echo ""
    echo "Next step: open models.yaml and update local_path fields"
    echo "to match your directory structure."
fi
