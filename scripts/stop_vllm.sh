#!/bin/bash
# ==============================================================================
# vLLM Stop Script — terminates all running vLLM instances
# ==============================================================================
#
# Usage:
#   bash scripts/stop_vllm.sh
#
# Stops instances started by start_vllm.sh by reading stored PIDs.
# Falls back to killing all python -m vllm.entrypoints processes if PID
# files are missing.
#
# NOTE: Does NOT stop the GLM-OCR vLLM instance (port 8080) — that is managed
#       separately by the GLM-OCR SDK.
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

kill_by_pid_file "main_llm"
kill_by_pid_file "vlm"

# ── Fallback: kill any remaining vLLM processes ───────────────────────────────
# Catches both `vllm serve` (new CLI) and `python -m vllm.entrypoints...` (old).
# Explicitly excludes the GLM-OCR vLLM instance on port 8080 — that is managed
# separately by the GLM-OCR SDK and must not be killed here.
echo ""
echo "Checking for residual vLLM processes (excluding GLM-OCR on port 8080)..."

# Collect PIDs from both invocation styles, then exclude port 8080
remaining=$(
    { pgrep -f "vllm.entrypoints.openai.api_server" 2>/dev/null || true; \
      pgrep -f "vllm serve" 2>/dev/null || true; } \
    | sort -u \
    | while read -r pid; do
        # Skip the GLM-OCR process which binds to port 8080
        if ! ss -tlnp 2>/dev/null | grep -q "pid=${pid}.*:8080" && \
           ! lsof -p "$pid" -i :8080 2>/dev/null | grep -q LISTEN; then
            echo "$pid"
        fi
    done
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

echo ""
echo "vLLM instances stopped."
echo "GLM-OCR (port 8080) was not touched — stop it via the glmocr SDK if needed."
