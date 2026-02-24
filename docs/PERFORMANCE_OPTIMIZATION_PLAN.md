# Performance Optimization Plan: OCR & LLM Speed

**Branch:** `feature/performance-optimization-ocr-llm`
**Created:** 2026-02-23
**Status:** In Progress

## Constraints

- Single system, 48GB VRAM (e.g. NVIDIA A6000 or equivalent)
- Models: GPT-OSS:20B (chat/summarization) + QWEN3-VL:8B (VLM/OCR)
- No external API calls — all processing stays local (sensitive documents)
- No quality compromise — all optimizations must be quality-neutral or quality-positive

---

## PART A: OCR SPEED OPTIMIZATION

### Current State — Bottleneck Map (Document Ingestion Pipeline)

```
Document Upload
    ├── PDF:    PyMuPDF text extraction → Table extraction → Embedded image OCR (EasyOCR) → Optional VLM
    ├── PPTX:   python-pptx text extraction → LibreOffice→PDF→Images@300DPI → EasyOCR → Optional VLM
    ├── DOCX:   python-docx text extraction → Embedded image OCR (EasyOCR) → Optional VLM
    ├── Images: EasyOCR (primary) → Tesseract (fallback)
    ├── Markdown: Text extraction → Embedded image OCR (EasyOCR)
    └── Excel/CSV: pandas (no OCR needed)
```

### Critical Bottlenecks Identified

| # | Bottleneck | Current State | Impact |
|---|-----------|---------------|--------|
| 1 | EasyOCR runs on CPU | `EASYOCR_GPU = False` in constants.py:27 | 4-7x slower than GPU mode. **Single biggest OCR bottleneck** |
| 2 | PPTX slide export at 300 DPI | slide_export.py:139 `dpi=300` | Creates 8.4MP images per slide. 200 DPI (3.7MP) sufficient for OCR with 56% fewer pixels |
| 3 | No OCR skip for text-rich PDF pages | Every embedded image gets OCR'd | Tiny decorative images still get OCR'd |
| 4 | VLM at 150 DPI for all candidate pages | main.py:1144 `dpi=150` | VLM `max_concurrent=3` and 240s timeout per page are bottleneck |
| 5 | Sequential PDF page processing | No CPU↔GPU pipelining | Good async pattern, but could overlap CPU rendering with GPU OCR |
| 6 | EasyOCR model loads ~200MB per reader | CPU-only negates caching benefit | GPU reader loads once, stays in VRAM (~200MB) |

### VRAM Budget for OCR

| Component | Current VRAM | Proposed VRAM |
|-----------|-------------|---------------|
| QWEN3-VL:8B (VLM) | ~5-6 GB | ~5-6 GB (unchanged) |
| EasyOCR GPU model | 0 (CPU) | ~200 MB |
| **Total OCR VRAM** | **~5-6 GB** | **~6 GB** |

Leaves ~42 GB for the 20B LLM and other components — no VRAM pressure.

---

### A1: Enable EasyOCR GPU Mode ✅

**File:** `core/constants.py:27`
**Change:** `EASYOCR_GPU = False` → `EASYOCR_GPU = True`
**Expected speedup:** 4-7x for all OCR operations

Additional GPU tuning in `core/parsers/image.py`:
- Enable cuDNN benchmark mode: `torch.backends.cudnn.benchmark = True`
- Increase `batch_size` in readtext calls (default=1 → 8-16 for GPU)
- Use `decoder='greedy'` (already default, fastest option)

**Quality impact:** None. Same model, same weights, faster hardware.
**Risk:** Very Low. ~200MB VRAM on 48GB system.

### A2: Reduce PPTX Slide Export DPI 300→200 ✅

**File:** `core/parsers/slide_export.py:139`
**Change:** `dpi=300` → `dpi=200`
**Expected speedup:** ~56% fewer pixels to render AND OCR

| DPI | Image Size (per slide) | Pixels | OCR Quality |
|-----|----------------------|--------|-------------|
| 300 | 2550×3300 | 8.4M | Excellent |
| 200 | 1700×2200 | 3.7M | Very good (sufficient for presentation text) |

