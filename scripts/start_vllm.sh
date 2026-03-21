#!/bin/bash
# ==============================================================================
# vLLM Startup Script — starts all vLLM model instances
# ==============================================================================
#
# Reads configuration from environment variables or .env file.
# Source your .env before running, or export variables directly.
#
# Usage:
#   bash scripts/start_vllm.sh           # Start all instances in background
#   bash scripts/start_vllm.sh --logs    # Tail logs after starting
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

# ── Configuration (defaults match Settings defaults in core/config.py) ────────
VLLM_MAIN_MODEL="${VLLM_MAIN_MODEL:-Qwen/Qwen3-14B-AWQ}"
VLLM_VLM_MODEL="${VLLM_VLM_MODEL:-Qwen/Qwen2-VL-7B-Instruct-AWQ}"
VLLM_DRAFT_MODEL="${VLLM_DRAFT_MODEL:-}"
VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.55}"
VLLM_VLM_GPU_MEMORY_UTILIZATION="${VLLM_VLM_GPU_MEMORY_UTILIZATION:-0.20}"
VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-131072}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

LOG_DIR="logs/vllm"
mkdir -p "$LOG_DIR"

# ── Helper ────────────────────────────────────────────────────────────────────
start_instance() {
    local name="$1"
    local port="$2"
    local model="$3"
    local gpu_mem="$4"
    local max_len="$5"
    local extra_args="${6:-}"
    local logfile="$LOG_DIR/${name}.log"

    echo "Starting vLLM instance: $name"
    echo "  Model  : $model"
    echo "  Port   : $port"
    echo "  GPU mem: $gpu_mem"
    echo "  Log    : $logfile"

    # shellcheck disable=SC2086
    CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
    python -m vllm.entrypoints.openai.api_server \
        --model "$model" \
        --port "$port" \
        --host 0.0.0.0 \
        --gpu-memory-utilization "$gpu_mem" \
        --max-model-len "$max_len" \
        --tensor-parallel-size 1 \
        --enable-prefix-caching \
        --enable-chunked-prefill \
        $extra_args \
        > "$logfile" 2>&1 &

    echo "  PID    : $!"
    echo "$!" > "$LOG_DIR/${name}.pid"
    echo ""
}

# ── Instance 1: Main LLM (port 8000) ─────────────────────────────────────────
MAIN_EXTRA_ARGS=""

# Speculative decoding — only when VLLM_DRAFT_MODEL is set
if [ -n "$VLLM_DRAFT_MODEL" ]; then
    MAIN_EXTRA_ARGS="--speculative-model ${VLLM_DRAFT_MODEL} --num-speculative-tokens 5"
    echo "[Main LLM] Speculative decoding enabled: draft=${VLLM_DRAFT_MODEL}"
fi

start_instance \
    "main_llm" \
    "8000" \
    "$VLLM_MAIN_MODEL" \
    "$VLLM_GPU_MEMORY_UTILIZATION" \
    "$VLLM_MAX_MODEL_LEN" \
    "$MAIN_EXTRA_ARGS"

# ── Instance 2: VLM (port 8001) ───────────────────────────────────────────────
# VLM uses a shorter context window (32K) — multimodal images consume many tokens
start_instance \
    "vlm" \
    "8001" \
    "$VLLM_VLM_MODEL" \
    "$VLLM_VLM_GPU_MEMORY_UTILIZATION" \
    "32768" \
    "--enable-prefix-caching"

# ── Wait for readiness ────────────────────────────────────────────────────────
echo "Waiting for vLLM instances to become ready..."
sleep 5

check_ready() {
    local name="$1"
    local port="$2"
    if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
        echo "  [OK] $name (port $port) is ready"
    else
        echo "  [WAIT] $name (port $port) is still starting — check $LOG_DIR/${name}.log"
    fi
}

check_ready "main_llm" "8000"
check_ready "vlm"      "8001"

echo ""
echo "vLLM startup complete."
echo "  Main LLM : http://localhost:8000/v1"
echo "  VLM      : http://localhost:8001/v1"
echo "  Logs     : $LOG_DIR/"
echo ""
echo "To stop all instances: bash scripts/stop_vllm.sh"

# ── Optional: tail logs ───────────────────────────────────────────────────────
if [ "${1:-}" = "--logs" ]; then
    tail -f "$LOG_DIR/main_llm.log" "$LOG_DIR/vlm.log"
fi
