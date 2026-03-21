#!/bin/bash
# ==============================================================================
# vLLM Startup Script — starts all vLLM model instances + GLM-OCR SDK server
# ==============================================================================
#
# Uses the official `vllm serve` CLI.
#
# ── PREREQUISITE: Custom vLLM build for gpt-oss-20b ──────────────────────────
# gpt-oss-20b requires OpenAI's custom vLLM wheel, NOT the standard build:
#
#   uv pip install --pre "vllm==0.10.1+gptoss" \
#       --extra-index-url https://wheels.vllm.ai/gpt-oss/ \
#       --extra-index-url https://download.pytorch.org/whl/nightly/cu128 \
#       --index-strategy unsafe-best-match
#
# Or Docker:  docker pull vllm/vllm-openai:gptoss
# Docs: https://docs.vllm.ai/projects/recipes/en/latest/OpenAI/GPT-OSS.html
#
# ── MXFP4 quantization (built into gpt-oss-20b) ──────────────────────────────
# gpt-oss-20b ships with MoE weights pre-quantized to MXFP4 (~4.25 bits/weight).
# Attention layers remain in BF16. Real VRAM footprint: ~16 GB (not ~42 GB BF16).
# On A6000 Ada (SM 8.9), vLLM automatically falls back to Marlin MXFP4 via Triton.
# Required env vars for Ada are set below in the "Ada Lovelace" section.
#
# ── VRAM budget on A6000 48GB ─────────────────────────────────────────────────
# Instance             Model                        Weights  KV@32K  GPU util
# ─────────────────────────────────────────────────────────────────────────────
# Main LLM (port 8000) openai/gpt-oss-20b MXFP4    ~16 GB   ~8 GB   0.72
# VLM      (port 8001) Qwen3.5-9B AWQ 4-bit         ~6 GB   ~3 GB   0.18
# GLM-OCR  (port 8080) THUDM/glm-ocr BF16           ~2 GB   ~0 GB   0.05
# ─────────────────────────────────────────────────────────────────────────────
# Total: 0.72+0.18+0.05 = 0.95 × 48 GB = 45.6 GB + ~1.5 GB OS = ~47.1 GB ✓
#
# gpt-oss-20b at 128K context: ~8 GB KV per session → 18.6 GB KV pool → ~2 concurrent.
#
# ── GLM-OCR two-tier deployment ───────────────────────────────────────────────
# GLM-OCR requires two processes:
#   1. vLLM (port 8080): serves the raw GLM-OCR 0.9B model
#   2. glmocr SDK server (port 5002): handles PP-DocLayout-V3 layout detection
#      and orchestrates calls to vLLM. This is what glm_ocr.py calls.
#
# Both are started by this script and stopped by stop_vllm.sh.
#
# ── VLM model (Qwen3.5-9B) ───────────────────────────────────────────────────
# Qwen3.5-9B is a full vision+text+reasoning model (image, video, text inputs).
# --reasoning-parser qwen3: vLLM strips <think>...</think> server-side.
# --quantization awq: added automatically for AWQ model variants.
#
# ── gpt-oss-20b serving notes ────────────────────────────────────────────────
# --trust-remote-code: required for custom MoE architecture.
# --no-enable-prefix-caching: recommended by official docs for all GPU families.
#   Set VLLM_MAIN_APC=1 in .env to enable APC (cross-user static prompt caching).
#
# --served-model-name: registers the model under MAIN_MODEL (e.g.
#   "gpt-oss:20b-50k-8k") so invoke_llm() calls succeed without Python changes.
#
# Usage:
#   bash scripts/start_vllm.sh           # Start all instances
#   bash scripts/start_vllm.sh --logs    # Tail logs after starting
#   bash scripts/start_vllm.sh --main    # Start main LLM only
#   bash scripts/start_vllm.sh --vlm     # Start VLM only
#   bash scripts/start_vllm.sh --glm     # Start GLM-OCR only (vLLM + SDK server)
#
# Instances managed here:
#   Instance 1: Main LLM        — port 8000  (VLLM_MAIN_URL)
#   Instance 2: VLM             — port 8001  (VLLM_VLM_URL)
#   Instance 3: GLM-OCR vLLM   — port 8080  (raw model backend)
#   Instance 4: GLM-OCR SDK    — port 5002  (layout detection + orchestration)
#
# ==============================================================================

