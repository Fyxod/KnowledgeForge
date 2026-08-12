#!/usr/bin/env bash
set -Eeuo pipefail

web_url="${1:-http://localhost:8080}"
api_url="${2:-http://localhost:8000}"
smoke_email="docker-smoke-$(date +%s)@example.com"

retry_curl() {
    curl \
        --fail \
        --silent \
        --show-error \
        --retry 30 \
        --retry-all-errors \
        --retry-delay 2 \
        "$@"
}

direct_health="$(retry_curl "${api_url}/health/")"
proxied_health="$(retry_curl "${web_url}/health/")"
frontend_html="$(retry_curl "${web_url}/")"
spa_html="$(retry_curl "${web_url}/dashboard")"

grep -q '"status":"ok"' <<<"${direct_health}"
grep -q '"status":"ok"' <<<"${proxied_health}"
grep -q '<div id="root"></div>' <<<"${frontend_html}"
grep -q '<div id="root"></div>' <<<"${spa_html}"

register_response="$(retry_curl \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Docker Smoke\",\"email\":\"${smoke_email}\",\"password\":\"docker-smoke-password\"}" \
    "${web_url}/user/")"
grep -q '"status":"success"' <<<"${register_response}"

login_response="$(retry_curl \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${smoke_email}\",\"password\":\"docker-smoke-password\"}" \
    "${web_url}/user/login")"
grep -q '"token"' <<<"${login_response}"

socket_handshake="$(retry_curl "${web_url}/socket.io/?EIO=4&transport=polling")"
grep -q '"sid"' <<<"${socket_handshake}"

printf 'Docker smoke test passed: frontend, SPA fallback, API, MongoDB auth flow, and Socket.IO proxy.\n'
