import os
from core.llm.prompts.strategic_roadmap_prompt import strategic_roadmap_prompt
from core.models.document import Document
from core.llm.client import invoke_llm
from core.llm.outputs import StrategicRoadmapLLMOutput
from core.constants import GPU_STRATEGIC_ROADMAP_LLM
from core.utils.compress_data import compress_global_file_data

os.makedirs("DEBUG", exist_ok=True)


async def generate_strategic_roadmap(
    document: Document | list[Document], n_years: int = 5
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

    prompt = build_strategic_roadmap_prompt(document_text, n_years)

    response: StrategicRoadmapLLMOutput = await invoke_llm(
        gpu_model=GPU_STRATEGIC_ROADMAP_LLM.model,
        response_schema=StrategicRoadmapLLMOutput,
        contents=prompt,
        port=GPU_STRATEGIC_ROADMAP_LLM.port,
    )

    return response


def fetch_document_content(document: Document | list[Document]) -> str:

    # If a single Document, use original logic
    if isinstance(document, Document):
        if hasattr(document, "full_text") and word_count(document.full_text) < 8000:
            print("Using full text for strategic roadmap creation")
            text = document.full_text
        elif hasattr(document, "summary") and document.summary:
            print("Using summary for strategic roadmap creation")
            text = document.summary
        else:
            print("Using truncated text for strategic roadmap creation")
            words = document.full_text.split()[:8000]
            text = " ".join(words)
        return f"\nTitle - {document.title}\n\n{text}"

    # If a list of Document, compress contents
    elif isinstance(document, list):
        doc_dicts = []
        for doc in document:
            if hasattr(doc, "full_text") and word_count(doc.full_text) < 8000:
                text = doc.full_text
            elif hasattr(doc, "summary") and doc.summary:
                text = doc.summary
            else:
                words = doc.full_text.split()[:8000]
                text = " ".join(words)
            doc_dicts.append({"title": doc.title, "content": text})

        compressed = compress_global_file_data(
            doc_dicts,
            max_tokens=50000,
            gpu_model=GPU_STRATEGIC_ROADMAP_LLM.model,
            prompt_offset=2500,
        )
        # Join all compressed docs into one string
        return "Multiple Documents\n\n".join(
            f"Title - {d['title']}\n\nContent - {d['content']}" for d in compressed
        )


def word_count(text: str) -> int:
    return len(text.split())


def build_strategic_roadmap_prompt(document_text: str, n_years: int) -> str:

    prompt = strategic_roadmap_prompt(document=document_text, n_years=n_years)
    return prompt
