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

    max_retries = 8
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


async def sql_query_node(state: AgentState) -> AgentState:
    """
    Executes a SQL query against the user's spreadsheet data in SQLite.
    The query is generated by the LLM in the generate step.
    After execution, the result is stored in state so the next generate
    call can use it to formulate the final answer.
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
    state.sql_attempts += 1

    try:
        result = await execute_sql_query(
            user_id=state.user_id,
            thread_id=state.thread_id,
            query=query,
        )
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
        print("Router -> Executing SQL query")
        if state.sql_attempts < MAX_SQL_RETRIES:
            return SQL_QUERY
        else:
            print("Router -> Max SQL retries reached, answering with what we have")
            return ANSWER

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
