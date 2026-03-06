import asyncio
import json
import os
import uuid

import aiofiles
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette import status

from core.document_creator.assemblers.docx_assembler import DocxAssembler
from core.document_creator.assemblers.pdf_assembler import PdfAssembler
from core.document_creator.assemblers.pptx_assembler import PptxAssembler
from core.document_creator.pipeline import (
    generate_outline,
    generate_sections,
    regenerate_section,
    review_document,
)
from core.document_creator.state import (
    ContentFormat,
    DocumentCreatorConfig,
    DocumentCreatorState,
    SectionSpec,
    SectionState,
    SectionStatus,
)
from core.models.document import Document
from core.utils.generation_status import (
    read_generation_status,
    write_failed_status,
    write_pending_status,
    write_result,
)

router = APIRouter(tags=["Document Creator"])


# ─── Request Models ──────────────────────────────────────────────────────


class OutlineRequest(BaseModel):
    thread_id: str
    document_type: str = "technical_report"
    audience: str = "general"
    tone: str = "professional"
    source_document_ids: list[str] | None = None
    custom_instructions: str | None = None
    length_preference: str = "medium"


class OutlineUpdateRequest(BaseModel):
    document_title: str | None = None
    document_subtitle: str | None = None
    sections: list[dict] = Field(description="List of section specs")


class IterateSectionRequest(BaseModel):
    feedback: str | None = None


class SelectVersionRequest(BaseModel):
    version_index: int


class EditSectionRequest(BaseModel):
    content: str | None = None
    bullet_points: list[str] | None = None
    key_takeaway: str | None = None
    speaker_notes: str | None = None


class ExportRequest(BaseModel):
    format: str = Field(description="pptx, docx, or pdf")


# ─── Helpers ─────────────────────────────────────────────────────────────


def _get_state_dir(user_id: str, thread_id: str) -> str:
    return f"data/{user_id}/threads/{thread_id}/document_creator"


def _get_state_path(user_id: str, thread_id: str, doc_gen_id: str) -> str:
    return os.path.join(
        _get_state_dir(user_id, thread_id), f"state_{doc_gen_id}.json"
    )


