# PRISM — Technical Implementation Reference

This document captures the complete technical architecture, code patterns, and implementation details of the PRISM platform. It is intended as a reference for future development, onboarding, and extension planning.

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             Client (React/Vite)                         │
│  React Router · shadcn/ui (Radix) · TailwindCSS · Socket.IO Client     │
│  ReactFlow (Mind Maps) · Recharts                                       │
└────────────────────────┬──────────────────────┬──────────────────────────┘
                         │ REST API              │ Socket.IO
┌────────────────────────▼──────────────────────▼──────────────────────────┐
│                        FastAPI + Socket.IO (ASGI)                        │
│  app/main.py → socketio.ASGIApp wrapping FastAPI                         │
│  Port 8000 · JWT Auth Middleware · CORS                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                         Agent Layer (LangGraph)                          │
│  agent/builder.py (graph) · agent/state.py (state) · graph_nodes.py     │
│  Nodes: Retriever → Evaluator → Generate → Router → [Action Nodes]      │
├──────────────────────────────────────────────────────────────────────────┤
│                         Core Services Layer                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ LLM      │ │Embeddings│ │ Parsers  │ │ Services │ │ Studio   │      │
│  │ Client   │ │ & Vector │ │          │ │          │ │ Features │      │
│  │          │ │ Store    │ │          │ │          │ │          │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├──────────────────────────────────────────────────────────────────────────┤
│                         Data Layer                                       │
│  MongoDB (Users/Threads) · ChromaDB (Vectors) · SQLite (Spreadsheets)   │
│  BM25 Index (Pickle) · Triple Store (SQLite)                             │
├──────────────────────────────────────────────────────────────────────────┤
│                         LLM Serving                                      │
│  Ollama (Port 11434, 11435) · Gemini API (Fallback) · OpenAI (Fallback) │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
PRISM Code/
├── app/                          # FastAPI application
│   ├── main.py                   # ASGI app: FastAPI + Socket.IO
│   ├── socket_handler.py         # Socket.IO server configuration
│   ├── routes/                   # REST API endpoints
│   │   ├── query.py              # POST /query/ — main Q&A endpoint
│   │   ├── upload.py             # POST /upload/ — file upload
│   │   ├── thread.py             # Thread CRUD
│   │   ├── documents.py          # Document management
│   │   ├── user.py               # Auth (register, login, profile)
│   │   ├── insights.py           # POST /insights/
│   │   ├── strategic_roadmap.py  # POST /strategic-roadmap/
│   │   ├── technical_roadmap.py  # POST /technical-roadmap/
│   │   ├── strategic_analysis.py # POST /strategic-analysis/
│   │   ├── technical_analysis.py # POST /technical-analysis/
│   │   └── extra.py              # POST /extra/ — mind maps, summaries, word clouds
│   └── middlewares/
│       ├── auth.py               # JWT validation middleware
│       └── auth_paths.py         # Protected route definitions
│
├── agent/                        # LangGraph agent
│   ├── state.py                  # AgentState (Pydantic BaseModel)
│   ├── builder.py                # Graph compilation (nodes + edges)
│   ├── graph_nodes.py            # Node function implementations
│   ├── decomposition.py          # Query decomposition logic
│   └── combination.py            # Sub-answer combination logic
│
├── core/                         # Shared business logic
│   ├── config.py                 # Settings (pydantic-settings, loaded from .env)
│   ├── constants.py              # Feature switches, model configs, limits
│   ├── database.py               # MongoDB connection + schema validation
│   │
│   ├── llm/                      # LLM integration
│   │   ├── client.py             # invoke_llm() — unified LLM call with retry/fallback
│   │   ├── configurations/
│   │   │   ├── local_llm.py      # ChatOllama setup (semaphore, caching)
│   │   │   └── remote_llm.py     # HTTP-based remote GPU LLM
│   │   ├── output_schemas/       # Pydantic response schemas
│   │   │   ├── main_outputs.py   # MainLLMOutputInternal/External, Decomposition, etc.
│   │   │   ├── summarizer.py     # Summarization output schemas
│   │   │   ├── mind_map.py       # Mind map output schemas
│   │   │   ├── insights.py       # Insights output schema
│   │   │   ├── roadmaps.py       # Strategic/Technical roadmap schemas
│   │   │   ├── analysis.py       # Analysis output schemas
│   │   │   ├── evaluator.py      # CRAG evaluator output
│   │   │   └── hyde.py           # HyDE output schema
│   │   └── prompts/              # LLM prompt templates
│   │       ├── main_prompt.py    # Primary Q&A prompt (answer style, grounding)
│   │       ├── decomposition_prompt.py
│   │       ├── evaluator_prompt.py
│   │       ├── hyde_prompt.py
│   │       ├── summarizer_prompt.py
│   │       └── combination_prompt.py
│   │
│   ├── embeddings/               # Embedding & retrieval
│   │   ├── vectorstore.py        # ChromaDB management, chunking, BM25
│   │   ├── retriever.py          # Hybrid retrieval, RRF, re-ranking, MMR
│   │   ├── embedding_function.py # nomic-embed-text-v1.5 setup
│   │   └── context_enrichment.py # NER, entity extraction, triple generation
│   │
│   ├── parsers/                  # Document parsing
│   │   ├── main.py               # extract_document() dispatcher
│   │   ├── extensions.py         # File extension constants
│   │   ├── process_files.py      # Batch file processing orchestrator
│   │   ├── vlm.py                # Vision Language Model parser (qwen3-vl:8b)
│   │   ├── glm_ocr.py            # GLM-OCR parser (structured OCR via Ollama)
│   │   ├── image.py              # EasyOCR / Tesseract image OCR
│   │   └── ...
│   │
│   ├── services/                 # Business services
│   │   ├── upload_files.py       # File upload handling
│   │   ├── sqlite_manager.py     # Spreadsheet → SQLite engine
│   │   └── triple_store.py       # Entity triple storage (SQLite)
│   │
│   ├── studio_features/          # Advanced analysis
│   │   ├── mind_map.py           # Mind map generation
│   │   ├── summarizer.py         # Document/global summarization
│   │   ├── word_cloud.py         # TF-IDF word cloud
│   │   ├── insights.py           # Insights extraction
│   │   ├── strategic_roadmap.py  # Strategic roadmap generation
│   │   ├── technical_roadmap.py  # Technical roadmap generation
│   │   ├── strategic_analysis.py # Strategic analysis
│   │   └── technical_analysis.py # Technical analysis
│   │
│   ├── models/                   # Data models
│   │   └── document.py           # Document, Page models
│   │
│   └── utils/                    # Helpers
│       ├── bcrypt.py             # Password hashing
│       ├── token_counter.py      # LLM token estimation
│       ├── sanitize.py           # LLM output sanitization
│       └── generation_status.py  # Progress tracking
│
├── frontend/                     # React/TypeScript/Vite
│   ├── src/
│   │   ├── pages/                # ThreadView, Dashboard, Login, Register
│   │   ├── components/           # Chat, MindMap, WordCloud, Summary, Roadmap modals
│   │   ├── context/              # Auth, Theme contexts
│   │   ├── lib/                  # api.ts (REST + Socket.IO client)
│   │   └── ...
│   └── ...
│
├── data/                         # Runtime data (per user, per thread)
│   └── {user_id}/
│       ├── threads/{thread_id}/
│       │   ├── uploads/          # Original uploaded files
│       │   ├── parsed/           # Per-document summaries (JSON)
│       │   ├── mind_maps/        # Generated mind maps (JSON)
│       │   └── global_summary.json
│       ├── bm25/{thread_id}.pkl  # BM25 index
│       └── triples/{thread_id}.db # Entity triple store
│
├── tests/                        # Test suite
│   ├── conftest.py               # Shared fixtures
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── CLAUDE.md                     # AI assistant instructions
├── backend.py                    # Backend entry point (uvicorn)
├── frontend.py                   # Frontend entry point (npm run dev)
├── docker-compose.yml
├── Dockerfile
├── Makefile                      # Build/run commands
├── Makefile.test                 # Test commands
├── pyproject.toml                # Python project config
├── requirements.txt
└── requirements-test.txt
```

---

## 3. Agent Architecture (LangGraph)

### 3.1 State Definition

**File**: `agent/state.py`

The `AgentState` is a Pydantic BaseModel that flows through every node in the graph. Key fields:

```python
class AgentState(BaseModel):
    # Identity
    user_id: str
    thread_id: str

    # Query
    query: str                          # Current query
    resolved_query: Optional[str]       # Rewritten query (decomposition)
    original_query: Optional[str]       # Preserved original
    sub_queries: Optional[List[str]]    # Decomposed sub-queries

    # Chat
    messages: List[BaseMessage]         # Conversation history

    # Retrieval
    chunks: Optional[List]              # Retrieved document chunks
    retrieval_attempts: int = 0         # CRAG retry counter
    retrieval_verdict: Optional[str]    # sufficient/ambiguous/insufficient

    # Generation
    answer: Optional[str]
    confidence_score: Optional[str]     # high/medium/low
    action: Optional[str]              # Router decision

    # Web search
    web_search: Optional[bool]
    web_search_queries: Optional[List[str]]
    web_search_results: Optional[List]

    # SQL
    sql_query: Optional[str]
    sql_result: Optional[str]
    sql_attempts: int = 0

    # Summarization
    summary: Optional[str]

    # Modes
    mode: str                           # INTERNAL or EXTERNAL
    use_self_knowledge: bool = False
    spreadsheet_only: bool = False      # Thread has only spreadsheets
    thread_instructions: Optional[List] # Per-thread custom instructions

    # Entity context (Phase 3.2)
    triple_context: Optional[str]       # Injected entity relationships
