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
# ── VRAM budget on A6000 48GB — VLLM_MODE=gpt-oss (default) ──────────────────
# Instance             Model                        Weights  KV pool GPU util
# ─────────────────────────────────────────────────────────────────────────────
# Main LLM (port 8000) openai/gpt-oss-20b MXFP4    ~16 GB  ~11 GB   0.57
# VLM      (port 8001) Qwen3.5-9B AWQ 4-bit         ~6 GB   ~3 GB   0.18
# GLM-OCR  (port 8080) THUDM/glm-ocr BF16           ~2 GB   ~0 GB   0.05
# ─────────────────────────────────────────────────────────────────────────────
# Total: 0.57+0.18+0.05 = 0.80 × 48 GB = 38.4 GB + ~1.5 GB OS = ~40 GB ✓
# gpt-oss-20b KV pool: ~11 GB / 128 KB/token → ~90K theoretical → 64K safe (65536).
#
# ── VRAM budget on A6000 48GB — VLLM_MODE=qwen-unified ───────────────────────
# Instance             Model                        Weights  KV pool GPU util
# ─────────────────────────────────────────────────────────────────────────────
# Unified  (port 8000) Qwen3.5-9B BF16             ~18 GB  ~18 GB   0.75
# GLM-OCR  (port 8080) THUDM/glm-ocr BF16           ~2 GB   ~0 GB   0.05
# ─────────────────────────────────────────────────────────────────────────────
# Total: 0.75+0.05 = 0.80 × 48 GB = 38.4 GB + ~1.5 GB OS = ~40 GB ✓
# Qwen3.5-9B KV pool: ~18 GB → supports 128K context (131072).
# Single instance serves both text (LLM) and image (VLM) requests on port 8000.
# Python: set VLLM_MODE=qwen-unified and MAIN_MODEL=Qwen/Qwen3.5-9B in .env.
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
#   bash scripts/start_vllm.sh           # Start all instances for current VLLM_MODE
#   bash scripts/start_vllm.sh --logs    # Tail logs after starting
#   bash scripts/start_vllm.sh --main    # Start main LLM only (or unified in qwen-unified mode)
#   bash scripts/start_vllm.sh --vlm     # Start VLM only (no-op in qwen-unified mode)
#   bash scripts/start_vllm.sh --glm     # Start GLM-OCR only (vLLM + SDK server)
#
# Mode switching (set in .env):
#   VLLM_MODE=gpt-oss        (default) gpt-oss-20b on 8000 + Qwen AWQ VLM on 8001
#   VLLM_MODE=qwen-unified   Single Qwen3.5-9B BF16 on 8000 — both LLM and VLM
#   Also set MAIN_MODEL=Qwen/Qwen3.5-9B in .env when using qwen-unified mode.
#
# Instances managed here (gpt-oss mode):
#   Instance 1: Main LLM        — port 8000  (VLLM_MAIN_URL)
#   Instance 2: VLM             — port 8001  (VLLM_VLM_URL)
#   Instance 3: GLM-OCR vLLM   — port 8080  (raw model backend)
#   Instance 4: GLM-OCR SDK    — port 5002  (layout detection + orchestration)
#
# Instances managed here (qwen-unified mode):
#   Instance 1: Unified LLM+VLM — port 8000  (VLLM_MAIN_URL, also handles VLM requests)
#   Instance 2: GLM-OCR vLLM    — port 8080  (raw model backend)
#   Instance 3: GLM-OCR SDK     — port 5002  (layout detection + orchestration)
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
# Mode: gpt-oss (default) or qwen-unified.
# In qwen-unified mode, a single Qwen3.5-9B BF16 instance serves port 8000 for
# both text (LLM) and image (VLM) requests. Port 8001 is not used.
VLLM_MODE="${VLLM_MODE:-gpt-oss}"

# Unified mode model — Qwen3.5-9B BF16 (~18 GB VRAM, 128K context, vision+text+reasoning).
# In gpt-oss mode this value is unused by the script.
VLLM_UNIFIED_MODEL="${VLLM_UNIFIED_MODEL:-Qwen/Qwen3.5-9B}"

