#!/bin/bash
# ==============================================================================
# vLLM Stop Script — terminates all vLLM instances and the GLM-OCR SDK server
# ==============================================================================
#
# Usage:
#   bash scripts/stop_vllm.sh
#
# Stops all instances started by start_vllm.sh by reading stored PID files:
#   - Main LLM        (port 9000)
#   - VLM             (port 9001)
#   - GLM-OCR vLLM    (port 8080)
#   - GLM-OCR SDK     (port 5002)
#
# Falls back to killing all vLLM processes via pgrep if PID files are missing.
#
# ==============================================================================

set -euo pipefail

LOG_DIR="logs/vllm"

kill_by_pid_file() {
    local name="$1"
    local pid_file="$LOG_DIR/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $name (PID $pid)..."
            kill "$pid"
            rm -f "$pid_file"
        else
            echo "$name (PID $pid) is not running — removing stale PID file."
            rm -f "$pid_file"
        fi
    else
        echo "No PID file found for $name — skipping."
    fi
}

# ── Stop all managed instances ────────────────────────────────────────────────
kill_by_pid_file "main_llm"
kill_by_pid_file "vlm"
kill_by_pid_file "glm_ocr"
kill_by_pid_file "glm_ocr_sdk"

# ── Fallback: kill any remaining vLLM processes ───────────────────────────────
# Catches both `vllm serve` (new CLI) and `python -m vllm.entrypoints...` (old).
echo ""
echo "Checking for residual vLLM processes..."

remaining=$(
    { pgrep -f "vllm.entrypoints.openai.api_server" 2>/dev/null || true; \
      pgrep -f "vllm serve" 2>/dev/null || true; } \
    | sort -u
)

if [ -n "$remaining" ]; then
    echo "Found residual vLLM processes: $(echo "$remaining" | tr '\n' ' ')"
    echo "Sending SIGTERM..."
    echo "$remaining" | xargs kill 2>/dev/null || true
    sleep 2
    # SIGKILL for any that didn't respond
    echo "$remaining" | xargs kill -9 2>/dev/null || true
else
    echo "No residual vLLM processes found."
fi

# ── Fallback: kill any remaining glmocr SDK server processes ──────────────────
echo ""
echo "Checking for residual glmocr SDK processes..."

sdk_remaining=$(pgrep -f "glmocr.server" 2>/dev/null || true)

if [ -n "$sdk_remaining" ]; then
    echo "Found residual glmocr SDK processes: $(echo "$sdk_remaining" | tr '\n' ' ')"
    echo "$sdk_remaining" | xargs kill 2>/dev/null || true
    sleep 1
    echo "$sdk_remaining" | xargs kill -9 2>/dev/null || true
else
    echo "No residual glmocr SDK processes found."
fi

echo ""
echo "All vLLM instances and GLM-OCR SDK server stopped."
