import uuid
from datetime import datetime, timezone
from typing import List, Optional

from core.constants import (
    GPU_DOC_ITERATE_LLM,
    GPU_DOC_OUTLINE_LLM,
    GPU_DOC_REVIEW_LLM,
    GPU_DOC_SECTION_LLM,
)
from core.document_creator.context_manager import DocumentContextManager
from core.document_creator.state import (
    ContentFormat,
    DocumentCreatorConfig,
    DocumentCreatorState,
    SectionSpec,
    SectionState,
    SectionStatus,
    SectionVersion,
)
from core.embeddings.retriever import hybrid_retrieve
from core.llm.client import invoke_llm
from core.llm.output_schemas.document_creator_outputs import (
    DocumentOutlineOutput,
    DocumentReviewOutput,
    SectionContentOutput,
    SectionIterationOutput,
)
from core.llm.prompts.document_creator_prompts import (
    build_outline_prompt,
    build_review_prompt,
    build_section_iteration_prompt,
    build_section_prompt,
)


async def generate_outline(
    config: DocumentCreatorConfig,
    user_id: str,
    thread_id: str,
    document_titles: List[str],
    document_contents: str,
) -> DocumentCreatorState:
    """
    Generate a document outline from source materials.

    Uses broad RAG retrieval across all source docs to build context,
    then calls LLM to generate a structured outline.
    """
    doc_gen_id = str(uuid.uuid4())

    # Build broad retrieval query from document titles
    broad_query = f"Key topics and themes from: {', '.join(document_titles)}"

    # Attempt RAG retrieval for additional context
    rag_context = document_contents
    try:
        chunks = await hybrid_retrieve(
            user_id=user_id,
            thread_id=thread_id,
            query=broad_query,
            vector_k=20,
            bm25_k=15,
        )
        if chunks:
            chunk_texts = []
            for c in chunks[:15]:
                text = c.get("page_content", "")
                meta = c.get("metadata", {})
                doc_title = meta.get("document_title", meta.get("file_name", ""))
                chunk_texts.append(f"[{doc_title}]: {text}")
            rag_context = "\n\n".join(chunk_texts)
    except Exception as e:
        print(f"RAG retrieval for outline failed, using document contents: {e}")

    # Build and call LLM
    prompt = build_outline_prompt(
        document_type=config.document_type.value,
        audience=config.audience.value,
        tone=config.tone.value,
        length_preference=config.length_preference,
        rag_context=rag_context,
        document_titles=document_titles,
        custom_instructions=config.custom_instructions,
    )

    response: DocumentOutlineOutput = await invoke_llm(
        gpu_model=GPU_DOC_OUTLINE_LLM.model,
        response_schema=DocumentOutlineOutput,
        contents=prompt,
        port=GPU_DOC_OUTLINE_LLM.port,
    )

    # Convert LLM output to pipeline state
    sections = []
    for i, section_out in enumerate(response.sections):
        content_format = ContentFormat.MIXED
        fmt = section_out.content_format.lower().strip()
        if fmt in [e.value for e in ContentFormat]:
            content_format = ContentFormat(fmt)

        sections.append(
            SectionState(
                spec=SectionSpec(
                    section_id=str(uuid.uuid4()),
                    title=section_out.title,
                    description=section_out.description,
                    content_format=content_format,
                    order=i,
                ),
            )
        )

    state = DocumentCreatorState(
        doc_gen_id=doc_gen_id,
        user_id=user_id,
        thread_id=thread_id,
        config=config,
        phase="outline",
        document_title=response.document_title,
        document_subtitle=response.document_subtitle,
        sections=sections,
    )

    return state