**Quality impact:** Negligible for presentation slides. Text is large enough (18pt+) that 200 DPI captures it perfectly.

### A3: Smart OCR Skip for PDF Embedded Images (DEFERRED)

**Status:** Deferred — risk of skipping flowchart blocks that are stored as individual small images.

**What was implemented instead:** Duplicate image detection only (xref-based caching).
If the same image appears on multiple pages (e.g. headers/footers/logos), OCR runs once and
the result is reused. This is safe and gives a speedup for documents with repeated images.

**Why deferred:** The "skip small images in text-rich pages" heuristic could lose content from
PDF flowcharts (e.g. Visio exports) where each shape block is a separate small raster image.
Will revisit after measuring speed gains from other optimizations (especially A1 GPU OCR).

### A4: Pipeline CPU Rendering with GPU OCR ✅

**File:** `core/parsers/slide_export.py`

Current: Render ALL slides → OCR ALL slides (sequential)
Proposed: Producer-Consumer pipeline with `asyncio.Queue`

```
[CPU: Render slide N to image] → Queue → [GPU: OCR slide N with EasyOCR]
[CPU: Render slide N+1]       →        → [GPU: OCR slide N result ready]
```

**Expected speedup:** ~30-60% from overlapping CPU rendering with GPU OCR.
**Quality impact:** None — same processing, different scheduling.

### A5: Evaluate PaddleOCR as EasyOCR Alternative (Future)

NOT a code change — needs evaluation. PaddleOCR PP-OCRv4 is 10-30x faster than EasyOCR on GPU.

### A6: VLM Concurrency and Timeout Tuning ✅

**File:** `core/parsers/vlm.py`

Changes:
- `num_predict`: 4096 → 2048 (most slide content fits in 1000-1500 tokens)
- `timeout`: 240s → 120s (fall back to OCR for stuck pages)
- Keep `max_concurrent=3` (VRAM-limited)

**Quality impact:** Minimal — slides rarely produce >2048 output tokens.

---

### OCR Speed Summary

| Optimization | Speedup | Effort | Risk |
|-------------|---------|--------|------|
| A1: EasyOCR GPU | 4-7x for all OCR | Low | Very Low |
| A2: PPTX DPI 300→200 | ~1.5x for PPTX | Low | Very Low |
| A3: Smart OCR Skip | ~1.2-1.4x for PDF | Medium | Low |
| A4: CPU↔GPU Pipeline | ~1.3-1.6x for PPTX | Medium | Low |
| A5: PaddleOCR Evaluation | 10-30x if adopted | High | Medium |
| A6: VLM Tuning | ~1.3-1.5x for VLM pages | Low | Very Low |

**Combined estimated speedup for OCR-heavy documents: 5-10x (A1-A4 and A6).**

---

## PART B: LLM PROCESSING / ANSWER RESPONSE TIME OPTIMIZATION

### Current State — Query Processing Pipeline

```
User Query
  ├─ 1. Decomposition (invoke_llm on PORT2)                    ~3-8s
  ├─ 2. For each sub-query (2 parallel workers max):
  │     ├─ 2a. Hybrid Retrieval (ChromaDB + BM25)              ~0.5-2s
  │     ├─ 2b. Cross-Encoder Reranking (CPU)                   ~0.1-0.3s
  │     ├─ 2c. LLM Generation (invoke_llm on PORT1 or PORT2)   ~5-15s
  │     └─ 2d. Retry loop (up to 8 attempts with 2s sleep)     ~0-16s (worst case)
  ├─ 3. Combination (invoke_llm on PORT2)                      ~3-8s
  └─ Total: ~10-35s typical, up to 60s+ under contention
```

### Critical Bottlenecks

