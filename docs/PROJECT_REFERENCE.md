# PRISM — Multi-Modal Enterprise Knowledge Synthesis Platform

## Complete Project Reference

> **Purpose of this document:** A comprehensive, self-contained reference that enables any LLM or developer to fully understand the project's purpose, architecture, codebase structure, data flows, features, technologies, and conventions — without needing to read the source code.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Why This Project Exists](#2-why-this-project-exists)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Repository Structure](#5-repository-structure)
6. [Backend — FastAPI Application (`app/`)](#6-backend--fastapi-application-app)
7. [LangGraph Agent System (`agent/`)](#7-langgraph-agent-system-agent)
8. [Core Business Logic (`core/`)](#8-core-business-logic-core)
9. [Frontend — React Application (`frontend/`)](#9-frontend--react-application-frontend)
10. [Data Flow & Pipelines](#10-data-flow--pipelines)
11. [LLM Integration & Fallback Strategy](#11-llm-integration--fallback-strategy)
12. [Document Parsing Pipeline](#12-document-parsing-pipeline)
13. [Embedding & Retrieval System](#13-embedding--retrieval-system)
14. [Studio Features (Analysis & Generation)](#14-studio-features-analysis--generation)
15. [Real-Time Communication (Socket.IO)](#15-real-time-communication-socketio)
16. [Database Schema (MongoDB)](#16-database-schema-mongodb)
17. [Authentication & Security](#17-authentication--security)
18. [API Reference](#18-api-reference)
19. [Configuration & Feature Switches](#19-configuration--feature-switches)
20. [Testing](#20-testing)
21. [Deployment & Docker](#21-deployment--docker)
22. [Key Design Patterns](#22-key-design-patterns)
23. [File-by-File Reference](#23-file-by-file-reference)

---

## 1. Project Overview

**PRISM** (Multi-Modal Enterprise Knowledge Synthesis Platform) is a full-stack document analysis and knowledge management system. Users upload multi-format documents (PDF, Excel, PowerPoint, Word, images, CSV, Markdown), and the system:

1. **Parses** them using format-specific extractors with OCR and optional Vision Language Model (VLM) support
2. **Indexes** the content in a vector store (ChromaDB) with hybrid search (dense + BM25)
3. **Summarizes** each document and generates a cross-document global summary
4. **Generates** mind maps, word clouds, strategic roadmaps, technical roadmaps, strategic analysis, technical analysis, and insights — all powered by LLM
5. **Answers questions** via a LangGraph stateful agent that performs retrieval-augmented generation (RAG) with query decomposition, web search fallback, SQL queries against spreadsheet data, self-knowledge fallback, and multi-document cross-referencing
6. **Streams** all long-running operations in real-time via Socket.IO
7. **Exports** chat histories as Markdown or HTML, and analysis results as PDF or PPTX

The platform is designed for enterprise knowledge workers who need to analyze, compare, and extract insights from large collections of heterogeneous documents.

---

## 2. Why This Project Exists

### Problem Statement

Enterprise teams deal with diverse document formats scattered across systems. Extracting actionable insights requires:

- Reading hundreds of pages across PDFs, spreadsheets, presentations, and reports
- Cross-referencing information across documents
- Performing data analysis on spreadsheet content
- Generating strategic and technical assessments
- Maintaining context across conversations

### Solution

PRISM provides a unified platform that:

- **Eliminates format barriers** — Any document type is parsed, chunked, and indexed uniformly
- **Enables conversational analysis** — Users ask natural-language questions and get grounded, citation-backed answers
- **Automates knowledge synthesis** — Summaries, mind maps, roadmaps, and analyses are generated automatically
- **Supports data-driven queries** — Spreadsheet data is queryable via natural language (translated to SQL by the LLM)
- **Scales from local to cloud** — Runs on a local GPU with Ollama or falls back to Gemini/OpenAI APIs

---

## 3. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                       │
│  React 18 · TypeScript · TailwindCSS · shadcn/ui · ReactFlow        │
│  Port 8080 (nginx in Docker, Vite dev server locally)                │
└────────────────────┬─────────────────────────────────────────────────┘
                     │  REST API + Socket.IO (WebSocket)
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI + Socket.IO)                    │
│  Python 3.11+ · FastAPI · python-socketio · uvicorn                  │
│  Port 8000                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  API Routes   │  │  Middleware   │  │   Socket.IO Handler      │   │
│  │  (13 routers) │  │  (JWT Auth)  │  │   (real-time streaming)  │   │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────┘   │
│         │                                                            │
│  ┌──────▼────────────────────────────────────────────────────────┐   │
│  │                    CORE BUSINESS LOGIC                         │   │
│  │  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────────────┐   │   │
│  │  │ Parsers │ │Embeddings│ │  LLM      │ │ Studio Features│   │   │
│  │  │ (6 fmt) │ │& Vector  │ │  Client   │ │ (8 features)   │   │   │
│  │  └─────────┘ │  Store   │ │ +Fallback │ └────────────────┘   │   │
│  │              └──────────┘ └───────────┘                       │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                 LANGGRAPH AGENT                                │   │
│  │  Retriever → Generate → Router → {Answer|WebSearch|SQL|       │   │
│  │                                    Summarizer|SelfKnowledge}  │   │
│  │  + Query Decomposition + Answer Combination                   │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌───────────────────────┐
│   MongoDB    │   │   ChromaDB   │   │      Ollama (GPU)     │
│  (user data, │   │  (vectors,   │   │  Port 11434 + 11435   │
│   threads,   │   │   embeddings)│   │  ┌─────────────────┐  │
│   chats)     │   │              │   │  │ Main Model      │  │
└──────────────┘   └──────────────┘   │  │ (qwen3/gpt-oss) │  │
                                      │  ├─────────────────┤  │
                                      │  │ VLM Model       │  │
                                      │  │ (qwen3-vl:8b)   │  │
                                      │  ├─────────────────┤  │
                                      │  │ Image Parser    │  │
                                      │  │ (gemma3:12b)    │  │
                                      │  └─────────────────┘  │
                                      └───────────────────────┘
                                               │ fallback
                                      ┌────────▼────────┐
                                      │  Gemini API     │
                                      │  (6 keys,       │
                                      │   round-robin)  │
                                      ├─────────────────┤
                                      │  OpenAI API     │
                                      │  (gpt-4o-mini)  │
                                      └─────────────────┘
```

---

## 4. Technology Stack

### Backend

| Category            | Technology                                     | Purpose                                      |
| ------------------- | ---------------------------------------------- | -------------------------------------------- |
| **Web Framework**   | FastAPI                                        | REST API with async support                  |
| **ASGI Server**     | Uvicorn                                        | Production ASGI server                       |
| **Real-Time**       | python-socketio                                | WebSocket communication                      |
| **Agent Framework** | LangGraph                                      | Stateful agent orchestration                 |
| **LLM Framework**   | LangChain                                      | LLM abstraction, output parsing              |
| **Vector Store**    | ChromaDB                                       | Embedding storage and similarity search      |
| **Embeddings**      | HuggingFace (`nomic-ai/nomic-embed-text-v1.5`) | Document and query embeddings                |
| **Re-ranking**      | CrossEncoder (`ms-marco-MiniLM-L-6-v2`)        | Cross-encoder re-ranking                     |
| **Database**        | MongoDB (pymongo)                              | User data, threads, chats, metadata          |
| **In-Memory DB**    | SQLite (per-user)                              | Spreadsheet data for SQL queries             |
| **Local LLM**       | Ollama (ChatOllama)                            | Self-hosted GPU inference                    |
| **Cloud LLM**       | Google Gemini API, OpenAI API                  | Fallback LLM providers                       |
| **OCR**             | EasyOCR + Tesseract                            | Image text extraction                        |
| **VLM**             | Ollama VLM (qwen3-vl:8b)                       | Vision-Language extraction for complex pages |
| **PDF Parsing**     | PyMuPDF (fitz)                                 | PDF text/table/image extraction              |
| **Excel**           | openpyxl + pandas                              | Spreadsheet parsing with metadata            |
| **PowerPoint**      | python-pptx                                    | Slide content extraction                     |
| **Word**            | python-docx                                    | Document content extraction                  |
| **Web Search**      | Tavily API                                     | External information retrieval               |
| **Token Counting**  | tiktoken                                       | Context window management                    |
| **Visualization**   | matplotlib, wordcloud                          | Word cloud generation                        |
| **NLP**             | NLTK                                           | Sentence tokenization, stop words            |
| **Auth**            | PyJWT + bcrypt                                 | JWT tokens + password hashing                |
| **Settings**        | pydantic-settings                              | Type-safe configuration from .env            |

### Frontend

| Category          | Technology                        | Purpose                       |
| ----------------- | --------------------------------- | ----------------------------- |
| **Framework**     | React 18                          | UI framework                  |
| **Language**      | TypeScript                        | Type-safe JavaScript          |
| **Build Tool**    | Vite                              | Fast development & build      |
| **Styling**       | TailwindCSS + tailwindcss-animate | Utility-first CSS             |
| **UI Components** | shadcn/ui (25+ Radix primitives)  | Accessible component library  |
| **Routing**       | React Router v6                   | Client-side routing           |
| **State**         | TanStack React Query              | Server state management       |
| **Forms**         | React Hook Form + Zod             | Form validation               |
| **Real-Time**     | socket.io-client                  | WebSocket client              |
| **Graphs**        | ReactFlow                         | Mind map / flow visualization |
| **Charts**        | Recharts                          | Data visualization charts     |
| **Markdown**      | react-markdown + rehype + remark  | Rich markdown rendering       |
| **Export**        | pdfmake, pptxgenjs                | PDF and PPTX generation       |
| **Theming**       | next-themes                       | Dark/light mode               |

### Infrastructure

| Category             | Technology                          | Purpose                       |
| -------------------- | ----------------------------------- | ----------------------------- |
| **Containerization** | Docker + docker-compose             | Deployment                    |
| **Reverse Proxy**    | nginx                               | Frontend serving + API proxy  |
| **GPU Inference**    | Ollama (2 instances)                | Parallel model serving        |
| **Process Manager**  | docker-entrypoint.sh                | Startup orchestration         |
| **Testing**          | pytest + pytest-asyncio + mongomock | Unit/integration/E2E tests    |
| **Linting**          | ruff                                | Python linting                |
| **Coverage**         | pytest-cov                          | Code coverage (75% threshold) |

---

## 5. Repository Structure

```
backend/
├── app/                          # FastAPI application layer
│   ├── main.py                   # App factory: FastAPI + Socket.IO + middleware + routers
│   ├── socket_handler.py         # Socket.IO server setup + heartbeat
│   ├── middlewares/
│   │   ├── auth.py               # JWT authentication middleware
│   │   └── auth_paths.py         # Protected route prefix list
│   └── routes/
│       ├── query.py              # POST /query/ — Main RAG Q&A pipeline
│       ├── upload.py             # POST /upload/ — File upload + parsing + indexing
│       ├── user.py               # User CRUD + auth (register, login, profile)
│       ├── thread.py             # Thread CRUD + documents + chats + instructions
│       ├── documents.py          # GET /data/... — Serve uploaded files
│       ├── health.py             # GET /health/ — Liveness probe
│       ├── export.py             # GET /export/ — Chat export (MD/HTML)
│       ├── extra.py              # Word cloud, mind map, summaries
│       ├── insights.py           # Insights generation
│       ├── strategic_roadmap.py  # Strategic roadmap generation
│       ├── technical_roadmap.py  # Technical roadmap generation
│       ├── strategic_analysis.py # Strategic analysis generation
│       └── technical_analysis.py # Technical analysis generation
│
├── agent/                        # LangGraph agent system
│   ├── builder.py                # State graph definition + compilation
│   ├── state.py                  # AgentState Pydantic model (all agent state fields)
│   ├── graph_nodes.py            # Node functions: retriever, generate, router, web_search, etc.
│   ├── graph_helpers.py          # Prompt builders + utility functions
│   ├── decomposition.py          # Query decomposition into sub-queries
│   ├── combination.py            # Sub-answer combination into final answer
│   └── tools/
│       ├── search.py             # Tavily web search wrapper
│       └── sql_query.py          # SQLite spreadsheet query bridge
│
├── core/                         # Shared business logic
│   ├── config.py                 # Settings (pydantic-settings from .env)
│   ├── constants.py              # Feature switches, model configs, graph node names
│   ├── database.py               # MongoDB connection + schema validation
│   │
│   ├── embeddings/
│   │   ├── embeddings.py         # HuggingFace embedding function (nomic-embed-text-v1.5)
│   │   ├── vectorstore.py        # ChromaDB CRUD, chunking, BM25, hybrid search
│   │   └── retriever.py          # Retrieval, RRF fusion, cross-encoder re-ranking, MMR
│   │
│   ├── llm/
│   │   ├── client.py             # Unified invoke_llm() with retry + fallback chain
│   │   ├── outputs.py            # Re-exports all Pydantic output schemas
│   │   ├── configurations/
│   │   │   ├── local_llm.py      # Ollama LLM wrapper (ChatOllama + semaphore)
│   │   │   └── remote_llm.py     # Remote GPU HTTP LLM wrapper
│   │   ├── output_schemas/       # 9 Pydantic models for structured LLM outputs
│   │   │   ├── base.py
│   │   │   ├── main_outputs.py
│   │   │   ├── mindmap_outputs.py
│   │   │   ├── summarizer_outputs.py
│   │   │   ├── insights_outputs.py
│   │   │   ├── strategic_analysis_outputs.py
│   │   │   ├── strategic_roadmap_outputs.py
│   │   │   ├── technical_analysis_outputs.py
│   │   │   └── technical_roadmap_outputs.py
│   │   └── prompts/              # 11 prompt templates
│   │       ├── main_prompt.py
│   │       ├── self_knowledge_prompt.py
│   │       ├── decomposition_prompt.py
│   │       ├── combination_prompt.py
│   │       ├── summarizer_prompt.py
│   │       ├── insights_prompt.py
│   │       ├── strategic_analysis_prompt.py
│   │       ├── strategic_roadmap_prompt.py
│   │       ├── technical_analysis_prompt.py
│   │       ├── technical_roadmap_prompt.py
│   │       └── thread_context.py
│   │
│   ├── models/                   # Pydantic data models
│   │   ├── document.py           # Page, Document, Documents
│   │   ├── user.py               # User, Thread, ChatMessage models
│   │   ├── thread.py             # Thread request/instruction models
│   │   └── gpu_config.py         # GPULLMConfig
│   │
│   ├── parsers/                  # Document format parsers
│   │   ├── main.py               # Central parser dispatcher (extract_document)
│   │   ├── excel_utils.py        # Header detection, merged cells, metadata enrichment
│   │   ├── process_files.py      # Batch file processing orchestrator
│   │   ├── image.py              # Dual-engine OCR (EasyOCR + Tesseract)
│   │   ├── vlm.py                # Vision Language Model extraction
│   │   ├── extensions.py         # File extension classification
│   │   └── slide_export.py       # Full-slide OCR export
│   │
│   ├── services/
│   │   ├── sqlite_manager.py     # Per-user SQLite for spreadsheet SQL queries
│   │   └── upload_files.py       # File upload handling
│   │
│   ├── studio_features/          # LLM-powered analysis features
│   │   ├── mind_map.py           # Mind map generation (2-phase: nodes + descriptions)
│   │   ├── summarizer.py         # Per-document + global summarization
│   │   ├── word_cloud.py         # Word cloud with LLM stop word extraction
│   │   ├── insights.py           # Document insights generation
│   │   ├── strategic_roadmap.py  # N-year strategic roadmap
│   │   ├── technical_roadmap.py  # N-year technical roadmap
│   │   ├── strategic_analysis.py # Strategic analysis (SWOT, positioning)
│   │   └── technical_analysis.py # Technical analysis
│   │
│   └── utils/
│       ├── bcrypt.py             # Password hashing (bcrypt)
│       ├── compress_data.py      # Token-budget document compression
│       ├── count_tokens.py       # tiktoken-based token counting
│       ├── extra_done_check.py   # Background task completion flag
│       ├── generation_status.py  # File-based async generation status protocol
│       ├── llm_output_sanitizer.py # Multi-stage JSON repair for LLM output
│       └── sanitize_schema.py    # JSON schema cleanup for LLM providers
│
├── frontend/                     # React/TypeScript frontend
│   ├── src/
│   │   ├── pages/                # 11 page components
│   │   ├── components/           # 15+ feature components + 45+ shadcn/ui primitives
│   │   ├── hooks/                # Custom React hooks
│   │   └── lib/                  # API client, auth, theme, export utilities
│   ├── package.json              # Dependencies
│   └── vite.config.ts            # Vite configuration
│
├── tests/
│   ├── conftest.py               # Root fixtures (mongomock, JWT, async client, mocks)
│   ├── unit/                     # 33 test files — isolated function tests
│   ├── integration/              # 11 test files — API route tests
│   └── e2e/                      # 1 test file — end-to-end user journey
│
├── data/                         # Runtime data directory
│   └── {user_id}/
│       └── threads/{thread_id}/
│           ├── uploads/          # Raw uploaded files
│           ├── parsed/           # Parsed document JSON
│           ├── mind_maps/        # Generated mind maps
│           └── global_summary.json
│
├── docker-compose.yml            # Docker Compose (app + MongoDB)
├── dockerfile                    # Multi-stage build (frontend + backend)
├── Makefile                      # Build + run + Ollama management
├── Makefile.test                 # Test runner
├── pyproject.toml                # Python project config + coverage settings
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Python dependencies
└── backend.py                    # Dev server entrypoint (uvicorn)
```

---

## 6. Backend — FastAPI Application (`app/`)

### 6.1 Application Factory (`app/main.py`)

The application is composed as:

1. **FastAPI** instance with CORS (allow all origins) and JWT auth middleware
2. **13 routers** mounted for different feature areas
3. **Socket.IO** wraps the FastAPI app as `socketio.ASGIApp(sio, other_asgi_app=fastapi_app)`

The final exported `app` object is the Socket.IO ASGI app that handles both HTTP and WebSocket connections.

### 6.2 Middleware

**Auth Middleware** (`app/middlewares/auth.py`):

- Starlette `BaseHTTPMiddleware` that intercepts requests
- Checks if request path matches any protected prefix (defined in `auth_paths.py`)
- Excluded routes: `POST /user` (register) and `POST /user/login`
- Extracts JWT from `Authorization: Bearer <token>` or `?token=` query param
- Decodes with HS256 using `settings.SECRET_KEY`
- Sets `request.state.user = UserJwtPayload(userId, name, email, is_active)`

**Protected prefixes:** `/user`, `/upload`, `/query`, `/thread`, `/extra`, `/mindmap`, `/wordcloud`, `/summary`, `/strategic_roadmap`, `/technical_roadmap`, `/insights`, `/strategic_analysis`, `/technical_analysis`, `/export`

### 6.3 Route Overview

| Router               | Prefix                | Key Endpoints                                      | Description                 |
| -------------------- | --------------------- | -------------------------------------------------- | --------------------------- |
| `query`              | `/query`              | `POST /`                                           | Main RAG question-answering |
| `upload`             | `/upload`             | `POST /`                                           | File upload + parse + index |
| `user`               | `/user`               | `POST /`, `POST /login`, `GET /{id}`               | Auth & user management      |
| `thread`             | `/thread`             | Full CRUD + docs + chats + instructions            | Thread management           |
| `documents`          | `/data`               | `GET /.../uploads/{file}`                          | Serve uploaded files        |
| `health`             | `/health`             | `GET /`                                            | Liveness probe              |
| `export`             | `/export`             | `GET /{id}/markdown`, `GET /{id}/html`             | Chat export                 |
| `extra`              | varies                | `POST /wordcloud`, `GET /mindmap`, `POST /summary` | Studio features             |
| `insights`           | `/insights`           | `POST /`, `POST /global`                           | Insights generation         |
| `strategic_roadmap`  | `/strategic_roadmap`  | `POST /`, `POST /global`                           | Strategic roadmaps          |
| `technical_roadmap`  | `/technical_roadmap`  | `POST /`, `POST /global`                           | Technical roadmaps          |
| `strategic_analysis` | `/strategic_analysis` | `POST /`, `POST /global`                           | Strategic analysis          |
| `technical_analysis` | `/technical_analysis` | `POST /`, `POST /global`                           | Technical analysis          |

---

## 7. LangGraph Agent System (`agent/`)

The agent is the core intelligence of the platform — a stateful graph built with LangGraph that orchestrates the RAG pipeline.

### 7.1 Agent State (`agent/state.py`)

`AgentState` is a Pydantic BaseModel containing all state passed between graph nodes:

| Field                                        | Type                  | Purpose                                             |
| -------------------------------------------- | --------------------- | --------------------------------------------------- |
| `user_id`, `thread_id`                       | str                   | User and thread identifiers                         |
| `query`, `resolved_query`, `original_query`  | str                   | Query text (original, resolved after decomposition) |
| `messages`                                   | List[BaseMessage]     | Conversation history (LangChain message format)     |
| `chunks`                                     | List[Dict]            | Retrieved document chunks                           |
| `web_search`                                 | bool                  | Whether web search was performed                    |
| `web_search_queries`, `web_search_results`   | List                  | Web search data                                     |
| `answer`                                     | str                   | Generated answer                                    |
| `chunks_used`                                | List[ChunksUsed]      | Citation references                                 |
| `confidence_score`                           | str                   | "high", "medium", or "low"                          |
| `suggested_questions`                        | List[str]             | Follow-up question suggestions                      |
| `action`                                     | Literal               | Agent's decided next action                         |
| `sql_query`, `sql_result`, `sql_attempts`    | various               | SQL query state                                     |
| `has_spreadsheet_data`, `spreadsheet_schema` | various               | Spreadsheet availability                            |
| `summary`                                    | str                   | Document summary context                            |
| `mode`                                       | "Internal"/"External" | Internal (docs only) or External (docs + web)       |
| `use_self_knowledge`                         | bool                  | Allow LLM to use its own knowledge                  |
| `thread_instructions`                        | List[str]             | User-defined per-thread instructions                |
| `llm`                                        | GPULLMConfig          | Which LLM model/port to use                         |

### 7.2 State Graph (`agent/builder.py`)

```
Entry Point: RETRIEVER
│
├── RETRIEVER ──────────────── GENERATE
│                                  │
│                          ┌───────┴──────────┐
│                          │   main_router()   │
│                          └───────┬──────────┘
│                                  │
├── action=ANSWER ─────────────── END
├── action=WEB_SEARCH ────────── WEB_SEARCH ──── GENERATE (loop)
├── action=SQL_QUERY ─────────── SQL_QUERY ───── GENERATE (loop)
├── action=DOCUMENT_SUMMARIZER ─ DOCUMENT_SUMMARIZER
│                                  │
│                          ┌───────┴──────────┐
│                          │ summary_router()  │
│                          └───────┬──────────┘
│                                  │
│   ├── after_summary=ANSWER ──── END
│   ├── after_summary=GENERATE ── GENERATE (loop)
│   └── FAILURE ──────────────── SELF_KNOWLEDGE ── END
│
├── action=GLOBAL_SUMMARIZER ─── GLOBAL_SUMMARIZER
│                                  │ (same summary_router as above)
│
└── action=FAILURE ──────────── SELF_KNOWLEDGE ──── END
```

### 7.3 Graph Nodes (`agent/graph_nodes.py`)

| Node                    | Function                | Purpose                                                                                                           |
| ----------------------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **retriever**           | `retriever()`           | Retrieves chunks from ChromaDB with adaptive scaling, re-ranks with cross-encoder + MMR diversity                 |
| **generate**            | `generate()`            | Builds prompt from state, calls `invoke_llm()` with mode-specific schema, retries up to 8 times                   |
| **main_router**         | `main_router()`         | Routes based on `state.action`: ANSWER, WEB_SEARCH, SQL_QUERY, DOCUMENT_SUMMARIZER, GLOBAL_SUMMARIZER, or FAILURE |
| **web_search**          | `web_search()`          | Executes parallel Tavily searches for multiple queries                                                            |
| **sql_query_node**      | `sql_query_node()`      | Executes LLM-generated SQL against SQLite spreadsheet data                                                        |
| **document_summarizer** | `document_summarizer()` | Retrieves pre-computed per-document summary from parsed JSON                                                      |
| **global_summarizer**   | `global_summarizer()`   | Retrieves pre-computed global summary                                                                             |
| **self_knowledge**      | `self_knowledge()`      | Fallback: LLM answers from its own knowledge when retrieval fails                                                 |
| **failure**             | `failure()`             | Returns a graceful failure message                                                                                |
| **summary_router**      | `summary_router()`      | After summarization: ends (if summary is the answer) or loops back to generate                                    |

### 7.4 Query Decomposition (`agent/decomposition.py`)

When `SWITCHES["DECOMPOSITION"]` is enabled:

1. Takes the user question + last 5 conversation turns
2. Includes spreadsheet schema context if available
3. Invokes LLM with `DecompositionLLMOutput` schema
4. Returns: `requires_decomposition` (bool), `resolved_query` (contextually resolved), `sub_queries` (list)

Decomposition serves dual purposes:

- **Query rewriting** — Resolves pronouns and context from chat history ("What about the other one?" → explicit reference)
- **Complex query splitting** — Breaks multi-part questions into independent sub-queries for parallel processing

### 7.5 Answer Combination (`agent/combination.py`)

After parallel sub-query execution, combines multiple sub-answers:

1. Takes all sub-answers + the resolved query + original query
2. Invokes LLM with `CombinationLLMOutput` schema
3. Returns a single coherent combined answer

### 7.6 Query Execution Flow (in `app/routes/query.py`)

The full pipeline as orchestrated by the query route:

1. **Auth + setup** — Validate user, load thread, collect instructions
2. **Spreadsheet loading** — Reload any Excel/CSV into SQLiteManager
3. **Decomposition** — If enabled, break query into sub-queries
4. **Parallel execution** — Sub-queries run through the agent graph in parallel using an `asyncio.Queue` with 2 GPU workers
5. **Combination** — Sub-answers merged into a single response
6. **Post-processing** — Compute confidence (min across sub-queries), deduplicate suggested questions (cap at 5)
7. **Persistence** — Save user + agent messages to MongoDB
8. **Response** — Return answer, sources, confidence, suggestions

For **External mode**, Tavily web search runs alongside document retrieval, and results include web source favicons.

---

## 8. Core Business Logic (`core/`)

### 8.1 Configuration (`core/config.py`)

`Settings` class using pydantic-settings, loaded from `.env`:

| Variable                        | Type | Purpose                                        |
| ------------------------------- | ---- | ---------------------------------------------- |
| `DATABASE_URL`                  | str  | MongoDB connection string                      |
| `SECRET_KEY`                    | str  | JWT signing key                                |
| `DATABASE_NAME`                 | str  | MongoDB database name (default: "bedrock")     |
| `MODE`                          | str  | "development" or "production"                  |
| `API_KEY_1` through `API_KEY_6` | str  | Gemini API keys (round-robin)                  |
| `OPENAI_API`                    | str  | OpenAI API key                                 |
| `QUERY_URL`                     | str  | Remote GPU LLM endpoint URL                    |
| `VISION_URL`                    | str  | Remote vision model endpoint URL               |
| `MAIN_MODEL`                    | str  | Ollama model name (e.g., "qwen3:14b-39500-8k") |
| `REMOTE_GPU`                    | bool | Use remote GPU instead of local Ollama         |
| `USE_VISION_MODEL`              | bool | Enable VLM for PDF/slide extraction            |
| `LOCAL_BASE_URL`                | str  | Ollama base URL (default: "http://localhost")  |

### 8.2 Feature Switches (`core/constants.py`)

The `SWITCHES` dictionary controls runtime behavior:

| Switch               | Default  | Purpose                                           |
| -------------------- | -------- | ------------------------------------------------- |
| `MIND_MAP`           | False    | Generate mind maps after document parsing         |
| `SUMMARIZATION`      | False    | Generate per-document + global summaries          |
| `FALLBACK_TO_GEMINI` | False    | Fallback to Gemini API if Ollama fails            |
| `FALLBACK_TO_OPENAI` | False    | Fallback to OpenAI if both Ollama and Gemini fail |
| `DECOMPOSITION`      | True     | Decompose complex queries + rewrite with context  |
| `REMOTE_GPU`         | from env | Use remote GPU LLMs instead of local Ollama       |

### 8.3 Constants & GPU Model Configs

```python
CHUNK_COUNT = 12             # Chunks per query
MIN_CHUNKS_PER_DOC = 10      # Min chunks per document in retrieval
MAX_TOTAL_CHUNKS = 50        # Max total chunks after retrieval
EASYOCR_WORKERS = 10         # Parallel OCR workers
TESSERACT_WORKERS = 50       # Parallel Tesseract workers
MAX_WEB_SEARCH = 2           # Max web search attempts
MAX_SQL_RETRIES = 6          # Max SQL query retries
PORT1 = 11434                # Ollama instance 1
PORT2 = 11435                # Ollama instance 2
```

**14 GPU LLM configurations** assign specific models and ports to different tasks (query, decomposition, combination, summarization, mind map, roadmaps, analysis, insights).

### 8.4 Database (`core/database.py`)

MongoDB with pymongo. Single collection `users` with JSON Schema validation.

Schema enforces: `userId`, `name`, `email`, `password`, `is_active`, `threads` (object of thread objects, each with `documents`, `chats`, `createdAt`, `updatedAt`, `extra_done`, `mindmap_enabled`, `instructions`).

See [Section 16](#16-database-schema-mongodb) for full schema detail.

---

## 9. Frontend — React Application (`frontend/`)

### 9.1 Pages

| Page Component      | Route                   | Purpose                               |
| ------------------- | ----------------------- | ------------------------------------- |
| `Landing.tsx`       | `/`                     | Marketing / landing page              |
| `Login.tsx`         | `/login`                | User login form                       |
| `Register.tsx`      | `/register`             | User registration form                |
| `Dashboard.tsx`     | `/dashboard`            | Main dashboard layout                 |
| `DashboardHome.tsx` | `/dashboard`            | Dashboard home / overview             |
| `NewThread.tsx`     | `/dashboard/new`        | Create new thread + upload files      |
| `ThreadView.tsx`    | `/dashboard/thread/:id` | Main chat interface + document viewer |
| `Profile.tsx`       | `/dashboard/profile`    | User profile settings                 |
| `SimHome.tsx`       | `/sim`                  | Simulation home                       |
| `Index.tsx`         | various                 | Index/redirect page                   |
| `NotFound.tsx`      | `*`                     | 404 page                              |

### 9.2 Feature Components

| Component                     | Purpose                            |
| ----------------------------- | ---------------------------------- |
| `AppNavbar.tsx`               | Top navigation bar                 |
| `ThreadSidebar.tsx`           | Left sidebar with thread list      |
| `RightSidebar.tsx`            | Right sidebar with document panel  |
| `ChatMessage.tsx`             | Individual chat message rendering  |
| `SourcesDisplay.tsx`          | Citation/source display            |
| `SafeMarkdownRenderer.tsx`    | Sanitized markdown rendering       |
| `MindMapModal.tsx`            | Mind map visualization (ReactFlow) |
| `WordCloudModal.tsx`          | Word cloud display                 |
| `SummaryModal.tsx`            | Document/global summary view       |
| `InsightsModal.tsx`           | Insights display                   |
| `StrategicRoadmapModal.tsx`   | Strategic roadmap display          |
| `TechnicalRoadmapModal.tsx`   | Technical roadmap display          |
| `StrategicAnalysisModal.tsx`  | Strategic analysis display         |
| `TechnicalAnalysisModal.tsx`  | Technical analysis display         |
| `ThreadInstructionsModal.tsx` | Per-thread instruction management  |

### 9.3 Infrastructure

| File                    | Purpose                                             |
| ----------------------- | --------------------------------------------------- |
| `lib/api.ts`            | Centralized API client (fetch wrapper)              |
| `lib/auth-context.tsx`  | React Context for auth state + JWT management       |
| `lib/RequireAuth.tsx`   | Route guard component (redirects to login)          |
| `lib/theme-context.tsx` | Dark/light theme provider                           |
| `lib/utils.ts`          | Utility functions (cn, etc.)                        |
| `lib/*-pdf.ts`          | PDF export generators (pdfmake) for each feature    |
| `lib/*-pptx.ts`         | PPTX export generators (pptxgenjs) for each feature |
| `hooks/use-mobile.tsx`  | Responsive breakpoint hook                          |
| `hooks/use-toast.ts`    | Toast notification hook                             |

### 9.4 UI Components

45+ shadcn/ui primitives in `components/ui/`: accordion, alert, alert-dialog, aspect-ratio, avatar, badge, button, card, chart, checkbox, collapsible, command, context-menu, dialog, dropdown-menu, form, hover-card, input, label, menubar, navigation-menu, popover, progress, radio-group, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toast, toaster, toggle, toggle-group, tooltip, etc.

---

## 10. Data Flow & Pipelines

### 10.1 Document Upload Pipeline

```
User uploads files via POST /upload/
│
├── 1. upload_files() → Save raw files to data/{user_id}/threads/{thread_id}/uploads/
│      Each file gets a timestamp-suffixed name: {name}_{timestamp}.{ext}
│
├── 2. process_files() → Parse each file via extract_document()
│      Batch processing (10 concurrent files)
│      Saves parsed JSON to data/.../parsed/{name}.json
│
├── 3. save_documents_to_store() → Index in ChromaDB
│      Chunks documents (512 chars, 100 overlap, sentence-boundary aware)
│      Creates embeddings via nomic-embed-text-v1.5
│      Also builds BM25 index (pickled to disk)
│
├── 4. SQLiteManager.load_spreadsheet() → Load spreadsheets into SQLite
│      Only for .xlsx, .xls, .csv files
│      Smart header detection + metadata enrichment
│
├── 5. [Background] summarize_documents()
│      Per-document summaries (chunked for large docs)
│      Global cross-document summary
│      Saves to parsed JSON + global_summary.json
│
├── 6. [Background] create_mind_map_global() (if SWITCHES["MIND_MAP"])
│      Two-phase: node generation + RAG-based description enrichment
│      Saves to data/.../mind_maps/
│
└── 7. [Background] create_stop_words() (for word cloud)
       LLM-powered domain-aware stop word extraction
```

### 10.2 Query Pipeline

```
User sends question via POST /query/
│
├── 1. Load thread data + user instructions from MongoDB
│
├── 2. Reload spreadsheet data into SQLiteManager (if needed)
│
├── 3. Decomposition (if SWITCHES["DECOMPOSITION"])
│      LLM resolves context + splits into sub-queries
│
├── 4. For each (sub-)query, run Agent graph:
│      │
│      ├── RETRIEVER
│      │   ├── Hybrid retrieval: ChromaDB (dense) + BM25 (sparse)
│      │   ├── Reciprocal Rank Fusion (RRF) merging
│      │   ├── Cross-encoder re-ranking (ms-marco-MiniLM-L-6-v2)
│      │   ├── MMR diversity selection
│      │   └── Adaptive scaling (min 10 chunks/doc, max 50 total)
│      │
│      ├── GENERATE
│      │   ├── Build prompt (question + chunks + history + summary + instructions + schema)
│      │   ├── Detect answer style (brief/compare/analyst/detailed)
│      │   ├── Call invoke_llm() with mode-specific schema
│      │   └── Parse structured output (answer, action, chunks_used, suggestions)
│      │
│      └── ROUTER → based on action:
│          ├── ANSWER → END (return answer)
│          ├── WEB_SEARCH → Tavily search → back to GENERATE
│          ├── SQL_QUERY → Execute SQL → back to GENERATE
│          ├── DOCUMENT_SUMMARIZER → Fetch summary → END or GENERATE
│          ├── GLOBAL_SUMMARIZER → Fetch global summary → END or GENERATE
│          └── FAILURE → SELF_KNOWLEDGE → END
│
├── 5. Combination (if decomposed)
│      Merge sub-answers into coherent response
│
├── 6. Post-process
│      Compute confidence, deduplicate suggestions
│
└── 7. Persist to MongoDB + return response
```

### 10.3 Studio Feature Pipeline

All studio features (insights, roadmaps, analyses) follow the same async pattern:

```
User requests feature via POST endpoint
│
├── 1. Check status file (data/.../feature_name.json)
│      ├── Not found → Create pending status → Spawn background task → Return "generating"
│      ├── Pending → Return "generating" (unless stale > 8 min → treat as failed)
│      ├── Failed → Return error (or regenerate if requested)
│      └── Completed → Return result data
│
├── 2. [Background task]
│      ├── Fetch document content (smart selection: full text <8k, summary, or truncated)
│      ├── For multi-document: compress_global_file_data() to fit token budget
│      ├── Build feature-specific prompt
│      ├── invoke_llm() with typed Pydantic output schema
│      └── Write result to JSON file
│
└── 3. User polls endpoint → Gets completed result
```

---

## 11. LLM Integration & Fallback Strategy

### 11.1 Unified LLM Client (`core/llm/client.py`)

**`invoke_llm()`** is the single entry point for all LLM calls across the entire codebase. It implements a 3-tier fallback chain:

```
Attempt 1..N (MAX_RETRIES=4):
│
├── 1. GPU Server (Ollama / Remote)
│      ├── Try primary port
│      └── If port 11435 fails, try port 11434
│
├── 2. Gemini API (if SWITCHES["FALLBACK_TO_GEMINI"])
│      ├── 6 API keys in round-robin
│      ├── 80s timeout per attempt
│      └── Cycles through all keys on failure
│
└── 3. OpenAI API (if SWITCHES["FALLBACK_TO_OPENAI"])
       └── gpt-4o-mini
```

### 11.2 Output Parsing Pipeline

````
Raw LLM output
│
├── Strategy 1: sanitize_llm_json() + PydanticOutputParser.parse()
│      ├── Strip markdown fences (```json...```)
│      ├── Replace unicode whitespace, remove zero-width chars
│      ├── Extract JSON block from preamble text
│      ├── Escape control characters
│      └── Parse with Pydantic
│
└── Strategy 2: parse_llm_json() with json_repair
       ├── json.loads() attempt
       ├── sanitize + json.loads()
       ├── json_repair library (fixes trailing commas, single quotes, etc.)
       └── Pydantic model_validate()
````

### 11.3 LLM Configurations

Two LLM wrapper classes:

**Local (`local_llm.py`):**

- Wraps `ChatOllama` from langchain-ollama
- Semaphore-based concurrency control per (model, port) — matches `OLLAMA_NUM_PARALLEL`
- Strips `<think>` and `<reasoning>` tags from output
- Cached instances to avoid re-initialization

**Remote (`remote_llm.py`):**

- HTTP POST to a GPU server endpoint
- Same `<think>` tag stripping
- 600s timeout

### 11.4 Structured Output Schemas

All LLM calls use Pydantic models as `response_schema`. Key schemas:

| Schema                             | Used By                   | Key Fields                                                               |
| ---------------------------------- | ------------------------- | ------------------------------------------------------------------------ |
| `MainLLMOutputInternal`            | Internal mode generate    | answer, action, chunks_used, suggested_questions, document_id, sql_query |
| `MainLLMOutputExternal`            | External mode generate    | Same + web_search_queries                                                |
| `MainLLMOutputInternalWithFailure` | Internal + self-knowledge | Same as Internal (failure action allowed)                                |
| `SelfKnowledgeLLMOutput`           | Self-knowledge node       | answer                                                                   |
| `DecompositionLLMOutput`           | Query decomposition       | requires_decomposition, resolved_query, sub_queries                      |
| `CombinationLLMOutput`             | Answer combination        | answer                                                                   |
| `SummarizerLLMOutputSingle`        | Single-chunk summary      | Summary fields                                                           |
| `SummarizerLLMOutputCombination`   | Multi-chunk combination   | Combined summary                                                         |
| `GlobalSummarizerLLMOutput`        | Global summary            | Cross-document summary                                                   |
| `MindMapOutput`                    | Mind map generation       | Flat nodes list                                                          |
| `FlatNodeWithDescriptionOutput`    | Mind map descriptions     | Node descriptions                                                        |
| `InsightsLLMOutput`                | Insights                  | Key points, strengths, improvements, innovations                         |
| `StrategicRoadmapLLMOutput`        | Strategic roadmap         | Vision, pillars, phases, metrics, risks, SWOT                            |
| `TechnicalRoadmapLLMOutput`        | Technical roadmap         | Technical phases, dependencies                                           |
| `StrategicAnalysisLLMOutput`       | Strategic analysis        | Strategic assessment                                                     |
| `TechnicalAnalysisLLMOutput`       | Technical analysis        | Technical assessment                                                     |

### 11.5 Answer Style Detection

The main prompt dynamically adapts based on question keywords:

| Style      | Trigger Keywords                                      | Behavior                                |
| ---------- | ----------------------------------------------------- | --------------------------------------- |
| `brief`    | "summarize", "brief", "concise", "short"              | Short, bullet-point answers             |
| `compare`  | "compare", "contrast", "versus", "differences"        | Side-by-side cross-document comparison  |
| `analyst`  | "recommend", "strategy", "SWOT", "insights", "trends" | Strategic analysis with recommendations |
| `detailed` | "detailed", "elaborate", "comprehensive" (default)    | Comprehensive structured answer         |

---

## 12. Document Parsing Pipeline

### 12.1 Supported Formats

| Format         | Extensions                           | Parser                   | Technique                                                                                 |
| -------------- | ------------------------------------ | ------------------------ | ----------------------------------------------------------------------------------------- |
| **PDF**        | .pdf                                 | PyMuPDF (fitz)           | Table-aware extraction (find_tables), text blocks, embedded image OCR, xref deduplication |
| **Excel**      | .xlsx, .xls, .csv                    | openpyxl + pandas        | Header detection, merged cells, metadata enrichment (comments, colors), markdown tables   |
| **PowerPoint** | .pptx, .ppt                          | python-pptx              | Recursive shape extraction (GroupShape), tables, SmartArt XML, image OCR, slide export    |
| **Word**       | .docx, .doc                          | python-docx / olefile    | Structured extraction (headings → markdown), tables, embedded images                      |
| **Images**     | .png, .jpg, .jpeg, .bmp, .tiff, .gif | EasyOCR + Tesseract      | Dual-engine with spatial sorting, GPU acceleration                                        |
| **Markdown**   | .md                                  | markdown + BeautifulSoup | HTML conversion → text, embedded image OCR                                                |

### 12.2 Central Dispatcher (`core/parsers/main.py`)

`extract_document(path, title, file_name, user_id, thread_id)` routes to format-specific logic based on file extension. Returns a `Document` Pydantic model with pages, text, and metadata.

### 12.3 Vision Language Model Enhancement

When `USE_VISION_MODEL` is enabled:

- Documents are converted to PDF (if not already)
- Pages rendered at 150 DPI as images
- Sent to `vlm_parse_concurrent()` using Ollama VLM model (`qwen3-vl:8b`)
- Auto-detection mode: landscape pages with <100 chars text → assume slides → use VLM
- Max 3 concurrent VLM calls, 240s timeout each, `keep_alive=300` keeps model warm

### 12.4 OCR Pipeline (`core/parsers/image.py`)

1. **EasyOCR** (primary): GPU-accelerated, spatial sort (Y then X for table/flowchart order), batch_size=8 on GPU
2. **Tesseract** (fallback): Preprocessing (grayscale → contrast boost → binary threshold), used when EasyOCR returns empty
3. Both engines use configurable semaphores for concurrency control

### 12.5 Excel Intelligence (`core/parsers/excel_utils.py`)

- **Smart header detection**: Heuristic scoring (string ratio 40%, uniqueness 30%, fullness 30%)
- **Multi-level header support**: Detects horizontally merged cells for hierarchical column names
- **Metadata enrichment**: Extracts cell comments (`[Note: ...]`) and semantic fill colors (`[Status: Green/Red]`)
- **Column deduplication**: Appends `_2`, `_3` suffixes for duplicate names

---

## 13. Embedding & Retrieval System

### 13.1 Embedding Model

**nomic-ai/nomic-embed-text-v1.5** via HuggingFace, GPU-accelerated:

- Task-specific prefixes: `"search_document: "` for indexing, `"search_query: "` for queries
- Batch size: 128, normalized embeddings
- Dimension auto-detected at runtime (typically 768)

### 13.2 Vector Store (ChromaDB)

`core/embeddings/vectorstore.py` manages:

**Indexing:**

- Sentence-boundary-aware chunking (512 chars, 100 overlap) using NLTK `sent_tokenize`
- Fallback: `RecursiveCharacterTextSplitter` with separators `["\n\n", "\n", ". ", " ", ""]`
- Each chunk gets metadata: `document_id`, `title`, `file_name`, `page_no`, `chunk_index`
- Documents prefixed with `"search_document: "` before embedding
- Persisted to `data/{user_id}/chromadb/`

**BM25 Index:**

- Parallel sparse retrieval index built alongside ChromaDB
- Pickled to disk per user: `data/{user_id}/bm25_index.pkl`
- Used for hybrid search (dense + sparse)

**FUSE Compatibility:**

- SQLite journal mode set to DELETE (not WAL) for FUSE filesystem support
- Synchronous writes disabled, normal locking mode, mmap disabled

**Dimension Migration:**

- Auto-detects if existing ChromaDB has mismatched embedding dimensions
- Nukes and recreates if dimensions changed (model upgrade)

### 13.3 Retrieval Pipeline (`core/embeddings/retriever.py`)

1. **Adaptive Retrieval**: `get_thread_documents_retriever()` scales chunks per document:
   - Min 10 chunks per document
   - Max 50 total chunks
   - Proportional allocation based on document count

2. **Hybrid Search**: Dense (ChromaDB similarity) + Sparse (BM25)

3. **Reciprocal Rank Fusion (RRF)**: Merges results from multiple ranked lists:

   ```
   score(d) = Σ 1/(k + rank_i)   for each list i containing d
   ```

   Standard k=60 constant.

4. **Cross-Encoder Re-ranking**: `cross-encoder/ms-marco-MiniLM-L-6-v2` with GPU FP16:
   - Scores each (query, chunk) pair for relevance
   - Lazy-loaded, cached globally

5. **MMR Diversity Selection**: Maximal Marginal Relevance with TF-IDF cosine similarity:
   ```
   MMR_score = (1 - λ) × relevance - λ × max_similarity_to_selected
   ```
   Default λ=0.5 balances relevance and diversity.

---

## 14. Studio Features (Analysis & Generation)

### 14.1 Mind Map (`core/studio_features/mind_map.py`)

**Two-phase generation:**

1. **Phase 1 — Node Creation**: LLM generates up to 100 hierarchical nodes (title + parent) using `MindMapOutput` schema. One root node, balanced breadth/depth.
2. **Phase 2 — Description Enrichment**: For each node, RAG retrieves relevant source text, then LLM generates a 40-50 word description. Processed in batches of 4 with 2 parallel LLM calls. Progressive state saved after each batch.

Saves to `data/.../mind_maps/mind_map_global.json`. Frontend visualizes with ReactFlow.

### 14.2 Summarization (`core/studio_features/summarizer.py`)

**Per-document:**

- ≤11k words: Single LLM call
- > 11k words: Split into 10k-word chunks → summarize each → combine with `SummarizerLLMOutputCombination`
- Up to 5 retries per chunk

**Global:** Collects all per-document summaries, invokes LLM for cross-document synthesis. Also generates a thread title. Saves to `global_summary.json`.

### 14.3 Word Cloud (`core/studio_features/word_cloud.py`)

- **LLM-powered stop words**: Documents processed in batches of 3 → LLM extracts domain-aware stop words (distinguishing trite words from thematically important terms)
- **Text cleaning**: Lowercase, NLTK English stopwords, custom list, lone characters removed
- **Generation**: `wordcloud` library, 1000×600, viridis colormap, 1000 max words

### 14.4 Insights (`core/studio_features/insights.py`)

Generates: key discussion points, strengths, improvement areas, innovation aspects, future considerations, pseudocode/technical outlines. Output schema: `InsightsLLMOutput`.

### 14.5 Strategic Roadmap (`core/studio_features/strategic_roadmap.py`)

Generates N-year (default 5) roadmap with: vision, strategic pillars, phased items, metrics/milestones, risks/mitigations, SWOT, enablers/dependencies, LLM-inferred additions. Output: `StrategicRoadmapLLMOutput`.

### 14.6 Technical Roadmap (`core/studio_features/technical_roadmap.py`)

Generates N-year technical implementation roadmap. Output: `TechnicalRoadmapLLMOutput`.

### 14.7 Strategic Analysis (`core/studio_features/strategic_analysis.py`)

Strategic assessment (market positioning, SWOT, competitive analysis). Output: `StrategicAnalysisLLMOutput`.

### 14.8 Technical Analysis (`core/studio_features/technical_analysis.py`)

Technical assessment of document content. Output: `TechnicalAnalysisLLMOutput`.

**Common pattern across all features:**

1. Smart content selection: full text (<8k words), pre-computed summary, or truncated
2. Multi-document compression: `compress_global_file_data()` iteratively trims to fit token budget
3. Feature-specific prompt template from `core/llm/prompts/`
4. Typed Pydantic output schema
5. File-based status tracking (pending/failed/completed)
6. Stale detection (>8 min pending → failed)

---

## 15. Real-Time Communication (Socket.IO)

### 15.1 Server Setup (`app/socket_handler.py`)

- `socketio.AsyncServer` with ASGI mode, CORS `*`
- 400s ping timeout, 20s ping interval
- Background heartbeat every 20s per connection
- `active_connections` set tracks connected session IDs

### 15.2 Events Emitted by Backend

| Event                    | Source                      | Data                                |
| ------------------------ | --------------------------- | ----------------------------------- |
| `heartbeat`              | socket_handler              | Keepalive                           |
| `upload_progress`        | upload_files, process_files | File processing status              |
| `summarization_progress` | summarizer                  | Summary generation progress         |
| `mindmap_progress`       | mind_map                    | Mind map generation stages          |
| `title_update`           | summarizer                  | Thread title generated from content |
| `extra_done`             | mind_map (delayed_mark)     | Background tasks completed          |

### 15.3 How It's Used

The `sio` object is imported throughout the codebase:

```python
from app.socket_handler import sio
await sio.emit("event_name", data, room=sid)
```

Socket.IO wraps FastAPI in `app/main.py`:

```python
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
```

---

## 16. Database Schema (MongoDB)

### Collection: `users`

```
{
  userId: string (unique index),
  name: string,
  email: string,
  password: string (bcrypt hash),
  is_active: bool,
  threads: {
    "<thread_id>": {
      thread_name: string,
      documents: [
        {
          docId: string,
          title: string,
          type: string,
          file_name: string,
          time_uploaded: date
        }
      ],
      chats: [
        {
          type: "agent" | "user",
          content: string,
          timestamp: date,
          sources: {
            documents_used: [
              { document_id: string, title: string, page_no: int }
            ],
            web_used: [
              { title: string, url: string, favicon: string }
            ]
          }
        }
      ],
      instructions: [
        { id: string, text: string, selected: bool }
      ],
      createdAt: date,
      updatedAt: date,
      extra_done: bool,
      mindmap_enabled: bool
    }
  }
}
```

### Design Choice: Embedded Document Model

All user data (threads, documents, chats, instructions) is embedded in a single `users` document. This is a deliberate choice for:

- **Read performance** — All user data in one document fetch
- **Atomic updates** — Thread updates are single-document operations
- **Simplicity** — No joins or multi-collection queries

The trade-off is a document size limit (16MB per user), which is acceptable for the expected data scale.

---

## 17. Authentication & Security

### 17.1 Registration

- Password hashed with bcrypt (salt_rounds from library default)
- `userId` generated as `{name}_{hex_digest[:6]}`

### 17.2 Login

- Email + password verification
- Returns JWT token (24h expiry, HS256, encoded with `SECRET_KEY`)
- Payload: `{userId, name, email, is_active}`

### 17.3 Request Authentication

- JWT extracted from `Authorization: Bearer <token>` header
- Fallback to `?token=` query parameter (for browser downloads)
- Decoded payload set on `request.state.user`

### 17.4 Authorization

- Routes verify `request.state.user.userId` matches resource owner
- Document serving enforces ownership check + path traversal protection

### 17.5 SQL Injection Prevention

- `SQLiteManager.execute_query()` blocks dangerous SQL keywords: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH
- Pattern: regex match against query text before execution
- Only SELECT queries allowed
- Results capped at 500 rows

---

## 18. API Reference

### User Management

| Method | Path              | Auth | Request Body              | Response                       |
| ------ | ----------------- | ---- | ------------------------- | ------------------------------ |
| `POST` | `/user/`          | No   | `{name, email, password}` | `{userId, name, email}`        |
| `POST` | `/user/login`     | No   | `{email, password}`       | `{token, userId, name, email}` |
| `GET`  | `/user/{user_id}` | Yes  | —                         | `{userId, name, email}`        |

### Thread Management

| Method   | Path                                         | Auth | Description                       |
| -------- | -------------------------------------------- | ---- | --------------------------------- |
| `POST`   | `/thread/`                                   | Yes  | Create empty thread               |
| `GET`    | `/thread/`                                   | Yes  | List all threads                  |
| `GET`    | `/thread/{thread_id}`                        | Yes  | Get single thread                 |
| `PUT`    | `/thread/{thread_id}`                        | Yes  | Rename thread                     |
| `DELETE` | `/thread/{thread_id}`                        | Yes  | Delete thread + all data          |
| `DELETE` | `/thread/{thread_id}/document/{doc_id}`      | Yes  | Delete document (6-step cleanup)  |
| `POST`   | `/thread/{thread_id}/documents/add-existing` | Yes  | Copy document from another thread |
| `DELETE` | `/thread/{thread_id}/chats/{index}`          | Yes  | Delete single chat                |
| `DELETE` | `/thread/{thread_id}/chats`                  | Yes  | Clear all chats                   |
| `GET`    | `/thread/{thread_id}/instructions`           | Yes  | Get thread instructions           |
| `POST`   | `/thread/{thread_id}/instructions`           | Yes  | Add instruction                   |
| `PUT`    | `/thread/{thread_id}/instructions/{id}`      | Yes  | Update instruction                |
| `DELETE` | `/thread/{thread_id}/instructions/{id}`      | Yes  | Delete instruction                |

### Documents & Upload

| Method | Path                                                 | Auth | Description                        |
| ------ | ---------------------------------------------------- | ---- | ---------------------------------- |
| `POST` | `/upload/`                                           | Yes  | Upload files (multipart/form-data) |
| `GET`  | `/data/{user_id}/threads/{thread_id}/uploads/{file}` | Yes  | Serve uploaded file                |

### Query

| Method | Path      | Auth | Request Body                                                   | Description            |
| ------ | --------- | ---- | -------------------------------------------------------------- | ---------------------- |
| `POST` | `/query/` | Yes  | `{thread_id, question, mode, use_self_knowledge, use_context}` | RAG question answering |

### Studio Features

| Method | Path                         | Auth | Description                     |
| ------ | ---------------------------- | ---- | ------------------------------- |
| `POST` | `/wordcloud/{thread_id}`     | Yes  | Generate word cloud PNG         |
| `GET`  | `/mindmap/{thread_id}`       | Yes  | Get mind map data               |
| `POST` | `/summary`                   | Yes  | Per-document summary            |
| `POST` | `/summary/global`            | Yes  | Global summary                  |
| `POST` | `/insights`                  | Yes  | Per-document insights           |
| `POST` | `/insights/global`           | Yes  | Global insights                 |
| `POST` | `/strategic_roadmap`         | Yes  | Per-document strategic roadmap  |
| `POST` | `/strategic_roadmap/global`  | Yes  | Global strategic roadmap        |
| `POST` | `/technical_roadmap`         | Yes  | Per-document technical roadmap  |
| `POST` | `/technical_roadmap/global`  | Yes  | Global technical roadmap        |
| `POST` | `/strategic_analysis`        | Yes  | Per-document strategic analysis |
| `POST` | `/strategic_analysis/global` | Yes  | Global strategic analysis       |
| `POST` | `/technical_analysis`        | Yes  | Per-document technical analysis |
| `POST` | `/technical_analysis/global` | Yes  | Global technical analysis       |

### Export

| Method | Path                           | Auth | Description                      |
| ------ | ------------------------------ | ---- | -------------------------------- |
| `GET`  | `/export/{thread_id}/markdown` | Yes  | Export chat as .md file          |
| `GET`  | `/export/{thread_id}/html`     | Yes  | Export chat as styled .html file |

### Health

| Method | Path       | Auth | Description        |
| ------ | ---------- | ---- | ------------------ |
| `GET`  | `/health/` | No   | `{"status": "ok"}` |

---

## 19. Configuration & Feature Switches

### 19.1 Environment Variables (`.env`)

```env
# Required
DATABASE_URL=mongodb://localhost:27017
SECRET_KEY=your-secret-key
DATABASE_NAME=bedrock
API_KEY_1=gemini-api-key-1
API_KEY_2=gemini-api-key-2
API_KEY_3=gemini-api-key-3
API_KEY_4=gemini-api-key-4
API_KEY_5=gemini-api-key-5
API_KEY_6=gemini-api-key-6
OPENAI_API=openai-api-key
QUERY_URL=http://gpu-server/query
VISION_URL=http://gpu-server/vision
MAIN_MODEL=qwen3:14b-39500-8k

# Optional
REMOTE_GPU=false
USE_VISION_MODEL=false
LOCAL_BASE_URL=http://localhost
MODE=development
TAVILY_API_KEY=tavily-api-key
```

### 19.2 Feature Switches (`core/constants.py`)

```python
SWITCHES = {
    "MIND_MAP": False,         # Mind map generation after upload
    "SUMMARIZATION": False,    # Per-doc + global summarization
    "FALLBACK_TO_GEMINI": False,  # Gemini fallback
    "FALLBACK_TO_OPENAI": False,  # OpenAI fallback
    "DECOMPOSITION": True,     # Query decomposition + context rewriting
    "REMOTE_GPU": False,       # Remote GPU LLMs
}
```

### 19.3 Tunable Parameters

| Parameter            | Default | File           | Purpose                               |
| -------------------- | ------- | -------------- | ------------------------------------- |
| `CHUNK_SIZE`         | 512     | vectorstore.py | Chunk size for text splitting         |
| `CHUNK_OVERLAP`      | 100     | vectorstore.py | Overlap between chunks                |
| `CHUNK_COUNT`        | 12      | constants.py   | Base chunks per retrieval             |
| `MIN_CHUNKS_PER_DOC` | 10      | constants.py   | Min chunks per document               |
| `MAX_TOTAL_CHUNKS`   | 50      | constants.py   | Max chunks after retrieval            |
| `MAX_WEB_SEARCH`     | 2       | constants.py   | Max web search loop attempts          |
| `MAX_SQL_RETRIES`    | 6       | constants.py   | Max SQL query retries                 |
| `MAX_RETRIES`        | 4       | client.py      | Max LLM invocation retries            |
| `EASYOCR_WORKERS`    | 10      | constants.py   | Parallel EasyOCR workers              |
| `TESSERACT_WORKERS`  | 50      | constants.py   | Parallel Tesseract workers            |
| `EASYOCR_GPU`        | True    | constants.py   | GPU for OCR                           |
| `OLLAMA_CONCURRENCY` | 2       | local_llm.py   | Parallel requests per Ollama instance |
| `diversity_lambda`   | 0.5     | retriever.py   | MMR relevance vs. diversity balance   |

---

## 20. Testing

### 20.1 Test Structure

```
tests/
├── conftest.py                    # Root fixtures
├── unit/                          # 33 test files
│   ├── test_config.py
│   ├── test_constants.py
│   ├── test_auth.py
│   ├── test_bcrypt.py
│   ├── test_agent_state.py
│   ├── test_graph_nodes.py
│   ├── test_graph_nodes_functions.py
│   ├── test_graph_helpers.py
│   ├── test_decomposition.py
│   ├── test_combination.py
│   ├── test_invoke_llm.py
│   ├── test_llm_client.py
│   ├── test_llm_output_sanitizer.py
│   ├── test_retriever.py
│   ├── test_retriever_functions.py
│   ├── test_vectorstore.py
│   ├── test_vectorstore_extended.py
│   ├── test_vectorstore_functions.py
│   ├── test_sql_query.py
│   ├── test_search_tool.py
│   ├── test_socket_handler.py
│   ├── test_socket_connect.py
│   ├── test_studio_features.py
│   ├── test_studio_features_functions.py
│   ├── test_mind_map.py
│   ├── test_models.py
│   ├── test_extensions.py
│   ├── test_compress_data.py
│   ├── test_count_tokens.py
│   ├── test_extra_done_check.py
│   ├── test_generation_status.py
│   ├── test_sanitize_schema.py
│   └── test_utils_extended.py
│
├── integration/                   # 11 test files
│   ├── test_user_api.py
│   ├── test_thread_api.py
│   ├── test_upload_api.py
│   ├── test_query_api.py
│   ├── test_health_api.py
│   ├── test_documents_api.py
│   ├── test_export_api.py
│   ├── test_extra_api.py
│   ├── test_studio_features_api.py
│   ├── test_routes_happy_paths.py
│   └── test_extra_thread_happy_paths.py
│
└── e2e/                           # 1 test file
    └── test_user_journey.py
```

### 20.2 Test Infrastructure

**Fixtures** (from `tests/conftest.py`):

- `mock_mongo_client` / `mock_db` — mongomock for MongoDB
- `patched_db` — Patches `db` across 15+ modules simultaneously
- `async_client` — httpx.AsyncClient wrapping FastAPI app
- `auth_token` / `auth_headers` — JWT creation for authenticated requests
- `sample_user_in_db` / `populated_db` — Pre-built test data
- `mock_invoke_llm` — Patches LLM calls globally
- `mock_tavily` — Patches web search with canned results
- `mock_embeddings` / `mock_vectorstore` — Patches vector store ops
- `tmp_data_dir` — Temp directory for file ops

**Environment**: 15+ env vars set in conftest.py before any app imports. No `.env` file needed for tests.

### 20.3 Test Commands

```bash
make -f Makefile.test test          # All tests with coverage
make -f Makefile.test test-unit     # Unit tests only (@pytest.mark.unit)
make -f Makefile.test test-int      # Integration tests only
make -f Makefile.test test-e2e      # E2E tests only
make -f Makefile.test test-fast     # Parallel run (pytest-xdist)
make -f Makefile.test lint          # ruff check
```

**Coverage**: 75% threshold, sources: `app/`, `core/`, `agent/`. Heavy I/O modules excluded from coverage (parsers/main.py, database.py, etc.).

### 20.4 Configuration

```ini
# pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
```

---

## 21. Deployment & Docker

### 21.1 Docker Architecture

**Multi-stage Dockerfile:**

1. **Stage 1** (node): Build frontend with `npm install && npm run build`
2. **Stage 2** (python:3.11): Install Python deps, system packages (tesseract, poppler, nginx, pandoc), NLTK data, copy backend code + built frontend

**docker-compose.yml:**

- `notebook` service: The main app container (host networking)
- `mongo` service: MongoDB (host networking, persistent volume)

### 21.2 System Dependencies

Installed in Docker:

- `libtesseract-dev` + `libleptonica-dev` — Tesseract OCR
- `poppler-utils` — PDF rendering (pdf2image)
- `pandoc` — Document conversion
- `nginx` — Frontend serving + reverse proxy

### 21.3 Nginx Configuration

Frontend served from `/usr/share/nginx/html` on port 8080. API requests proxied to uvicorn on port 8000.

### 21.4 Ollama Setup

Two Ollama instances for parallel inference:

- **Port 11434**: Primary (model serving for most tasks)
- **Port 11435**: Secondary (query model for parallel sub-query execution)
- `OLLAMA_KEEP_ALIVE=-1`: Models stay loaded permanently
- Models configured via `scripts/setmodel.sh`

### 21.5 Build & Run Commands

```bash
make build        # Docker build + pull mongo + install ollama + set models
make run          # docker compose up (attached)
make run-silent   # docker compose up -d (detached)
make ollama       # Start both Ollama instances
make ollama-stop  # Kill all Ollama processes
```

### 21.6 Local Development

```bash
python backend.py     # Start uvicorn on port 8000
python frontend.py    # npm install + npm run dev on port 8080
```

---

## 22. Key Design Patterns

### 22.1 Unified LLM Invocation

All LLM calls go through `invoke_llm()` — never direct. This ensures consistent retry logic, fallback chains, and output parsing across the 20+ places the system calls an LLM.

### 22.2 Typed Structured Output

Every LLM call specifies a Pydantic `response_schema`. The LLM is instructed to produce JSON matching the schema. Output is parsed, sanitized, and validated — no unstructured text handling.

### 22.3 Feature Switch Architecture

The `SWITCHES` dictionary in `core/constants.py` controls all optional behaviors. This enables running on minimal hardware (all switches off) or full-featured deployment (all switches on).

### 22.4 Async Background Generation

Studio features use a file-based status protocol:

- Write `{"_status": "pending"}` → spawn `asyncio.create_task` → return immediately
- Client polls → check file status → return result when complete
- Stale detection: pending >8 minutes → treated as failed

### 22.5 Adaptive Retrieval

Instead of fixed chunk counts, the system adapts based on document count:

- Each document guaranteed minimum chunks
- Total capped at a maximum
- Proportional allocation ensures balanced representation
- Followed by hybrid search (dense + BM25), RRF fusion, cross-encoder re-ranking, and MMR diversity selection

### 22.6 Multi-Tier LLM Fallback

```
Local Ollama (GPU) → Gemini API (6 keys, round-robin) → OpenAI API
```

Each tier has its own retry logic. The system gracefully degrades from free local inference to paid APIs.

### 22.7 Per-User Data Isolation

- File system: `data/{user_id}/threads/{thread_id}/`
- ChromaDB: `data/{user_id}/chromadb/`
- SQLite: In-memory, keyed by `(user_id, thread_id)`
- MongoDB: All data under user document

### 22.8 Semaphore-Based Concurrency

- Ollama requests: Semaphore per (model, port) matching `OLLAMA_NUM_PARALLEL`
- OCR: Separate semaphores for EasyOCR and Tesseract workers
- VLM: Semaphore limiting concurrent VLM calls
- Sub-query execution: asyncio.Queue with 2 GPU workers

### 22.9 Dual-Model Parallel Query Execution

When decomposition produces sub-queries, they're executed in parallel across two Ollama instances (ports 11434/11435), maximizing GPU utilization:

```python
# Two workers pull from queue, each using a different GPU port
worker_1 → GPU_QUERY_LLM (port 11435)
worker_2 → GPU_QUERY_LLM2 (port 11434)
```

### 22.10 Progressive State Saving

Mind map generation saves state after each batch of nodes. If the process crashes, it can resume from the last saved batch rather than starting over.

---

## 23. File-by-File Reference

### Entry Points

| File          | Purpose                                    |
| ------------- | ------------------------------------------ |
| `backend.py`  | Dev server: starts uvicorn on port 8000    |
| `frontend.py` | Dev helper: runs npm install + npm run dev |
| `main.py`     | Alternative entry point                    |
| `app/main.py` | FastAPI + Socket.IO application factory    |

### Agent Layer (`agent/`)

| File                 | Purpose                                                                                  |
| -------------------- | ---------------------------------------------------------------------------------------- |
| `builder.py`         | LangGraph state graph definition + compilation → exports `Agent`                         |
| `state.py`           | `AgentState` Pydantic model with all agent fields                                        |
| `graph_nodes.py`     | 10 node functions (retriever, generate, router, web_search, sql_query, etc.)             |
| `graph_helpers.py`   | Prompt builders (`build_main_prompt`, `build_self_knowledge_prompt`) + `parallel_search` |
| `decomposition.py`   | `decomposition_node()` — query decomposition with LLM                                    |
| `combination.py`     | `combination_node()` — sub-answer combination with LLM                                   |
| `tools/search.py`    | `search_tavily()` — Tavily web search wrapper                                            |
| `tools/sql_query.py` | `execute_sql_query()`, `get_sql_schema()` — SQLite bridge                                |

### API Layer (`app/`)

| File                           | Purpose                                                      |
| ------------------------------ | ------------------------------------------------------------ |
| `main.py`                      | App factory (FastAPI + CORS + Auth + 13 routers + Socket.IO) |
| `socket_handler.py`            | Socket.IO server (heartbeat, connection tracking)            |
| `middlewares/auth.py`          | JWT auth middleware                                          |
| `middlewares/auth_paths.py`    | Protected route prefixes                                     |
| `routes/query.py`              | POST /query/ — Full RAG pipeline                             |
| `routes/upload.py`             | POST /upload/ — File upload + parse + index                  |
| `routes/user.py`               | User CRUD + auth                                             |
| `routes/thread.py`             | Thread CRUD (661 lines, most complex route)                  |
| `routes/documents.py`          | Serve uploaded files with ownership check                    |
| `routes/health.py`             | GET /health/                                                 |
| `routes/export.py`             | Chat export (Markdown/HTML)                                  |
| `routes/extra.py`              | Word cloud, mind map, summary endpoints                      |
| `routes/insights.py`           | Insights generation                                          |
| `routes/strategic_roadmap.py`  | Strategic roadmap generation                                 |
| `routes/technical_roadmap.py`  | Technical roadmap generation                                 |
| `routes/strategic_analysis.py` | Strategic analysis generation                                |
| `routes/technical_analysis.py` | Technical analysis generation                                |

### Core Layer (`core/`)

| File                                    | Purpose                                                         |
| --------------------------------------- | --------------------------------------------------------------- |
| `config.py`                             | `Settings` (pydantic-settings from .env)                        |
| `constants.py`                          | `SWITCHES`, GPU configs, graph node names, tunable params       |
| `database.py`                           | MongoDB connection + `users` collection schema validation       |
| `embeddings/embeddings.py`              | HuggingFace embedding function (nomic-embed-text-v1.5)          |
| `embeddings/vectorstore.py`             | ChromaDB management, chunking, BM25, hybrid search (475 lines)  |
| `embeddings/retriever.py`               | RRF fusion, cross-encoder re-ranking, MMR diversity (515 lines) |
| `llm/client.py`                         | `invoke_llm()` — unified LLM call with 3-tier fallback          |
| `llm/outputs.py`                        | Re-exports all output schema classes                            |
| `llm/configurations/local_llm.py`       | Ollama wrapper (ChatOllama + semaphore)                         |
| `llm/configurations/remote_llm.py`      | Remote GPU HTTP wrapper                                         |
| `llm/output_schemas/*.py`               | 9 Pydantic output schemas                                       |
| `llm/prompts/*.py`                      | 11 prompt templates                                             |
| `models/document.py`                    | Page, Document, Documents                                       |
| `models/user.py`                        | User, Thread, ChatMessage, ThreadDocument                       |
| `models/thread.py`                      | Thread/Instruction request models                               |
| `models/gpu_config.py`                  | GPULLMConfig                                                    |
| `parsers/main.py`                       | Central document parser dispatcher                              |
| `parsers/excel_utils.py`                | Excel intelligence (headers, merged cells, metadata)            |
| `parsers/process_files.py`              | Batch file processing orchestrator                              |
| `parsers/image.py`                      | Dual-engine OCR (EasyOCR + Tesseract)                           |
| `parsers/vlm.py`                        | Vision Language Model parser                                    |
| `parsers/extensions.py`                 | File extension classification                                   |
| `parsers/slide_export.py`               | Full-slide OCR fallback                                         |
| `services/sqlite_manager.py`            | Per-user SQLite for spreadsheet SQL                             |
| `services/upload_files.py`              | File upload to filesystem                                       |
| `studio_features/mind_map.py`           | 2-phase mind map generation                                     |
| `studio_features/summarizer.py`         | Per-doc + global summarization                                  |
| `studio_features/word_cloud.py`         | LLM-powered word cloud generation                               |
| `studio_features/insights.py`           | Document insights                                               |
| `studio_features/strategic_roadmap.py`  | Strategic roadmap                                               |
| `studio_features/technical_roadmap.py`  | Technical roadmap                                               |
| `studio_features/strategic_analysis.py` | Strategic analysis                                              |
| `studio_features/technical_analysis.py` | Technical analysis                                              |
| `utils/bcrypt.py`                       | Password hashing                                                |
| `utils/compress_data.py`                | Token-budget content compression                                |
| `utils/count_tokens.py`                 | tiktoken token counting                                         |
| `utils/extra_done_check.py`             | Background task flag                                            |
| `utils/generation_status.py`            | File-based async status protocol                                |
| `utils/llm_output_sanitizer.py`         | Multi-stage JSON repair (293 lines)                             |
| `utils/sanitize_schema.py`              | JSON schema cleanup                                             |

### Frontend (`frontend/src/`)

| File                                     | Purpose                  |
| ---------------------------------------- | ------------------------ |
| `pages/Landing.tsx`                      | Landing page             |
| `pages/Login.tsx`                        | Login form               |
| `pages/Register.tsx`                     | Registration form        |
| `pages/Dashboard.tsx`                    | Dashboard layout         |
| `pages/DashboardHome.tsx`                | Dashboard overview       |
| `pages/NewThread.tsx`                    | New thread + file upload |
| `pages/ThreadView.tsx`                   | Main chat interface      |
| `pages/Profile.tsx`                      | User profile             |
| `components/ChatMessage.tsx`             | Chat message rendering   |
| `components/ThreadSidebar.tsx`           | Thread list sidebar      |
| `components/RightSidebar.tsx`            | Document panel           |
| `components/MindMapModal.tsx`            | Mind map (ReactFlow)     |
| `components/WordCloudModal.tsx`          | Word cloud display       |
| `components/SummaryModal.tsx`            | Summary view             |
| `components/InsightsModal.tsx`           | Insights display         |
| `components/StrategicRoadmapModal.tsx`   | Strategic roadmap        |
| `components/TechnicalRoadmapModal.tsx`   | Technical roadmap        |
| `components/StrategicAnalysisModal.tsx`  | Strategic analysis       |
| `components/TechnicalAnalysisModal.tsx`  | Technical analysis       |
| `components/ThreadInstructionsModal.tsx` | Per-thread instructions  |
| `components/SourcesDisplay.tsx`          | Citation display         |
| `components/SafeMarkdownRenderer.tsx`    | Sanitized markdown       |
| `lib/api.ts`                             | API client               |
| `lib/auth-context.tsx`                   | Auth state management    |
| `lib/RequireAuth.tsx`                    | Route guard              |
| `lib/theme-context.tsx`                  | Theme provider           |
| `lib/*-pdf.ts`                           | PDF export generators    |
| `lib/*-pptx.ts`                          | PPTX export generators   |

### Configuration & Build

| File                      | Purpose                                                |
| ------------------------- | ------------------------------------------------------ |
| `pyproject.toml`          | Python project config, dependencies, coverage settings |
| `pytest.ini`              | Pytest configuration                                   |
| `requirements.txt`        | Python dependencies (pip)                              |
| `requirements-docker.txt` | Docker-specific dependencies                           |
| `requirements-test.txt`   | Test dependencies                                      |
| `Makefile`                | Build, run, Ollama management                          |
| `Makefile.test`           | Test runner                                            |
| `docker-compose.yml`      | Docker Compose (app + MongoDB)                         |
| `dockerfile`              | Multi-stage Docker build                               |
| `docker-entrypoint.sh`    | Container startup script                               |
| `nginx/default.conf`      | Nginx reverse proxy config                             |

---

_This document was auto-generated as a comprehensive reference for the project codebase. It covers the complete architecture, all features, every API endpoint, data flows, design patterns, and file-level details needed to understand and work with the project._