async def generate_sections(
    state: DocumentCreatorState,
    progress_callback=None,
) -> DocumentCreatorState:
    """
    Generate content section-by-section.

    Each section uses per-section RAG retrieval and sliding context
    (compact outline + previous section summary + terminology).
    """
    state.phase = "generating"
    state.touch()

    ctx = DocumentContextManager(state)
    compact_outline = ctx.get_compact_outline()

    for i, section_state in enumerate(state.sections):
        if section_state.status == SectionStatus.APPROVED:
            continue  # Skip already-approved sections

        section_state.status = SectionStatus.GENERATING
        state.touch()

        if progress_callback:
            await progress_callback(
                section_index=i,
                section_title=section_state.spec.title,
                phase="generating",
                total=len(state.sections),
            )

        try:
            # Per-section RAG retrieval
            section_query = (
                f"{section_state.spec.title}: {section_state.spec.description}"
            )
            rag_context = ""
            try:
                chunks = await hybrid_retrieve(
                    user_id=state.user_id,
                    thread_id=state.thread_id,
                    query=section_query,
                    vector_k=15,
                    bm25_k=10,
                )
                if chunks:
                    chunk_texts = []
                    for c in chunks[:8]:
                        text = c.get("page_content", "")
                        meta = c.get("metadata", {})
                        doc_title = meta.get(
                            "document_title", meta.get("file_name", "")
                        )
                        chunk_texts.append(f"[{doc_title}]: {text}")
                    rag_context = "\n\n".join(chunk_texts)
            except Exception as e:
                print(f"RAG retrieval for section '{section_state.spec.title}' failed: {e}")

            # Build section prompt with sliding context
            prompt = build_section_prompt(
                section_title=section_state.spec.title,
                section_description=section_state.spec.description,
                content_format=section_state.spec.content_format.value,
                section_guidance=section_state.spec.guidance,
                rag_context=rag_context,
                compact_outline=compact_outline,
                previous_summary=ctx.get_previous_section_summary(i),
                terminology=ctx.get_terminology_context(),
                style_excerpt=state.style_excerpt,
                audience=state.config.audience.value,
                tone=state.config.tone.value,
            )

            # Call LLM
            response: SectionContentOutput = await invoke_llm(
                gpu_model=GPU_DOC_SECTION_LLM.model,
                response_schema=SectionContentOutput,
                contents=prompt,
                port=GPU_DOC_SECTION_LLM.port,
            )

            # Create version from response
            version = SectionVersion(
                version_id=str(uuid.uuid4()),
                content=response.content,
                bullet_points=response.bullet_points,
                table_data=response.table_data,
                speaker_notes=response.speaker_notes,
                key_takeaway=response.key_takeaway,
            )

            section_state.versions.append(version)
            section_state.selected_version_index = len(section_state.versions) - 1
            section_state.status = SectionStatus.GENERATED

            # Update context for next section
            ctx.update_after_section(i, response.content)

            # Extract terminology from generated content
            new_terms = ctx.extract_terminology_from_content(response.content)
            state.terminology.update(new_terms)

            if progress_callback:
                await progress_callback(
                    section_index=i,
                    section_title=section_state.spec.title,
                    phase="completed",
                    total=len(state.sections),
                )

        except Exception as e:
            print(f"Section generation failed for '{section_state.spec.title}': {e}")
            section_state.status = SectionStatus.FAILED
            if progress_callback:
                await progress_callback(
                    section_index=i,
                    section_title=section_state.spec.title,
                    phase="failed",
                    total=len(state.sections),
                )

    # Check if all sections completed
    all_done = all(
        s.status in (SectionStatus.GENERATED, SectionStatus.APPROVED, SectionStatus.FAILED)
        for s in state.sections
    )
    if all_done:
        state.phase = "ready"

    state.touch()
    return state


