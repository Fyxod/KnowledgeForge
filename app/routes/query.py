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

from agent.builder import Agent, AgentState
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

    state = AgentState(
        user_id=user_id,
        thread_id=thread_id,
        question=question,
        original_question=question,
        messages=messages,
        web_search=False,
    )
    start_time = time.time()
    response = await Agent.ainvoke(state)
    response = AgentState(**response)
    end_time = time.time()

    print("I actually reached here" * 10)
    print(f"Agent response time: {end_time - start_time:.2f} seconds")

    # Update the thread with the new messages
    now = datetime.now(timezone.utc)
    new_messages = [
        {"type": "user", "content": response.question, "timestamp": now},
        {"type": "agent", "content": response.answer, "timestamp": now},
    ]

    thread["chats"].extend(new_messages)
    thread["updatedAt"] = now

    chunks_used = []
    if response.chunks_used:
        print(f"Processing {len(response.chunks_used)} citations...")
        
        for doc_i in response.chunks_used:
            for doc_j in response.documents:
                if doc_i.document_id == doc_j["metadata"]["document_id"] and doc_i.page_no == doc_j["metadata"]["page_no"] and doc_i.chunk_index == doc_j["metadata"]["chunk_index"]:
                    chunks_used.append(doc_j)
                    break

    print(f"Found {len(chunks_used)} citation matches")

    db.users.update_one({"userId": user_id}, {"$set": {f"threads.{thread_id}": thread}})


    response = response.model_dump(exclude_none=True)
    response["documents_used"] = chunks_used
    del response["search_queries_results"]
    del response["documents"]
    return response
