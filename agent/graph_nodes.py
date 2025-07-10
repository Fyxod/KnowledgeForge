import json
import time

from langchain_core.messages import AIMessage, HumanMessage

from agent.graph_helpers import build_main_prompt, build_rewrite_prompt, parallel_search
from agent.state import AgentState
from agent.tools.search import search_tool

from core.constants import *
from core.embeddings.retriever import get_user_retriever
from core.llm.client import llm
from core.llm.outputs import MainLLMOutput, REWRITELLMOutput



async def generate(state: AgentState) -> AgentState:
    prompt = build_main_prompt(state)
    with open("formatted_prompt.txt", "w", encoding="utf-8") as f:
        for msg in prompt:
            role = msg.__class__.__name__.replace("Message", "").upper()
            f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

    structured_llm = llm.with_structured_output(MainLLMOutput)
    start_time = time.time()
    result: MainLLMOutput = await structured_llm.ainvoke(prompt)
    end_time = time.time()
    print("LLM result: ", result)
    print(f"LLM response time: {end_time - start_time:.2f} seconds")
    with open("llm_result.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=4)
    state.messages.append(HumanMessage(content=state.question))  # controversial
    state.messages.append(AIMessage(content=result.answer))
    state.messages.append(AIMessage("Action: " + result.action))
    state.answer = result.answer
    state.action = result.action
    state.documents_used = result.documents_used or []
    state.search_queries = result.web_search_queries or []
    state.attempts += 1
    return state


async def web_search(state: AgentState) -> AgentState:
    queries = state.search_queries

    results = await parallel_search(queries, search_tool)
    print("Web search results: ", results)
    with open("web_search_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    state.web_search = True
    state.documents = []
    state.messages.append(
        HumanMessage(content=f"Web search initiated for queries: {queries}")
    )
    state.web_search_attempts += 1
    state.search_queries_results = results

    state.messages.append(HumanMessage(content=f"Web search results: {results}"))

    return state


async def failure(state: AgentState) -> AgentState:
    """
    Handles the failure case when no action can be taken.
    """
    failure_message = (
        "I am unable to answer your question at this time. "
        "Please try rephrasing or asking a different question."
    )
    state.messages.append(AIMessage(content=failure_message))
    state.answer = failure_message
    return state
    # return END if the above line ever throws error


async def rewrite_query(state: AgentState) -> AgentState:
    """
    Rewrites the user's question for semantic vector search.
    This function uses the most recent conversation turns to rewrite the question.
    """
    prompt = build_rewrite_prompt(state)
    with open("rewrite_query.txt", "w", encoding="utf-8") as f:
        for msg in prompt:
            role = msg.__class__.__name__.replace("Message", "").upper()
            f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

    structured_llm = llm.with_structured_output(REWRITELLMOutput)
    start_time = time.time()
    result: REWRITELLMOutput = await structured_llm.ainvoke(prompt)
    end_time = time.time()
    print("Rewrite result: ", result)
    print(f"Rewrite response time: {end_time - start_time:.2f} seconds")
    rewritten_query = result.rewritten_query
    with open("rewrite_result.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=4)
    # state.messages.append(
    #     HumanMessage(
    #         content=f"Rewriting question for semantic search: {state.question}"
    #     )
    # )
    # state.messages.append(HumanMessage(content=f"Rewritten query: {rewritten_query}"))
    state.retrieval_query = rewritten_query
    return state


async def retriever(state: AgentState) -> AgentState:
    """Retrieves documents based on the user's question.
    This is a placeholder function that simulates document retrieval.
    """
    print("SLEEPING " * 8)
    start_time = time.time()
    doc_retriever = get_user_retriever(state.user_id, k=25)  # try different k values
    end_time = time.time()
    print(
        f"Initialized retriever in {end_time - start_time:.2f} seconds for user {state.user_id}"
    )

    start_time = time.time()
    retrieved_docs = await doc_retriever.ainvoke(
        state.retrieval_query or state.question
    )
    end_time = time.time()
    print(
        f"Retrieved {len(retrieved_docs)} documents in {end_time - start_time:.2f} seconds for user {state.user_id}"
    )
    retrieved_docs = [doc.model_dump() for doc in retrieved_docs]
    # print("docs retrieved: ", retrieved_docs)
    with open(f"retrieved_docs_{state.user_id}.json", "w", encoding="utf-8") as f:
        json.dump(retrieved_docs, f)
    state.documents = retrieved_docs
    return state


def router(state: AgentState) -> str:
    if state.action == "answer":
        print("Answering the question")
        return ANSWER

    elif state.action == "web_search":
        print("Initiating web search")
        if state.web_search_attempts < MAX_WEB_SEARCH:
            return WEB_SEARCH
        else:
            return FAILURE

    return ANSWER
