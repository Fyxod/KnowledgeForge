import os
from core.llm.prompts.pros_cons_prompt import pros_cons_prompt
from core.models.document import Document
from core.llm.client import invoke_llm
from core.llm.outputs import ProsConsOutput
from core.constants import GPU_PROS_CONS_LLM

os.makedirs("DEBUG", exist_ok=True)


async def generate_pros_cons(document: Document, count: int = 10) -> ProsConsOutput:

    document_text = fetch_document_content(document)

    prompt = build_pros_cons_prompt(document_text, count)

    response: ProsConsOutput = await invoke_llm(
        gpu_model=GPU_PROS_CONS_LLM.model,
        response_schema=ProsConsOutput,
        contents=prompt,
        port=GPU_PROS_CONS_LLM.port,
    )

    return response


def fetch_document_content(document: Document) -> str:
    if hasattr(document, "full_text") and word_count(document.full_text) < 6000:
        print("Using full text for pros and cons extraction")
        text = document.full_text
    elif hasattr(document, "summary") and document.summary:
        print("Using summary for pros and cons extraction")
        text = document.summary
    else:
        print("Using truncated text for pros and cons extraction")
        words = document.full_text.split()[:15000]
        text = " ".join(words)

    return f"\n{document.title}\n\n{text}"


def word_count(text: str) -> int:
    return len(text.split())


def build_pros_cons_prompt(document_text: str, count: int) -> str:

    prompt = pros_cons_prompt(document=document_text, count=count)
    return prompt
