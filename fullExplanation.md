# PRISM - Multi-Modal Enterprise Knowledge Synthesis Platform

## What Is This?

Imagine you have hundreds of documents — PDFs, spreadsheets, PowerPoint presentations, scanned images — and you need to quickly find answers, extract insights, and generate analyses from all of them. Instead of manually reading through each document, PRISM lets you upload everything, ask questions in plain English, and get precise answers with exact source citations.

Think of it as a **private, enterprise-grade ChatGPT that actually reads your documents** and tells you exactly which page and paragraph its answer came from.

**What PRISM does:**
- Accepts documents in any format (PDF, Excel, PowerPoint, Word, images, CSV, etc.)
- Reads and understands them using AI (including scanned documents, handwritten text, charts, and tables)
- Lets you ask questions and get cited answers with confidence scores
- Generates summaries, mind maps, insights, strategic roadmaps, and technical analyses
- Creates new documents (PPTX, DOCX, PDF) and Excel files from your data
- Supports web search fallback when documents don't have the answer

---

## Architecture Diagram

```
                                    PRISM SYSTEM ARCHITECTURE
 ============================================================================================================

  BROWSER (React SPA)                                   BACKEND (Python/FastAPI)
 +-------------------------------+                    +----------------------------------------------------+
 |                               |                    |                                                    |
 |  +----------+ +------------+  |   REST API (8000)  |  +---------------+     +------------------------+  |
 |  | Login /  | | Thread     |  | -----------------> |  | FastAPI App   |---->| JWT Auth Middleware     |  |
 |  | Register | | Sidebar    |  |                    |  | (app/main.py) |     | (Bearer token / query) |  |
 |  +----------+ +------------+  |                    |  +-------+-------+     +------------------------+  |
 |                               |                    |          |                                          |
 |  +----------+ +------------+  |   Socket.IO (WS)   |          v                                          |
 |  | Chat     | | Right      |  | <----------------> |  +-------+-------+     +------------------------+  |
 |  | Messages | | Sidebar    |  |  (real-time events) |  |   API Routes  |     |  Socket.IO Handler     |  |
 |  | (Q&A)    | | (Analysis) |  |                    |  | /query /upload|     | (progress, heartbeat)  |  |
 |  +----------+ +------------+  |                    |  | /thread /extra|     +------------------------+  |
 |                               |                    |  +-------+-------+                                  |
 |  +----------+ +------------+  |                    |          |                                          |
 |  | Document | | Export     |  |                    |          v                                          |
 |  | Creator  | | (PDF/PPTX) |  |                    |  +------+-----------------------------------------------+
 |  +----------+ +------------+  |                    |  |              CORE ENGINE                          |  |
 |                               |                    |  |                                                   |  |
 +-------------------------------+                    |  |  +-----------+  +-----------+  +---------------+  |  |
                                                      |  |  | Document  |  | Embedding |  | LLM Client    |  |  |
  Served via Nginx (port 8080)                        |  |  | Parsers   |  | & Vector  |  | invoke_llm()  |  |  |
  Proxies /api/* to backend                           |  |  | (PDF,XLSX |  | Store     |  | with fallback |  |  |
                                                      |  |  |  PPTX,IMG)|  | (ChromaDB)|  | chain         |  |  |
                                                      |  |  +-----------+  +-----------+  +-------+-------+  |  |
                                                      |  |                                        |           |  |
                                                      |  |  +-----------+  +-----------+          |           |  |
                                                      |  |  | SQLite    |  | BM25      |          v           |  |
                                                      |  |  | Manager   |  | Keyword   |  +-------+-------+  |  |
                                                      |  |  |(Spread-   |  | Index     |  | LangGraph     |  |  |
                                                      |  |  | sheets)   |  |           |  | Agent         |  |  |
                                                      |  |  +-----------+  +-----------+  | (Query Graph) |  |  |
                                                      |  |                                +---------------+  |  |
                                                      |  +----------------------------------------------+---+  |
                                                      |                                                        |
                                                      +----------------------------------------------------+
                                                                         |
                                           +-----------------------------+-----------------------------+
                                           |                             |                             |
                                           v                             v                             v
                                   +---------------+            +----------------+           +-----------------+
                                   |   MongoDB     |            |  Ollama (GPU)  |           | External APIs   |
                                   |  (port 27017) |            | PORT1: 11434   |           | - Gemini (x6)   |
                                   |               |            |  (Query LLM)   |           | - OpenAI        |
                                   | Users, Threads|            | PORT2: 11435   |           | - Tavily Search |
                                   | Chats, Docs   |            |  (Vision LLM)  |           +-----------------+
                                   +---------------+            +----------------+

                                   +------------------------------------------------------------------+
                                   |                        FILE SYSTEM                                |
                                   |  data/{user_id}/                                                  |
                                   |    threads/{thread_id}/uploads/    (original files)                |
                                   |    threads/{thread_id}/parsed/     (extracted text as JSON)        |
                                   |    threads/{thread_id}/mind_maps/  (generated mind maps)           |
                                   |    threads/{thread_id}/sqlite/     (spreadsheet SQL tables)        |
                                   |    chroma/                         (vector embeddings)             |
                                   |    bm25/{thread_id}.pkl            (keyword search index)          |
                                   |    triples/{thread_id}.db          (entity relationships)          |
                                   +------------------------------------------------------------------+
```

