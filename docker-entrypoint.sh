#!/usr/bin/env bash
set -Eeuo pipefail

backend_pid=""
nginx_pid=""

shutdown() {
    trap - TERM INT EXIT
    if [[ -n "${nginx_pid}" ]]; then
        kill -TERM "${nginx_pid}" 2>/dev/null || true
    fi
    if [[ -n "${backend_pid}" ]]; then
        kill -TERM "${backend_pid}" 2>/dev/null || true
    fi
    wait || true
}

trap shutdown TERM INT EXIT

python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips="127.0.0.1" &
backend_pid=$!

nginx -g "daemon off;" &
nginx_pid=$!

wait -n "${backend_pid}" "${nginx_pid}"
status=$?
exit "${status}"