set -euo pipefail

# ── Load .env if present ──────────────────────────────────────────────────────
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

# ── Ada Lovelace (A6000, SM 8.9) required env vars ───────────────────────────
# Required for Triton MXFP4 emulation on Ada Lovelace (no native MXFP4 tensor cores).
# These are no-ops on Hopper (H100) or Blackwell (B200) — safe to leave in.
# Docs: https://docs.vllm.ai/projects/recipes/en/latest/OpenAI/GPT-OSS.html
export VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-TRITON_ATTN_VLLM_V1}"
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.9}"
# Uncomment if multiple CUDA versions are installed (gptoss build requires cu128):
# export CUDA_HOME=/usr/local/cuda-12.8

# ── Configuration ─────────────────────────────────────────────────────────────
# Main LLM: official OpenAI gpt-oss model. Requires OpenAI's custom vLLM build.
# Override in .env:  VLLM_MAIN_MODEL=openai/gpt-oss-120b  for the 120B variant.
VLLM_MAIN_MODEL="${VLLM_MAIN_MODEL:-openai/gpt-oss-20b}"

# The name registered in the vLLM API — must match MAIN_MODEL in .env so that
# invoke_llm() requests succeed without any Python changes.
MAIN_MODEL="${MAIN_MODEL:-gpt-oss:20b}"

# VLM: Qwen3.5-9B AWQ 4-bit — vision+text+reasoning at ~6 GB VRAM.
# Set VLLM_VLM_MODEL=Qwen/Qwen3.5-9B in .env for BF16 (better quality, still fits).
VLLM_VLM_MODEL="${VLLM_VLM_MODEL:-cyankiwi/Qwen3.5-9B-AWQ-4bit}"

# GLM-OCR: 0.9B model for structured document OCR (tables, formulas, layout).
# HuggingFace: THUDM/glm-ocr  (zai-org/GLM-OCR on GitHub)
VLLM_GLM_OCR_MODEL="${VLLM_GLM_OCR_MODEL:-THUDM/glm-ocr}"

VLLM_DRAFT_MODEL="${VLLM_DRAFT_MODEL:-}"

# gpt-oss-20b MXFP4: 0.57 × 48 GB = 27.36 GB reserved.
# Weights ~16 GB + ~11.36 GB KV pool.
# KV estimate: 32 layers × 2 × 8 GQA heads × 128 head_dim × 2 bytes = 128 KB/token.
# Theoretical max: 11.36 GB / 128 KB = ~90K tokens.
# max-model-len 65536 (64K): leaves ~3.4 GB buffer against ~90K theoretical ceiling,
# since gpt-oss-20b layer/head counts are estimated (architecture not fully published).
# Total model VRAM at these settings: 27.36 + 8.64 + 2.4 = ~38.4 GB ≈ 40 GB cap.
# For --main-only: raise VLLM_GPU_MEMORY_UTILIZATION to 0.85 and VLLM_MAX_MODEL_LEN to 131072.
VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.57}"
VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-65536}"

# Qwen3.5-9B AWQ: 0.18 × 48 GB = 8.6 GB reserved.
# Weights ~6 GB + ~2.6 GB KV — sufficient for image tasks at 32K context.
# For --vlm-only + BF16: raise to 0.85 and set VLLM_VLM_MAX_MODEL_LEN=262144.
VLLM_VLM_GPU_MEMORY_UTILIZATION="${VLLM_VLM_GPU_MEMORY_UTILIZATION:-0.18}"
VLLM_VLM_MAX_MODEL_LEN="${VLLM_VLM_MAX_MODEL_LEN:-32768}"

# GLM-OCR: 0.05 × 48 GB = 2.4 GB reserved — ample for a 0.9B BF16 model (~1.8 GB).
GLM_OCR_VLLM_PORT="${GLM_OCR_VLLM_PORT:-8080}"
GLM_OCR_SDK_PORT="${GLM_OCR_SDK_PORT:-5002}"
VLLM_GLM_OCR_GPU_MEMORY_UTILIZATION="${VLLM_GLM_OCR_GPU_MEMORY_UTILIZATION:-0.05}"

CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

LOG_DIR="logs/vllm"
mkdir -p "$LOG_DIR"

# ── Helper ────────────────────────────────────────────────────────────────────
start_instance() {
    local name="$1"
    local port="$2"
    local model="$3"
    local served_name="$4"
    local gpu_mem="$5"
    local max_len="$6"
    local extra_args="${7:-}"
    local logfile="$LOG_DIR/${name}.log"

    echo "Starting vLLM instance: $name"
    echo "  Weights model  : $model"
    echo "  Served as      : $served_name"
    echo "  Port           : $port"
    echo "  GPU util       : $gpu_mem"
    echo "  Max context    : $max_len tokens"
    echo "  Log            : $logfile"

    # shellcheck disable=SC2086
    CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
    vllm serve "$model" \
        --port "$port" \
        --host 0.0.0.0 \
        --served-model-name "$served_name" \
        --gpu-memory-utilization "$gpu_mem" \
        --max-model-len "$max_len" \
        --tensor-parallel-size 1 \
        --enable-chunked-prefill \
        $extra_args \
        > "$logfile" 2>&1 &

    echo "  PID            : $!"
    echo "$!" > "$LOG_DIR/${name}.pid"
    echo ""
}

# ── Parse arguments ───────────────────────────────────────────────────────────
START_MAIN=true
START_VLM=true
START_GLM=true
TAIL_LOGS=false

for arg in "$@"; do
    case "$arg" in
        --main) START_VLM=false; START_GLM=false ;;
        --vlm)  START_MAIN=false; START_GLM=false ;;
        --glm)  START_MAIN=false; START_VLM=false ;;
        --logs) TAIL_LOGS=true ;;
    esac
done

# ── Instance 1: Main LLM (port 8000) ─────────────────────────────────────────
if [ "$START_MAIN" = true ]; then
    # --trust-remote-code: required for gpt-oss-20b custom MoE architecture.
    # --no-enable-prefix-caching: recommended by official docs for all GPU families.
    #   Set VLLM_MAIN_APC=1 in .env to enable APC (static prompt prefix caching).
    if [ "${VLLM_MAIN_APC:-}" = "1" ]; then
        MAIN_EXTRA_ARGS="--trust-remote-code --enable-prefix-caching"
        echo "[Main LLM] APC enabled (VLLM_MAIN_APC=1)"
    else
        MAIN_EXTRA_ARGS="--trust-remote-code --no-enable-prefix-caching"
    fi

    # Speculative decoding via EAGLE3 — enabled when VLLM_DRAFT_MODEL is non-empty.
    # Official EAGLE3 draft for gpt-oss-120b: nvidia/gpt-oss-120b-Eagle3-v2
    # No official draft model confirmed for gpt-oss-20b yet; check HuggingFace.
    if [ -n "$VLLM_DRAFT_MODEL" ]; then
        MAIN_EXTRA_ARGS="$MAIN_EXTRA_ARGS --speculative-model ${VLLM_DRAFT_MODEL} --num-speculative-tokens 3"
        echo "[Main LLM] Speculative decoding enabled — draft model: ${VLLM_DRAFT_MODEL}"
    fi

    start_instance \
        "main_llm" \
        "8000" \
        "$VLLM_MAIN_MODEL" \
        "$MAIN_MODEL" \
        "$VLLM_GPU_MEMORY_UTILIZATION" \
        "$VLLM_MAX_MODEL_LEN" \
        "$MAIN_EXTRA_ARGS"
fi

# ── Instance 2: VLM (port 8001) ──────────────────────────────────────────────
# Qwen3.5-9B — vision+text+reasoning for slide/PDF parsing and visual QnA.
# --reasoning-parser qwen3: strips <think>...</think> server-side.
# --quantization awq: auto-added for AWQ model variants.
if [ "$START_VLM" = true ]; then
    VLM_EXTRA_ARGS="--enable-prefix-caching --reasoning-parser qwen3"

    if echo "$VLLM_VLM_MODEL" | grep -qi "awq"; then
        VLM_EXTRA_ARGS="$VLM_EXTRA_ARGS --quantization awq"
        echo "[VLM] AWQ quantization detected — adding --quantization awq"
    fi

    start_instance \
        "vlm" \
        "8001" \
        "$VLLM_VLM_MODEL" \
        "$VLLM_VLM_MODEL" \
        "$VLLM_VLM_GPU_MEMORY_UTILIZATION" \
        "$VLLM_VLM_MAX_MODEL_LEN" \
        "$VLM_EXTRA_ARGS"
