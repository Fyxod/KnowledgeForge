import json
import logging
import os
import time

from core.constants import GPU_TECHNICAL_ROADMAP_LLM
from core.llm.client import invoke_llm
from core.llm.outputs import TechnicalRoadmapLLMOutput
from core.llm.output_schemas.technical_roadmap_outputs import (
    TechnicalRoadmapFoundation,
    TechnicalRoadmapAnalysis,
    TechnicalPhasedRoadmapOutput,
)
from core.llm.prompts.technical_roadmap_prompt import (
    technical_roadmap_foundation_prompt,
    technical_roadmap_analysis_prompt,
    technical_roadmap_phases_prompt,
)
from core.models.document import Document
from core.utils.compress_data import compress_global_file_data

os.makedirs("DEBUG", exist_ok=True)
logger = logging.getLogger("studio.technical_roadmap")


async def generate_technical_roadmap(
    document: Document | list[Document], n_years: int = 5
) -> TechnicalRoadmapLLMOutput:
    """
    Generate a technical roadmap using three-phase LLM generation.

    Phase 1 (Foundation): title, vision, current state, technology domains
    Phase 2 (Analysis): enablers, risks, innovations, tabular summary, inferred additions
    Phase 3 (Phases): detailed phased roadmap (short/mid/long term)
    """
    document_text = fetch_document_content(document)

    # ── Phase 1: Foundation ──
    phase1_start = time.time()
    logger.info("[Phase 1/3] Generating technical roadmap foundation...")

    foundation_prompt = technical_roadmap_foundation_prompt(document_text, n_years)
    foundation = await invoke_llm(
        gpu_model=GPU_TECHNICAL_ROADMAP_LLM.model,
        response_schema=TechnicalRoadmapFoundation,
        contents=foundation_prompt,
        port=GPU_TECHNICAL_ROADMAP_LLM.port,
    )
    foundation = TechnicalRoadmapFoundation.model_validate(foundation)

    phase1_time = time.time() - phase1_start
    logger.info(
        f"[Phase 1/3] Foundation generated in {phase1_time:.1f}s — "
        f"domains={len(foundation.technology_domains)}"
    )

    foundation_json = json.dumps(foundation.model_dump(), indent=2, ensure_ascii=False)

    # ── Phase 2: Analysis ──
    phase2_start = time.time()
    logger.info("[Phase 2/3] Generating analysis (enablers, risks, innovations)...")

    analysis_prompt = technical_roadmap_analysis_prompt(document_text, n_years, foundation_json)
    analysis = await invoke_llm(
        gpu_model=GPU_TECHNICAL_ROADMAP_LLM.model,
        response_schema=TechnicalRoadmapAnalysis,
        contents=analysis_prompt,
        port=GPU_TECHNICAL_ROADMAP_LLM.port,
    )
    analysis = TechnicalRoadmapAnalysis.model_validate(analysis)

    phase2_time = time.time() - phase2_start
    logger.info(
        f"[Phase 2/3] Analysis generated in {phase2_time:.1f}s — "
        f"enablers={len(analysis.key_technology_enablers)}, risks={len(analysis.risks_and_mitigations)}"
    )

    # ── Phase 3: Phased Roadmap ──
    phase3_start = time.time()
    logger.info("[Phase 3/3] Generating phased roadmap...")

    phases_prompt = technical_roadmap_phases_prompt(document_text, n_years, foundation_json)
    phases = await invoke_llm(
        gpu_model=GPU_TECHNICAL_ROADMAP_LLM.model,
        response_schema=TechnicalPhasedRoadmapOutput,
        contents=phases_prompt,
        port=GPU_TECHNICAL_ROADMAP_LLM.port,
    )
    phases = TechnicalPhasedRoadmapOutput.model_validate(phases)

    phase3_time = time.time() - phase3_start
    logger.info(f"[Phase 3/3] Phased roadmap generated in {phase3_time:.1f}s")

    # ── Merge ──
    total_time = phase1_time + phase2_time + phase3_time
    result = TechnicalRoadmapLLMOutput(
        **foundation.model_dump(),
        **analysis.model_dump(),
        phased_roadmap=phases.phased_roadmap,
    )

    logger.info(
        f"Technical roadmap complete in {total_time:.1f}s "
        f"(phase1={phase1_time:.1f}s, phase2={phase2_time:.1f}s, phase3={phase3_time:.1f}s)"
    )

    return result


def fetch_document_content(document: Document | list[Document]) -> str:

    # If a single Document, use original logic
    if isinstance(document, Document):
        if hasattr(document, "full_text") and word_count(document.full_text) < 8000:
            print("Using full text for technical roadmap creation")
            text = document.full_text
        elif hasattr(document, "summary") and document.summary:
            print("Using summary for technical roadmap creation")
            text = document.summary
        else:
            print("Using truncated text for technical roadmap creation")
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
            max_tokens=50000,
            gpu_model=GPU_TECHNICAL_ROADMAP_LLM.model,
            prompt_offset=2800,
        )
        # Join all compressed docs into one string
        docs_string = "\n\n".join(
            f"Title - {d['title']}\n\nContent - {d['content']}" for d in compressed
        )
        return f"Multiple Documents\n\n{docs_string}"


def word_count(text: str) -> int:
    return len(text.split())