```

### 3.2 Graph Topology

**File**: `agent/builder.py`

```
START
  │
  ▼
RETRIEVER ──────────────────────────────────────────┐
  │                                                  │
  ▼                                                  │ (re-retrieve
EVALUATOR                                            │  if insufficient)
  │                                                  │
  ├─ sufficient/ambiguous ──▶ GENERATE               │
  │                                                  │
  └─ insufficient ──────────────────────────────────┘
                               │
                               ▼
                           GENERATE
                               │
                               ▼
                           ROUTER ─────┐
                               │       │
            ┌──────┬──────┬────┼───┬───┘
            ▼      ▼      ▼    ▼   ▼
         ANSWER  WEB   SQL  DOC  GLOBAL  SELF
          (END) SEARCH QUERY SUM   SUM  KNOWLEDGE
                  │      │    │     │      │
                  └──────┴────┘     │      │
                       │            │      │
                       ▼            ▼      ▼
                   GENERATE       END    END
                   (loop)
```

### 3.3 Node Implementations

**File**: `agent/graph_nodes.py`

| Node | Function | Key Logic |
|------|----------|-----------|
| `retriever` | Hybrid retrieval (vector + BM25 + RRF) | Multi-query expansion, adaptive chunk count, entity boosting, confidence scoring. Skips if `spreadsheet_only=True` |
| `evaluator` | CRAG quality assessment | LLM judges context sufficiency. Triggers re-retrieval if insufficient (max 2 attempts) |
| `generate` | Main LLM invocation | Dynamic response schema selection, 8 retries on failure. Returns answer + action + sources |
| `main_router` | Conditional edge routing | Checks `state.action`, enforces limits (MAX_WEB_SEARCH=2, MAX_SQL_RETRIES=6) |
| `web_search` | Tavily search execution | Parallel multi-query search. Results stored for next GENERATE pass |
| `sql_query_node` | Spreadsheet SQL execution | Executes LLM-generated SQL against SQLite. Results fed to next GENERATE |
| `document_summarizer` | Per-document summary | Loads from pre-generated JSON files |
| `global_summarizer` | Cross-document summary | Loads global summary JSON |
| `self_knowledge` | LLM fallback | Uses LLM's general knowledge (INTERNAL mode only) |
| `failure` | Error handling | Generates error message |

### 3.4 Query Decomposition

**File**: `agent/decomposition.py`

1. LLM analyzes query complexity
2. If complex → generates 2–4 focused sub-queries + a resolved (rewritten) query
3. Each sub-query runs through the full agent pipeline independently
4. Results combined via combination LLM (`agent/combination.py`)
5. Sub-queries processed in parallel using 2 model instances (`GPU_QUERY_LLM` + `GPU_QUERY_LLM2`)

---

## 4. RAG Pipeline

### 4.1 Document Ingestion

**File**: `core/parsers/main.py` → `extract_document()`

Dispatcher logic:
```python
ext = file_name.split(".")[-1].lower()

