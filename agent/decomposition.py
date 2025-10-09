from core.llm.prompts.decomposition_prompt import decomposition_prompt
from agent.graph_helpers import get_recent_history
from core.llm.outputs import DecompositionLLMOutput
from core.llm.client import invoke_llm
from core.constants import Ollama_DECOMPOSITION_LLM


async def decomposition_node(question: str, messages: list) -> DecompositionLLMOutput:
    recent_chat_history = get_recent_history(full_history=messages, turns=5)
    prompt = decomposition_prompt(recent_history=recent_chat_history, question=question)

    result: DecompositionLLMOutput = await invoke_llm(
        contents=prompt,
        ollama_model=Ollama_DECOMPOSITION_LLM.model,
        port=Ollama_DECOMPOSITION_LLM.port,
        response_schema=DecompositionLLMOutput,
    )
    return result
