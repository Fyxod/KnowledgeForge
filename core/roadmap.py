import os
from core.llm.prompts.roadmap_prompt import roadmap_prompt
from core.models.document import Document
from core.llm.client import invoke_llm
from core.llm.outputs import StrategicRoadmapLLMOutput
from core.constants import GPU_ROADMAP_LLM

os.makedirs("DEBUG", exist_ok=True)


async def generate_roadmap(
    document: Document, n_years: int = 5
) -> StrategicRoadmapLLMOutput:
    """
    Generate a strategic roadmap based on the provided document.

    Args:
        document (Document): The document to base the roadmap on.
        n_years (int): The number of years for the roadmap.

    Returns:
        StrategicRoadmapLLMOutput: The generated strategic roadmap.
    """
    document_text = fetch_document_content(document)

    prompt = build_roadmap_prompt(document_text, n_years)

    response: StrategicRoadmapLLMOutput = await invoke_llm(
        gpu_model=GPU_ROADMAP_LLM.model,
        response_schema=StrategicRoadmapLLMOutput,
        contents=prompt,
        port=GPU_ROADMAP_LLM.port,
    )

    return response


def fetch_document_content(document: Document) -> str:
    if hasattr(document, "full_text") and word_count(document.full_text) < 6000:
        print("Using full text for roadmap creation")
        text = document.full_text
    elif hasattr(document, "summary") and document.summary:
        print("Using summary for roadmap creation")
        text = document.summary
    else:
        print("Using truncated text for roadmap creation")
        words = document.full_text.split()[:15000]
        text = " ".join(words)

    return f"\n{document.title}\n\n{text}"


def word_count(text: str) -> int:
    return len(text.split())


def build_roadmap_prompt(document_text: str, n_years: int) -> str:

    prompt = roadmap_prompt(document=document_text, n_years=n_years)
    return prompt