if ext in PDF_EXTENSIONS:       → PyMuPDF (fitz) + optional VLM or GLM-OCR
if ext in EXCEL_EXTENSIONS:     → pandas → SQLite tables
if ext in PPTX_EXTENSIONS:      → python-pptx + OCR (VLM or GLM-OCR for slides)
if ext in IMAGE_EXTENSIONS:     → EasyOCR / Tesseract (or GLM-OCR if enabled)
if ext in MARKDOWN_EXTENSIONS:  → html2text
```

When `SWITCHES["GLM_OCR"]` is enabled, PDF/PPTX/Image parsing uses GLM-OCR's structured
Markdown output (tables, formulas, layout preservation) alongside or instead of the default OCR pipeline.

Output: `Document(id, type, file_name, content=[Page(number, text, images)], title, full_text)`

### 4.2 Chunking

**File**: `core/embeddings/vectorstore.py`

| Parameter | Value |
|-----------|-------|
| Chunk size | 512 characters |
| Chunk overlap | 100 characters |
| Strategy | Sentence-boundary aware (NLTK) with RecursiveCharacterTextSplitter fallback |
| Tokenization | Sentence tokenization via NLTK punkt |

### 4.3 Embedding

**File**: `core/embeddings/embedding_function.py`

| Parameter | Value |
|-----------|-------|
| Model | `nomic-ai/nomic-embed-text-v1.5` |
| Dimensions | 768 |
| Device | GPU (CUDA) |
| Batch size | 128 |
| Normalization | Enabled |
| Index prefix | `search_document: ` |
| Query prefix | `search_query: ` |

### 4.4 Vector Store

**File**: `core/embeddings/vectorstore.py`

ChromaDB (persistent, SQLite backend) with:
- Collection: `user_docs`
- Metadata per chunk:
  ```json
  {
    "document_id": "uuid",
    "document_title": "Report.pdf",
    "page_no": 1,
    "file_name": "Report.pdf",
    "user_id": "user_123",
    "thread_id": "thread_456",
    "chunk_index": 0,
    "entities": "Entity1,Entity2",
    "entity_types": "PERSON,ORG"
  }
  ```
- SQLite settings: `journal_mode=DELETE`, `synchronous=OFF`, `locking_mode=NORMAL`, `mmap_size=0`

### 4.5 BM25 Index

- Tokenization: lowercase, punctuation removal, whitespace split
- Persistence: pickle at `data/{user_id}/bm25/{thread_id}.pkl`
- Rebuilt on document add/remove

### 4.6 Hybrid Retrieval

**File**: `core/embeddings/retriever.py`

**Flow**:
1. **Multi-Query Expansion**: original + resolved + HyDE queries
2. **Vector Search**: ChromaDB semantic search (k=30 per query)
3. **BM25 Search**: keyword search (k=20 per query)
4. **RRF Fusion**: `Score(d) = Σ(1/(k + rank_i))` across all result lists, deduplication by (doc_id, page_no, chunk_idx)
5. **Entity Boosting**: +20% score per matching entity
6. **Adaptive Chunk Allocation**:

| Document Count | k (total chunks) | chunks_per_doc |
|---------------|-------------------|----------------|
| 1–2 | 20 | max(ceil(20/n), 10) |
| 3–5 | 50 | max(ceil(50/n), 10) |
| 6–10 | 100 | max(ceil(100/n), 10) |
| >10 | min(n×10, 500) | max(ceil(k/n), 10) |

### 4.7 Re-Ranking & MMR

**File**: `core/embeddings/retriever.py` → `rerank_chunks()`

1. **Cross-Encoder Scoring**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (GPU, FP16). Scores normalized to [0,1] via sigmoid
2. **MMR Diversity Selection**: `MMR = (1-λ) × relevance - λ × max_similarity_to_selected`, λ=0.5. TF-IDF vectors for similarity

### 4.8 CRAG (Corrective Retrieval)

1. Retrieve chunks → evaluator LLM judges: `sufficient | ambiguous | insufficient`
2. If `insufficient` or `ambiguous`: refine query (LLM-suggested), re-retrieve
3. Max `MAX_RETRIEVAL_ATTEMPTS = 2`
4. Confidence scoring: `high` (≥5 chunks, avg_rerank ≥0.5), `medium` (≥3, ≥0.3), `low` (otherwise)

### 4.9 Context Enrichment

**File**: `core/embeddings/context_enrichment.py`

- **NER**: spaCy NER for PERSON, ORG, GPE, DATE, etc.
- **Triple Extraction**: Entity co-occurrences → (subject, predicate, object) triples
- **Triple Store**: SQLite at `data/{user_id}/triples/{thread_id}.db`
- **Query-Time Injection**: Extract query entities → lookup triples → inject as `triple_context` in prompt

---

## 5. LLM Integration

### 5.1 Unified Invocation

**File**: `core/llm/client.py` → `invoke_llm()`

```python
async def invoke_llm(
    gpu_model: str,                # Ollama model name
    response_schema: BaseModel,    # Pydantic schema for structured output
    contents: str,                 # Full prompt
    port: int = 11434,             # Ollama port
    remove_thinking: bool = False  # Strip <think>/<reasoning> tags
) → parsed Pydantic model instance
```

**Fallback Chain** (MAX_RETRIES=4 per provider):

```
Ollama (port 11434)
  ↓ fail