async def _save_state(state: DocumentCreatorState) -> None:
    """Persist pipeline state to JSON file."""
    path = _get_state_path(state.user_id, state.thread_id, state.doc_gen_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(state.model_dump_json(indent=2))


async def _load_state(user_id: str, thread_id: str, doc_gen_id: str) -> DocumentCreatorState:
    """Load pipeline state from JSON file."""
    path = _get_state_path(user_id, thread_id, doc_gen_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Document generation not found")
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()
    return DocumentCreatorState.model_validate_json(content)


def _load_thread_documents(user_id: str, thread_id: str, source_ids: list[str] | None = None) -> list[Document]:
    """Load parsed documents from the thread's parsed directory."""
    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    documents = []
    if not os.path.exists(parsed_dir):
        return documents

    for filename in os.listdir(parsed_dir):
        if not filename.endswith(".json"):
            continue
        file_path = os.path.join(parsed_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if source_ids and data.get("id") not in source_ids:
            continue
        try:
            documents.append(Document.model_validate(data))
        except Exception:
            continue

    return documents


# ─── List & Delete Saved Documents ────────────────────────────────────────


@router.get("/document-creator/list/{thread_id}")
async def list_documents(request: Request, thread_id: str):
    """List all saved document creator instances for a thread."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    state_dir = _get_state_dir(user_id, thread_id)

    if not os.path.exists(state_dir):
        return JSONResponse(content={"documents": []})

    documents = []
    for filename in os.listdir(state_dir):
        if not filename.startswith("state_") or not filename.endswith(".json"):
            continue
        file_path = os.path.join(state_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            documents.append({
                "doc_gen_id": data.get("doc_gen_id", ""),
                "document_title": data.get("document_title") or "Untitled Document",
                "phase": data.get("phase", "initialized"),
                "document_type": data.get("config", {}).get("document_type", "technical_report"),
                "section_count": len(data.get("sections", [])),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
            })
        except Exception:
            continue

    # Sort by updated_at descending
    documents.sort(key=lambda d: d.get("updated_at", ""), reverse=True)

    return JSONResponse(content={"documents": documents})


@router.delete("/document-creator/{doc_gen_id}")
async def delete_document(request: Request, doc_gen_id: str):
    """Delete a saved document creator instance and its exports."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob
    import shutil

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    state_dir = os.path.dirname(state_path)

    # Delete the state file
    os.remove(state_path)

    # Delete any outline status files for this doc
    for f in glob.glob(os.path.join(state_dir, f"outline_status_*.json")):
        try:
            os.remove(f)
        except Exception:
            pass

    # Delete export files if they exist
    exports_dir = os.path.join(state_dir, "exports")
    if os.path.exists(exports_dir):
        # Only delete exports associated with this doc_gen_id
        # Since exports are named by title, we just leave exports dir intact
        pass

    return JSONResponse(content={"status": "deleted", "doc_gen_id": doc_gen_id})


# ─── Phase 1: Generate Outline ───────────────────────────────────────────


@router.post("/document-creator/outline")
async def create_outline(request: Request, body: OutlineRequest = Body(...)):
    """Generate a document outline from source documents."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    thread_id = body.thread_id

    # Load source documents
    documents = _load_thread_documents(
        user_id, thread_id, body.source_document_ids
    )
    if not documents:
        raise HTTPException(status_code=404, detail="No documents found in thread")

    # Prepare document content for outline generation
    document_titles = [doc.title for doc in documents]
    document_contents = "\n\n".join(
        f"Title: {doc.title}\n{doc.full_text[:3000]}" for doc in documents
    )

    # Build config
    config = DocumentCreatorConfig(
        document_type=body.document_type,
        audience=body.audience,
        tone=body.tone,
        source_document_ids=body.source_document_ids,
        custom_instructions=body.custom_instructions,
        length_preference=body.length_preference,
    )

    # Use status file pattern for background generation
    state_dir = _get_state_dir(user_id, thread_id)
    os.makedirs(state_dir, exist_ok=True)

    # Generate a temporary ID for status tracking
    temp_id = str(uuid.uuid4())
    status_path = os.path.join(state_dir, f"outline_status_{temp_id}.json")
    await write_pending_status(status_path)

    async def _generate():
        try:
            state = await generate_outline(
                config=config,
                user_id=user_id,
                thread_id=thread_id,
                document_titles=document_titles,
                document_contents=document_contents,
            )
            await _save_state(state)
            # Write the outline result with doc_gen_id reference
            result = {
                "doc_gen_id": state.doc_gen_id,
                "document_title": state.document_title,
                "document_subtitle": state.document_subtitle,
                "sections": [
                    {
                        "section_id": s.spec.section_id,
                        "title": s.spec.title,
                        "description": s.spec.description,
                        "content_format": s.spec.content_format.value,
                        "order": s.spec.order,
                    }
                    for s in state.sections
                ],
            }
            await write_result(status_path, result)
        except Exception as e:
            await write_failed_status(status_path, str(e))
            print(f"Outline generation failed: {e}")

    asyncio.create_task(_generate())

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": False,
            "message": "Generating document outline...",
            "tracking_id": temp_id,
        },
    )


@router.get("/document-creator/outline-status/{tracking_id}")
async def get_outline_status(request: Request, tracking_id: str):
    """Poll for outline generation status."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    # Search for the status file across threads (tracking_id is unique)
    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/outline_status_{tracking_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Tracking ID not found")

    status_path = matches[0]
    gen_status = await read_generation_status(status_path)

    if gen_status is None:
        raise HTTPException(status_code=404, detail="Status file not found")

    if gen_status["state"] == "pending":
        return JSONResponse(
            content={"status": False, "message": "Generating document outline..."}
        )
    elif gen_status["state"] == "failed":
        return JSONResponse(
            content={"status": False, "failed": True, "error": gen_status["error"]}
        )
    elif gen_status["state"] == "completed":
        return JSONResponse(
            content={"status": True, "outline": gen_status["data"]}
        )


# ─── Phase 1b: Update Outline (User Edits) ───────────────────────────────


@router.put("/document-creator/outline/{doc_gen_id}")
async def update_outline(
    request: Request, doc_gen_id: str, body: OutlineUpdateRequest = Body(...)
):
    """Save user's edited outline."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    # Find the state file
    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    # Update title/subtitle
    if body.document_title is not None:
        state.document_title = body.document_title
    if body.document_subtitle is not None:
        state.document_subtitle = body.document_subtitle

    # Update sections from user edits
    new_sections = []
    for i, sec_data in enumerate(body.sections):
        content_format = ContentFormat.MIXED
        fmt = sec_data.get("content_format", "mixed").lower()
        if fmt in [e.value for e in ContentFormat]:
            content_format = ContentFormat(fmt)

        new_sections.append(
            SectionState(
                spec=SectionSpec(
                    section_id=sec_data.get("section_id", str(uuid.uuid4())),
                    title=sec_data["title"],
                    description=sec_data.get("description", ""),
                    content_format=content_format,
                    guidance=sec_data.get("guidance"),
                    order=i,
                ),
            )
        )

    state.sections = new_sections
    state.phase = "outline_approved"
    state.touch()
    await _save_state(state)

    return JSONResponse(
        content={
            "doc_gen_id": doc_gen_id,
            "status": "outline_approved",
            "section_count": len(state.sections),
        }
    )


# ─── Phase 2: Generate Sections ──────────────────────────────────────────


@router.post("/document-creator/generate/{doc_gen_id}")
async def start_generation(request: Request, doc_gen_id: str):
    """Start section-by-section content generation."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    # Socket.IO progress callback
    from app.socket_handler import sio

    async def progress_callback(section_index, section_title, phase, total):
        await sio.emit(
            f"{user_id}/{state.thread_id}/doc_creator/progress",
            {
                "doc_gen_id": doc_gen_id,
                "section_index": section_index,
                "section_title": section_title,
                "phase": phase,
                "total": total,
            },
        )

    async def _generate():
        try:
            updated_state = await generate_sections(
                state=state, progress_callback=progress_callback
            )
            await _save_state(updated_state)
        except Exception as e:
            state.phase = "failed"
            state.touch()
            await _save_state(state)
            print(f"Section generation failed: {e}")

    asyncio.create_task(_generate())

    return JSONResponse(
        content={
            "doc_gen_id": doc_gen_id,
            "status": "generating",
            "total_sections": len(state.sections),
        }
    )


# ─── Phase 2b: Get Generation Status ─────────────────────────────────────


@router.get("/document-creator/status/{doc_gen_id}")
async def get_status(request: Request, doc_gen_id: str):
    """Poll for section generation status."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    sections_status = []
    completed = 0
    for s in state.sections:
        sections_status.append({
            "section_id": s.spec.section_id,
            "title": s.spec.title,
            "status": s.status.value,
        })
        if s.status in (SectionStatus.GENERATED, SectionStatus.APPROVED):
            completed += 1

    return JSONResponse(
        content={
            "doc_gen_id": doc_gen_id,
            "phase": state.phase,
            "sections": sections_status,
            "completed_count": completed,
            "total_count": len(state.sections),
        }
    )


# ─── Phase 3: Get Full Document Preview ──────────────────────────────────


@router.get("/document-creator/preview/{doc_gen_id}")
async def get_preview(request: Request, doc_gen_id: str):
    """Get the full document state for preview rendering."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    # Serialize full section state so frontend gets spec/versions/status
    sections_data = [s.model_dump(mode="json") for s in state.sections]

    return JSONResponse(
        content={
            "doc_gen_id": doc_gen_id,
            "document_title": state.document_title,
            "document_subtitle": state.document_subtitle,
            "phase": state.phase,
            "config": {
                "document_type": state.config.document_type.value,
                "audience": state.config.audience.value,
                "tone": state.config.tone.value,
            },
            "sections": sections_data,
            "review_result": state.review_result,
        }
    )


# ─── Iteration: Regenerate a Section ─────────────────────────────────────


@router.post("/document-creator/iterate/{doc_gen_id}/{section_id}")
async def iterate_section(
    request: Request,
    doc_gen_id: str,
    section_id: str,
    body: IterateSectionRequest = Body(...),
):
    """Regenerate a specific section, optionally with user feedback."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    try:
        state = await regenerate_section(
            state=state,
            section_id=section_id,
            feedback=body.feedback,
        )
        await _save_state(state)

        # Find updated section
        section = next(
            s for s in state.sections if s.spec.section_id == section_id
        )
        return JSONResponse(
            content={
                "section_id": section_id,
                "version_count": len(section.versions),
                "selected_version_index": section.selected_version_index,
                "status": section.status.value,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Section iteration failed: {e}")


# ─── Iteration: Select Section Version ───────────────────────────────────


@router.post("/document-creator/select-version/{doc_gen_id}/{section_id}")
async def select_version(
    request: Request,
    doc_gen_id: str,
    section_id: str,
    body: SelectVersionRequest = Body(...),
):
    """Select a specific version for a section."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    section = next(
        (s for s in state.sections if s.spec.section_id == section_id), None
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    if body.version_index < 0 or body.version_index >= len(section.versions):
        raise HTTPException(status_code=422, detail="Invalid version index")

    section.selected_version_index = body.version_index
    state.touch()
    await _save_state(state)

    return JSONResponse(
        content={"section_id": section_id, "selected_version_index": body.version_index}
    )


# ─── Iteration: Approve Section ──────────────────────────────────────────


@router.post("/document-creator/approve/{doc_gen_id}/{section_id}")
async def approve_section(request: Request, doc_gen_id: str, section_id: str):
    """Mark a section as approved."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    section = next(
        (s for s in state.sections if s.spec.section_id == section_id), None
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    section.status = SectionStatus.APPROVED
    state.touch()
    await _save_state(state)

    return JSONResponse(
        content={"section_id": section_id, "status": "approved"}
    )


# ─── Iteration: Edit Section Content ──────────────────────────────────────


@router.put("/document-creator/edit-section/{doc_gen_id}/{section_id}")
async def edit_section(
    request: Request,
    doc_gen_id: str,
    section_id: str,
    body: EditSectionRequest = Body(...),
):
    """Directly edit the content of the currently selected version."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    section = next(
        (s for s in state.sections if s.spec.section_id == section_id), None
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    if not section.versions:
        raise HTTPException(status_code=422, detail="Section has no generated content to edit")

    version = section.versions[section.selected_version_index]

    if body.content is not None:
        version.content = body.content
    if body.bullet_points is not None:
        version.bullet_points = body.bullet_points
    if body.key_takeaway is not None:
        version.key_takeaway = body.key_takeaway
    if body.speaker_notes is not None:
        version.speaker_notes = body.speaker_notes

    state.touch()
    await _save_state(state)

    return JSONResponse(
        content={"section_id": section_id, "status": "updated"}
    )


# ─── Export: Generate Document File ───────────────────────────────────────


@router.post("/document-creator/export/{doc_gen_id}")
async def export_document(
    request: Request, doc_gen_id: str, body: ExportRequest = Body(...)
):
    """Assemble and export the document in the requested format."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/state_{doc_gen_id}.json"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="Document generation not found")

    state_path = matches[0]
    async with aiofiles.open(state_path, "r", encoding="utf-8") as f:
        content = await f.read()
    state = DocumentCreatorState.model_validate_json(content)

    fmt = body.format.lower()
    if fmt not in ("pptx", "docx", "pdf"):
        raise HTTPException(status_code=422, detail="Format must be pptx, docx, or pdf")

    # Prepare export directory
    export_dir = os.path.join(
        _get_state_dir(state.user_id, state.thread_id), "exports"
    )
    os.makedirs(export_dir, exist_ok=True)

    # Sanitize title for filename
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_"
        for c in (state.document_title or "document")
    ).strip()[:50]
    filename = f"{safe_title}.{fmt}"
    output_path = os.path.join(export_dir, filename)

    # Select assembler
    assembler_map = {
        "pptx": PptxAssembler(),
        "docx": DocxAssembler(),
        "pdf": PdfAssembler(),
    }
    assembler = assembler_map[fmt]

    try:
        await assembler.assemble(
            title=state.document_title or "Untitled Document",
            subtitle=state.document_subtitle,
            sections=state.sections,
            config=state.config,
            output_path=output_path,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Export failed: {e}"
        )

    state.phase = "exported"
    state.touch()
    await _save_state(state)

    return JSONResponse(
        content={
            "doc_gen_id": doc_gen_id,
            "format": fmt,
            "filename": filename,
            "download_url": f"/document-creator/download/{doc_gen_id}/{filename}",
        }
    )


# ─── Export: Download Generated File ──────────────────────────────────────


@router.get("/document-creator/download/{doc_gen_id}/{filename}")
async def download_file(request: Request, doc_gen_id: str, filename: str):
    """Serve the generated document file for download."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId

    import glob

    pattern = f"data/{user_id}/threads/*/document_creator/exports/{filename}"
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = matches[0]

    # Determine media type
    media_types = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
    }
    ext = os.path.splitext(filename)[1].lower()
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
    )
