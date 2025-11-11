import asyncio
from typing import Dict, List

from agent.state import AgentState
from core.llm.prompts.main_prompt import main_prompt
from core.llm.prompts.self_knowledge_prompt import self_knowledge_prompt


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
    tasks = [tool(query) for query in queries]
    results = await asyncio.gather(*tasks)
    return results


def build_main_prompt(state: AgentState):
    """
    Builds the main prompt for the agent based on the current state.
    """

    recent_chats = get_recent_history(
        state.messages, turns=5
    )  # fine tune the no of turns

    return main_prompt(
        messages=recent_chats,
        chunks=state.chunks,
        question=state.query or state.resolved_query or state.original_query,
        summary=state.summary,
        web_search_results=state.web_search_results or None,
        initial_search_answer=state.initial_search_answer or None,
        initial_search_results=state.initial_search_results or None,
        mode=state.mode,
        use_self_knowledge=state.use_self_knowledge or False,
    )


def build_self_knowledge_prompt(
    state: AgentState,
):
    """
    Builds the self-knowledge prompt for the agent based on the current state.
    """

    recent_chats = get_recent_history(
        state.messages, turns=5
    )  # fine tune the no of turns

    return self_knowledge_prompt(
        messages=recent_chats,
        question=state.query or state.resolved_query or state.original_query,
    )
