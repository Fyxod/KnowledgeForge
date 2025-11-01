import os
from core.llm.prompts.insights_prompt import insights_prompt
from core.models.document import Document
from core.llm.client import invoke_llm
from core.llm.outputs import InsightsLLMOutput
from core.constants import GPU_INSIGHTS_LLM

os.makedirs("DEBUG", exist_ok=True)


async def generate_insights(document: Document) -> InsightsLLMOutput:
    print("Generating insights for document ID:", document.id)
    document_text = fetch_document_content(document)

    prompt = build_insights_prompt(document_text)

    response: InsightsLLMOutput = await invoke_llm(
        gpu_model=GPU_INSIGHTS_LLM.model,
        response_schema=InsightsLLMOutput,
        contents=prompt,
        port=GPU_INSIGHTS_LLM.port,
    )

    return response


def fetch_document_content(document: Document) -> str:
    if hasattr(document, "full_text") and word_count(document.full_text) < 6000:
        print("Using full text for insights extraction")
        text = document.full_text
    elif hasattr(document, "summary") and document.summary:
        print("Using summary for insights extraction")
        text = document.summary
    else:
        print("Using truncated text for insights extraction")
        words = document.full_text.split()[:15000]
        text = " ".join(words)

    return f"\n{document.title}\n\n{text}"


def word_count(text: str) -> int:
    return len(text.split())


def build_insights_prompt(document_text: str) -> str:

    prompt = insights_prompt(document=document_text)
    return prompt
