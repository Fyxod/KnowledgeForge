#!/bin/bash
# ==============================================================================
# Ollama Performance Environment Variables
# ==============================================================================
# Apply these BEFORE starting Ollama for optimal performance.
#
# Usage:
#   Option 1: Source this file before starting Ollama:
#     source scripts/ollama_env_setup.sh && ollama serve
#
#   Option 2: Add to your systemd service or .bashrc/.profile
#
#   Option 3 (Windows): Set as system environment variables
#     setx OLLAMA_FLASH_ATTENTION 1
#     setx OLLAMA_KV_CACHE_TYPE q8_0
#     setx OLLAMA_NUM_PARALLEL 2
#     setx OLLAMA_MAX_LOADED_MODELS 3
#     setx OLLAMA_KEEP_ALIVE -1
# ==============================================================================

# Flash Attention: Zero quality loss, 10-20% faster attention computation
# Prerequisite for KV cache quantization
export OLLAMA_FLASH_ATTENTION=1

# KV Cache Quantization: 50% VRAM reduction for KV cache
# Quality impact: +0.002-0.05 perplexity (imperceptible to humans)
#
# ⚠️  WARNING: If your main model (GPT-OSS:20B) is based on Gemma3 architecture,
#     DO NOT use q8_0 — there's a known severe regression (speed drops from
#     ~30 tok/s to ~5 tok/s). Comment out this line for Gemma3-based models.
export OLLAMA_KV_CACHE_TYPE=q8_0

# Parallel Requests: Allow 2 concurrent requests per model
# Eliminates the biggest bottleneck — decomposition and sub-query can run simultaneously
export OLLAMA_NUM_PARALLEL=2

# Max Loaded Models: Keep main model + VLM model loaded in VRAM
export OLLAMA_MAX_LOADED_MODELS=3

# Keep Alive: Keep models loaded indefinitely (no cold-start latency)
export OLLAMA_KEEP_ALIVE=-1

echo "[Ollama] Performance environment variables set:"
echo "  OLLAMA_FLASH_ATTENTION=$OLLAMA_FLASH_ATTENTION"
echo "  OLLAMA_KV_CACHE_TYPE=$OLLAMA_KV_CACHE_TYPE"
echo "  OLLAMA_NUM_PARALLEL=$OLLAMA_NUM_PARALLEL"
echo "  OLLAMA_MAX_LOADED_MODELS=$OLLAMA_MAX_LOADED_MODELS"
echo "  OLLAMA_KEEP_ALIVE=$OLLAMA_KEEP_ALIVE"
