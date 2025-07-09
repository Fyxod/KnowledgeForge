import asyncio
import json
from typing import List, Literal, Optional, Dict, Any

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate, HumanMessagePromptTemplate
class AbortGraphExecution(Exception):
    pass
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
import time

from core.constants import *
from core.state import AgentState
from agents.nodes import *
# maybe add descriptions to each field

    



    


# Building the state graph

graph_builder = StateGraph(AgentState)

graph_builder.add_node(REWRITE_QUERY, rewrite_query)
graph_builder.add_node(RETRIEVER, retriever)
graph_builder.add_node(GENERATE, generate)
graph_builder.add_node(ROUTER, router)
graph_builder.add_node(WEB_SEARCH, web_search)
graph_builder.add_node(ANSWER, lambda state: END)
graph_builder.add_node(FAILURE, failure)

graph_builder.set_entry_point(REWRITE_QUERY)

graph_builder.add_edge(REWRITE_QUERY, RETRIEVER)
graph_builder.add_edge(RETRIEVER, GENERATE)

graph_builder.add_conditional_edges(
    GENERATE,
    router,
    {
        ANSWER: END,      
        WEB_SEARCH: WEB_SEARCH,
        FAILURE: FAILURE,
    }
)
graph_builder.add_edge(WEB_SEARCH, GENERATE)
graph_builder.add_edge(FAILURE, END)

Agent = graph_builder.compile()
