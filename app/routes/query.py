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
    sub_answers = []
    if decomposed:
        print("TO BE DECOMPOSED")
        print("No of sub-queries:", len(decomposition_result.sub_queries))
        for idx, sub_query in enumerate(decomposition_result.sub_queries):
            qs = time.time()
            state = await Agent.ainvoke(AgentState(
                user_id=user_id,
                thread_id=thread_id,
                query=sub_query,
                resolved_query=decomposition_result.resolved_query,
                original_query=question,
                messages=[],
                web_search=False,
            ))
            state = AgentState(**state)
            qe = time.time() - qs
            print(f"Sub-query '{idx}. {sub_query}' processed in {qe:.2f} seconds")
            sub_answers.append({"sub_query": sub_query, "sub_answer": state.answer})
        cs = time.time()
        answer = await combination_node(sub_answers, decomposition_result.resolved_query, question)
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
    

    # chunks_used = []
    # if response.chunks_used:
    #     print(f"Processing {len(response.chunks_used)} citations...")
        
    #     for doc_i in response.chunks_used:
    #         for doc_j in response.documents:
    #             if doc_i.document_id == doc_j["metadata"]["document_id"] and doc_i.page_no == doc_j["metadata"]["page_no"] and doc_i.chunk_index == doc_j["metadata"]["chunk_index"]:
    #                 chunks_used.append(doc_j)
    #                 break

    # print(f"Found {len(chunks_used)} citation matches")

    # # Update the agent message with citations
    # if chunks_used:
    #     thread["chats"][-1]["documents_used"] = chunks_used

    db.users.update_one({"userId": user_id}, {"$set": {f"threads.{thread_id}": thread}})
    response = {
        "thread_id": thread_id,
        "user_id": user_id,
        "question": question,
        "answer": answer,
    }
    # response["documents_used"] = chunks_used
    # del response["search_queries_results"]
    # del response["documents"]
    return response
