import asyncio
from typing import Annotated, List, Literal, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.graph import END, StateGraph, START
from core.llm import llm
from pydantic import BaseModel, Field
from types import NotRequired, Optional
from core.search_tool import search_tool
from langgraph.graph import add_messages, StateGraph, END

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from core.schemas.user import User

from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate

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


class AgentState(TypedDict):
    user_id: str
    thread_id: str
    messages: List[BaseMessage]
    documents: List[str] = []
    question: str
    original_question: str
    web_search: bool = False
    search_queries: List[str] = []
    search_queries_results: List[str] = []
    answer: str = ""
    action: NotRequired[Literal["answer", "rephrase_question", "web_search"]]
    documents_used: List[str] = []
    attempts: int = 0
    rephrases: int = 0
    web_search_attempts: int = 0


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
    documents_used: NotRequired[List[str]] = Field(
        default=None,
        description="List of document ids of documents used to generate the answer, if applicable.",
    )
    web_search_queries: NotRequired[List[str]] = Field(
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
        FAILURE: FAILURE,
        ANSWER: ANSWER,
        REPHRASE: REPHRASE,
        WEB_SEARCH: WEB_SEARCH,
    },
)

graph_builder.add_edge(REPHRASE, RETRIEVER)
graph_builder.add_edge(WEB_SEARCH, GENERATE)
graph_builder.add_edge(FAILURE, END)

Agent = graph_builder.compile()