# gpu-util for unified Qwen: 0.75 × 48 GB = 36 GB → ~18 GB weights + ~18 GB KV pool → 128K context.
VLLM_UNIFIED_GPU_MEMORY_UTILIZATION="${VLLM_UNIFIED_GPU_MEMORY_UTILIZATION:-0.75}"
VLLM_UNIFIED_MAX_MODEL_LEN="${VLLM_UNIFIED_MAX_MODEL_LEN:-131072}"

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
    if [ "$VLLM_MODE" = "qwen-unified" ]; then
        # ── qwen-unified mode: single Qwen3.5-9B BF16 serves both LLM + VLM ────
        # --reasoning-parser qwen3: strips <think>...</think> server-side.
        # --enable-prefix-caching: safe for Qwen (no known issues unlike gpt-oss-20b).
        # No --trust-remote-code needed for standard HuggingFace Qwen models.
        echo "[qwen-unified] Starting Qwen3.5-9B BF16 as unified LLM+VLM on port 8000"
        echo "[qwen-unified] Context: ${VLLM_UNIFIED_MAX_MODEL_LEN} tokens  |  GPU util: ${VLLM_UNIFIED_GPU_MEMORY_UTILIZATION}"
        echo "[qwen-unified] Python: set VLLM_MODE=qwen-unified and MAIN_MODEL=Qwen/Qwen3.5-9B in .env"

        UNIFIED_EXTRA_ARGS="--enable-prefix-caching --reasoning-parser qwen3"

        start_instance \
            "main_llm" \
            "8000" \
            "$VLLM_UNIFIED_MODEL" \
            "$MAIN_MODEL" \
            "$VLLM_UNIFIED_GPU_MEMORY_UTILIZATION" \
            "$VLLM_UNIFIED_MAX_MODEL_LEN" \
            "$UNIFIED_EXTRA_ARGS"
    else
        # ── gpt-oss mode (default): gpt-oss-20b MXFP4 ───────────────────────────
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
fi

# ── Instance 2: VLM (port 8001) ──────────────────────────────────────────────
# Qwen3.5-9B — vision+text+reasoning for slide/PDF parsing and visual QnA.
# --reasoning-parser qwen3: strips <think>...</think> server-side.
# --quantization awq: auto-added for AWQ model variants.
# Skipped in qwen-unified mode — port 8000 handles all VLM requests.
if [ "$START_VLM" = true ] && [ "$VLLM_MODE" != "qwen-unified" ]; then
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
[ "$START_VLM"  = true ] && [ "$VLLM_MODE" != "qwen-unified" ] && check_ready "vlm" "8001"
[ "$START_GLM"  = true ] && check_ready "glm_ocr"  "$GLM_OCR_VLLM_PORT"

echo ""
echo "vLLM startup complete.  [mode: ${VLLM_MODE}]"
if [ "$VLLM_MODE" = "qwen-unified" ]; then
    [ "$START_MAIN" = true ] && echo "  Unified LLM+VLM: http://localhost:8000/v1  (model: ${VLLM_UNIFIED_MODEL}, ctx: ${VLLM_UNIFIED_MAX_MODEL_LEN})"
else
    [ "$START_MAIN" = true ] && echo "  Main LLM       : http://localhost:8000/v1  (model: ${MAIN_MODEL}, MXFP4 via Triton, ctx: ${VLLM_MAX_MODEL_LEN})"
    [ "$START_VLM"  = true ] && echo "  VLM            : http://localhost:8001/v1  (model: ${VLLM_VLM_MODEL})"
fi
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
    [ "$START_VLM"  = true ] && [ "$VLLM_MODE" != "qwen-unified" ] && LOG_FILES+=("$LOG_DIR/vlm.log")
    [ "$START_GLM"  = true ] && LOG_FILES+=("$LOG_DIR/glm_ocr.log")
    tail -f "${LOG_FILES[@]}"
fi
