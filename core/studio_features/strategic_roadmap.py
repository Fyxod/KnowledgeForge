import json
import logging
import os
import time

from core.constants import GPU_STRATEGIC_ROADMAP_LLM
from core.llm.client import invoke_llm
from core.llm.outputs import StrategicRoadmapLLMOutput
from core.llm.output_schemas.strategic_roadmap_outputs import (
    StrategicRoadmapSkeleton,
    StrategicPhasedRoadmapOutput,
)
from core.llm.prompts.strategic_roadmap_prompt import (
    strategic_roadmap_skeleton_prompt,
    strategic_roadmap_phases_prompt,
)
from core.models.document import Document
from core.utils.compress_data import compress_global_file_data

os.makedirs("DEBUG", exist_ok=True)
logger = logging.getLogger("studio.strategic_roadmap")


async def generate_strategic_roadmap(
    document: Document | list[Document], n_years: int = 5
) -> StrategicRoadmapLLMOutput:
    """
    Generate a strategic roadmap using two-phase LLM generation.

    Phase 1 (Skeleton): vision, baseline, pillars, enablers, risks, metrics, opportunities
    Phase 2 (Phases): detailed phased roadmap aligned with the skeleton
    """
    document_text = fetch_document_content(document)

    # ── Phase 1: Skeleton ──
    phase1_start = time.time()
    logger.info("[Phase 1/2] Generating strategic roadmap skeleton...")

    skeleton_prompt = strategic_roadmap_skeleton_prompt(document_text, n_years)
    skeleton = await invoke_llm(
        gpu_model=GPU_STRATEGIC_ROADMAP_LLM.model,
        response_schema=StrategicRoadmapSkeleton,
        contents=skeleton_prompt,
        port=GPU_STRATEGIC_ROADMAP_LLM.port,
    )
    skeleton = StrategicRoadmapSkeleton.model_validate(skeleton)

    phase1_time = time.time() - phase1_start
    logger.info(
        f"[Phase 1/2] Skeleton generated in {phase1_time:.1f}s — "
        f"pillars={len(skeleton.strategic_pillars)}, risks={len(skeleton.risks_and_mitigation)}"
    )

    # ── Phase 2: Phased Roadmap ──
    phase2_start = time.time()
    logger.info("[Phase 2/2] Generating phased roadmap...")

    skeleton_json = json.dumps(skeleton.model_dump(), indent=2, ensure_ascii=False)
    phases_prompt = strategic_roadmap_phases_prompt(document_text, n_years, skeleton_json)
    phases = await invoke_llm(
        gpu_model=GPU_STRATEGIC_ROADMAP_LLM.model,
        response_schema=StrategicPhasedRoadmapOutput,
        contents=phases_prompt,
        port=GPU_STRATEGIC_ROADMAP_LLM.port,
    )
    phases = StrategicPhasedRoadmapOutput.model_validate(phases)

    phase2_time = time.time() - phase2_start
    logger.info(
        f"[Phase 2/2] Phased roadmap generated in {phase2_time:.1f}s — "
        f"phases={len(phases.phased_roadmap)}"
    )

    # ── Merge ──
    result = StrategicRoadmapLLMOutput(
        **skeleton.model_dump(),
        phased_roadmap=phases.phased_roadmap,
    )

    logger.info(
        f"Strategic roadmap complete in {phase1_time + phase2_time:.1f}s "
        f"(phase1={phase1_time:.1f}s, phase2={phase2_time:.1f}s)"
    )

    return result


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
            gpu_model=GPU_STRATEGIC_ROADMAP_LLM.model,
            prompt_offset=2500,
        )
        # Join all compressed docs into one string
        docs_string = "\n\n".join(
            f"Title - {d['title']}\n\nContent - {d['content']}" for d in compressed
        )
        return f"Multiple Documents\n\n{docs_string}"


def word_count(text: str) -> int:
    return len(text.split())


def build_strategic_roadmap_prompt(document_text: str, n_years: int) -> str:

    prompt = strategic_roadmap_prompt(document=document_text, n_years=n_years)
    return prompt