---

## Data Flow Diagram

This diagram shows how data moves through the system from the moment a user interacts with it.

### Flow 1: Document Upload & Ingestion

```
                           DOCUMENT UPLOAD & INGESTION FLOW
 ===========================================================================================

  USER                    FRONTEND                     BACKEND                   STORAGE
  ----                    --------                     -------                   -------

  Selects files     -->  FormData with files     -->  POST /upload
  (PDF, XLSX,            + thread_name                    |
   PPTX, images,                                         v
   CSV, DOCX...)                                  [1] Save originals
                                                   to uploads/ dir  ---------> data/.../uploads/
                                                         |
                                                         v
                                                  [2] PARSE EACH FILE
                                                  +------------------+
                                                  | PDF  -> PyMuPDF  |
                                                  | XLSX -> openpyxl |
                                                  | PPTX -> pptx lib |
                                                  | IMG  -> OCR      |
                                                  | DOCX -> docx lib |
                                                  +--------+---------+
                                                           |
                                              +------------+-------------+
                                              |            |             |
                                              v            v             v
                                         [VLM Model]  [GLM-OCR]    [EasyOCR/
                                         qwen3.5:9b   (tables,      Tesseract]
                                         (visual      formulas)     (fallback)
                                          understanding)
                                              |            |             |
                                              +-----+------+-------------+
                                                    |
                                                    v
                                            [3] COMBINED TEXT
                                            per page/sheet/slide
                                                    |
                                          +---------+---------+
                                          |                   |
                                          v                   v
                                   Save parsed JSON    [4] CHUNK TEXT
                                   to parsed/ dir      Parent: 1500 chars
                                          |            Child:  500 chars
                                          |                   |
                                          v            +------+------+
                                   data/.../parsed/    |             |
                                                       v             v
                                                 [5] EMBED      [6] BM25
                                                 nomic-embed     Keyword
                                                 text-v1.5       Tokenize
                                                       |             |
                                                       v             v
                                                   ChromaDB     .pkl file
                                                   (vectors)    (keywords)
                                                       |
                                                       v
                                              [7] EXTRACT ENTITIES
                                              (people, orgs, dates)
                                                       |
                                                       v
                                              Triple Store (SQLite)
                                              "Apple -> founded_by -> Steve Jobs"

                                              [8] IF SPREADSHEET:
                                              Load into SQLite for SQL queries
                                                       |
                                                       v
                                              thread.db (queryable tables)

                                              [9] BACKGROUND TASKS:
                                              - Auto-summarize documents
                                              - Generate mind map (if enabled)
                                              - Extract insights
                                                       |
                                                       v
                                              Progress sent to frontend
                                              via Socket.IO events
```