| # | Bottleneck | Current State | Impact |
|---|-----------|---------------|--------|
| 1 | model_port_lock serializes ALL requests | One request per (model, port) at a time | Requests queue behind each other |
| 2 | OLLAMA_NUM_PARALLEL likely =1 | Default Ollama setting | Single request processing per instance |
| 3 | No Flash Attention | Not set in Ollama env | Missing free speed improvement |
| 4 | KV Cache at f16 (default) | Not explicitly set | Using 2x more VRAM for KV cache |
| 5 | Embedding model on CPU | `"device": "cpu"` | ~3-4x slower than GPU |
| 6 | Cross-encoder on CPU | No device specified | ~4-9x slower than GPU |
| 7 | Buffered (non-streaming) responses | Uses `invoke()` and `stream=False` | User waits for full generation |
| 8 | 8 retry attempts | MAX_RETRIES=8 | With JSON sanitizer, most errors recovered on first attempt |
| 9 | Two separate Ollama instances | PORT1=11434, PORT2=11435 | Each manages own VRAM pool |
| 10 | LLM re-instantiated per call | MyServerLLM created fresh each call | Minor per-call overhead |

### VRAM Budget for LLM

| Component | Current VRAM (est.) | Optimized VRAM (est.) |
|-----------|-------------------|---------------------|
| GPT-OSS:20B weights (Q4_K_M) | ~10-12 GB | ~10-12 GB |
| GPT-OSS:20B KV cache (f16) | ~2.8 GB (×2 instances) | ~1.4 GB (q8_0, 1 instance) |
| QWEN3-VL:8B weights | ~5-6 GB | ~5-6 GB |
| QWEN3-VL:8B KV cache | ~1.1 GB | ~0.55 GB (q8_0) |
| EasyOCR GPU | 0 | ~0.2 GB |
| Embedding model (nomic-embed) | 0 (CPU) | ~0.5 GB |
| Cross-encoder (MiniLM-L6) | 0 (CPU) | ~0.1 GB |
| CUDA overhead | ~1-2 GB | ~1-2 GB |
| **Total** | **~22-26 GB** | **~20-22 GB** |

---

### B1: Ollama Environment Variables (Zero-Code) ✅

```bash
export OLLAMA_FLASH_ATTENTION=1          # Zero quality loss, faster attention
export OLLAMA_KV_CACHE_TYPE=q8_0         # 50% KV cache VRAM reduction
export OLLAMA_NUM_PARALLEL=2             # Allow 2 concurrent requests per model
export OLLAMA_MAX_LOADED_MODELS=3        # Keep both models + embedding model loaded
export OLLAMA_KEEP_ALIVE=-1              # Keep models loaded indefinitely
```

**⚠️ IMPORTANT:** If GPT-OSS:20B is based on Gemma3 architecture, DO NOT use `OLLAMA_KV_CACHE_TYPE=q8_0` — known severe regression.

### B2: Replace model_port_lock with Semaphore ✅

**File:** `core/llm/configurations/local_llm.py`

Replace `threading.Lock` with `threading.Semaphore(OLLAMA_CONCURRENCY)` to allow N concurrent requests matching `OLLAMA_NUM_PARALLEL`.

**Expected impact:** ~1.5-2x throughput improvement for decomposed queries.

### B3: Move Embedding Model to GPU ✅

**File:** `core/embeddings/embeddings.py`
**Change:** `"device": "cpu"` → `"device": "cuda"`
**Additional:** Add `"batch_size": 128` to encode_kwargs

**Expected speedup:** ~3-4x faster embedding generation.
Model is 137M parameters (~550MB VRAM).

### B4: Move Cross-Encoder to GPU with FP16 ✅

**File:** `core/embeddings/retriever.py`
**Change:** Add `device='cuda'` and `torch_dtype='float16'`

**Expected speedup:** ~4-9x faster reranking.
MiniLM-L6 is 22.7M parameters (~100MB VRAM in FP16).

### B5: Implement Response Streaming (Future)

Medium-High complexity. Requires changes to query endpoint, LLM client, and frontend. Planned for Phase 3.

### B6: Consolidate to Single Ollama Instance (Future)

Medium risk. Planned for Phase 3.

### B7: Cache LLM Client Instances ✅

**File:** `core/llm/client.py`

Cache `MyServerLLM` instances by `(model, port)` key to avoid repeated initialization.

