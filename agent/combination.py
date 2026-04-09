from core.constants import GPU_COMBINATION_LLM
from core.llm.client import invoke_llm
from core.llm.outputs import CombinationLLMOutput
from core.llm.prompts.combination_prompt import combination_prompt


async def combination_node(
    sub_answers: list, resolved_query: str, original_query: str,
    chunks: list | None = None,
    generative_mode: bool = False,
) -> str:
    combined_prompt = combination_prompt(
        resolved_query=resolved_query or original_query,
        original_query=original_query,
        sub_answers=sub_answers,
        chunks=chunks,
        generative_mode=generative_mode,
    )

    result: CombinationLLMOutput = await invoke_llm(
        contents=combined_prompt,
        gpu_model=GPU_COMBINATION_LLM.model,
        port=GPU_COMBINATION_LLM.port,
        response_schema=CombinationLLMOutput,
    )

    return result.answer
