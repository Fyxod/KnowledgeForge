# AGENTS.md

This file provides implementation context and working guidance for any LLM agent operating in this repository.

## Project Overview

Multi-Modal Enterprise Knowledge Synthesis Platform: a document analysis system that ingests multi-format files (PDF, Excel, PPTX, images), indexes them in a vector store (ChromaDB), and answers queries via a LangGraph agent with LLM fallback chains (local Ollama -> Gemini -> OpenAI).

## Architecture

Backend (Python/FastAPI on port 8000):
- `app/` - FastAPI application. `app/main.py` creates the ASGI app wrapping Socket.IO (`socketio.ASGIApp`). Routes live in `app/routes/`. Auth middleware in `app/middlewares/`.
- `agent/` - LangGraph state graph. `builder.py` compiles the graph; `state.py` defines `AgentState` (Pydantic model); `graph_nodes.py` has node functions.
- `core/` - Shared business logic:
  - `core/config.py` - `Settings` (pydantic-settings) loaded from `.env`
  - `core/constants.py` - Feature switches (`SWITCHES` dict), model configs (`GPULLMConfig`), chunk counts, graph node names
  - `core/llm/client.py` - `invoke_llm()`: unified structured LLM call with retry + fallback (GPU -> Gemini -> OpenAI). Uses `PydanticOutputParser` + JSON sanitization.
  - `core/embeddings/` - Embedding functions (nomic-embed-text-v1.5), ChromaDB vector store, hybrid retriever (BM25 + vector + RRF)
  - `core/parsers/` - Document parsing (PDF via PyMuPDF, Excel via openpyxl, PPTX, images via EasyOCR/Tesseract, VLM via qwen3.5:9b, GLM-OCR)
  - `core/services/` - SQLite manager (spreadsheet -> SQL for query), file upload handling, entity triple store
  - `core/studio_features/` - Mind maps, summarization, word clouds, strategic/technical roadmaps, insights
  - `core/utils/` - Helpers: bcrypt, token counting, LLM output sanitization, generation status tracking
  - `core/database.py` - MongoDB connection + schema validation (pymongo/mongomock)

Frontend (React/TypeScript/Vite on port 8080):
- Located in `frontend/`. Uses shadcn/ui (Radix), TailwindCSS, React Router, Socket.IO client, ReactFlow, Recharts.
- `frontend/src/lib/api.ts` - All REST + Socket.IO client types and functions.
- `frontend/config.ts` - `API_URL`, `PROJECT_NAME`, `SIM_PAGE_ENABLED`.

Communication: REST API + Socket.IO for real-time streaming.

## Agent Graph Flow

The LangGraph agent (`agent/builder.py`) orchestrates query processing:

```
RETRIEVER -> EVALUATOR (CRAG)
                |- sufficient/ambiguous -> GENERATE
                \- insufficient -> RETRIEVER (re-retrieve, max 2 attempts)

GENERATE -> main_router
    |- ANSWER -> END
    |- WEB_SEARCH -> GENERATE (loop, max 2)
    |- SQL_QUERY -> GENERATE (loop, max 6 retries)
    |- DOCUMENT_SUMMARIZER -> summary_router -> {END, GENERATE, SELF_KNOWLEDGE}
    |- GLOBAL_SUMMARIZER -> summary_router -> {END, GENERATE, SELF_KNOWLEDGE}
    |- EXCEL_CREATE -> END
    \- FAILURE -> SELF_KNOWLEDGE -> END
```

Key retrieval capabilities:
- CRAG corrective retrieval: evaluator judges chunk sufficiency, re-retrieves with expanded queries if insufficient
- Decomposition: complex queries split into sub-queries for parallel retrieval
- HyDE: hypothetical document embeddings for better retrieval (adds latency, off by default)
- Entity triple injection: relationship triples from triple store enriched into context

## Data Directory Layout

```
data/{user_id}/
  |- threads/{thread_id}/
  |   |- uploads/            # Original uploaded files
  |   |- parsed/             # Per-document summaries (JSON)
  |   |- mind_maps/          # Generated mind maps (JSON)
  |   \- global_summary.json
  |- bm25/{thread_id}.pkl    # BM25 index (pickled)
  \- triples/{thread_id}.db  # Entity triple store (SQLite)
```

## Development Commands

### Backend (run from repo root)

```bash
# Local dev server (no Docker)
python backend.py                  # Starts uvicorn on port 8000

# Frontend dev server
python frontend.py                 # Runs npm install + npm run dev in frontend/

# Docker
make build                         # Build image + pull mongo + install ollama + set models
make run                           # docker compose up (attached)
make run-silent                    # docker compose up -d (detached)
make ollama                        # Start two Ollama instances on ports 11434/11435
make ollama-stop                   # Kill all Ollama instances
```

