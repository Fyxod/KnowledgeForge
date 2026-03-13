import asyncio
import json
import os
import time

import aiofiles
from langchain_core.messages import AIMessage, HumanMessage

from agent.graph_helpers import (
    build_main_prompt,
    build_self_knowledge_prompt,
    parallel_search,
)
from agent.state import AgentState
from agent.tools.search import search_tavily as search_tool
from agent.tools.sql_query import execute_sql_query
from core.constants import *
from core.embeddings.context_enrichment import extract_query_entities
from core.embeddings.retriever import get_thread_documents_retriever, rerank_chunks
from core.services.triple_store import TripleStore
from core.llm.client import invoke_llm
from core.llm.output_schemas.evaluator_output import EvaluatorLLMOutput
from core.llm.output_schemas.hyde_output import HyDELLMOutput
from core.llm.outputs import (
    MainLLMOutputExternal,
    MainLLMOutputInternal,
    MainLLMOutputInternalWithFailure,
    SelfKnowledgeLLMOutput,
)
from core.llm.prompts.evaluator_prompt import evaluator_prompt
from core.llm.prompts.hyde_prompt import hyde_prompt

os.makedirs("DEBUG", exist_ok=True)


async def retriever(state: AgentState) -> AgentState:
    """
    Retrieves documents based on the user's question with balanced multi-document representation.

    This function now uses the robust retrieval strategy that ensures:
    1. Balanced representation across all documents in the thread
    2. Each document gets proportional chunks based on total document count
    3. Better coverage when multiple documents are present
    4. Re-ranking for optimal relevance and diversity
    """
    # Skip RAG retrieval when the thread contains only spreadsheet files.
    # Spreadsheet data is queried via SQL which is faster and more accurate
    # than text chunks extracted from spreadsheet cells.
    if state.has_spreadsheet_data and state.spreadsheet_only:
        print(
            f"[retriever] Skipping RAG — spreadsheet-only thread for user {state.user_id}"
        )
        state.chunks = []
        state.confidence_score = "high"
        return state

    start_time = time.time()

    # Use the new robust retrieval function that ensures document diversity
    # Uses adaptive scaling based on document count
    query = state.query or state.resolved_query or state.original_query

    # Phase 2.2: Multi-query retrieval — collect distinct query variants
    # for broader coverage (original phrasing + resolved/rewritten versions)
    additional_queries = []
    if state.original_query and state.original_query != query:
        additional_queries.append(state.original_query)
    if (
        state.resolved_query
        and state.resolved_query != query
        and state.resolved_query not in additional_queries
    ):
        additional_queries.append(state.resolved_query)

    # Phase 2.3: HyDE — generate a hypothetical document passage for retrieval
    if SWITCHES.get("HYDE", False):
        try:
            hyde_start = time.time()
            prompt = hyde_prompt(query)
            hyde_result = await invoke_llm(
                response_schema=HyDELLMOutput,
                contents=prompt,
                gpu_model=GPU_HYDE_LLM.model,
                port=GPU_HYDE_LLM.port,
            )
            hyde_result = HyDELLMOutput.model_validate(hyde_result)
            if hyde_result.hypothetical_document:
                additional_queries.append(hyde_result.hypothetical_document)
                print(
                    f"[HyDE] Generated hypothetical doc ({time.time() - hyde_start:.2f}s): "
                    f"{hyde_result.hypothetical_document[:80]}..."
                )
        except Exception as e:
            print(f"[HyDE] Error generating hypothetical document: {e}, skipping")

    retrieved_docs = await get_thread_documents_retriever(
        user_id=state.user_id,
        thread_id=state.thread_id,
        query=query,
        additional_queries=additional_queries if additional_queries else None,
        k=None,  # None enables adaptive scaling
        min_chunks_per_doc=MIN_CHUNKS_PER_DOC,
        max_total_chunks=MAX_TOTAL_CHUNKS,
    )

    end_time = time.time()
    print(
        f"Retrieved {len(retrieved_docs)} documents in {end_time - start_time:.2f} seconds for user {state.user_id}"
    )

    # Re-rank chunks for better relevance and diversity
    rerank_start = time.time()
    reranked_docs = rerank_chunks(
        query=query,
        chunks=retrieved_docs,
        top_k=len(retrieved_docs),
        diversity_lambda=0.5,  # Balance between relevance and diversity
    )
    rerank_end = time.time()
    print(f"Re-ranking completed in {rerank_end - rerank_start:.2f} seconds")

    modified_docs = []
    for doc in reranked_docs:
        metadata = doc.get("metadata", {}) or {}
        doc_title = metadata.get("title", "Unknown Title")
        doc_id = metadata.get("document_id", "")

        # Format content with document name prominently displayed
        content = doc.get("page_content", "")
        formatted_content = f"[Document: {doc_title}]\n\n{content}"

        modified_docs.append(
            {
                "document_id": doc_id,
                "title": doc_title,
                "page_no": metadata.get("page_no", 1),
                "file_name": metadata.get("file_name", ""),
                "content": formatted_content,
                "rerank_score": doc.get("rerank_score", 0.0),
            }
        )

    with open(f"DEBUG/retrieved_docs.json", "w") as f:
        json.dump(modified_docs, f, indent=2)

    # Compute confidence score from retrieval quality
    num_chunks = len(modified_docs)
    avg_rerank = 0.0
    if modified_docs:
        scores = [d.get("rerank_score", 0.0) for d in modified_docs]
        avg_rerank = sum(scores) / len(scores) if scores else 0.0

    if num_chunks >= 5 and avg_rerank >= 0.5:
        state.confidence_score = "high"
    elif num_chunks >= 3 and avg_rerank >= 0.3:
        state.confidence_score = "medium"
    else:
        state.confidence_score = "low"

    # On re-retrieval (CRAG retry), merge new chunks with previous set
    # so the LLM sees both retrieval attempts for broader coverage
    if state.retrieval_attempts > 0 and state.chunks:
        existing_keys = set()
        for c in state.chunks:
            key = (c.get("document_id", ""), c.get("page_no", 0), c.get("content", "")[:100])
            existing_keys.add(key)

        merged = list(state.chunks)
        for doc in modified_docs:
            key = (doc.get("document_id", ""), doc.get("page_no", 0), doc.get("content", "")[:100])
            if key not in existing_keys:
                merged.append(doc)

        # Sort merged set by rerank_score descending
        merged.sort(key=lambda d: d.get("rerank_score", 0.0), reverse=True)
        state.chunks = merged
        print(
            f"[CRAG Merge] Combined {len(state.chunks)} chunks "
            f"(prev: {len(existing_keys)}, new unique: {len(merged) - len(existing_keys)})"
        )
    else:
        state.chunks = modified_docs

    # Phase 3.2: Look up entity-relation triples for query entities
    try:
        query_entities = extract_query_entities(query)
        if query_entities:
            triple_ctx = await asyncio.to_thread(
                TripleStore.get_context_for_query,
                state.user_id,
                state.thread_id,
                query_entities,
            )
            if triple_ctx:
                state.triple_context = triple_ctx
                print(f"[Triples] Injected {len(triple_ctx.splitlines()) - 1} triples")
    except Exception as e:
        print(f"[Triples] Error querying triples: {e}")

    return state


