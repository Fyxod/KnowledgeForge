import os

from core.constants import GPU_TECHNICAL_ANALYSIS_LLM, MODEL_INPUT_BUDGET
from core.llm.client import invoke_llm
from core.llm.outputs import TechnicalAnalysisLLMOutput
from core.llm.prompts.technical_analysis_prompt import technical_analysis_prompt
from core.models.document import Document
from core.utils.compress_data import compress_global_file_data

os.makedirs("DEBUG", exist_ok=True)


async def generate_technical_analysis(
    document: Document | list[Document],
) -> TechnicalAnalysisLLMOutput:
    """
    Generate a technical analysis based on the provided document.

    Args:
        document: The document (or list of documents) to analyze.

    Returns:
        TechnicalAnalysisLLMOutput: The generated technical analysis.
    """
    document_text = fetch_document_content(document)

    prompt = build_technical_analysis_prompt(document_text)

    response: TechnicalAnalysisLLMOutput = await invoke_llm(
        gpu_model=GPU_TECHNICAL_ANALYSIS_LLM.model,
        response_schema=TechnicalAnalysisLLMOutput,
        contents=prompt,
        port=GPU_TECHNICAL_ANALYSIS_LLM.port,
    )

    return response


def fetch_document_content(document: Document | list[Document]) -> str:

    # If a single Document, use original logic
    if isinstance(document, Document):
        if hasattr(document, "full_text") and word_count(document.full_text) < 8000:
            print("Using full text for technical analysis")
            text = document.full_text
        elif hasattr(document, "summary") and document.summary:
            print("Using summary for technical analysis")
            text = document.summary
        else:
            print("Using truncated text for technical analysis")
            words = document.full_text.split()[:8000]
            text = " ".join(words)
        return f"\nTitle - {document.title}\n\n{text}"

    # If a list of Document, compress contents
    elif isinstance(document, list):
        if not document:
            return ""
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
            max_tokens=MODEL_INPUT_BUDGET,
            gpu_model=GPU_TECHNICAL_ANALYSIS_LLM.model,
            prompt_offset=2500,
        )
        # Join all compressed docs into one string
        docs_string = "\n\n".join(
            f"Title - {d['title']}\n\nContent - {d['content']}" for d in compressed
        )
        return f"Multiple Documents\n\n{docs_string}"


def word_count(text: str) -> int:
    return len(text.split())


def build_technical_analysis_prompt(document_text: str) -> str:

    prompt = technical_analysis_prompt(document=document_text)
    return prompt
