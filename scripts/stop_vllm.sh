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

# Fallback: kill any remaining vLLM API server processes
# (excludes GLM-OCR on port 8080 — it manages its own process)
echo ""
echo "Checking for remaining vLLM processes (excluding GLM-OCR on port 8080)..."
remaining=$(pgrep -f "vllm.entrypoints.openai.api_server" 2>/dev/null || true)
if [ -n "$remaining" ]; then
    echo "Found residual vLLM processes: $remaining"
    echo "Sending SIGTERM..."
    echo "$remaining" | xargs kill 2>/dev/null || true
fi

echo ""
echo "vLLM instances stopped."
