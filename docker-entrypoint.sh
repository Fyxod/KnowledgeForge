#!/bin/bash
set -e

# Start FastAPI backend in background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Start nginx in foreground
nginx -g "daemon off;"