### Flow 2: Question Answering (The RAG Pipeline)

```
                            QUESTION ANSWERING DATA FLOW
 ===========================================================================================

  USER                    FRONTEND                     BACKEND (LangGraph Agent)
  ----                    --------                     -------

  Types question    -->  POST /query              -->  [1] DECOMPOSITION
  + selects mode         {question, thread_id,              |
  (Internal/External)     mode, use_context}          Is this a complex question?
                                                      +-----+------+
                                                      | YES         | NO
                                                      v             v
                                                Split into       Use as-is
                                                sub-queries      (rewrite with
                                                + generate       chat context)
                                                alt phrasings
                                                      |             |
                                                      +------+------+
                                                             |
                                                             v
                                                      [2] RETRIEVER
                                                      +------------------+
                                                      |                  |
                                                      v                  v
                                                 Vector Search      BM25 Search
                                                 (ChromaDB)         (keyword match)
                                                 "What is the       "strategy Q1
                                                  strategy?"         revenue target"
                                                      |                  |
                                                      v                  v
                                                 Ranked results     Ranked results
                                                      |                  |
                                                      +--------+---------+
                                                               |
                                                               v
                                                      [3] RRF MERGE
                                                      (Reciprocal Rank Fusion)
                                                      Combines both rankings
                                                      into single scored list
                                                               |
                                                               v
                                                      [4] RE-RANK
                                                      Cross-encoder model
                                                      scores each chunk's
                                                      relevance to question
                                                               |
                                                               v
                                                      [5] EXPAND CONTEXT
                                                      Child chunks -> Parent chunks
                                                      + Entity triples injected
                                                      + VLM visual answer (if visual query)
                                                               |
                                                               v
                                                      [6] EVALUATOR (CRAG)
                                                      "Are these chunks sufficient?"
                                                      +-------+--------+
                                                      |       |        |
                                                      v       v        v
                                                Sufficient Ambiguous Insufficient
                                                      |       |        |
                                                      v       v        v
                                                  Continue Continue  Re-retrieve
                                                                     (max 2x)
                                                      |       |        |
                                                      +-------+--------+
                                                               |
                                                               v
                                                      [7] GENERATE
                                                      LLM produces answer
                                                      using chunks as context
                                                      + chat history
                                                      + thread instructions
                                                               |
                                                               v
                                                      [8] ROUTER DECISION
                                                +------+------+------+------+------+
                                                |      |      |      |      |      |
                                                v      v      v      v      v      v
                                             ANSWER  WEB   SQL    EXCEL SUMMA- FAILURE
                                                   SEARCH QUERY  CREATE RIZE
                                                |      |      |      |      |      |
                                                |      v      v      v      v      v
                                                |   Tavily  Execute  Build  Doc/  Self-
                                                |   Search  on       .xlsx  Global Knowledge
                                                |   API     SQLite   file   Summary fallback
                                                |      |      |      |      |      |
                                                |      +--+---+      |      +--+---+
                                                |         |          |         |
                                                |         v          |         v
                                                |    Loop back       |    Return to
                                                |    to GENERATE     |    user
                                                |         |          |
                                                +---------+----------+
                                                          |
                                                          v
                                                   [9] FINAL ANSWER
                                                   + source citations
                                                   + confidence score
                                                   (high/medium/low)
                                                          |
                                                          v
  Sees answer       <--  ChatMessage renders  <--  Save to MongoDB
  with sources           markdown + sources        (thread.chats[])
  and confidence         accordion
```

### Flow 3: Analysis & Export

