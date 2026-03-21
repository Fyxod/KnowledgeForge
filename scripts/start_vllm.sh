#!/bin/bash
# ==============================================================================
# vLLM Startup Script — starts all vLLM model instances
# ==============================================================================
#
# Uses the official `vllm serve` CLI (equivalent to python -m vllm.entrypoints.openai.api_server).
#
# Supported main models (native vLLM support, no conversion needed):
#   openai/gpt-oss-20b   ← default (fits A6000 48GB in BF16 at ~85% util)
#   openai/gpt-oss-120b  ← requires multi-GPU or quantization
#
# VRAM budget on A6000 48GB:
#   Main LLM (gpt-oss-20b BF16): ~40GB weights → VLLM_GPU_MEMORY_UTILIZATION=0.85
#   VLM      (Qwen2-VL-7B AWQ):  ~6GB  weights → VLLM_VLM_GPU_MEMORY_UTILIZATION=0.13
#   GLM-OCR  (0.9B, port 8080):  ~2GB  (managed by glmocr SDK — NOT started here)
#   Total: ~48GB — tight but feasible. If VRAM pressure occurs, reduce VLM util
#   or enable vLLM Sleep Mode for the VLM instance.
#
# --served-model-name:
#   vLLM loads weights from openai/gpt-oss-20b but registers the model under
#   MAIN_MODEL (e.g. "gpt-oss:20b-50k-8k") so that invoke_llm() can send the
#   same model name it uses today without any Python-side changes.
#
# Usage:
#   bash scripts/start_vllm.sh           # Start all instances in background
#   bash scripts/start_vllm.sh --logs    # Tail logs after starting
#   bash scripts/start_vllm.sh --main    # Start main LLM only
#   bash scripts/start_vllm.sh --vlm     # Start VLM only
#
# Instances managed by this script:
#   Instance 1: Main LLM  — port 8000  (VLLM_MAIN_URL)
#   Instance 2: VLM       — port 8001  (VLLM_VLM_URL)
#
# NOT managed here (already running via GLM-OCR SDK):
#   Instance 3: GLM-OCR   — port 8080  (core/parsers/glm_ocr.py, DO NOT TOUCH)
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

# ── Configuration ─────────────────────────────────────────────────────────────
# Main LLM: official OpenAI gpt-oss model served natively by vLLM.
# Override in .env:  VLLM_MAIN_MODEL=openai/gpt-oss-120b  for the 120B variant.
VLLM_MAIN_MODEL="${VLLM_MAIN_MODEL:-openai/gpt-oss-20b}"

# The name registered in the vLLM API — must match MAIN_MODEL in .env so that
# invoke_llm() requests succeed without any Python changes.
MAIN_MODEL="${MAIN_MODEL:-gpt-oss:20b}"

VLLM_VLM_MODEL="${VLLM_VLM_MODEL:-Qwen/Qwen2-VL-7B-Instruct-AWQ}"
VLLM_DRAFT_MODEL="${VLLM_DRAFT_MODEL:-}"

# gpt-oss-20b is ~40GB in BF16 on a 48GB A6000 → use 0.85 for main LLM.
# VLM gets the remaining ~6GB slice.
VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.85}"
VLLM_VLM_GPU_MEMORY_UTILIZATION="${VLLM_VLM_GPU_MEMORY_UTILIZATION:-0.13}"
VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-131072}"

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
        --enable-prefix-caching \
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
TAIL_LOGS=false

for arg in "$@"; do
    case "$arg" in
        --main) START_VLM=false ;;
        --vlm)  START_MAIN=false ;;
        --logs) TAIL_LOGS=true ;;
    esac
done

# ── Instance 1: Main LLM (port 8000) ─────────────────────────────────────────
if [ "$START_MAIN" = true ]; then
    MAIN_EXTRA_ARGS=""

    # Speculative decoding — enabled when VLLM_DRAFT_MODEL is non-empty.
    # For gpt-oss-20b, EAGLE3 draft heads are available on HuggingFace.
    # Example: VLLM_DRAFT_MODEL=openai/gpt-oss-20b-draft (check HF for availability)
    if [ -n "$VLLM_DRAFT_MODEL" ]; then
        MAIN_EXTRA_ARGS="--speculative-model ${VLLM_DRAFT_MODEL} --num-speculative-tokens 5"
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

# ── Instance 2: VLM (port 8001) ───────────────────────────────────────────────
# Multimodal model for slide/PDF visual parsing (vlm.py).
# Uses 32K context — images consume many tokens.
# NOTE: If VRAM is tight after gpt-oss-20b, reduce VLLM_VLM_GPU_MEMORY_UTILIZATION
#       or start with --vlm flag only and use vLLM Sleep Mode to swap models.
if [ "$START_VLM" = true ]; then
    start_instance \
        "vlm" \
        "8001" \
        "$VLLM_VLM_MODEL" \
        "$VLLM_VLM_MODEL" \
        "$VLLM_VLM_GPU_MEMORY_UTILIZATION" \
        "32768" \
        "--enable-prefix-caching"
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

echo ""
echo "vLLM startup complete."
[ "$START_MAIN" = true ] && echo "  Main LLM : http://localhost:8000/v1  (model: ${MAIN_MODEL})"
[ "$START_VLM"  = true ] && echo "  VLM      : http://localhost:8001/v1  (model: ${VLLM_VLM_MODEL})"
echo "  GLM-OCR  : http://localhost:8080    (managed by glmocr SDK — not started here)"
echo "  Logs     : $LOG_DIR/"
echo ""
echo "To stop:  bash scripts/stop_vllm.sh"
echo "To watch: tail -f $LOG_DIR/main_llm.log"

# ── Optional: tail logs ───────────────────────────────────────────────────────
if [ "$TAIL_LOGS" = true ]; then
    LOG_FILES=()
    [ "$START_MAIN" = true ] && LOG_FILES+=("$LOG_DIR/main_llm.log")
    [ "$START_VLM"  = true ] && LOG_FILES+=("$LOG_DIR/vlm.log")
    tail -f "${LOG_FILES[@]}"
fi
