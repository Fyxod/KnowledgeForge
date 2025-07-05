import asyncio
from typing import List, Literal, Optional
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate

from langgraph.graph import (
    StateGraph,
    add_messages,
    END,
    START
)

from pydantic import BaseModel, Field

from core.llm import llm
from core.search_tool import search_tool
from core.schemas.user import UserModel
from core.vectorstore import get_user_retriever


RETRIEVER = "retriever"
GENERATE = "generate"
WEB_SEARCH = "web_search"
REPHRASE = "rephrase"
ANSWER = "answer"
ROUTER = "router"
FAILURE = "failure"

    
main_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="You are a helpful assistant that answers questions based on the provided documents."
        ),
        SystemMessage(
            content="If the question is not answerable based on the provided documents, you should rephrase the question to make it more specific or initiate a web search for queries that you think are relevant."
        ),
        SystemMessage(
            content="If you are unsure about the answer, you should rephrase the question to make it more specific or initiate a web search for queries that you think are relevant."
        ),
        MessagesPlaceholder(variable_name="messages"),
        HumanMessage(
            content="Here is the retrieved context according to the question: {documents}"
        ),
        HumanMessage(content="{question}"),
    ]
)



class AgentState(TypedDict, total=False):
    user_id: str
    thread_id: str
    question: str
    original_question: str
    messages: List[BaseMessage]
    documents: List[str]
    web_search: bool
    search_queries: List[str]
    search_queries_results: List[str]
    answer: str
    documents_used: List[str]
    attempts: int
    rephrases: int
    web_search_attempts: int
    action: Literal["answer", "rephrase_question", "web_search"]

MAX_REPHRASE = 2
MAX_WEB_SEARCH = 2


async def parallel_search(queries, tool):
    tasks = [tool.ainvoke(query) for query in queries]
    results = await asyncio.gather(*tasks)
    return results

class LLMOutput(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal["answer", "rephrase_question", "web_search"] = Field(
        description="The action to take based on the answer."
    )
    documents_used: Optional[List[str]] = Field(
        default=None,
        description="List of document ids of documents used to generate the answer, if applicable.",
    )
    web_search_queries: Optional[List[str]] = Field(
        default=None,
        description="List of 2-3 web search queries used to generate the answer, if applicable.",
    )


def build_main_prompt(state: AgentState) -> ChatPromptTemplate:
    """
    Builds the main prompt for the agent based on the current state.
    """

    if state["web_search"]:
        documents = state.get("search_queries_results", [])
    else:
        documents = state.get("documents", [])

    return main_prompt.format_messages(
        messages=MessagesPlaceholder(variable_name="messages"),
        documents=documents,
        question=state.get("question", ""),
    )


async def generate(state: AgentState) -> AgentState:
    prompt = build_main_prompt(state)
    structured_llm = llm.with_structured_output(LLMOutput)
    result: LLMOutput = await structured_llm.ainvoke(prompt)
    state["messages"].append(AIMessage(content=result.answer))
    state["messages"].append(AIMessage("Action: " + result.action))
    state["answer"] = result.answer
    state["action"] = result.action
    state["documents_used"] = result.documents_used or []
    state["search_queries"] = result.web_search_queries or []
    state["attempts"] += 1
    return state

async def rephrase_question(state: AgentState) -> AgentState:
    rephrased = f"Refined: {state['question']}"
    state["messages"].append(
        HumanMessage(
            content=f"Rephrasing question: {state['question']}"
        )
    )
    state["question"] = rephrased
    state["rephrases"] = state.get("rephrases", 0) + 1
    # state["messages"].append(HumanMessage(content=rephrased))
    return state

async def web_search(state: AgentState) -> AgentState:
    queries = state.get("search_queries", [])
    
    results = await parallel_search(queries, search_tool)
    
    state["web_search"] = True
    state["documents"] = []
    state["messages"].append(
        HumanMessage(content=f"Web search initiated for queries: {queries}")
    )
    state["web_search_attempts"] = state.get("web_search_attempts", 0) + 1
    state["search_queries_results"] = results

    state["messages"].append(HumanMessage(content=f"Web search results: {results}"))

    return state

def failure(state: AgentState) -> AgentState:
    """ 
    Handles the failure case when no action can be taken.
    """
    failure_message = (
        "I am unable to answer your question at this time. "
        "Please try rephrasing or asking a different question."
    )
    state["messages"].append(AIMessage(content=failure_message))
    state["answer"] = failure_message
    # state["action"] = "failure"
    return END

async def failure(state: AgentState) -> AgentState:
    failure_message = (
        "I am unable to answer your question at this time. "
        "Please try rephrasing or asking a different question."
    )
    state["messages"].append(AIMessage(content=failure_message))
    state["answer"] = failure_message
    return state

async def retriever(state: AgentState) -> AgentState:
    """ Retrieves documents based on the user's question.
    This is a placeholder function that simulates document retrieval.
    """

    doc_retrievar = get_user_retriever();

    retrieved_docs = await doc_retrievar.ainvoke(state["question"])
    state["documents"] = retrieved_docs
    return state

def router(state: AgentState) -> str:
    if state["action"] == "answer":
        return ANSWER
    elif state["action"] == "rephrase_question":
        if state.get("rephrases", 0) < MAX_REPHRASE:
            return REPHRASE
        else:
            return (
                WEB_SEARCH
                if state.get("web_search_attempts", 0) < MAX_WEB_SEARCH
                else FAILURE
            )
    elif state["action"] == "web_search":
        return (
            WEB_SEARCH if state.get("web_search_attempts", 0) < MAX_WEB_SEARCH else FAILURE
        )
    return ANSWER


# Building the state graph

graph_builder = StateGraph(AgentState)

graph_builder.add_node(RETRIEVER, retriever)
graph_builder.add_node(GENERATE, generate)
graph_builder.add_node(ROUTER, router)
graph_builder.add_node(REPHRASE, rephrase_question)
graph_builder.add_node(WEB_SEARCH, web_search)
graph_builder.add_node(ANSWER, lambda state: END)
graph_builder.add_node(FAILURE, failure)

graph_builder.set_entry_point(RETRIEVER)

graph_builder.add_edge(RETRIEVER, GENERATE)
graph_builder.add_edge(GENERATE, ROUTER)

graph_builder.add_conditional_edges(
    ROUTER,
    {   
        FAILURE: failure,
        ANSWER: lambda state: END,
        REPHRASE: rephrase_question,
        WEB_SEARCH: web_search,
    },
)

graph_builder.add_edge(REPHRASE, RETRIEVER)
graph_builder.add_edge(WEB_SEARCH, GENERATE)
graph_builder.add_edge(FAILURE, END)

Agent = graph_builder.compile()