```
                           ANALYSIS & EXPORT DATA FLOW
 ===========================================================================================

  USER                         FRONTEND                        BACKEND
  ----                         --------                        -------

  Clicks "Insights"     -->  api.insights()            -->  Load parsed documents
  in right sidebar           POST /insights                      |
                                                                 v
                                                          invoke_llm() with
                                                          analysis prompt
                                                                 |
                                                                 v
                                                          Structured JSON output
                                                          (themes, strengths,
                                                           improvements, etc.)
                                                                 |
  Sees InsightsModal    <--  Renders analysis data    <--  Save to file + return
  with formatted data        in modal component            to insights/{doc_id}.json
        |
        v
  Clicks "Export PDF"   -->  pdfmake generates PDF
  or "Export PPTX"           client-side (no backend
                             call needed)
                                   |
                                   v
                             Browser download triggered
```

---

## Understanding the Product (Plain Language)

### The Problem

Organizations produce enormous amounts of documents: reports, presentations, financial spreadsheets, research papers, scanned memos, images with text. When someone needs to find a specific answer, they have to:

1. Remember which document might contain the answer
2. Open that document and search through it manually
3. Cross-reference with other documents
4. Synthesize information from multiple sources
5. Repeat this for every question

This takes hours of work that could be automated.

### The Solution

PRISM creates a **knowledge base** from all your uploaded documents. Behind the scenes, it:

1. **Reads every document** using multiple AI models (text extraction, OCR for scanned pages, vision AI for charts and figures)
2. **Breaks the content into small, searchable pieces** (called "chunks") and stores them in a searchable database
3. **When you ask a question**, it finds the most relevant pieces across ALL documents, evaluates whether they're sufficient, and generates a precise answer
4. **Cites its sources** so you can verify the answer yourself (document name, page number, exact passage)
5. **Falls back intelligently** - if documents don't have the answer, it can search the web or use general AI knowledge

### Who Uses This?

- **Analysts** who need to quickly extract insights from financial reports
- **Legal teams** reviewing large document sets
- **Researchers** synthesizing findings from multiple papers
- **Business strategists** who need cross-document analysis
- **Anyone** who works with large volumes of documents

---

## The Tech Stack (What Powers Each Layer)

### Frontend (What the User Sees)

| Technology | Purpose |
|---|---|
| React 18 + TypeScript | UI framework with type safety |
| Vite | Fast build tool and dev server |
| Tailwind CSS | Utility-first styling |
| shadcn/ui (Radix) | 40+ headless UI components (buttons, modals, panels, etc.) |
| React Router v6 | Client-side page navigation |
| Socket.IO Client | Real-time updates from backend |
| ReactFlow | Interactive mind map visualization |
| Recharts | Data charts and visualizations |
| pdfmake | Client-side PDF generation for exports |
| pptxgen | Client-side PowerPoint generation for exports |

### Backend (What Processes Your Data)

| Technology | Purpose |
|---|---|
| Python 3.11+ / FastAPI | High-performance async web framework |
| LangGraph | Agent state machine for query orchestration |
| LangChain | LLM abstractions and output parsing |
| Ollama | Local LLM inference (GPU-accelerated) |
| ChromaDB | Vector database for semantic search |
| PyMuPDF (fitz) | PDF parsing and image extraction |
| openpyxl | Excel file parsing |
| python-pptx | PowerPoint parsing |
| EasyOCR / Tesseract | Optical character recognition |
| nomic-embed-text-v1.5 | Text embedding model (768 dimensions) |
| MongoDB (pymongo) | User accounts, threads, chat history |
| SQLite | Spreadsheet data for SQL queries |
| Socket.IO (python-socketio) | Real-time event streaming |
| pydantic / pydantic-settings | Data validation and configuration |
| bcrypt | Password hashing |
| PyJWT | JSON Web Token authentication |

### External Services

