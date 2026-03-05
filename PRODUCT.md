# PRISM — Product Overview

## Executive Summary

PRISM (Multi-Modal Enterprise Knowledge Synthesis Platform) is a document analysis system that enables organizations to ingest multi-format files, build a unified knowledge base, and answer complex questions using an AI-powered agentic pipeline. It goes beyond simple document Q&A by offering strategic analysis, mind maps, insights extraction, roadmap generation, and cross-document synthesis — turning static documents into actionable intelligence.

---

## 1. Core Value Proposition

| Dimension | What PRISM Delivers |
|-----------|-------------------|
| **Multi-Format Ingestion** | Upload PDFs, spreadsheets (Excel/CSV), presentations (PPTX/PPT), images, and Markdown — all indexed into a unified knowledge base |
| **Intelligent Q&A** | Ask natural-language questions and receive grounded, cited answers synthesized across all uploaded documents |
| **Enterprise Privacy** | Runs entirely on local infrastructure (Ollama LLMs on GPU) — no data leaves the organization |
| **Strategic Intelligence** | Automatically generates insights, SWOT analyses, roadmaps, and mind maps from uploaded documents |
| **Spreadsheet Intelligence** | Converts spreadsheet questions to SQL queries, enabling natural-language data analysis |

---

## 2. Agentic Architecture (User Perspective)

PRISM uses a multi-node AI agent (LangGraph state machine) that autonomously decides the best strategy to answer each question. The agent operates through an intelligent decision pipeline:

### 2.1 Query Understanding

When a user asks a question, the system first analyzes whether the query is:
- **Simple** — answerable directly from retrieved documents
- **Complex** — requires decomposition into sub-questions that are answered independently and then combined
- **Data-Oriented** — requires SQL execution against spreadsheet data
- **Broad** — requires document or global summarization

The agent uses a **Decomposition Engine** that breaks complex, multi-part questions into 2–4 focused sub-queries, processes each through the full pipeline in parallel (using multiple GPU-served models), and then combines the sub-answers into a coherent response.

### 2.2 Intelligent Routing

After retrieval and initial generation, the agent's **Router** decides the next action:

```
Question → Retrieve → Evaluate → Generate → Route
                                                 ├→ Direct Answer (confident, well-supported)
                                                 ├→ Web Search (needs external data, EXTERNAL mode)
                                                 ├→ SQL Query (spreadsheet question detected)
                                                 ├→ Document Summary (user asks for summary)
                                                 ├→ Global Summary (cross-document overview)
                                                 └→ Self-Knowledge (fallback to LLM knowledge)
```

### 2.3 Self-Correcting Retrieval (CRAG)

The agent doesn't blindly trust its first retrieval attempt. A **Corrective Retrieval-Augmented Generation (CRAG)** loop evaluates whether the retrieved context is sufficient:
- **Sufficient** — proceed to answer generation
- **Ambiguous** — refine the query and re-retrieve
- **Insufficient** — reformulate and try again (up to 2 attempts)

This ensures the user gets the most relevant context possible before the LLM generates an answer.

### 2.4 Confidence Scoring

Every answer includes a confidence score (High / Medium / Low) based on:
- Number of relevant chunks retrieved
- Cross-encoder re-ranking scores
- Retrieval evaluation verdict

Users can see at a glance how well-supported the answer is by the available documents.

---

## 3. User Features

### 3.1 Thread-Based Workspaces

Each analysis project lives in a **Thread** — an isolated workspace where users:
- Upload documents specific to a project or topic
- Ask questions within the context of those documents
- Build chat history that provides conversational context
- Set custom **Thread Instructions** (e.g., "Always respond in bullet points", "Focus on financial data")

### 3.2 Multi-Format Document Upload

| Format | Capabilities |
|--------|-------------|
| **PDF** | Full text extraction with page-level granularity. Optional VLM parsing for scanned/image-heavy PDFs. Optional GLM-OCR for structured table/formula/layout extraction |
| **Excel / CSV** | Automatic table detection, header inference, multi-sheet support. Loaded into SQL for natural-language querying |
| **PowerPoint (PPTX/PPT)** | Slide text extraction + OCR for embedded images and diagrams. VLM or GLM-OCR enhancement for complex slides |
| **Images (PNG/JPG/TIFF)** | OCR via EasyOCR or Tesseract for text extraction from photos, screenshots, diagrams |
| **Markdown** | Direct text indexing |

### 3.3 GLM-OCR (Structured Document Understanding)

