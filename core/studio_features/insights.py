import os
from core.llm.prompts.insights_prompt import insights_prompt
from core.models.document import Document
from core.llm.client import invoke_llm
from core.llm.outputs import InsightsLLMOutput
from core.constants import GPU_INSIGHTS_LLM
from core.utils.compress_data import compress_global_file_data

os.makedirs("DEBUG", exist_ok=True)
os.makedirs("debug", exist_ok=True)


async def generate_insights(document: Document | list[Document]) -> InsightsLLMOutput:
    document_text = fetch_document_content(document)

    prompt = build_insights_prompt(document_text)
    
    response: InsightsLLMOutput = await invoke_llm(
        gpu_model=GPU_INSIGHTS_LLM.model,
        response_schema=InsightsLLMOutput,
        contents=prompt,
        port=GPU_INSIGHTS_LLM.port,
    )

    return response


def fetch_document_content(document: Document | list[Document]) -> str:

    # If a single Document, use original logic
    if isinstance(document, Document):
        if hasattr(document, "full_text") and word_count(document.full_text) < 8000:
            print("Using full text for insights extraction")
            text = document.full_text
        elif hasattr(document, "summary") and document.summary:
            print("Using summary for insights extraction")
            text = document.summary
        else:
            print("Using truncated text for insights extraction")
            words = document.full_text.split()[:8000]
            text = " ".join(words)
        return f"\n{document.title}\n\n{text}"

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
        # Dummy values for other args
        compressed = compress_global_file_data(
            doc_dicts,
            max_tokens=50000,
            gpu_model=GPU_INSIGHTS_LLM.model,
            prompt_offset=2000,
        )
        # Join all compressed docs into one string
        return "Multiple Documents\n\n".join(
            f"Title - {d['title']}\n\nContent - {d['content']}" for d in compressed
        )


def word_count(text: str) -> int:
    return len(text.split())


def build_insights_prompt(document_text: str) -> str:

    prompt = insights_prompt(document=document_text)
    return prompt
