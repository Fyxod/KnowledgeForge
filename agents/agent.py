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
            content="Here are the retrieved documents according to the question: {documents}"
        ),
        HumanMessage(content="{question}"),
    ]
)


class AgentState(TypedDict):
    user_id: str
    thread_id: str
    messages: List[BaseMessage]
    documents: List[str]
    question: str
    rephrased_question: str
    web_search: bool
    search_queries: List[str]
    search_queries_results: List[str]
    answer: str
    action: Literal["answer", "rephrase_question", "web_search"]
    documents_used: List[str]
    attempts: int
    rephrases: int
    web_search_attempts: int


MAX_REPHRASE = 2
MAX_WEB_SEARCH = 2


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
        description="List of web search queries used to generate the answer, if applicable.",
    )


def build_main_prompt(state: AgentState) -> ChatPromptTemplate:
    """
    Builds the main prompt for the agent based on the current state.
    """
    return main_prompt.format_messages(
        messages=MessagesPlaceholder(variable_name="messages"),
        documents=state.get("documents", []),
        question=state.get("question", ""),
    )


def generate(state: AgentState) -> AgentState:
    prompt = build_main_prompt(state)
    structured_llm = llm.with_structured_output(LLMOutput)
    result: LLMOutput = structured_llm.invoke(prompt)
    state["messages"].append(AIMessage(content=result.answer))
    state["messages"].append(AIMessage("Action: " + result.action))
    state["answer"] = result.answer
    state["action"] = result.action
    state["documents_used"] = result.documents_used or []
    state["search_queries"] = result.web_search_queries or []
    state["attempts"] += 1

    return state


def rephrase_question(state: AgentState) -> AgentState:
    """
    Rephrases the question based on the current state.
    """

    return state


def rephrase_question(state: AgentState) -> AgentState:

    rephrased = f"Refined: {state['question']}"
    state["question"] = rephrased
    state["rephrases"] = state.get("rephrases", 0) + 1
    state["messages"].append(HumanMessage(content=rephrased))
    return state


def web_search(state: AgentState) -> AgentState:
    query = state["question"]
    results = search_tool.invoke([query])
    state["web_search_attempts"] = state.get("web_search_attempts", 0) + 1
    state["search_queries"] = [query]
    state["search_queries_results"] = results
    state["messages"].append(HumanMessage(content=f"Web search results: {results}"))
    return state


def web_search(state: AgentState) -> AgentState:
    queries = state.get("search_queries", [])
    results = search_tool.invoke(queries)
    state["web_search_attempts"] = state.get("web_search_attempts", 0) + 1
    state["search_queries_results"] = results

    state["messages"].append(HumanMessage(content=f"Web search results: {results}"))

    return state


# def router(state: AgentState) -> AgentState:
#     """
#     Routes the action based on the current state.
#     """


def router(state: AgentState) -> str:
    if state["action"] == "answer":
        return END
    elif state["action"] == "rephrase_question":
        if state.get("rephrases", 0) < MAX_REPHRASE:
            return REPHRASE
        else:
            return (
                WEB_SEARCH
                if state.get("web_search_attempts", 0) < MAX_WEB_SEARCH
                else END
            )
    elif state["action"] == "web_search":
        return (
            WEB_SEARCH if state.get("web_search_attempts", 0) < MAX_WEB_SEARCH else END
        )
    return END


# Building the state graph

graph_builder = StateGraph(AgentState)

graph_builder.add_node(RETRIEVER, retriever)
graph_builder.add_node(GENERATE, generate)
graph_builder.add_node(ROUTER, router)
graph_builder.add_node(REPHRASE, rephrase_question)
graph_builder.add_node(WEB_SEARCH, web_search)

graph_builder.set_entry_point(RETRIEVER)

graph_builder.add_edge(RETRIEVER, GENERATE)
graph_builder.add_edge(GENERATE, ROUTER)

graph_builder.add_conditional_edges(
    ROUTER,
    {
        ANSWER: END,
        REPHRASE: REPHRASE,
        WEB_SEARCH: WEB_SEARCH,
    },
)

graph_builder.add_edge(REPHRASE, RETRIEVER)
graph_builder.add_edge(WEB_SEARCH, GENERATE)

agent = graph_builder.compile()