Ollama (port 11435)     ← alternate port
  ↓ fail
Gemini API              ← if SWITCHES["FALLBACK_TO_GEMINI"]=True
  (round-robin 6 API keys, 80s timeout)
  ↓ fail
OpenAI API              ← if SWITCHES["FALLBACK_TO_OPENAI"]=True
  (gpt-4o-mini)
```

**JSON Parsing Strategy**:
1. Sanitize (remove control chars, escape newlines, strip markdown blocks)
2. `PydanticOutputParser.parse()`
3. If fails → `json_repair.repair_json()` + `model.model_validate()`

### 5.2 Model Configuration

**File**: `core/constants.py`

16 GPU model configurations, all pointing to `MAIN_MODEL` (e.g., `qwen3:14b`) with port distribution across 11434/11435:

| Config Name | Purpose | Port |
|-------------|---------|------|
| `GPU_QUERY_LLM` | Primary Q&A | 11435 |
| `GPU_QUERY_LLM2` | Parallel sub-query | 11434 |
| `GPU_DECOMPOSITION_LLM` | Query decomposition | 11435 |
| `GPU_COMBINATION_LLM` | Sub-answer combination | 11435 |
| `GPU_EVALUATOR_LLM` | CRAG evaluation | 11434 |
| `GPU_HYDE_LLM` | Hypothetical document | 11434 |
| `GPU_DOC_SUMMARIZER_LLM` | Per-doc summarization | 11434 |
| `GPU_GLOBAL_SUMMARIZER_LLM` | Global summarization | 11434 |
| `GPU_NODE_GENERATION_LLM` | Mind map node gen | 11434 |
| `GPU_NODE_DESCRIPTION_LLM` | Mind map descriptions | 11434 |
| `GPU_INSIGHTS_LLM` | Insights extraction | 11434 |
| `GPU_STRATEGIC_ROADMAP_LLM` | Strategic roadmap | 11434 |
| `GPU_TECHNICAL_ROADMAP_LLM` | Technical roadmap | 11434 |
| `GPU_STRATEGIC_ANALYSIS_LLM` | Strategic analysis | 11434 |
| `GPU_TECHNICAL_ANALYSIS_LLM` | Technical analysis | 11434 |
| `GPU_ENTITY_PROFILE_LLM` | Entity profiling | 11434 |
| `GPU_TRIPLE_EXTRACTION_LLM` | Triple extraction | 11434 |

### 5.3 Local LLM Setup

**File**: `core/llm/configurations/local_llm.py`

- Uses `ChatOllama` from langchain_ollama
- Semaphore-based concurrency limiting: `OLLAMA_CONCURRENCY` (default 2)
- Cached per `(model, port)` pair — lazy-loaded singleton
- Timeout: 600 seconds

### 5.4 Structured Output Schemas

**Directory**: `core/llm/output_schemas/`

| Schema | Fields | Used By |
|--------|--------|---------|
| `MainLLMOutputInternal` | answer, action (no web_search), chunks_used, sql_query | Internal mode Q&A |
| `MainLLMOutputExternal` | answer, action (with web_search), chunks_used, web_search_queries | External mode Q&A |
| `DecompositionLLMOutput` | requires_decomposition, resolved_query, sub_queries | Query decomposition |
| `CombinationLLMOutput` | answer | Sub-answer merging |
| `SelfKnowledgeLLMOutput` | answer | Fallback LLM knowledge |
| `EvaluatorLLMOutput` | verdict (sufficient/ambiguous/insufficient) | CRAG evaluation |
| `HyDELLMOutput` | hypothetical_document | HyDE retrieval |
| `SummarizerLLMOutputSingle` | summary | Per-chunk summarization |
| `SummarizerLLMOutputCombination` | summary | Summary merging |
| `GlobalSummarizerLLMOutput` | summary | Cross-doc summary |
| `MindMapOutput` | nodes (title, children) | Mind map structure |
| `FlatNodeWithDescriptionOutput` | nodes (title, description) | Mind map descriptions |
| `InsightsLLMOutput` | strengths, improvements, future, ... | Insights |
| `StrategicRoadmapLLMOutput` | vision, baseline, SWOT, phases, ... | Strategic roadmap |
| `TechnicalRoadmapLLMOutput` | architecture, stack, phases, ... | Technical roadmap |

### 5.5 Prompt Architecture

**Directory**: `core/llm/prompts/`

**Main Prompt** (`main_prompt.py`):
- **Answer Style Detection**: Brief / Detailed / Analyst / Compare (keyword-triggered)
- **Dynamic System Prompt**: Role assignment, task definition, formatting guidelines, grounding rules
- **Content Assembly**:
  ```
  [System Prompt]
  [Thread Context]: custom instructions, chat history
  [Documents Provided]: chunked content with titles
  [Web Search Results]: if available
  [SQL Query Results]: if available
  [Entity Relationships]: triple_context
  User Question: {query}
  ```

---

## 6. Feature Switches & Constants

**File**: `core/constants.py`

### Switches
```python
SWITCHES = {
    "MIND_MAP": False,              # Auto-generate mind maps on upload
    "SUMMARIZATION": False,          # Auto-generate summaries on upload
    "FALLBACK_TO_GEMINI": False,    # Enable Gemini API fallback
    "FALLBACK_TO_OPENAI": False,    # Enable OpenAI API fallback
    "DECOMPOSITION": True,           # Enable query decomposition
    "REMOTE_GPU": settings.REMOTE_GPU,  # Use remote GPU server
    "CORRECTIVE_RETRIEVAL": True,    # Enable CRAG re-retrieval
    "HYDE": False,                   # Enable HyDE retrieval
    "GLM_OCR": False,               # GLM-OCR for structured OCR (tables, formulas, figures)
    "DOCUMENT_CREATOR": True,        # Interactive document generation (PPTX/DOCX/PDF)
}
```

### GLM-OCR Constants
```python
GLM_OCR_MODEL = "glm-ocr-32k"      # Custom Modelfile: 32K context, 8K output
GLM_OCR_WORKERS = 3                 # Max concurrent GLM-OCR inferences (VRAM-aware)
```

### Limits
```python
CHUNK_COUNT = 12                    # Default retrieval count
MIN_CHUNKS_PER_DOC = 10            # Minimum chunks from any document
MAX_TOTAL_CHUNKS = 50              # Maximum chunks after reranking
MAX_WEB_SEARCH = 2                 # Max web search loop iterations
MAX_SQL_RETRIES = 6                # Max SQL query attempts
MAX_RETRIEVAL_ATTEMPTS = 2         # CRAG re-retrieval limit
```

---

## 7. Database Layer

### 7.1 MongoDB

**File**: `core/database.py`

Schema (users collection):
```javascript
{
  userId: string (unique index),
  name: string,
  email: string,
  password: string (bcrypt),
  is_active: boolean,
  threads: {
    [thread_id]: {
      thread_name: string,
      documents: [{
        docId: string,
        title: string,
        type: string,
        file_name: string,
        time_uploaded: date
      }],
      chats: [{
        type: "user" | "agent",
        content: string,
        timestamp: date,
        sources: {
          documents_used: [{ document_id, title, page_no }],
          web_used: [{ title, url, favicon }]
        }
      }],
      createdAt: date,
      updatedAt: date,
      extra_done: boolean,
      mindmap_enabled: boolean,
      instructions: [{ id, text, selected }]
    }
  }
}
```

### 7.2 SQLite (Spreadsheets)

**File**: `core/services/sqlite_manager.py`

- In-memory per (user_id, thread_id)
- Excel/CSV → Pandas → SQL tables
- Features: header detection, multi-level header flattening, column deduplication, type inference
- Table naming: `{sheet_name}_{doc_id}` (sanitized)
- Schema exposed to LLM for SQL generation

### 7.3 Triple Store

**File**: `core/services/triple_store.py`

- SQLite file at `data/{user_id}/triples/{thread_id}.db`
- Schema: `(id, document_id, subject, predicate, object, page_no)`
- Indexes on subject, object (case-insensitive)
- Queried at retrieval time to inject relationship context

---

## 8. API Endpoints

### 8.1 Query

```
POST /query/
Body: { thread_id, question, mode, use_self_knowledge, use_context }
Response: { answer, chunks_used, confidence_score, web_results, sources }
```

Processing flow:
1. Decomposition check → generate sub-queries if needed
2. Parallel sub-query processing (2 workers max)
3. Each worker runs full agent pipeline
4. Combination LLM merges sub-answers
5. Store chat in MongoDB, emit via Socket.IO

### 8.2 Upload

```
POST /upload/
Body: multipart/form-data (files + thread_id)
Response: { thread_id, documents }
```

Processing flow:
1. Save files to disk
2. Parse each file (format-specific)
3. Background: summarization, mind maps, SQLite loading
4. Chunk + embed + store in ChromaDB
5. Extract entities + build triples

### 8.3 Thread/Document CRUD

```
POST   /thread/                    # Create thread
GET    /thread/{thread_id}         # Get thread
GET    /thread/                    # List threads
PUT    /thread/{thread_id}         # Update name
DELETE /thread/{thread_id}         # Delete thread
DELETE /documents/{doc_id}         # Remove document
```

### 8.4 Studio Features

```
POST /insights/                    # Generate insights
POST /strategic-roadmap/           # Strategic roadmap
POST /technical-roadmap/           # Technical roadmap
POST /strategic-analysis/          # Strategic analysis
POST /technical-analysis/          # Technical analysis
POST /extra/                       # Mind maps, summaries, word clouds
```

### 8.5 Socket.IO Events

| Event | Direction | Purpose |
|-------|-----------|---------|
| `{user_id}/progress` | Server → Client | Processing status updates |
| `{user_id}/{thread_id}/mind_map/progress` | Server → Client | Mind map generation progress |
| `{user_id}/{thread_id}/global_mind_map` | Server → Client | Mind map completion |
| `{user_id}/{thread_id}/global` | Server → Client | Global summary completion |
| `heartbeat` | Server → Client | Keep-alive (every 20s) |

---

## 9. Frontend Architecture

### 9.1 Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 18 + TypeScript |
| Build | Vite |
| Styling | TailwindCSS |
| Components | shadcn/ui (Radix primitives) |
| Routing | React Router |
| Visualization | ReactFlow (mind maps), Recharts |
| Real-time | Socket.IO client |

### 9.2 Key Pages

| Page | Route | Purpose |
|------|-------|---------|
| `ThreadView` | `/thread/{threadId}` | Main chat + analysis workspace |
| `Dashboard` | `/` | Thread management |
| `Login` | `/login` | Authentication |
| `Register` | `/register` | User creation |

### 9.3 Key Components

| Component | Purpose |
|-----------|---------|
| `ChatMessage` | Render messages with source attribution |
| `SourcesDisplay` | Citation rendering (docs + web) |
| `MindMapModal` | Interactive mind map (ReactFlow) |
| `WordCloudModal` | Word cloud visualization |
| `SummaryModal` | Document summaries |
| `RoadmapModal` | Strategic/technical roadmaps |
| `AnalysisModal` | Analysis results |
| `ThreadInstructionsModal` | Per-thread instructions |
| `RightSidebar` | Document list & management |

### 9.4 State Management

- `auth-context.tsx` — User authentication state
- `theme-context.tsx` — Dark/light mode
- `lib/api.ts` — Centralized API client (Fetch + Socket.IO)

---

## 10. Document Parsing Details

### 10.1 PDF Parser

- **Engine**: PyMuPDF (fitz)
- **VLM Enhancement**: Optional `qwen3-vl:8b` for image-heavy/scanned PDFs
- **Output**: Page-level text + image extraction
- **Config**: `USE_VISION_MODEL` in settings

### 10.2 Excel/CSV Parser

- **Engine**: Pandas (openpyxl for xlsx, csv module for CSV)
- **Processing**: Header detection → multi-level header flattening → type inference → SQLite table creation
- **Table naming**: `{sheet_name}_{doc_id}` (sanitized)
- **Text representation**: Tabular data converted to text for embedding

### 10.3 PowerPoint Parser

- **PPTX Engine**: python-pptx (direct slide text + shape extraction)
- **PPT Engine**: LibreOffice conversion to PPTX, then python-pptx
- **OCR**: EasyOCR/Tesseract for embedded images in slides
- **Output**: Slide-level pages

### 10.4 Image Parser

- **Primary**: EasyOCR (GPU-accelerated)
- **Fallback**: Tesseract
- **Output**: Single-page document with OCR text

### 10.5 GLM-OCR Parser

**File**: `core/parsers/glm_ocr.py`

Structured document OCR using the GLM-OCR model (0.9B params) served via Ollama. Activated when `SWITCHES["GLM_OCR"] = True`.

**Architecture**: CogViT encoder + PP-DocLayout-V3 + GLM-0.5B decoder (OmniDocBench V1.5 score: 94.62, #1 overall).

| Parameter | Value |
|-----------|-------|
| Model | `glm-ocr-32k` (custom Modelfile: 32K ctx, 8K output) |
| API | Ollama `/api/generate` (NOT `/api/chat`) |
| Max image dim | 2048 px |
| Concurrency | 3 workers (semaphore-controlled) |
| Timeout | 120s (text), 180s (table) |

**Three-Pass Strategy** — each page is analyzed with three specialized prompts:

| Pass | Prompt | Purpose |
|------|--------|---------|
| 1 | `"Text Recognition:"` | Body text, headings, paragraphs |
| 2 | `"Table Recognition:"` | Tables → Markdown tables |
| 3 | `"Figure Recognition:"` | Charts, diagrams → structured descriptions |

Results from all three passes are merged per page. Empty passes are skipped.

**Concurrent Processing** (`glm_ocr_parse_concurrent`):
- Converts PDF pages to images (150 DPI via PyMuPDF)
- Processes all pages in parallel with semaphore limiting (default 3)
- Returns combined Markdown output per page

**Key Design Decisions**:
- Uses Ollama HTTP API (not local model loading) — no GPU memory consumed by the backend process
- Images resized to max 2048px (vs 1280px for VLM) — GLM-OCR handles higher resolution
- Custom Modelfile extends default context from 2K to 32K for multi-page documents

---

## 11. Performance Architecture

### 11.1 Caching

| Component | Strategy |
|-----------|----------|
| Embedding model | Lazy-loaded singleton (GPU) |
| Cross-encoder | Lazy-loaded singleton (GPU, FP16) |
| LLM instances | Per-(model, port) cached instances |
| BM25 index | Pickle-persisted, loaded on demand |

### 11.2 Concurrency

| Mechanism | Detail |
|-----------|--------|
| Ollama concurrency | Semaphore-limited (env `OLLAMA_CONCURRENCY`, default 2) |
| Sub-query parallelism | 2 workers max (GPU_QUERY_LLM + GPU_QUERY_LLM2) |
| Mind map descriptions | Batch 4 nodes × 2 parallel LLM calls |
| Async throughout | All I/O operations use async/await |

### 11.3 GPU Memory

| Model | Approximate VRAM |
|-------|-----------------|
| Main LLM (Qwen3-14B quantized) | ~28GB |
| nomic-embed-text-v1.5 | ~0.5GB |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | ~0.1GB |
| EasyOCR | ~0.2GB |
| VLM (qwen3-vl:8b, when active) | ~8GB |
| GLM-OCR (served by Ollama) | ~2GB (in Ollama process, not backend) |

### 11.4 GPU Memory Management

PyTorch's CUDA memory allocator caches freed GPU memory and does not return it to the OS.
To prevent the backend from accumulating unreleased GPU memory, `torch.cuda.empty_cache()`
is called after every heavy GPU operation:

| Location | File | After |
|----------|------|-------|
| Batch embedding | `vectorstore.py` | `embed_documents()` in both `save_documents_to_store()` and `add_existing_document_to_store()` |
| Cross-encoder re-ranking | `retriever.py` | `cross_encoder.predict()` |
| EasyOCR inference | `image.py` | `reader.readtext()` (GPU mode only) |

---

## 12. Testing Architecture

### 12.1 Organization

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # @pytest.mark.unit
├── integration/         # @pytest.mark.integration
└── e2e/                 # @pytest.mark.e2e
```