| Service | Purpose |
|---|---|
| Ollama (local) | Runs LLMs on your GPU (primary inference) |
| Google Gemini | Fallback LLM (6 API keys for rate limit rotation) |
| OpenAI GPT-4o-mini | Final fallback LLM |
| Tavily | Web search when documents don't have the answer |

### Infrastructure

| Component | Port | Purpose |
|---|---|---|
| Nginx | 8080 | Serves frontend, proxies API requests |
| FastAPI/Uvicorn | 8000 | Backend API server |
| Ollama Instance 1 | 11434 | Query-answering LLM (e.g., gpt-oss:20b) |
| Ollama Instance 2 | 11435 | Vision LLM for document understanding (qwen3.5:9b) |
| MongoDB | 27017 | Primary database |

---

## Deep Dive: How Each Major Feature Works

### 1. Document Ingestion (Upload to Searchable)

When you upload a file, PRISM runs a multi-stage pipeline:

**Stage 1 - Raw Parsing:** Extract text from the file format.
- PDFs: PyMuPDF extracts text layer; if text is missing (scanned PDF), falls back to OCR
- Excel: openpyxl reads every sheet, handles merged cells, preserves table structure
- PowerPoint: python-pptx extracts text from slides, shapes, SmartArt diagrams
- Images: Directly sent to OCR
- Word docs: python-docx extracts text, tables, embedded images

**Stage 2 - AI-Enhanced Understanding (runs in parallel):**
- **Vision Language Model (VLM):** Converts each page/slide to an image and sends it to qwen3.5:9b. This model "sees" the page and produces structured Markdown — understanding charts, diagrams, handwritten notes, complex layouts that text extraction misses.
- **GLM-OCR:** Specialized OCR model for tables, formulas, and structured documents. Produces clean Markdown with proper table formatting.
- **EasyOCR/Tesseract:** Traditional OCR as fallback.

**Stage 3 - Chunking:** The combined text is split into hierarchical chunks:
- Parent chunks (1500 characters): Provide broader context
- Child chunks (500 characters): Precise retrieval units
- Each child stores a reference to its parent for context expansion during retrieval

**Stage 4 - Embedding & Indexing:**
- Each child chunk is embedded using nomic-embed-text-v1.5 (768-dimensional vectors)
- Stored in ChromaDB (vector database) for semantic search
- A BM25 index is built for keyword-based search
- Entity-relationship triples are extracted (e.g., "Company X acquired Company Y in 2024")

**Stage 5 - Spreadsheet Special Handling:**
- Excel/CSV files are also loaded into SQLite databases
- This allows the agent to write and execute SQL queries against your data
- Useful for "What was the total revenue in Q3?" type questions

### 2. Question Answering (The RAG Pipeline)

RAG stands for **Retrieval-Augmented Generation** — the AI retrieves relevant information from your documents before generating an answer.

**Step 1 - Query Understanding:**
The system first analyzes your question:
- If it references previous conversation ("what about the other one?"), it rewrites it with full context
- If it's complex ("Compare the Q1 and Q2 strategies and list differences"), it decomposes it into sub-questions
- It generates alternative phrasings for broader search coverage

**Step 2 - Hybrid Retrieval:**
Two search methods run simultaneously:
- **Vector search** (ChromaDB): Finds chunks that are semantically similar (understands meaning)
- **BM25 search**: Finds chunks with matching keywords (exact term matching)
- Results are merged using Reciprocal Rank Fusion (RRF), which combines both rankings fairly

**Step 3 - Re-ranking:**
A cross-encoder model re-scores each chunk for relevance to the specific question. This is more accurate than the initial retrieval but slower, so it only runs on the top candidates.

**Step 4 - Quality Evaluation (CRAG):**
An evaluator LLM checks: "Are these retrieved chunks sufficient to answer the question?"
- **Sufficient**: Proceed to answer generation
- **Ambiguous**: Proceed but with lower confidence
- **Insufficient**: Re-retrieve with broader parameters (up to 2 retries)

