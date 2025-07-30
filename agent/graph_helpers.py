import asyncio
from typing import Dict, List

from langchain_core.prompts import ChatPromptTemplate

from agent.state import AgentState
from core.llm.prompts.main_query import main_prompt
from core.llm.prompts.rewrite_query import rewrite_query_prompt

def get_recent_history(
    full_history: List[Dict[str, str]], turns: int = 2
) -> List[Dict[str, str]]:
    """
    Returns the most recent conversation turns from the full history.
    Each turn consists of a user message and an assistant response.
    """
    if len(full_history) < turns * 2:
        return full_history
    
    # Get the last 'turns' pairs of user and AI messages
    recent_history = full_history[-(turns * 2) :]
    return recent_history


async def parallel_search(queries, tool):
    tasks = [tool.ainvoke(query) for query in queries]
    results = await asyncio.gather(*tasks)
    return results


def build_main_prompt(state: AgentState) -> ChatPromptTemplate:
    """
    Builds the main prompt for the agent based on the current state.
    """
    if state.web_search:
        documents = state.search_queries_results
    else:
        documents = state.documents

    recent_chats = get_recent_history(
        state.messages, turns=5
    )  # fine tune the no of turns

    return main_prompt.format_messages(
        messages=recent_chats,
        documents=documents,
        question=state.question,
        # question=state.question + "\n" + (state.retrieval_query or ""),  # append retrieval query if exists,
    )


def build_rewrite_prompt(state: AgentState) -> ChatPromptTemplate:
    """Builds the rewrite prompt for the agent based on the current state."""
    recent_history = get_recent_history(state.messages, turns=5)
    prompt = rewrite_query_prompt.format_messages(
        question=state.question,
        recent_history=recent_history,
    )
    return prompt