fi

# ── Instance 3: GLM-OCR vLLM (port 8080) + SDK server (port 5002) ────────────
# GLM-OCR uses a two-tier deployment:
#   - vLLM (port 8080): serves the raw GLM-OCR 0.9B model
#   - glmocr SDK server (port 5002): runs PP-DocLayout-V3 layout detection,
#     then calls vLLM at 8080. This is the endpoint glm_ocr.py calls.
if [ "$START_GLM" = true ]; then
    # Step 1: Start the GLM-OCR vLLM backend (port 8080)
    start_instance \
        "glm_ocr" \
        "$GLM_OCR_VLLM_PORT" \
        "$VLLM_GLM_OCR_MODEL" \
        "$VLLM_GLM_OCR_MODEL" \
        "$VLLM_GLM_OCR_GPU_MEMORY_UTILIZATION" \
        "8192" \
        "--enable-prefix-caching"

    # Step 2: Start the glmocr SDK server (port 5002)
    # This process handles layout detection and orchestrates calls to vLLM.
    # glm_ocr.py calls this server, not vLLM directly.
    GLM_SDK_LOG="$LOG_DIR/glm_ocr_sdk.log"
    echo "Starting glmocr SDK server (port $GLM_OCR_SDK_PORT)..."
    python -m glmocr.server --port "$GLM_OCR_SDK_PORT" \
        > "$GLM_SDK_LOG" 2>&1 &
    GLM_SDK_PID=$!
    echo "  PID            : $GLM_SDK_PID"
    echo "$GLM_SDK_PID" > "$LOG_DIR/glm_ocr_sdk.pid"
    echo "  Log            : $GLM_SDK_LOG"
    echo ""
fi

# ── Wait for readiness ────────────────────────────────────────────────────────
echo "Waiting for vLLM instances to initialise (model load takes 30-120s for large models)..."
sleep 10

check_ready() {
    local name="$1"
    local port="$2"
    if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
        echo "  [OK]   $name (port $port) is ready"
    else
        echo "  [WAIT] $name (port $port) still loading — tail: $LOG_DIR/${name}.log"
    fi
}

[ "$START_MAIN" = true ] && check_ready "main_llm" "8000"
[ "$START_VLM"  = true ] && check_ready "vlm"      "8001"
[ "$START_GLM"  = true ] && check_ready "glm_ocr"  "$GLM_OCR_VLLM_PORT"

echo ""
echo "vLLM startup complete."
[ "$START_MAIN" = true ] && echo "  Main LLM       : http://localhost:8000/v1  (model: ${MAIN_MODEL}, MXFP4 via Triton)"
[ "$START_VLM"  = true ] && echo "  VLM            : http://localhost:8001/v1  (model: ${VLLM_VLM_MODEL})"
[ "$START_GLM"  = true ] && echo "  GLM-OCR vLLM   : http://localhost:${GLM_OCR_VLLM_PORT}/v1  (model: ${VLLM_GLM_OCR_MODEL})"
[ "$START_GLM"  = true ] && echo "  GLM-OCR SDK    : http://localhost:${GLM_OCR_SDK_PORT}/glmocr/parse  (layout + orchestration)"
echo "  Logs           : $LOG_DIR/"
echo ""
echo "To stop:  bash scripts/stop_vllm.sh"
echo "To watch: tail -f $LOG_DIR/main_llm.log"

# ── Optional: tail logs ───────────────────────────────────────────────────────
if [ "$TAIL_LOGS" = true ]; then
    LOG_FILES=()
    [ "$START_MAIN" = true ] && LOG_FILES+=("$LOG_DIR/main_llm.log")
    [ "$START_VLM"  = true ] && LOG_FILES+=("$LOG_DIR/vlm.log")
    [ "$START_GLM"  = true ] && LOG_FILES+=("$LOG_DIR/glm_ocr.log")
    tail -f "${LOG_FILES[@]}"
fi
