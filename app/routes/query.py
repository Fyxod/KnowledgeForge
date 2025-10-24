import asyncio
import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage
from core.llm.outputs import DecompositionLLMOutput
from agent.builder import Agent, AgentState
from agent.decomposition import decomposition_node
from agent.combination import combination_node
from core.database import db
from core.utils.extra_done_check import is_extra_done
from core.constants import Ollama_QUERY_LLM, Ollama_QUERY_LLM2, INTERNAL, EXTERNAL, SWITCHES
from agent.tools.search import search_tavily as search_tool
from typing import Literal

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    thread_id: str
    question: str
    mode: Literal[f"{INTERNAL}", f"{EXTERNAL}"] = EXTERNAL


@router.post("/")
async def query(request: Request, body: QueryRequest):
    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    question = body.question
    mode = body.mode

    print(
        f"Received query for thread_id: {thread_id} with question: {question} and mode: {mode}"
    )

    user_id = payload.userId
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}

    thread = user["threads"].get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    messages = []
    chunks = []
    chunks_used = []

    for message in thread.get("chats", []):
        if message["type"] == "user":
            messages.append(HumanMessage(content=message["content"]))
        elif message["type"] == "agent":
            messages.append(AIMessage(content=message["content"]))
    ds = time.time()
    if SWITCHES["DECOMPOSITION"]:
        decomposition_result: DecompositionLLMOutput = await decomposition_node(
            question, messages
        )
    else:
        decomposition_result = DecompositionLLMOutput(
            requires_decomposition=False, resolved_query=question, sub_queries=[]
        )

    de = time.time() - ds
    print(f"Rewrite query time: {de:.2f} seconds")
    decomposed = decomposition_result.requires_decomposition
    all_favicons = []
    start_time = time.time()
    if decomposed:
        can_use_second_model = is_extra_done(user_id, thread_id)
        print("Query to be decomposed")
        print("No of sub-queries:", len(decomposition_result.sub_queries))

        async def run_worker(model, task_queue, results):
            while True:
                try:
                    idx, query_data = task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                qs = time.time()
                state = await Agent.ainvoke(
                    AgentState(
                        user_id=user_id,
                        thread_id=thread_id,
                        query=query_data["query"],
                        resolved_query=decomposition_result.resolved_query,
                        original_query=question,
                        messages=messages,
                        # messages=[],
                        web_search=False,
                        llm=model,
                        initial_search_answer=query_data["answer"] or "",
                        initial_search_results=query_data["results"] or [],
                        mode=mode,
                    )
                )

                state = AgentState(**state)

                if getattr(state, "web_search_queries", None):
                    for res in state.web_search_queries:
                        favicons = [
                            r.get("favicon") for r in res["results"] if r.get("favicon")
                        ]
                        all_favicons.extend(favicons)

                qe = time.time() - qs
                chunks.extend(state.chunks)
                chunks_used.extend(state.chunks_used)
                print(
                    f"Sub-query '{idx}. {query_data['query']}' processed in {qe:.2f} seconds using {model}"
                )

                results[idx] = {
                    "sub_query": query_data["query"],
                    "sub_answer": state.answer,
                }

        # Prepare a queue of sub-queries
        if mode == EXTERNAL:
            search_results = await asyncio.gather(
                *(
                    search_tool(sub_query)
                    for sub_query in decomposition_result.sub_queries
                )
            )

            cleaned_results = []

            for idx, sub_query in enumerate(decomposition_result.sub_queries):
                if idx < len(search_results) and search_results[idx]:
                    res = search_results[idx]

                    favicons = [
                        {
                            "favicon": r.get("favicon", None),
                            "url": r.get("url", None),
                            "title": r.get("title", None),
                        }
                        for r in res.get("results", [])
                    ]
                    all_favicons.extend(favicons)

                    # Strip unwanted keys
                    for r in res.get("results", []):
                        r.pop("raw_content", None)
                        r.pop("score", None)
                        r.pop("favicon", None)

                    cleaned_results.append(
                        {
                            "query": res.get("query", sub_query),
                            "answer": res.get("answer", None),
                            "results": res.get("results", None),
                        }
                    )
                else:
                    # No search result → keep subquery with None values
                    cleaned_results.append(
                        {
                            "query": sub_query,
                            "answer": None,
                            "results": None,
                        }
                    )

        else:
            cleaned_results = [
                {
                    "query": sub_query,
                    "answer": None,
                    "results": None,
                }
                for sub_query in decomposition_result.sub_queries
            ]

        task_queue = asyncio.Queue()
        for idx, query_data in enumerate(cleaned_results):
            task_queue.put_nowait((idx, query_data))

        # Results stored in index order
        results = [None] * len(cleaned_results)

        # Start with the first model
        workers = [asyncio.create_task(run_worker(Ollama_QUERY_LLM, task_queue, results))]

        # Can't use 2nd model as we are on cpu and theres not enough ram
        # # Add the second model only if allowed
        # if can_use_second_model:
        #     print("Using second model for parallel execution")
        #     workers.append(asyncio.create_task(run_worker(Ollama_QUERY_LLM2, task_queue, results)))
        # else:
        #     print("Second model disabled, running only on first model")

        await asyncio.gather(*workers)

        cs = time.time()
        answer = await combination_node(
            results, decomposition_result.resolved_query, question
        )
        ce = time.time() - cs
        print(f"Subqueries combination time: {ce:.2f} seconds")
    else:
        print("Query not being decomposed")

        if mode == EXTERNAL:
            search_result = await search_tool(
                decomposition_result.resolved_query or question
            )
        else:
            search_result = {}

        all_favicons.extend(
            [
                {
                    "favicon": r.get("favicon", None),
                    "url": r.get("url", None),
                    "title": r.get("title", None),
                }
                for r in search_result.get("results", [])
            ]
        )

        for r in search_result.get("results", []):
            r.pop("raw_content", None)
            r.pop("score", None)
            r.pop("favicon", None)

        resolved_query = (
            getattr(decomposition_result, "resolved_query", None) or question
        )
        state = await Agent.ainvoke(
            AgentState(
                user_id=user_id,
                thread_id=thread_id,
                query=resolved_query,
                resolved_query=resolved_query,
                original_query=question,
                messages=messages,
                # messages=[],
                web_search=False,
                llm=Ollama_QUERY_LLM,
                mode=mode,
                initial_search_answer=search_result.get("answer", ""),
                initial_search_results=search_result.get("results", []),
            )
        )

        state = AgentState(**state)
        if getattr(state, "web_search_queries", None):
            for res in state.web_search_queries:
                favicons = [
                    {
                        "favicon": r.get("favicon", None),
                        "url": r.get("url", None),
                        "title": r.get("title", None),
                    }
                    for r in res["results"]
                ]
                all_favicons.extend(favicons)

        answer = state.answer
        chunks.extend(state.chunks)
        chunks_used.extend(state.chunks_used)
    end_time = time.time()

    print(f"Total Agent response time: {end_time - start_time:.2f} seconds")

    documents_used = []
    if chunks_used:
        print(f"Processing {len(chunks_used)} citations...")

        for doc_i in chunks_used:
            for doc_j in chunks:
                meta = doc_j.get("metadata", {})
                if (
                    doc_i.document_id == meta.get("document_id")
                    and doc_i.page_no == meta.get("page_no")
                    and doc_i.chunk_index == meta.get("chunk_index")
                ):
                    documents_used.append(doc_j)
                    break

    modified_used = []
    for doc in documents_used:
        modified_used.append(
            {
                "title": doc.get("metadata", {}).get("title"),
                "document_id": doc.get("metadata", {}).get("document_id"),
                "page_no": doc.get("metadata", {}).get("page_no"),
            }
        )
    print(f"Found {len(documents_used)} citation matches")

    with open("debug_agent_response.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "thread_id": thread_id,
                "user_id": user_id,
                "question": question,
                "answer": answer,
                "documents_used": documents_used,
                "all_favicons": all_favicons,
                "decomposed": decomposed,
                "decomposition_result": decomposition_result.dict(),
                "chunks": chunks,
                "chunks_used": [doc.dict() for doc in chunks_used],
            },
            f,
            ensure_ascii=False,
            indent=4,
        )

    # Update the thread with the new messages
    now = datetime.now(timezone.utc)
    new_messages = [
        {"type": "user", "content": question, "timestamp": now},
        {
            "type": "agent",
            "content": answer,
            "timestamp": now,
            "sources": {"documents_used": modified_used, "web_used": all_favicons},
        },
    ]

    db.users.update_one(
        {"userId": user_id},
        {
            "$push": {f"threads.{thread_id}.chats": {"$each": new_messages}},
            "$set": {f"threads.{thread_id}.updatedAt": now},
        },
    )

    response = {
        "thread_id": thread_id,
        "user_id": user_id,
        "question": question,
        "answer": answer,
        "sources": {
            "documents_used": modified_used,
            "web_used": all_favicons,
        },
    }

    return response