async def generate(state: AgentState) -> AgentState:
    prompt = build_main_prompt(state)

    async with aiofiles.open(f"DEBUG/main_prompt.json", "w") as f:
        await f.write(json.dumps(prompt, indent=2))

    # invoke_llm already handles retries (4 attempts) with self-correction
    # and fallback chains (GPU -> Gemini -> OpenAI).  This outer loop only
    # guards against unexpected transient errors (network, timeout).
    max_retries = 2
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            if state.mode == EXTERNAL:
                response_schema = MainLLMOutputExternal
            else:
                if state.use_self_knowledge:
                    response_schema = MainLLMOutputInternalWithFailure
                else:
                    response_schema = MainLLMOutputInternal

            result = await invoke_llm(
                response_schema=response_schema,
                contents=prompt,
                gpu_model=state.llm.model,
                port=state.llm.port,
            )

            result = response_schema.model_validate(result)
            end_time = time.time()
            print("LLM result: ", result)
            print(f"LLM response time: {end_time - start_time:.2f} seconds")

            # Guard against blank/empty answers — retry if the model returned nothing
            answer_text = (result.answer or "").strip()
            if not answer_text and result.action in (ANSWER, None):
                print(f"[generate] Blank answer detected (attempt {attempt+1}/{max_retries}), retrying...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                # Last attempt — fall through with a generic message
                result.answer = "I was unable to generate an answer for this query. Please try rephrasing your question."

            state.messages.append(HumanMessage(content=state.query))  # controversial
            state.messages.append(AIMessage(content=result.answer))
            state.messages.append(AIMessage("Action taken: " + result.action))

            state.answer = result.answer
            state.action = result.action
            state.chunks_used = result.chunks_used or []
            state.web_search_queries = getattr(result, "web_search_queries", []) or []
            state.attempts += 1
            state.document_id = result.document_id or None
            state.sql_query = getattr(result, "sql_query", None)
            state.excel_request = getattr(result, "excel_request", None)
            return state

        except Exception as e:
            print(f"Error in generate (attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                state.answer = "An error occurred while generating the answer. Please try again later."
                state.action = FAILURE
                return state
            await asyncio.sleep(1)  # brief pause before retry


async def web_search(state: AgentState) -> AgentState:
    queries = state.web_search_queries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            results = await parallel_search(queries, search_tool)
            state.web_search = True
            # state.chunks = []
            state.messages.append(
                HumanMessage(content=f"Web search initiated for queries: {queries}")
            )
            state.web_search_attempts += 1
            state.web_search_results = results
            return state
        except Exception as e:
            print(f"Error in web search (attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                state.web_search = False
                state.web_search_results = []
                state.messages.append(
                    AIMessage(content="Web search failed. Please try again later.")
                )
                return state
            await asyncio.sleep(0.5)  # brief pause before retry


async def failure(state: AgentState) -> AgentState:
    """
    Handles the failure case when no action can be taken.
    """
    failure_message = (
        "I am unable to answer your question at this time. "
        "Please try rephrasing or asking a different question."
    )
    state.messages.append(AIMessage(content=failure_message))
    state.answer = failure_message
    return state
    # return END if the above line ever throws error


async def self_knowledge(state: AgentState) -> AgentState:
    if state.mode == EXTERNAL or not state.use_self_knowledge:
        if not state.answer or not state.answer.strip():
            state.answer = (
                "I am unable to answer your question at this time. "
                "Please try rephrasing or asking a different question."
            )
        return state

    print("Using self-knowledge to answer the question.")
    prompt = build_self_knowledge_prompt(state)
    with open(f"DEBUG/self_knowledge_prompt.json", "w") as f:
        json.dump(prompt, f, indent=2)

    result = await invoke_llm(
        response_schema=SelfKnowledgeLLMOutput,
        contents=prompt,
        gpu_model=state.llm.model,
        port=state.llm.port,
    )

    result = SelfKnowledgeLLMOutput.model_validate(result)
    state.messages.append(AIMessage(content=result.answer))
    state.answer = result.answer
    return state


async def document_summarizer(state: AgentState) -> AgentState:
    document_id = state.document_id
    if not document_id:
        print("No document ID provided for summarization.")
        state.summary = "No summary available for this document."
        return state

    print(f"Summarizing document with ID: {document_id}")

    state.messages.append(
        HumanMessage(content=f"Summarizing document with ID: {document_id}")
    )

    parsed_dir = f"data/{state.user_id}/threads/{state.thread_id}/parsed"
    os.makedirs(parsed_dir, exist_ok=True)

    for doc in state.chunks:
        # Support both flat chunk format (from retriever) and legacy metadata format
        meta = doc.get("metadata", {})
        doc_id = doc.get("document_id") or meta.get("document_id", "")
        if doc_id == document_id:
            file_name = doc.get("file_name") or meta.get("file_name", "")
            title = doc.get("title") or meta.get("title", "Unknown Title")
            if not file_name:
                print(f"Document {doc_id} has no file name, skipping...")
                continue

            name, _ = os.path.splitext(file_name)
            json_file_path = os.path.join(parsed_dir, f"{name}.json")

            if not os.path.exists(json_file_path):
                print(f"Parsed file {json_file_path} does not exist, skipping...")
                continue

            async with aiofiles.open(json_file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            document_data = json.loads(content)
            if document_data.get("summary"):
                state.answer = f"Summary: \n {document_data['summary']}"
                state.summary = f"Summary for document {document_id}, title: {title}, summary: {document_data['summary']}"
                state.after_summary = ANSWER
                print(
                    f"Summary for document {document_id}, title: {title}, summary: {document_data['summary']}"
                )
            else:
                state.summary = "No summary available for this document. Use your own knowledge and context to provide an answer."
                state.after_summary = GENERATE
                print(f"No summary found for document {document_id}")
            break

    return state


async def global_summarizer(state: AgentState) -> AgentState:
    parsed_dir = f"data/{state.user_id}/threads/{state.thread_id}"
    os.makedirs(parsed_dir, exist_ok=True)
    json_file_path = os.path.join(parsed_dir, "global_summary.json")

    if not os.path.exists(json_file_path):
        print("Global summary for the documents not available")
        state.summary = "No global summary available for the documents. Use your own knowledge and context to provide an answer."
        state.after_summary = GENERATE
        return state

    async with aiofiles.open(json_file_path, "r", encoding="utf-8") as f:
        content = await f.read()

    global_summary_data = json.loads(content)
    if global_summary_data.get("summary"):
        state.answer = f"{global_summary_data['summary']}"
        state.summary = (
            f"Global summary of all the documents: {global_summary_data['summary']}"
        )
        state.after_summary = ANSWER
        print(f"Global summary: {global_summary_data['summary']}")
    else:
        state.summary = "No global summary available for the documents. Use your own knowledge and context to provide an answer."
        state.after_summary = GENERATE

    return state



# Maximum characters for SQL result injected into the LLM prompt.
# ~4000 tokens ≈ 16000 chars — leaves room for schema, chunks, instructions, and 8K output.
_SQL_RESULT_MAX_CHARS = 16000

# NLP query detection keywords — triggers chunked theme extraction on large results
_NLP_KEYWORDS = [
    "sentiment", "theme", "themes", "tone", "opinion", "opinions",
    "categorize", "categorise", "classify", "classification",
    "analyze comments", "analyse comments", "analyze feedback", "analyse feedback",
    "positive", "negative", "neutral",
    "overarching", "common patterns", "common themes", "recurring",
    "feedback analysis", "what do people say", "what are people saying",
    "mood", "attitude", "complaints", "praise", "criticism",
    "subjective", "qualitative analysis",
]

# Minimum row count to trigger NLP chunked extraction
_NLP_MIN_ROWS = 100
# Target rows per chunk — keeps each chunk within LLM context
_NLP_ROWS_PER_CHUNK = 200


def _is_nlp_query(question: str) -> bool:
    """Check if the user's question requires NLP/subjective analysis."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in _NLP_KEYWORDS)


def _parse_markdown_table_rows(result_text: str) -> tuple:
    """
    Parse a markdown table into header and data rows.
    Returns (header_line, separator_line, data_rows) or (None, None, []) if not a table.
    """
    lines = result_text.strip().split("\n")
    # Find the markdown table — look for header separator (|---|---|)
    header_line = None
    separator_line = None
    data_start = 0

    for i, line in enumerate(lines):
        if "|" in line and "---" in line:
            separator_line = line
            if i > 0:
                header_line = lines[i - 1]
            data_start = i + 1
            break

    if not separator_line:
        return None, None, []

    data_rows = [l for l in lines[data_start:] if l.strip() and "|" in l]
    return header_line, separator_line, data_rows


async def _extract_nlp_themes(
    result_text: str,
    user_question: str,
    row_count: int,
) -> str | None:
    """
    Run chunked NLP theme extraction on a large SQL result.

    Splits the markdown table into chunks, runs lightweight theme
    extraction on each chunk in parallel, then merges results.

    Returns a formatted theme summary string, or None if extraction fails.
    """
    from core.constants import GPU_NLP_THEME_LLM
    from core.llm.output_schemas.nlp_theme_output import NLPThemeExtraction
    from core.llm.prompts.nlp_theme_prompt import nlp_theme_extraction_prompt

    header_line, separator_line, data_rows = _parse_markdown_table_rows(result_text)
    if not data_rows or len(data_rows) < _NLP_MIN_ROWS:
        return None

    # Split data rows into chunks of ~_NLP_ROWS_PER_CHUNK rows each
    chunk_count = max(1, (len(data_rows) + _NLP_ROWS_PER_CHUNK - 1) // _NLP_ROWS_PER_CHUNK)
    chunk_size = max(1, len(data_rows) // chunk_count)
    chunks = []
    for i in range(0, len(data_rows), chunk_size):
        chunks.append(data_rows[i : i + chunk_size])

    # Last chunk absorbs any remainder from rounding
    if len(chunks) > chunk_count:
        chunks[chunk_count - 1].extend(
            row for c in chunks[chunk_count:] for row in c
        )
        chunks = chunks[:chunk_count]

    print(
        f"[NLP Theme Extraction] Detected NLP query, chunking {len(data_rows)} rows "
        f"into {len(chunks)} batches ({[len(c) for c in chunks]} rows each)"
    )

    # Extract text content from markdown table rows (take all cell values)
    def rows_to_text(rows):
        entries = []
        for row in rows:
            cells = [c.strip() for c in row.split("|") if c.strip()]
            entries.append(" | ".join(cells))
        return entries

    # Run theme extraction on each chunk in parallel
    async def extract_chunk(chunk_rows, batch_num):
        entries = rows_to_text(chunk_rows)
        prompt = nlp_theme_extraction_prompt(
            entries=entries,
            user_question=user_question,
            batch_number=batch_num,
            total_batches=len(chunks),
        )
        try:
            result = await invoke_llm(
                gpu_model=GPU_NLP_THEME_LLM.model,
                response_schema=NLPThemeExtraction,
                contents=prompt,
                port=GPU_NLP_THEME_LLM.port,
                remove_thinking=True,
            )
            return NLPThemeExtraction.model_validate(result)
        except Exception as e:
            print(f"[NLP Theme Extraction] Chunk {batch_num} failed: {e}")
            return None

    chunk_results = await asyncio.gather(
        *(extract_chunk(chunk, i + 1) for i, chunk in enumerate(chunks))
    )

    # Merge themes across chunks
    theme_map = {}  # theme_name_lower -> {theme, count, examples}
    total_analyzed = 0

    for cr in chunk_results:
        if cr is None:
            continue
        total_analyzed += cr.total_rows_analyzed
        for t in cr.themes:
            key = t.theme.strip().lower()
            if key in theme_map:
                theme_map[key]["count"] += t.count
                # Keep up to 3 unique examples
                existing = set(theme_map[key]["examples"])
                for ex in t.examples:
                    if len(theme_map[key]["examples"]) < 3 and ex not in existing:
                        theme_map[key]["examples"].append(ex)
            else:
                theme_map[key] = {
                    "theme": t.theme.strip(),
                    "count": t.count,
                    "examples": list(t.examples[:3]),
                }

    if not theme_map:
        return None

    # Sort by count descending
    sorted_themes = sorted(theme_map.values(), key=lambda x: x["count"], reverse=True)

    # Format as readable summary
    lines = [f"**Pre-Analyzed Themes** (from ALL {total_analyzed} rows across {len(chunks)} batches):\n"]
    for i, t in enumerate(sorted_themes, 1):
        pct = (t["count"] / total_analyzed * 100) if total_analyzed > 0 else 0
        examples_str = "; ".join(f'"{ex}"' for ex in t["examples"])
        lines.append(
            f"{i}. **{t['theme']}** — {t['count']} entries ({pct:.0f}%)\n"
            f"   Examples: {examples_str}"
        )

    summary = "\n".join(lines)
    print(f"[NLP Theme Extraction] Extracted {len(sorted_themes)} themes from {total_analyzed} rows")
    return summary


async def sql_query_node(state: AgentState) -> AgentState:
    """
    Executes a SQL query against the user's spreadsheet data in SQLite.
    The query is generated by the LLM in the generate step.
    After execution, the result is stored in state so the next generate
    call can use it to formulate the final answer.

    For NLP/subjective queries on large datasets, runs chunked theme
    extraction so the main LLM has accurate analysis from ALL rows.

    Large results are truncated to fit within the LLM context window,
    with a note appended so the LLM knows the data is partial.
    """
    query = state.sql_query
    if not query:
        print("[sql_query_node] No SQL query provided")
        state.sql_result = "No SQL query was provided."
        state.messages.append(
            AIMessage(content="SQL query action requested but no query was provided.")
        )
        return state

    print(f"[sql_query_node] Executing SQL: {query}")
    state.sql_last_executed_query = query
    state.sql_attempts += 1

    try:
        result = await execute_sql_query(
            user_id=state.user_id,
            thread_id=state.thread_id,
            query=query,
        )

        # NLP chunked theme extraction — needs ALL rows, not just the default 500.
        # LLM flag (requires_full_data) takes priority; keyword matching is fallback.
        user_q = state.original_query or state.query or ""
        is_nlp = state.requires_full_data or _is_nlp_query(user_q)
        if is_nlp:
            # Re-fetch with no row limit so NLP extraction sees the COMPLETE dataset
            full_result = await execute_sql_query(
                user_id=state.user_id,
                thread_id=state.thread_id,
                query=query,
                max_rows=None,
            )
            if not full_result.startswith("SQL query failed"):
                try:
                    nlp_summary = await _extract_nlp_themes(
                        result_text=full_result,
                        user_question=user_q,
                        row_count=full_result.count("\n"),
                    )
                    if nlp_summary:
                        state.sql_nlp_summary = nlp_summary
                        print(f"[NLP Theme Extraction] Complete — analyzed all rows")
                except Exception as e:
                    print(f"[NLP Theme Extraction] Failed: {e}")

        # Truncate large results to prevent context overflow and output truncation.
        # When NLP themes were already extracted, use a much smaller sample —
        # the themes cover ALL data so the raw sample is just for examples.
        if state.sql_nlp_summary:
            max_chars = 4000  # ~50 rows — just enough for example references
        else:
            max_chars = _SQL_RESULT_MAX_CHARS

        if len(result) > max_chars:
            full_len = len(result)
            row_count = result.count("\n")
            # Find the last complete row (newline) within the limit
            truncated = result[:max_chars]
            last_newline = truncated.rfind("\n")
            if last_newline > max_chars // 2:
                truncated = truncated[:last_newline]

            if state.sql_nlp_summary:
                result = (
                    f"{truncated}\n\n"
                    f"... [SAMPLE ONLY — {row_count} total rows in dataset] ...\n"
                    "Full-data theme analysis is provided above. "
                    "Use these rows only as example references."
                )
            else:
                result = (
                    f"{truncated}\n\n"
                    f"... [OUTPUT TRUNCATED — showing {len(truncated)}/{full_len} chars] ...\n"
                    "The dataset is too large to display in full. "
                    "Summarize, aggregate, or categorize the data in your answer. "
                    "Do NOT try to list every row — provide counts, percentages, "
                    "and key groupings instead."
                )
            print(f"[sql_query_node] Result truncated: {full_len} -> {len(result)} chars"
                  f" (NLP mode: {bool(state.sql_nlp_summary)})")

        state.sql_result = result
        state.messages.append(HumanMessage(content=f"SQL query executed: {query}"))
        state.messages.append(AIMessage(content=f"SQL Result:\n{result}"))
        print(f"[sql_query_node] Query result length: {len(result)} chars")
    except Exception as e:
        error_msg = f"SQL execution error: {str(e)}"
        print(f"[sql_query_node] {error_msg}")
        state.sql_result = error_msg
        state.messages.append(AIMessage(content=error_msg))

    return state


async def excel_skill_node(state: AgentState) -> AgentState:
    """
    Executes the Excel Skill: generates a downloadable .xlsx file
    based on the user's natural-language request.

    The pipeline uses LLM only for planning and NLP columns;
    data extraction and Excel assembly are deterministic.
    """
    from core.excel_skill.pipeline import generate_excel

    request_text = state.excel_request
    if not request_text:
        # Fallback: use the original query as the request
        request_text = state.query or state.original_query or "Export all data"

    print(f"[excel_skill_node] Generating Excel: {request_text}")

    try:
        result = await generate_excel(
            user_request=request_text,
            user_id=state.user_id,
            thread_id=state.thread_id,
        )

        state.excel_result = result.download_url

        # Build a user-friendly answer with download link
        # Preserve any LLM-generated summary (e.g., when auto-routing large output to Excel)
        llm_summary = state.answer.strip() if state.answer else ""
        download_info = (
            f"I've created your Excel file: **{result.file_name}**\n\n"
            f"{result.description}\n\n"
            f"- **Sheets:** {result.sheet_count}\n"
            f"- **Total rows:** {result.total_rows}\n\n"
            f"[Download {result.file_name}]({result.download_url})"
        )
        if llm_summary:
            state.answer = f"{llm_summary}\n\n---\n\n{download_info}"
        else:
            state.answer = download_info

        state.messages.append(
            AIMessage(content=f"Excel file created: {result.file_name}")
        )

        # Persist status metadata so chat-generated files appear in the list
        import json
        import uuid as _uuid
        from datetime import datetime, timezone

        status_dir = f"data/{state.user_id}/threads/{state.thread_id}/excel_exports"
        os.makedirs(status_dir, exist_ok=True)
        _tracking_id = str(_uuid.uuid4())
        status_data = {
            "file_name": result.file_name,
            "download_url": result.download_url,
            "description": result.description,
            "sheet_count": result.sheet_count,
            "total_rows": result.total_rows,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "request_text": request_text,
        }
        _status_path = os.path.join(status_dir, f"status_{_tracking_id}.json")
        with open(_status_path, "w", encoding="utf-8") as _f:
            json.dump(status_data, _f, ensure_ascii=False, indent=2)

        print(
            f"[excel_skill_node] Created {result.file_name} "
            f"({result.sheet_count} sheets, {result.total_rows} rows)"
        )

    except Exception as e:
        error_msg = f"Failed to create Excel file: {str(e)}"
        print(f"[excel_skill_node] {error_msg}")
        state.answer = (
            "I wasn't able to create the Excel file. "
            "Please try again or rephrase your request."
        )
        state.messages.append(AIMessage(content=error_msg))

    return state


def main_router(state: AgentState) -> str:
    if state.action == ANSWER:
        print("Router -> Answering the question")
        return ANSWER

    elif state.action == WEB_SEARCH:
        print("Router -> Initiating web search")
        if state.web_search_attempts < MAX_WEB_SEARCH:
            return WEB_SEARCH
        else:
            return FAILURE
    elif state.action == SQL_QUERY:
        # Break SQL loop: if the LLM re-issues the same query when a valid
        # result already exists, force it to answer.  But allow NEW/different
        # queries through (multi-part questions, drill-downs, corrections).
        if (
            state.sql_result
            and "SQL query failed:" not in state.sql_result
            and state.sql_last_executed_query
        ):
            new_q = (state.sql_query or "").strip().lower()
            prev_q = state.sql_last_executed_query.strip().lower()
            if new_q == prev_q or not new_q:
                print("Router -> Same SQL query repeated with valid result, forcing answer (loop breaker)")
                return ANSWER
            print(f"Router -> Different SQL query (attempt {state.sql_attempts + 1}), allowing")

        if state.sql_attempts < MAX_SQL_RETRIES:
            print(f"Router -> Executing SQL query (attempt {state.sql_attempts + 1})")
            return SQL_QUERY
        else:
            print("Router -> Max SQL retries reached, answering with what we have")
            return ANSWER

    elif state.action == EXCEL_CREATE:
        print("Router -> Creating Excel file")
        return EXCEL_CREATE

    elif state.action == DOCUMENT_SUMMARIZER:
        print("Router -> Summarizing document")
        return DOCUMENT_SUMMARIZER

    elif state.action == GLOBAL_SUMMARIZER:
        print("Router -> Summarizing global context")
        return GLOBAL_SUMMARIZER

    elif state.action == FAILURE:
        return FAILURE

    return ANSWER


def summary_router(state: AgentState) -> str:
    if state.after_summary == ANSWER:
        print("Routing to answer after summarization")
        return ANSWER
    elif state.after_summary == GENERATE:
        print("Routing to generate after summarization")
        return GENERATE
    return ANSWER


async def evaluator(state: AgentState) -> AgentState:
    """
    Phase 2.1: CRAG Corrective Retrieval — evaluates retrieved chunk quality.

    After the retriever, this node assesses whether the chunks are sufficient
    to answer the query. If not, it refines the query and triggers re-retrieval.
    """
    # Pass through if feature is disabled
    if not SWITCHES.get("CORRECTIVE_RETRIEVAL", False):
        state.retrieval_verdict = "sufficient"
        return state

    # Pass through if already at max attempts
    if state.retrieval_attempts >= MAX_RETRIEVAL_ATTEMPTS:
        print(
            f"[CRAG Evaluator] Max retrieval attempts ({MAX_RETRIEVAL_ATTEMPTS}) reached, proceeding"
        )
        state.retrieval_verdict = "sufficient"
        return state

    # Pass through if no chunks (e.g., spreadsheet-only thread)
    if not state.chunks:
        state.retrieval_verdict = "sufficient"
        return state

    state.retrieval_attempts += 1

    try:
        start_time = time.time()
        prompt = evaluator_prompt(state.query, state.chunks)
        result = await invoke_llm(
            response_schema=EvaluatorLLMOutput,
            contents=prompt,
            gpu_model=GPU_EVALUATOR_LLM.model,
            port=GPU_EVALUATOR_LLM.port,
        )
        result = EvaluatorLLMOutput.model_validate(result)

        elapsed = time.time() - start_time
        state.retrieval_verdict = result.verdict
        print(
            f"[CRAG Evaluator] Verdict: {result.verdict} | "
            f"Reasoning: {result.reasoning} | Time: {elapsed:.2f}s"
        )

        if result.verdict in ("ambiguous", "insufficient") and result.refined_query:
            state.query = result.refined_query
            print(
                f"[CRAG Evaluator] Refined query for re-retrieval: {result.refined_query}"
            )

    except Exception as e:
        print(f"[CRAG Evaluator] Error: {e}, proceeding with current chunks")
        state.retrieval_verdict = "sufficient"

    return state


def evaluator_router(state: AgentState) -> str:
    """Route based on the CRAG evaluator verdict."""
    if (
        state.retrieval_verdict in ("ambiguous", "insufficient")
        and state.retrieval_attempts < MAX_RETRIEVAL_ATTEMPTS
    ):
        print(
            f"[CRAG Router] Re-retrieving (attempt {state.retrieval_attempts + 1})"
        )
        return RETRIEVER

    # sufficient or max attempts exhausted → proceed to generate
    print(
        f"[CRAG Router] Proceeding to generate (verdict: {state.retrieval_verdict})"
    )
    return GENERATE
