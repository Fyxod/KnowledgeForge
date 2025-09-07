from langgraph.graph import END, StateGraph

from agent.graph_nodes import (
    failure,
    generate,
    retriever,
    main_router,
    summary_router,
    web_search,
    document_summarizer,
    global_summarizer,
)
from agent.state import AgentState
from core.constants import *


# Building the state graph
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node(RETRIEVER, retriever)
graph_builder.add_node(GENERATE, generate)
graph_builder.add_node(ROUTER, main_router)
graph_builder.add_node(WEB_SEARCH, web_search)
graph_builder.add_node(ANSWER, lambda state: END)
graph_builder.add_node(FAILURE, failure)
graph_builder.add_node(DOCUMENT_SUMMARIZER, document_summarizer)
graph_builder.add_node(GLOBAL_SUMMARIZER, global_summarizer)

# Set the entry point
graph_builder.set_entry_point(RETRIEVER)

# Define edges
graph_builder.add_edge(RETRIEVER, GENERATE)

# Conditional edges from GENERATE via router
graph_builder.add_conditional_edges(
    GENERATE,
    main_router,
    {
        ANSWER: END,
        WEB_SEARCH: WEB_SEARCH,
        DOCUMENT_SUMMARIZER: DOCUMENT_SUMMARIZER,
        GLOBAL_SUMMARIZER: GLOBAL_SUMMARIZER,
        FAILURE: FAILURE,
    },
)

graph_builder.add_conditional_edges(
    DOCUMENT_SUMMARIZER,
    summary_router,
    {
        ANSWER: END,
        GENERATE: GENERATE,
    },
)
graph_builder.add_conditional_edges(
    GLOBAL_SUMMARIZER,
    summary_router,
    {
        ANSWER: END,
        GENERATE: GENERATE,
    },
)

# Web search loops back to GENERATE
graph_builder.add_edge(WEB_SEARCH, GENERATE)

graph_builder.add_edge(FAILURE, END)

# Compile the agent
Agent = graph_builder.compile()
