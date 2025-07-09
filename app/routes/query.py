from fastapi import APIRouter, Request
from pydantic import BaseModel
from core.database import db
from agents.agent import Agent, AgentState
from core.schemas.user import UserModel
from langchain.schema import HumanMessage, AIMessage
from datetime import datetime, timezone
import time
router=APIRouter(
    prefix='/query',
    tags=['query']
)

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

    print(user)

    thread = user["threads"].get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    print(f"Thread found: {thread}")
    messages = []

    for message in thread.get("chats", []):
        if message["type"] == "user":
            messages.append(HumanMessage(content=message["content"]))
        elif message["type"] == "agent":
            messages.append(AIMessage(content=message["content"]))

    print(messages)
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
    print(type(response))
    end_time = time.time()
    
    print("I actually reached here"*10)
    print(f"Response from agent: {response}")
    print(f"Agent response time: {end_time - start_time:.2f} seconds")

    # if isinstance(response, AgentState):
    # Update the thread with the new messages
    now = datetime.now(timezone.utc)
    new_messages = [
        {
            "type": "user",
            "content": response.question,
            "timestamp": now
        },
        {
            "type": "agent",
            "content": response.answer,
            "timestamp": now
        }
    ]
    thread["chats"].extend(new_messages)
    thread["updatedAt"] = now
    db.users.update_one(
        {"userId": user_id},
        {"$set": {f"threads.{thread_id}": thread}}
    )
    # else:
    # # If the response is not an AgentState, it might be an error or a different type, still have to figure out errors
    #     return {"error": "Unexpected response from agent"}
    
    return response.model_dump(exclude_none=True)