### 12.2 Key Fixtures

| Fixture | Purpose |
|---------|---------|
| `patched_db` | Mocks MongoDB with mongomock across all modules |
| `async_client` | Async HTTP test client for FastAPI |
| `auth_headers` | JWT token for protected route testing |
| `mock_invoke_llm` | Mocks LLM responses for deterministic tests |

### 12.3 Configuration

- **pytest.ini**: `asyncio_mode = auto`, strict markers
- **Coverage**: 75% threshold, source = `app/`, `core/`, `agent/`
- **Environment**: Set in `conftest.py` before imports (no `.env` needed)
- **Markers**: `unit`, `integration`, `e2e`, `slow`

---

## 13. Deployment

### 13.1 Docker Compose

```bash
make build    # Build image + pull mongo + install ollama + configure models
make run      # docker compose up (attached)
make ollama   # Start dual Ollama instances (ports 11434, 11435)
```

### 13.2 Manual

```bash
python backend.py     # uvicorn on port 8000
python frontend.py    # npm install + npm run dev on port 8080
```

### 13.3 Required Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | MongoDB connection string |
| `SECRET_KEY` | JWT signing key |
| `MAIN_MODEL` | Ollama model name (e.g., `qwen3:14b`) |
| `API_KEY_1`–`API_KEY_6` | Gemini API keys (round-robin) |
| `OPENAI_API` | OpenAI API key |
| `QUERY_URL` | Remote GPU endpoint |
| `VISION_URL` | VLM endpoint |
| `REMOTE_GPU` | Boolean: use remote GPU |
| `USE_VISION_MODEL` | Force VLM for all PDFs |
| `LOCAL_BASE_URL` | Ollama base URL (default: `http://localhost`) |

