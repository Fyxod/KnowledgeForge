# Model Configuration Guide (48GB VRAM)

This guide highlights the optimal model configuration for a **48GB VRAM** environment (e.g., 2x RTX 3090/4090 NVLink, RTX 6000 Ada, or A6000).

## Recommended Setup: "The Powerhouse"
Maximize reasoning capability while fitting within 48GB.

| Role | Model | Size (Quantized) | VRAM Usage | Capabilities |
|------|-------|------------------|------------|--------------|
| **Main LLM** | `llama3.3:70b-instruct-q4_K_M` | ~42 GB | High | Superior reasoning, citation, analyst mode |
| **Query LLM** | `llama3.1:8b-instruct-q4_K_M` | ~5 GB | Low | Fast query decomposition, simple tasks |
| **Embedding** | `nomic-embed-text` | ~0.5 GB | Negligible | High-quality retrieval |

**Total Estimated VRAM**: ~47.5 GB (Very tight, requires efficient context handling)

### Alternative Setup: "The Balanced Speedster"
Better speed and breathing room for long contexts (50k+ tokens).

| Role | Model | Size | VRAM Usage |
|------|-------|------|------------|
| **Main LLM** | `qwen2.5:32b-instruct-fp16` | ~60 GB (Too big!) <br> use **Q4_K_M (~20GB)** | Medium |
| **Query LLM** | `qwen2.5:14b-instruct-q4_K_M` | ~9 GB | Low |
| **Embedding** | `nomic-embed-text` | ~0.5 GB | Negligible |

**Total Estimated VRAM**: ~30 GB (Leaves 18GB for massive context window KV cache)

---

## Configuration Steps

### 1. Pull Models (Ollama)
Run these commands in your terminal:

```bash
# For Powerhouse Setup
ollama pull llama3.3:70b
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# For Balanced Setup
ollama pull qwen2.5:32b
ollama pull qwen2.5:14b

# VLM (Vision Language Model) for PDF/Slide Parsing
ollama pull qwen3-vl:8b
```

### 2. Configure Environment (`.env`)
Edit your `.env` file to match the selected models.

**Option A: Powerhouse (70B + 8B)**
```ini
# Main Reasoning Model
GPU_LLM=llama3.3:70b

# Helper Model (Decomposition/Search)
GPU_QUERY_LLM=llama3.1:8b

# Embedding Model
EMBEDDING_MODEL_NAME=nomic-embed-text
```

**Option B: Balanced (32B + 14B)**
```ini
GPU_LLM=qwen2.5:32b
GPU_QUERY_LLM=qwen2.5:14b
EMBEDDING_MODEL_NAME=nomic-embed-text
```

## Performance Tips

1.  **Context Window**: 
    - Llama 3.3 supports 128k context, but 48GB VRAM limits how much you can actually fill.
    - With the **70B** model, you may be limited to ~8k-16k context before OOM.
    - With the **32B** model, you can easily utilize 32k-50k context.

2.  **Ollama Concurrency**:
    - If you encounter OOM errors, ensure `OLLAMA_NUM_PARALLEL=1` to prevent multiple requests from loading extra layers.
    - Set `OLLAMA_KEEP_ALIVE=5m` to keep models loaded.

3.  **Cross-Document Comparison**:
    - This feature consumes significant context (multiple document chunks). 
    - **Recommendation**: If comparing >3 large documents, use the **Balanced Setup (32B)** to avoid truncating data.
