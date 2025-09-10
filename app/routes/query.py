"""
POST /query/
-------------
Handles user queries within a specific thread.

Request Body (JSON):
    - thread_id (str): The unique identifier of the thread to query.
    - question (str): The user's question to be processed by the agent.

Request Context:
    - Expects an authenticated user, available as `request.state.user`.

Returns (JSON):
    - On success: The agent's response as a dictionary, containing the answer and relevant state fields, with all None values excluded.
    - On error: A dictionary with an "error" key and a descriptive message, e.g., {"error": "User not authenticated"}, {"error": "User not found"}, or {"error": "Thread not found"}.
"""
import asyncio
import json
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel
from langchain.schema import AIMessage, HumanMessage
from core.llm.outputs import DecompositionLLMOutput
from agent.builder import Agent, AgentState
from agent.decomposition import decomposition_node
from agent.combination import combination_node
from core.database import db
from core.utils.extra_done_check import is_extra_done 
from core.constants import GPU_QUERY_LLM, GPU_QUERY_LLM2

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    thread_id: str
    question: str


@router.post("/")
async def query(request: Request, body: QueryRequest):
    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    question = body.question

    print(f"Received query for thread_id: {thread_id} with question: {question}")

    user_id = payload.userId
    print(f"User ID from payload: {user_id}")
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}


    thread = user["threads"].get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    messages = []

    for message in thread.get("chats", []):
        if message["type"] == "user":
            messages.append(HumanMessage(content=message["content"]))
        elif message["type"] == "agent":
            messages.append(AIMessage(content=message["content"]))
    ds = time.time()
    decomposition_result: DecompositionLLMOutput = await decomposition_node(question, messages)
    de = time.time() - ds
    print(f"Decomposition time: {de:.2f} seconds")
    decomposed = decomposition_result.requires_decomposition

    start_time = time.time()
    if decomposed:
        can_use_second_model = is_extra_done(user_id, thread_id)
        print("TO BE DECOMPOSED")
        print("No of sub-queries:", len(decomposition_result.sub_queries))

        async def run_worker(model, task_queue, results):
            while True:
                try:
                    idx, sub_query = task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                qs = time.time()
                state = await Agent.ainvoke(AgentState(
                    user_id=user_id,
                    thread_id=thread_id,
                    query=sub_query,
                    resolved_query=decomposition_result.resolved_query,
                    original_query=question,
                    messages=[],
                    web_search=False,
                    llm=model
                ))
                state = AgentState(**state)
                qe = time.time() - qs
                print(f"Sub-query '{idx}. {sub_query}' processed in {qe:.2f} seconds using {model}")

                results[idx] = {"sub_query": sub_query, "sub_answer": state.answer}

        # Prepare a queue of sub-queries
        task_queue = asyncio.Queue()
        for idx, sub_query in enumerate(decomposition_result.sub_queries):
            task_queue.put_nowait((idx, sub_query))

        # Results stored in index order
        results = [None] * len(decomposition_result.sub_queries)

        # Start with the first model
        workers = [asyncio.create_task(run_worker(GPU_QUERY_LLM, task_queue, results))]

    # Add the second model only if allowed
        if can_use_second_model:
            print("Using second model for parallel execution")
            workers.append(asyncio.create_task(run_worker(GPU_QUERY_LLM2, task_queue, results)))
        else:
            print("Second model disabled, running only on first model")

        await asyncio.gather(*workers)

        cs = time.time()
        answer = await combination_node(results, decomposition_result.resolved_query, question)
        ce = time.time() - cs
        print(f"Combination time: {ce:.2f} seconds")
    else:
        print("NO DECOMPOSITION REQUIRED")
        state = await Agent.ainvoke(AgentState(
            user_id=user_id,
            thread_id=thread_id,
            query=decomposition_result.resolved_query,
            resolved_query=decomposition_result.resolved_query,
            original_query=question,
            messages=[],
            web_search=False,
            llm=GPU_QUERY_LLM
        ))
        state = AgentState(**state)
        answer = state.answer
    end_time = time.time()

    print("I actually reached here" * 10)
    print(f"Agent response time: {end_time - start_time:.2f} seconds")

    # Update the thread with the new messages
    now = datetime.now(timezone.utc)
    new_messages = [
        {"type": "user", "content": question, "timestamp": now},
        {"type": "agent", "content": answer, "timestamp": now},
    ]

    thread["chats"].extend(new_messages)
    thread["updatedAt"] = now

    db.users.update_one({"userId": user_id}, {"$set": {f"threads.{thread_id}": thread}})
    response = {
        "thread_id": thread_id,
        "user_id": user_id,
        "question": question,
        "answer": answer,
    }
    
    return response