When enabled (`GLM_OCR` switch), PRISM uses the **GLM-OCR** model (0.9B, #1 on OmniDocBench V1.5) for high-fidelity document OCR that goes beyond plain text extraction:

| Capability | What It Does |
|------------|-------------|
| **Table Recognition** | Converts complex tables (merged cells, multi-level headers) into proper Markdown tables |
| **Formula Extraction** | Recognizes mathematical formulas and outputs them in a structured format |
| **Layout Preservation** | Maintains reading order, column layouts, and heading hierarchy |
| **Figure Analysis** | Generates structured descriptions of charts, flowcharts, and diagrams |

GLM-OCR runs alongside the existing OCR pipeline — it is served via Ollama and does not require additional GPU memory from the backend process. It processes each page with three specialized passes (text, table, figure) and merges the results into structured Markdown.

### 3.4 Natural-Language Spreadsheet Queries

Users can ask questions like:
- *"What was the total revenue in Q3 2024?"*
- *"Compare employee counts across departments"*
- *"Show me the top 5 products by sales volume"*

The system automatically:
1. Detects that the question is about spreadsheet data
2. Generates an SQL query
3. Executes it against the in-memory database
4. Presents results in a formatted answer with the SQL query shown for transparency

The SQL engine supports up to 6 retries with query refinement if the initial SQL fails.

### 3.5 Web Search Integration (External Mode)

When operating in **External Mode**, the agent can:
- Detect when uploaded documents don't contain the answer
- Automatically generate 2–3 targeted web search queries
- Retrieve and synthesize web results alongside document context
- Clearly attribute which parts of the answer come from web vs. documents

### 3.6 Real-Time Streaming

All processing communicates progress via Socket.IO:
- Document upload and parsing status
- Mind map generation progress
- Query processing stages
- Users see live updates during long operations

### 3.7 Operating Modes

| Mode | Description |
|------|-------------|
| **Internal** | Answers grounded strictly in uploaded documents. No web search. Best for confidential analysis |
| **External** | Allows web search as a fallback when documents are insufficient. Best for research tasks |
| **Self-Knowledge** | Enables the LLM to use its general training knowledge when documents don't cover the topic |
| **Context Mode** | Uses conversation history to resolve references ("it", "the previous", etc.) |

---

## 4. RAG Features (Retrieval-Augmented Generation)

### 4.1 Hybrid Retrieval

PRISM combines two retrieval methods for comprehensive search:

| Method | How It Works | Strength |
|--------|-------------|----------|
| **Semantic Search** | Vector similarity via ChromaDB (nomic-embed-text-v1.5, 768-dim) | Understands meaning — "revenue growth" matches "sales increased" |
| **Keyword Search** | BM25 index (term frequency) | Catches exact terms, names, IDs that semantic search might miss |

Results are merged using **Reciprocal Rank Fusion (RRF)** — a proven technique that combines ranked lists from multiple search methods into a single, higher-quality ranking.

### 4.2 Multi-Query Expansion

For each user question, the retriever generates multiple search variants:
- **Original query** — the user's exact question
- **Resolved query** — rewritten version with resolved references and clarified intent
- **HyDE (Hypothetical Document Embedding)** — a generated hypothetical answer used as a search query, often finding more relevant passages than the question itself

### 4.3 Adaptive Retrieval

The system dynamically adjusts how many chunks to retrieve based on the thread's document count:

| Documents in Thread | Chunks Retrieved | Minimum per Document |
|--------------------|-----------------|---------------------|
| 1–2 | 20 | 10 |
| 3–5 | 50 | 10 |
| 6–10 | 100 | 10 |
| >10 | Up to 500 | 10 |

This ensures both small and large document collections are well-covered without overwhelming the LLM context.

### 4.4 Cross-Encoder Re-Ranking

After initial retrieval, a **cross-encoder model** (ms-marco-MiniLM-L-6-v2) scores each chunk against the query for fine-grained relevance. This is more accurate than embedding similarity alone and catches subtle relevance that vector search misses.

### 4.5 Diversity Enforcement (MMR)

To prevent the answer from being dominated by a single section of a single document, **Maximal Marginal Relevance (MMR)** balances:
- **Relevance** — how well the chunk answers the question
- **Diversity** — how different the chunk is from already-selected chunks

This produces a set of chunks that covers multiple perspectives and document sections.

### 4.6 Entity-Aware Retrieval

The system extracts named entities (people, organizations, locations, dates) from both documents and queries:
- **At index time**: Entities are stored as chunk metadata
- **At query time**: Query entities boost matching chunks by 20% per entity match
- **Triple Store**: Subject–Predicate–Object relationships are stored in a dedicated SQLite database and injected into the LLM prompt for relationship-aware reasoning

### 4.7 Source Attribution

Every answer includes precise source citations:
- Document name and page number for document-sourced information
- URL, title, and favicon for web-sourced information
- Users can click through to verify any claim

---

## 5. Studio Features (Advanced Analysis)

### 5.1 Mind Maps

Automatically generates interactive mind maps from uploaded documents:
- Extracts key concepts and relationships
- LLM generates hierarchical node structure
- Batch-processes descriptions for each node
- Rendered as an interactive graph (ReactFlow) in the frontend
- Available per-document and as a global cross-document mind map

### 5.2 Document Summarization

- **Per-Document Summary**: Condensed overview of each uploaded document
- **Global Summary**: Cross-document synthesis highlighting themes, agreements, and contrasts
- Handles long documents via chunk-and-combine strategy (10k words per chunk)

### 5.3 Word Clouds

Visual representation of key terms using TF-IDF-based frequency analysis with stop word filtering. Gives users an instant visual overview of document content.

### 5.4 Insights Extraction

Automatically analyzes documents to extract:
- Strengths and advantages
- Areas for improvement
- Future considerations and opportunities
- Innovation aspects
- Key discussion points
- Technical outlines with pseudocode

### 5.5 Strategic Roadmap

Generates a comprehensive strategic roadmap including:
- Vision and end-goal definition
- Current baseline assessment
- SWOT analysis
- Phased implementation plan
- Risk identification and mitigation strategies
- Key metrics and milestones
- Enablers and dependencies

### 5.6 Technical Roadmap

Generates a technical implementation roadmap covering:
- Architecture recommendations
- Technology stack decisions
- Implementation phases
- Integration points
- Performance targets

### 5.7 Strategic & Technical Analysis

Deep-dive analyses providing:
- Strategic positioning assessment
- Technical capability evaluation
- Competitive landscape analysis
- Risk and opportunity mapping

---

## 6. Architecture Overview (Product Perspective)

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRISM Platform                          │
├─────────────┬───────────────────────────┬───────────────────────┤
│   INGEST    │        UNDERSTAND         │       PRESENT         │
├─────────────┼───────────────────────────┼───────────────────────┤
│ PDF Parser  │ Hybrid Retrieval          │ Chat Interface        │
│ Excel → SQL │ (Semantic + BM25 + RRF)   │ Source Citations       │
│ PPTX Parser │                           │ Confidence Scores      │
│ Image OCR   │ Cross-Encoder Re-Ranking  │                       │
│ GLM-OCR     │ CRAG Self-Correction      │ Mind Maps (ReactFlow) │
│ Markdown    │ Entity Relationships      │ Word Clouds           │
│             │                           │ Summaries             │
│             │ LangGraph Agent           │ Insights              │
│             │ (Retrieve → Evaluate →    │ Roadmaps              │
│             │  Generate → Route)        │ Analyses              │
│             │                           │                       │
│             │ Query Decomposition       │ Real-Time Streaming   │
│             │ Multi-Model Parallel      │ (Socket.IO)           │
│             │ SQL Query Engine          │                       │
│             │ Web Search (External)     │ Thread Workspaces     │
└─────────────┴───────────────────────────┴───────────────────────┘
```

---

## 7. Privacy & Security

| Feature | Detail |
|---------|--------|
| **Local LLM Inference** | All LLM processing runs on-premise via Ollama — no data sent to cloud APIs (unless explicitly enabled via fallback switches) |
| **Per-User Isolation** | Each user's documents, embeddings, and threads are fully isolated |
| **JWT Authentication** | Secure token-based access control |
| **No Telemetry** | No usage data collected or transmitted |
| **Configurable Fallbacks** | Cloud LLM fallbacks (Gemini/OpenAI) are off by default and require explicit configuration |

---

## 8. LLM Flexibility

PRISM's unified LLM invocation layer supports:

| Priority | Provider | When Used |
|----------|----------|-----------|
| 1 (Primary) | **Local Ollama** (GPU) | Always attempted first. Configurable model (default: Qwen3-14B) |
| 2 (Fallback) | **Google Gemini** | Only if enabled and local fails. Round-robin across 6 API keys |
| 3 (Last Resort) | **OpenAI** | Only if enabled and Gemini fails |

All providers are accessed through a single `invoke_llm()` function with automatic retry, JSON sanitization, and structured output parsing via Pydantic schemas.

---

## 9. Deployment Model

| Component | Technology |
|-----------|-----------|
| **Backend API** | Python / FastAPI (port 8000) |
| **Frontend** | React / TypeScript / Vite (port 8080) |
| **LLM Serving** | Ollama (ports 11434, 11435 for dual-model) |
| **Vector Database** | ChromaDB (embedded, persistent) |
| **Document Database** | MongoDB |
| **Spreadsheet Engine** | SQLite (in-memory per thread) |
| **Entity Store** | SQLite (file-based per thread) |
| **Containerization** | Docker Compose |
| **GPU Requirement** | NVIDIA GPU with CUDA support |