---

## 14. Data Flow Diagrams

### 14.1 Query Processing

```
User Question
      │
      ▼
  POST /query/
      │
      ▼
  ┌─ Decomposition ─┐
  │  LLM check:      │
  │  complex?         │
  └──┬────────┬──────┘
     │        │
   Simple   Complex
     │        │
     │    ┌───┴───┐
     │    ▼       ▼
     │  Worker1  Worker2  (parallel, 2 models)
     │    │       │
     │    └───┬───┘
     │        │
     │    Combination LLM
     │        │
     ▼        ▼
  Agent Pipeline (per query):
     │
     ├─ Retriever → Hybrid search (vector + BM25 + RRF)
     │                Entity boost, adaptive chunks
     │
     ├─ Evaluator → CRAG: sufficient/ambiguous/insufficient
     │                Re-retrieve if needed (max 2)
     │
     ├─ Generate → LLM invocation (structured output)
     │               Returns: answer + action + sources
     │
     └─ Router → answer     → END
                 web_search  → search → GENERATE (loop, max 2)
                 sql_query   → execute → GENERATE (loop, max 6)
                 summarizer  → load summary → END
                 failure     → self_knowledge → END
```

### 14.2 Document Ingestion

```
File Upload
      │
      ▼
  Save to disk: data/{user_id}/threads/{thread_id}/uploads/
      │
      ▼
  extract_document() per file
      │
       ├─ PDF → PyMuPDF + optional VLM/GLM-OCR
       ├─ Excel/CSV → Pandas → SQLite
       ├─ PPTX → python-pptx + OCR/VLM/GLM-OCR
       ├─ Image → EasyOCR/Tesseract (or GLM-OCR)
       └─ Markdown → html2text
      │
      ▼
  Document(id, type, file_name, content=[Page], title, full_text)
      │
      ├─ Background: Summarization (chunk → summarize → combine)
      ├─ Background: Mind Map (keywords → LLM nodes → descriptions)
      └─ Background: SQLite loading (spreadsheets only)
      │
      ▼
  save_documents_to_store():
      │
      ├─ Chunk (512 chars, 100 overlap, sentence-aware)
      ├─ Embed (nomic-embed-text-v1.5, batch=128)
      ├─ NER (spaCy: PERSON, ORG, GPE, DATE...)
      ├─ Extract keywords + triples
      ├─ Store → ChromaDB (vectors + metadata)
      ├─ Build → BM25 index (pickle)
      └─ Persist → Triple store (SQLite)
      │
      ▼
  MongoDB: Add doc metadata to thread
  Socket.IO: Emit progress events
```
