# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-Modal Enterprise Knowledge Synthesis Platform — a document analysis system that ingests multi-format files (PDF, Excel, PPTX, images), indexes them in a vector store (ChromaDB), and answers queries via a LangGraph agent with LLM fallback chains (local Ollama → Gemini → OpenAI).

## Architecture

**Backend** (Python/FastAPI on port 8000):
- `app/` — FastAPI application. `app/main.py` creates the ASGI app wrapping Socket.IO (`socketio.ASGIApp`). Routes live in `app/routes/`. Auth middleware in `app/middlewares/`.
- `agent/` — LangGraph state graph. `builder.py` compiles the graph; `state.py` defines `AgentState` (Pydantic model); `graph_nodes.py` has node functions. Flow: Retriever → Generate → Router → (Answer | WebSearch | Summarizer | SQLQuery | SelfKnowledge).
- `core/` — Shared business logic:
  - `core/config.py` — `Settings` (pydantic-settings) loaded from `.env`
  - `core/constants.py` — Feature switches (`SWITCHES` dict), model configs (`GPULLMConfig`), chunk counts, graph node names
  - `core/llm/client.py` — `invoke_llm()`: unified structured LLM call with retry + fallback (GPU → Gemini → OpenAI). Uses `PydanticOutputParser` + JSON sanitization.
  - `core/embeddings/` — Embedding functions, vector store (ChromaDB), retriever
  - `core/parsers/` — Document parsing (PDF via PyMuPDF, Excel via openpyxl, PPTX, images via EasyOCR/Tesseract)
  - `core/services/` — SQLite manager (for spreadsheet SQL queries), file upload handling
  - `core/studio_features/` — Higher-level analysis: mind maps, summarization, word clouds, strategic/technical roadmaps, insights
  - `core/utils/` — Helpers: bcrypt, token counting, LLM output sanitization, generation status tracking
  - `core/database.py` — MongoDB connection + schema validation (pymongo/mongomock)

**Frontend** (React/TypeScript/Vite on port 8080):
- Located in `frontend/`. Uses shadcn/ui (Radix), TailwindCSS, React Router, Socket.IO client, ReactFlow, Recharts.
- Dev server: `cd frontend && npm run dev`
- Build: `cd frontend && npm run build`
- Lint: `cd frontend && npm run lint`

**Communication**: REST API + Socket.IO for real-time streaming.

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
- Environment variables are set in `conftest.py` before any app imports — no `.env` file needed for tests

## Key Patterns

- **LLM invocation**: Always use `invoke_llm()` from `core/llm/client.py`. It handles retries, fallback chains, and JSON parsing/sanitization. Pass a Pydantic schema as `response_schema` for structured output.
- **Feature switches**: `core/constants.py` `SWITCHES` dict controls behavior (decomposition, fallbacks, mind maps, summarization, remote GPU). Check switches before adding conditional features.
- **Database access**: `from core.database import db`. In tests, use the `patched_db` fixture which mocks `db` across all modules that import it.
- **Agent state**: The LangGraph agent uses `AgentState` (Pydantic BaseModel in `agent/state.py`). Add new fields there when extending agent capabilities.
- **Structured outputs**: LLM output schemas live in `core/llm/output_schemas/`. Prompts in `core/llm/prompts/`.

## Environment Setup

Copy `.env.example` to `.env` and fill in API keys. Required variables: `DATABASE_URL`, `SECRET_KEY`, `API_KEY_1`–`API_KEY_6` (Gemini keys for round-robin), `OPENAI_API`, `QUERY_URL`, `VISION_URL`, `MAIN_MODEL`. Python ≥ 3.11.8.
