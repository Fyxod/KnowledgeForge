import json
import time
import os
import aiofiles
import asyncio

from langchain_core.messages import AIMessage, HumanMessage

from agent.graph_helpers import (
    build_main_prompt,
    parallel_search,
    build_self_knowledge_prompt,
)
from agent.state import AgentState
from agent.tools.search import search_tavily as search_tool
from agent.tools.sql_query import execute_sql_query

from core.constants import *
from core.embeddings.retriever import get_thread_documents_retriever, rerank_chunks
from core.llm.client import invoke_llm
from core.llm.outputs import (
    MainLLMOutputExternal,
    MainLLMOutputInternal,
    MainLLMOutputInternalWithFailure,
    SelfKnowledgeLLMOutput,
)

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
    start_time = time.time()

    # Use the new robust retrieval function that ensures document diversity
    # Uses adaptive scaling based on document count
    query = state.query or state.resolved_query or state.original_query
    retrieved_docs = await get_thread_documents_retriever(
        user_id=state.user_id,
        thread_id=state.thread_id,
        query=query,
        k=None,  # None enables adaptive scaling
        min_chunks_per_doc=MIN_CHUNKS_PER_DOC,
        max_total_chunks=MAX_TOTAL_CHUNKS
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
        diversity_lambda=0.5  # Balance between relevance and diversity
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
    unique_docs = set(d["document_id"] for d in modified_docs if d["document_id"])
    num_chunks = len(modified_docs)
    if num_chunks >= 5 and len(unique_docs) >= 2:
        state.confidence_score = "high"
    elif num_chunks >= 3:
        state.confidence_score = "medium"
    else:
        state.confidence_score = "low"

    state.chunks = modified_docs
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
            state.suggested_questions = getattr(result, "suggested_questions", None) or []
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
    if state.mode == EXTERNAL:
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