**Step 5 - Answer Generation:**
The LLM receives:
- The relevant chunks (with document titles and page numbers)
- Entity relationship context
- Recent chat history
- Thread-level custom instructions
- Visual context from VLM (if the query references figures/slides)

It produces a structured response with the answer text, source citations, confidence score, and a routing decision.

**Step 6 - Routing:**
Based on the generated response, the agent decides the next action:
- **Answer**: Return directly to the user
- **Web Search**: The documents don't have the answer; search the web via Tavily, then re-generate
- **SQL Query**: The question needs numerical analysis of spreadsheet data; generate and execute SQL
- **Excel Create**: The user asked for data in spreadsheet format; generate an .xlsx file
- **Summarize**: The user asked for a document or global summary
- **Self-Knowledge**: All methods failed; provide an honest "I don't have enough information" response

**Step 7 - Combination (for decomposed queries):**
If the original question was split into sub-questions, each sub-answer is synthesized into a coherent final answer.

### 3. LLM Fallback Chain

PRISM never wants to leave you without an answer. The LLM invocation system has a three-tier fallback:

```
Attempt 1: Local Ollama (your GPU) ---- fastest, free, private
    |
    | (if fails: timeout, GPU error, model not loaded)
    v
Attempt 2: Google Gemini 2.5 Flash ---- fast, cheap, 6 API keys rotated
    |
    | (if fails: rate limited, API error)
    v
Attempt 3: OpenAI GPT-4o-mini --------- reliable last resort
```

Each tier includes retry logic with self-correction: if the LLM produces malformed JSON, the error is fed back into the next attempt so the model can fix its output.

### 4. Studio Features

Beyond Q&A, PRISM generates rich analyses:

- **Mind Maps**: Hierarchical visualization of document themes and relationships (rendered with ReactFlow)
- **Summaries**: Per-document and cross-document summaries
- **Word Clouds**: TF-IDF frequency visualization
- **Insights**: Key themes, discussion points, strengths, areas for improvement, future considerations
- **Strategic Roadmap**: Vision, baseline assessment, strategic pillars, phased implementation plan
- **Technical Roadmap**: Technical scope, architecture decisions, implementation timeline
- **Strategic Analysis**: Market positioning, stakeholder mapping, risk assessment
- **Technical Analysis**: Technical readiness, innovation areas, implementation concerns

All analyses can be exported as PDF or PowerPoint directly from the browser.

### 5. Document Creator

An interactive multi-step workflow for generating new documents from your knowledge base:

1. **Configure**: Choose document type (PPTX/DOCX/PDF), target audience, tone, source documents
2. **Outline**: AI generates a structured outline; you can edit sections
3. **Generate**: AI writes content for each section (multiple versions per section)
4. **Iterate**: Provide feedback on any section to regenerate it
5. **Approve**: Lock in final versions for each section
6. **Export**: Download as PPTX, DOCX, or PDF

### 6. Excel Skill

Describe what you need in plain English ("Create a spreadsheet comparing Q1 and Q2 revenue by region"), and PRISM generates a formatted .xlsx file with data extracted from your documents.

---

## How Data Is Stored

PRISM uses four different storage systems, each optimized for its purpose:

| Storage | What It Holds | Why This Storage |
|---|---|---|
| **MongoDB** | User accounts, threads, chat history, document metadata | Flexible document model for nested thread/chat structures |
| **ChromaDB** | Vector embeddings of text chunks | Purpose-built for fast similarity search |
| **SQLite** (per thread) | Spreadsheet data loaded as tables | Enables SQL queries against uploaded Excel/CSV files |
| **File System** | Original uploads, parsed JSON, mind maps, exports, BM25 indexes, entity triples | Large binary data and serialized objects |

**Data Isolation**: Each user's data is completely separate — different ChromaDB collections, different file directories, different BM25 indexes. Users can never access each other's documents.

---

## Authentication & Security