**Expected impact:** ~5% per-call overhead reduction.

### B8: Reduce MAX_RETRIES 8→4 ✅

**File:** `core/llm/client.py`
**Change:** `MAX_RETRIES = 8` → `MAX_RETRIES = 4`

With JSON sanitizer + json_repair already implemented, most parse errors recovered on first attempt.

**Expected impact:** Worst-case response time drops from ~60s to ~30s.

### B9: Optimize Retrieval and Context Size ✅

**Files:** `core/embeddings/retriever.py`, `core/constants.py`

Changes:
- `MAX_TOTAL_CHUNKS`: 100 → 50
- Add relevance score threshold after cross-encoder reranking (drop chunks < 0.01)

**Expected impact:** 20-40% reduction in generation time for multi-document queries.

### B10: ChromaDB HNSW Tuning (Future)

Requires re-indexing existing collections. Planned for Phase 4.

---

### LLM Speed Summary

| Optimization | Speedup | Effort | Risk |
|-------------|---------|--------|------|
| B1: Ollama env vars | 10-20% LLM speed | Very Low | Very Low |
| B2: Remove model_port_lock | ~1.5-2x throughput | Low | Low |
| B3: Embedding → GPU | ~3-4x embedding speed | Very Low | Very Low |
| B4: Cross-encoder → GPU FP16 | ~4-9x reranking | Low | Very Low |
| B5: Response streaming | 3-5x perceived latency | High | Medium |
| B6: Single Ollama instance | ~5-10% VRAM savings | Medium | Low |
| B7: Cache LLM clients | ~5% per-call reduction | Very Low | Very Low |
| B8: Reduce retries | ~50% worst-case time | Very Low | Very Low |
| B9: Optimize retrieval | ~20-40% generation time | Medium | Low |
| B10: ChromaDB HNSW tuning | Better recall | Medium | Very Low |

**Combined estimated speedup for query response: 2-4x (B1-B4, B7-B8 quick wins).**

---

## Implementation Priority Order

### Phase 1: Quick Wins (zero risk) ✅
- [x] A1 — Enable EasyOCR GPU
- [x] A2 — Reduce PPTX DPI 300→200
- [x] B3 — Move embedding model to GPU
- [x] B4 — Move cross-encoder to GPU with FP16
- [x] B7 — Cache LLM client instances
- [x] B8 — Reduce MAX_RETRIES 8→4
- [x] B1 — Ollama env var documentation

### Phase 2: Moderate Changes (low risk) ✅
- [x] B2 — Replace model_port_lock with semaphore
- [ ] A3 — Smart OCR skip (DEFERRED — risk to flowcharts; duplicate detection implemented instead)
- [x] A6 — VLM parameter tuning
- [x] B9 — Optimize retrieval chunk count + relevance threshold

### Phase 3: Architecture Changes (medium risk)
- [ ] A4 — CPU↔GPU OCR pipeline for PPTX
- [ ] B6 — Consolidate to single Ollama instance
- [ ] B5 — Response streaming with SSE

### Phase 4: Evaluation (ongoing)
- [ ] A5 — Evaluate PaddleOCR / RapidOCR
- [ ] B10 — ChromaDB HNSW tuning

---

## VRAM Budget After All Optimizations

| Component | VRAM |
|-----------|------|
| GPT-OSS:20B (Q4_K_M weights) | 10-12 GB |
| GPT-OSS:20B KV cache (q8_0, NUM_PARALLEL=2) | 2.8 GB |
| QWEN3-VL:8B (weights) | 5-6 GB |
| QWEN3-VL:8B KV cache (q8_0, max_concurrent=3) | 1.65 GB |
| EasyOCR GPU | 0.2 GB |
| nomic-embed-text-v1.5 GPU | 0.5 GB |
| cross-encoder/MiniLM-L6 GPU FP16 | 0.1 GB |
| CUDA/runtime overhead | 1-2 GB |
| **Total** | **~22-25 GB** |
| **Remaining (of 48 GB)** | **~23-26 GB** |
