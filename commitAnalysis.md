# Commit Analysis: All Changes Since `ddbbe6d`

**129 commits | 226 files changed | +38,391 / -2,605 lines**

---

## Table of Contents

1. [RAG Pipeline & Retrieval](#1-rag-pipeline--retrieval)
2. [LLM System & Invocation](#2-llm-system--invocation)
3. [SQL, Spreadsheet & Excel Skill](#3-sql-spreadsheet--excel-skill)
4. [Agent Pipeline & Query-Time VLM](#4-agent-pipeline--query-time-vlm)
5. [GLM-OCR Integration](#5-glm-ocr-integration)
6. [VLM & Document Parsing](#6-vlm--document-parsing)
7. [Docling Integration](#7-docling-integration)
8. [Document Creator](#8-document-creator)
9. [Studio Features & Export](#9-studio-features--export)
10. [Testing & Infrastructure](#10-testing--infrastructure)
11. [Bug Fixes & Stability](#11-bug-fixes--stability)

---

## 1. RAG Pipeline & Retrieval

### Major Changes

| Commit | Description |
|---|---|
| `85a0c4f` | **Enhanced RAG pipeline** — CRAG corrective retrieval, multi-query expansion, entity-relationship triples, entity profiles, index-time enrichment (headings, keywords, adjacent sentences), HyDE option. +1296 lines across 15 files. |
| `58acc1f` | **Core pipeline improvements** — UUID doc IDs (was 5-char prefix), BM25 merge on incremental upload, hierarchical parent/child chunking (parent=1500, child=500), persistent SQLite (was in-memory), score-aware document selection with quality gate. |
| `5ae6eb3` | **MapReduce batching** — When retrieved chunks exceed the LLM context window, groups by document, processes batches in parallel, combines results. Also adds "Lost in the Middle" reordering (best chunks at positions 0 and -1). |
| `3fbe2b3` | **Semantic query expansion** — Decomposition LLM generates 2-3 alternative phrasings with synonyms. Piggybacked onto existing decomposition call (zero extra latency). |
| `d12e3e4` | **Improved combination node** — Chunk deduplication across sub-queries, top-15 chunks passed to combination LLM, cross-referencing instructions for multi-entity queries. |
| `2925a76` | **Grounded inference fallback** — For inferential questions where documents don't literally state the answer but provide reasoning foundation. Hardcoded transparency prefix. |

### Minor Changes / Fixes

| Commit | Description |
|---|---|
| `f01fdf5` | Add `search_query:` / `search_document:` prefixes for nomic-embed-text-v1.5 |
| `2d445da` | Fix prefix: use `query_encode_kwargs` (the correct parameter) instead of `query_instruction` |
| `6b2f9b2` | Fix confidence always "low" — sigmoid normalization for cross-encoder scores, propagate `rerank_score` through MMR |
| `78a4053` | Skip RAG retrieval for spreadsheet-only threads (SQL handles these) |
| `f361a60` | CRAG retry on both "ambiguous" AND "insufficient"; narrow entity boost types; synonym expansion |
| `a88b397` | Increase retrieval budget from 50 to 200 chunks (MapReduce handles overflow) |
| `7b5ccc7` | Remove per-doc chunk cap — let RRF scoring naturally balance documents |
| `c047d3e` | Filter chunks with `rerank_score < 0.5` before passing to LLM (keep min 2) |
| `dd463c9` | Catch embedding model errors per-query to prevent full request crash |

---

## 2. LLM System & Invocation

### Major Changes

| Commit | Description |
|---|---|
| `4ddd99e` | **Self-correction retry** — On parse failure, inject the failed output + error into next attempt. GPU-only tight feedback loop. |
| `f9ee567` | **Schema-aware prompt framing** — Answer schemas preserve the full prompt structure; extraction schemas use simple wrapper. Fixes the "Extract structured data" wrapper causing terse answers. |
| `93f990d` | **Runtime-toggleable switches** — UI settings panel for Disable Thinking, HyDE, CRAG, Decomposition. Settings API endpoints. |

### Minor Changes / Fixes

| Commit | Description |
|---|---|
| `3635971` | Log all LLM parse failures to `DEBUG/parse_errors/failures.jsonl` |
| `4acbffd` | Consolidate all LLM calls to single Ollama port (11434) for KV cache consistency |
| `0e70459` | Break KV cache with timestamp nonce + explicit JSON format for SQL reminders |
| `b4b4ea8` | Disable Ollama thinking mode (`reasoning=False`) for faster Qwen3.5 inference |

---

## 3. SQL, Spreadsheet & Excel Skill

### Major Changes

| Commit | Description |
|---|---|
| `3e0afe9` | **Excel Skill** — Full feature: LLM-driven plan generation, data extraction (SQL + doc tables), NLP column interpretation, openpyxl assembly with charts/pivots. Backend pipeline + API + frontend modal. ~2300 new lines. |
| `e20e529` | **Dynamic token-budget SQL** — Replace hardcoded 16K char limit with dynamic budget calculation against 128K context. MapReduce for results exceeding budget. |
| `f8f6e96` | **Chunked NLP theme extraction** — Parse all rows, split into 3 chunks, extract themes in parallel, merge/deduplicate. For "What are the main themes?" on 2000-row datasets. |
| `99bb66a` | **LLM-based NLP intent classification** — LLM classifies whether query needs full-data NLP analysis (replaced brittle keyword matching). |

### Minor Changes / Fixes

| Commit | Description |
|---|---|
| `ca1257d` | Move NLP intent classification from main generate to decomposition (simpler schema) |
| `17c1a1d` | Auto-route large outputs to Excel; sanitizer strips `<think>` tags; SQL loop breaker |
| `96b655d` | Stronger SQL-first prompt: action reordering, recency bias, answer restriction |
| `58cc24e` | Mandatory SQL-first for spreadsheet queries; remove auto-LIMIT |
| `5ecaf29` | Semantic analysis instead of SQL keyword matching (`LIKE '%bad%'`) for NLP |
| `5f28834` | NLP columns returning N/A — send full row data (all columns) to LLM |
| `78fb981` | Fix zero-row Excel exports; add file history; SQLite reload before extraction |
| `e5c7d82` | Fix Excel builder table name errors and NLP columns returning blank |
| `87df328` | Fix Excel export and SQL routing regressions |
| `e96d3d9` | Excel downloads in decomposed queries + Shift+Enter multiline input |
| `9afbd98` | Pass prior SQL query to Excel planner to preserve filter in proactive exports |
| `ebdee81` | Include executed SQL query in prompt context for port failover |
| `53d2a2b` | Reduce context overload for NLP theme queries |
| `727ecd1` | Remove 500-row cap for NLP extraction, use dynamic chunking |

---

## 4. Agent Pipeline & Query-Time VLM

### Major Changes

| Commit | Description |
|---|---|
| `a3d3366` | **Query-time VLM** — Detect visual references ("page 3", "the flowchart"), render source page, send to VLM with user's question. Persist converted PDFs for PPTX/DOCX. |
| `4c7c46f` | **Multi-page VLM** — For all queries (not just visual references), send top-scoring pages (rerank >= 0.8, max 5) to VLM concurrently. |
| `06d7401` | VLM prompt rewrite: answer the question directly instead of describing the image |

### Minor Changes / Fixes

| Commit | Description |
|---|---|
| `2140c16` | Demote VLM from "core of response" to "additional context alongside chunks" |
| `930b7e3` | Route large embedded images (>400px, >25% page area) to Mermaid VLM |
| `16c27cf` | Switch VLM from `/api/generate` to `/api/chat` (fixes empty responses) |
| `afa1c4d` | Fix PPTX VLM path, increase chunk sizes (parent 1500, child 500), page-level dedup |
| `0308213` + `f12fa6c` | Reverts of VLM demotion/figure-number fixes (reinstated later) |
| `0b90fce` | Stop confusing figure/table numbers with page numbers in VLM |

---

## 5. GLM-OCR Integration

### Major Changes

| Commit | Description |
|---|---|
| `6eafc89` | **Initial GLM-OCR integration** — 0.9B vision model alongside existing OCR. Concurrent processing with semaphore. All 5 document types. Additive output (never replaces). |
| `a4494fc` | **Migrate to ZAI-ORG SDK Server** — Dual-service architecture: PP-DocLayout-V3 layout detection + vLLM model serving. Port 5002. Fourth and final backend migration. |

### Minor Changes / Fixes

| Commit | Description |
|---|---|
| `5fbcbec` | Switch from `/api/generate` to `/api/chat` (image token handling) |
| `eff554f` | Rewrite per official guide + add Modelfile for 32K context / 8K output |
| `4f707cf` | Add `max_length=512` to cross-encoder (prevent tensor mismatch on GLM-OCR Markdown) |
| `5121200` | Migrate from Ollama to vLLM OpenAI-compatible endpoint |
| `82046c9` | Add GLM-OCR config YAML reference for deployment |
| `1960d36` | Fix Docling per-page export, mermaid dedup, GLM-OCR response handling |
| `11469e7` | Change GLM-OCR SDK default port from 11434 to 5002 |
| `97a7ff8` | Update tmp_glm_ocr submodule |

---

## 6. VLM & Document Parsing

### Major Changes

| Commit | Description |
|---|---|
| `ca71842` | **Unified PDF pipeline** — DOC/DOCX/PPTX all convert to PDF and reuse the PDF handler. Eliminates ~530 lines of duplicated code. Adds table-specific VLM prompt. |
| `f0b1c44` | **VLM on every page by default** — Remove heuristic detection, always run VLM, additive merge (never replaces PyMuPDF text). |
| `0efc416` | **Dynamic diagram cropping** — Detect vector drawings, group into bounding boxes, crop to images, send to VLM for Mermaid transcription. |
| `632dd44` | **Large PPT handling** — Single LibreOffice conversion (was 3), batched rendering (10 pages), scaled timeouts, VRAM safety caps. |

### Minor Changes / Fixes

| Commit | Description |
|---|---|
| `95d0443` | Move VLM to PORT2 (11435) — separate from query LLM to avoid contention |
| `a224dbd` | Prevent CUDA OOM on oversized images, handle palette/WMF formats |
| `6f7f722` | On-demand summary generation, DOCX Docling+VLM support, remove OCR-source markers |
| `091872b` | Revert VLM timeout to 240s, add image resizing (max 1280px), remove broken relevance threshold |
| `7bde071` | Handle LibreOffice crash-after-write (check file existence, not exit code) |
| `6bb6edb` | Add `torch.cuda.empty_cache()` after GPU ops |

---

## 7. Docling Integration

| Commit | Description |
|---|---|
| `b1c2bab` | **Implement Docling for PDFs** — IBM's structural PDF parser. Per-document markdown extraction. Conditional import for graceful degradation. |
| `17994bd` | Fix: prevent VLM from overwriting Docling output on page 0 |
| `7501c0e` | Documentation update for Docling |
| `1960d36` | Fix: per-page Docling export (was dumping all text on page 0) |

---

## 8. Document Creator

### Major Changes

| Commit | Description |
|---|---|
| `28a64f5` | **Full document creator** — Outline-first pipeline, section-by-section LLM generation, version history, multi-format export (PPTX/DOCX/PDF), async background tasks + polling, frontend 4-view wizard. ~5700 new lines. |
| `6eb9486` | **My Documents view** — List/delete/resume documents, inline section editing. |

### Minor Changes / Fixes

| Commit | Description |
|---|---|
| `84ab591` | Fix infinite polling loop (frontend type mismatches with backend responses) |
| `0570ddb` | Switch PDF export to client-side pdfmake (bypasses fpdf2 crashes) |
| `cd730c1` | Switch PDF assembler to DejaVuSans Unicode font |
| `f9fe480` | Sanitize Unicode text in PDF assembler |
| `c337602` | Fix scroll clipping in document creator views |
| `792616e` | Handle transitive diagram bounding box merges |

---

## 9. Studio Features & Export

| Commit | Description |
|---|---|
| `7a394a2` | Strategic Analysis + Technical Analysis features (new routes, schemas, prompts, frontend modals) |
| `52130f1` | Enhance PDF/PPT exports with themed styling and landscape PPT layout |
| `e5ebd8c` | Per-document deletion + LLM output parsing fixes |
| `0a7187f` | Export auth fix, insights crash fix, document list overflow |
| `47f1372` | Add strategic/technical analysis routes to auth_paths (security fix) |
| `34c6aae` | Normalize escaped newlines in ALL LLM string fields (not just answer) |
| `3fbe2b3` | Fix duplicate backend calls during studio artifact generation |
| `1d399d1` | Remove suggested follow-up questions feature |

---

## 10. Testing & Infrastructure

| Commit | Description |
|---|---|
| `0b16047` | **Full testing suite** — 51 files, 5015 lines. Unit + integration + E2E. mongomock, conftest fixtures, 75% coverage threshold. |
| `2342c07` | **11 bug fixes from static review** — Socket.IO auth, sigmoid overflow, BM25-Chroma sync, VLM semaphore timeout, WAL journal, chat pagination, error responses, O(n^2) fix. |
| `affae85` | **Performance optimization (Phase 1-3)** — GPU OCR, FP16 cross-encoder, LLM client caching, Ollama env setup. |
| `55ad8c1` | Cross-thread document import (skip OCR re-processing) |
| `d31811c` | Structured generation status handling with JSON files |
| `bd2af3b` | Add CLAUDE.md |
| `0b333fd` | Refactor imports across all modules |
| `affae85` | Dual-instance Ollama systemd setup for Ubuntu |

---

## 11. Bug Fixes & Stability

| Commit | Description |
|---|---|
| `c52e1d3` | Guard BM25 index creation against empty chunk data (ZeroDivisionError) |
| `ebacf11` | Fix Regenerate button disabled (loading state not reset) |
| `f9807b3` | Pin torch to CUDA 12.4 compatible version |
| `9c66da0` | Correct spreadsheet detection and cross-thread doc import paths |
| `34f19e7` | Improve figure retrieval via caption stitching and relaxed VLM threshold |
| `262d8dd` | Correct JSON keys in reindex.py to match Document model |
| `678e87b` | Re-enable GPU server (Ollama) and disable cloud fallbacks |
| `859b110` | Merge: document-delete-and-parsing-fixes |
| Multiple | Reverts and re-applies of parsing fixes (GLM-OCR, mermaid dedup, Docling) |