- **JWT tokens** (24-hour expiration) authenticate every request
- Passwords stored as bcrypt hashes (never plaintext)
- Token sent as `Authorization: Bearer <token>` header (or `?token=` query param for file downloads)
- Every endpoint validates token and checks user ownership before returning data
- CORS configured for cross-origin requests

---

## Real-Time Updates

The backend pushes real-time updates to the frontend via Socket.IO:

- **Upload progress**: Per-file parsing status during document ingestion
- **Document creator progress**: Per-section generation updates
- **Thread title updates**: When the backend auto-generates a thread name from the first message
- **Heartbeat**: 20-second ping to keep connections alive

---

## Feature Switches

PRISM has 14 feature switches in `core/constants.py` that control system behavior without code changes:

| Switch | Default | What It Controls |
|---|---|---|
| DECOMPOSITION | ON | Break complex queries into sub-questions |
| CORRECTIVE_RETRIEVAL | ON | Re-retrieve if chunks are insufficient (CRAG) |
| SUMMARIZATION | ON | Auto-summarize documents after upload |
| MIND_MAP | OFF | Generate mind maps during summarization |
| HYDE | OFF | Hypothetical Document Embeddings (slower but better retrieval) |
| FALLBACK_TO_GEMINI | OFF | Use Gemini API when local LLM fails |
| FALLBACK_TO_OPENAI | OFF | Use OpenAI API as final fallback |
| DOCUMENT_CREATOR | ON | Interactive document generation feature |
| GLM_OCR | ON | Specialized OCR for tables and formulas |
| EXCEL_SKILL | ON | Excel file generation from chat |
| DOC_BATCH_REDUCER | ON | MapReduce for large multi-document queries |
| USE_VLM_FOR_ANSWER | ON | Visual AI for page/slide/figure queries |
| DISABLE_THINKING | ON | Skip LLM "thinking" mode for faster responses |
| REMOTE_GPU | .env | Use HTTP-based remote LLM instead of local Ollama |

---

## Running the System

### Prerequisites
- Python >= 3.11.8
- Node.js (for frontend)
- GPU with CUDA support (for local LLM inference)
- MongoDB instance
- Ollama installed with models pulled

### Quick Start (Local Development)
```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your API keys and configuration

# 2. Start Ollama instances
make ollama                    # Starts on ports 11434 and 11435

# 3. Start backend
python backend.py              # FastAPI on port 8000

# 4. Start frontend (in another terminal)
python frontend.py             # React dev server
```

### Docker Deployment
```bash
make build                     # Build image + pull dependencies
make run                       # Start containers (app + MongoDB)
```

The Docker setup builds the frontend, serves it via Nginx on port 8080, and proxies API calls to the backend on port 8000.

---

## Explaining This to Others

### The Elevator Pitch
> "PRISM is an AI-powered document analysis platform. Upload any documents — PDFs, spreadsheets, presentations, even scanned images — and ask questions in plain English. It finds the exact answer across all your documents and tells you exactly where it came from. It also generates summaries, insights, strategic roadmaps, and can even create new documents from your data."

### For Technical Audiences
> "It's a RAG (Retrieval-Augmented Generation) system with hybrid retrieval (vector + BM25 + RRF), CRAG corrective evaluation, query decomposition, and a multi-tier LLM fallback chain. Documents are ingested through a multi-modal pipeline (text extraction + VLM + OCR), chunked hierarchically, and indexed in ChromaDB with entity-enriched context. The query agent is a LangGraph state machine that can route to web search, SQL execution, document generation, or direct answer based on confidence evaluation."

### For Business Audiences
> "Instead of spending hours searching through documents for answers, your team uploads everything to PRISM and asks questions like they would ask a colleague who has read every document. The system gives precise answers with page-level citations, generates executive summaries, creates strategic roadmaps, and can even produce new presentations from your knowledge base. It runs on your own infrastructure, so sensitive documents never leave your network."