async def regenerate_section(
    state: DocumentCreatorState,
    section_id: str,
    feedback: Optional[str] = None,
) -> DocumentCreatorState:
    """
    Regenerate a single section, optionally with user feedback.
    Appends a new version to the section's version history.
    """
    # Find the section
    section_state = None
    for s in state.sections:
        if s.spec.section_id == section_id:
            section_state = s
            break

    if section_state is None:
        raise ValueError(f"Section {section_id} not found")

    section_state.status = SectionStatus.GENERATING
    state.touch()

    # Get current version content for context
    current_content = ""
    current_bullets = None
    if section_state.versions:
        current = section_state.versions[section_state.selected_version_index]
        current_content = current.content
        current_bullets = current.bullet_points

    # Per-section RAG retrieval
    section_query = (
        f"{section_state.spec.title}: {section_state.spec.description}"
    )
    rag_context = ""
    try:
        chunks = await hybrid_retrieve(
            user_id=state.user_id,
            thread_id=state.thread_id,
            query=section_query,
            vector_k=15,
            bm25_k=10,
        )
        if chunks:
            chunk_texts = []
            for c in chunks[:8]:
                text = c.get("page_content", "")
                meta = c.get("metadata", {})
                doc_title = meta.get("document_title", meta.get("file_name", ""))
                chunk_texts.append(f"[{doc_title}]: {text}")
            rag_context = "\n\n".join(chunk_texts)
    except Exception as e:
        print(f"RAG retrieval for iteration failed: {e}")

    if feedback and current_content:
        # Iteration with feedback
        prompt = build_section_iteration_prompt(
            section_title=section_state.spec.title,
            current_content=current_content,
            current_bullets=current_bullets,
            feedback=feedback,
            rag_context=rag_context,
            audience=state.config.audience.value,
            tone=state.config.tone.value,
        )
        response: SectionIterationOutput = await invoke_llm(
            gpu_model=GPU_DOC_ITERATE_LLM.model,
            response_schema=SectionIterationOutput,
            contents=prompt,
            port=GPU_DOC_ITERATE_LLM.port,
        )
    else:
        # Fresh regeneration (no feedback)
        ctx = DocumentContextManager(state)
        section_index = next(
            i for i, s in enumerate(state.sections) if s.spec.section_id == section_id
        )
        prompt = build_section_prompt(
            section_title=section_state.spec.title,
            section_description=section_state.spec.description,
            content_format=section_state.spec.content_format.value,
            section_guidance=section_state.spec.guidance,
            rag_context=rag_context,
            compact_outline=ctx.get_compact_outline(),
            previous_summary=ctx.get_previous_section_summary(section_index),
            terminology=ctx.get_terminology_context(),
            style_excerpt=state.style_excerpt,
            audience=state.config.audience.value,
            tone=state.config.tone.value,
        )
        response: SectionContentOutput = await invoke_llm(
            gpu_model=GPU_DOC_ITERATE_LLM.model,
            response_schema=SectionContentOutput,
            contents=prompt,
            port=GPU_DOC_ITERATE_LLM.port,
        )

    # Create new version
    version = SectionVersion(
        version_id=str(uuid.uuid4()),
        content=response.content,
        bullet_points=response.bullet_points,
        table_data=response.table_data,
        speaker_notes=response.speaker_notes,
        key_takeaway=response.key_takeaway,
        feedback_used=feedback,
    )

    section_state.versions.append(version)
    section_state.selected_version_index = len(section_state.versions) - 1
    section_state.status = SectionStatus.GENERATED
    state.touch()

    return state


async def review_document(state: DocumentCreatorState) -> DocumentCreatorState:
    """
    Quality self-review of the generated document.
    """
    ctx = DocumentContextManager(state)
    outline_summary = ctx.get_compact_outline()

    # Build sections summary for review
    sections_lines = []
    for section in state.sections:
        if section.versions:
            v = section.versions[section.selected_version_index]
            # Truncate content for review
            content_preview = v.content[:500]
            if len(v.content) > 500:
                content_preview += "..."
            sections_lines.append(
                f"## {section.spec.title}\n{content_preview}"
            )
            if v.key_takeaway:
                sections_lines.append(f"Key takeaway: {v.key_takeaway}")
            sections_lines.append("")

    sections_summary = "\n".join(sections_lines)

    prompt = build_review_prompt(
        outline_summary=outline_summary,
        sections_summary=sections_summary,
    )

    response: DocumentReviewOutput = await invoke_llm(
        gpu_model=GPU_DOC_REVIEW_LLM.model,
        response_schema=DocumentReviewOutput,
        contents=prompt,
        port=GPU_DOC_REVIEW_LLM.port,
    )

    state.review_result = {
        "overall_score": response.overall_score,
        "coherence_score": response.coherence_score,
        "completeness_score": response.completeness_score,
        "consistency_score": response.consistency_score,
        "issues": response.issues,
        "approved": response.approved,
    }
    state.phase = "review"
    state.touch()

    return state
