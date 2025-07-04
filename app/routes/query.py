from fastapi import APIRouter, Request
from pydantic import BaseModel
from core.database import db
from agents.agent import Agent, AgentState
from core.schemas.user import UserModel
from langchain.schema import HumanMessage, AIMessage

router=APIRouter(
    prefix='/query',
    tags=['query']
)

# Define the request body model
class QueryRequest(BaseModel):
    thread_id: str
    question: str

@router.post("/")
async def query(request: Request, body: QueryRequest):
    payload = request.state.user
    
    if not payload:
        return {"error": "User not authenticated"}
    
    # Access thread_id and question from body
    thread_id = body.thread_id
    question = body.question

    user_id = payload.id

    user = await db.users.find_one({"_id": user_id})
    if not user:
        return {"error": "User not found"}

    user = UserModel(**user)

    thread = user.threads.get(thread_id)
    if not thread:
        return {"error": "Thread not found"}
    
    messages = []

    for message in thread.get("messages", []):
        if message.type == "user":
            messages.append(HumanMessage(content=message.content))
        elif message.type == "agent":
            messages.append(AIMessage(content=message.content))

    state = AgentState(
        user_id=user_id,
        thread_id=thread_id,
        question=question,
        messages=messages,
        original_question=question,
    )
    
    response = Agent.ainvoke(state)

    if isinstance(response, AgentState):
        # Update the thread with the new message
        new_messages = [
            HumanMessage(content=state.question),
            AIMessage(content=response.answer)
        ]
        thread["messages"].extend(new_messages)
        await db.users.update_one(
            {"_id": user_id},
            {"$set": {f"threads.{thread_id}": thread}}
        )
    else:
    # If the response is not an AgentState, it might be an error or a different type, still have to figure out errors
        return {"error": "Unexpected response from agent"}
    
    return response # have to set a good json response format
