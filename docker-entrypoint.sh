#!/bin/bash
set -e

# Start FastAPI backend in background
gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000  &

# Start nginx in foreground
nginx -g "daemon off;" # used to serve frontend