### Frontend

```bash
cd frontend && npm run dev         # Dev server
cd frontend && npm run build       # Production build
cd frontend && npm run lint        # ESLint
```

### Testing (uses Makefile.test)

```bash
make -f Makefile.test test          # All tests with coverage
make -f Makefile.test test-unit     # Unit tests only (marker: @pytest.mark.unit)
make -f Makefile.test test-int      # Integration tests only (marker: @pytest.mark.integration)
make -f Makefile.test test-e2e      # E2E tests only (marker: @pytest.mark.e2e)
make -f Makefile.test test-fast     # Parallel run (pytest-xdist)
make -f Makefile.test lint          # ruff check app/ core/ agent/ tests/

# Run a single test file
python -m pytest tests/unit/test_config.py -v

# Run a single test function
python -m pytest tests/unit/test_config.py::test_function_name -v

# Install test dependencies
pip install -r requirements-test.txt
```

Coverage threshold: 75% (configured in `pyproject.toml`). Coverage source: `app/`, `core/`, `agent/`.

### Pytest Configuration

- `pytest.ini`: test paths = `tests/`, async mode = auto, strict markers enabled
- Markers: `unit`, `integration`, `e2e`, `slow`
- Tests use mongomock (not real MongoDB). See `tests/conftest.py` for shared fixtures (`patched_db`, `async_client`, `auth_headers`, `mock_invoke_llm`, etc.)
- Environment variables are set in `conftest.py` before any app imports; no `.env` file is required for tests
- `patched_db` patches `core.database.db` AND every route/module that directly imports `db`; when adding a new route that imports `db`, add its patch target to the `_targets` list in `conftest.py`

## Key Patterns

- LLM invocation: always use `invoke_llm()` from `core/llm/client.py`. It handles retries, fallback chains, and JSON parsing/sanitization. Pass a Pydantic schema as `response_schema` for structured output.
- Feature switches: `core/constants.py` `SWITCHES` dict controls behavior. Current switches: `MIND_MAP`, `SUMMARIZATION`, `DECOMPOSITION`, `CORRECTIVE_RETRIEVAL`, `HYDE`, `FALLBACK_TO_GEMINI`, `FALLBACK_TO_OPENAI`, `REMOTE_GPU`, `DOCUMENT_CREATOR`, `GLM_OCR`, `EXCEL_SKILL`, `DOC_BATCH_REDUCER`, `USE_VLM_FOR_ANSWER`, `DISABLE_THINKING`.
- Database access: `from core.database import db`. In tests, use the `patched_db` fixture which mocks `db` across all modules that import it.
- Agent state: the LangGraph agent uses `AgentState` (Pydantic BaseModel in `agent/state.py`). Add new fields there when extending agent capabilities.
- Structured outputs: LLM output schemas live in `core/llm/output_schemas/`. Prompts in `core/llm/prompts/`.
- API route pattern: routes get the authenticated user from `request.state.user` (set by JWT middleware). Protected routes are listed in `app/middlewares/auth_paths.py`.
- Parse failure logging: LLM parse failures are logged to `DEBUG/parse_errors/failures.jsonl` for debugging structured output issues.
- Gemini key round-robin: `API_KEY_1` to `API_KEY_6` are cycled via `itertools.cycle` in the fallback path to avoid rate limits.

## Docker Deployment

Multi-stage Dockerfile: stage 1 builds the frontend (Node), stage 2 runs the Python backend with system dependencies (Tesseract, Pandoc, Poppler, Nginx, fonts, NLTK).

- Entrypoint (`docker-entrypoint.sh`): starts gunicorn (port 8000) + nginx (port 8080)
- Nginx (`nginx/default.conf`): serves React SPA on 8080, proxies `/api/*` to backend on 8000
- Ports: 8080 (frontend), 8000 (backend API), 11434/11435 (Ollama), 27017 (MongoDB)
- Volumes: `./data:/backend/data` persists uploaded files and indexes

## Environment Setup

Copy `.env.example` to `.env` and fill in API keys. Required variables: `DATABASE_URL`, `SECRET_KEY`, `API_KEY_1` to `API_KEY_6` (Gemini keys for round-robin), `OPENAI_API`, `QUERY_URL`, `VISION_URL`, `MAIN_MODEL`. Python >= 3.11.8.

Key env vars:
- `REMOTE_GPU`: `True` to use HTTP-based remote LLM, `False` for local Ollama (ChatOllama)
- `USE_VISION_MODEL`: `True` to run VLM on document pages during parsing
- `TAVILY_API_KEY`: required for web search fallback
- `QUERY_URL` / `VISION_URL`: Ollama endpoints (default ports 11434 / 11435)