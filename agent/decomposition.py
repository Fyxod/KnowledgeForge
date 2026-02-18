from typing import Optional
from core.llm.prompts.decomposition_prompt import decomposition_prompt
from core.llm.outputs import DecompositionLLMOutput
from core.llm.client import invoke_llm
from core.constants import GPU_DECOMPOSITION_LLM


async def decomposition_node(
    question: str,
    messages: list,
    has_spreadsheet_data: bool = False,
    spreadsheet_schema: Optional[str] = None,
) -> DecompositionLLMOutput:
    recent_chat_history = []

    prompt = decomposition_prompt(
        recent_history=recent_chat_history,
        question=question,
        has_spreadsheet_data=has_spreadsheet_data,
        spreadsheet_schema=spreadsheet_schema,
    )

    result: DecompositionLLMOutput = await invoke_llm(
        contents=prompt,
        gpu_model=GPU_DECOMPOSITION_LLM.model,
        port=GPU_DECOMPOSITION_LLM.port,
        response_schema=DecompositionLLMOutput,
    )
    return result
