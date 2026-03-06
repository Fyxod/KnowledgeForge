# PRISM Document Creator — Technical Specification

## 1. Architecture Overview

### 1.1 System Context

The Document Creator extends PRISM's existing architecture with a new **multi-phase generation pipeline** that sits alongside the existing Q&A agent and Studio Features. It reuses the core infrastructure — `invoke_llm()`, ChromaDB retriever, Pydantic schemas, Socket.IO streaming, and the FastAPI route layer.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             Client (React/Vite)                          │
│  Document Creator UI: Configure → Outline Editor → Preview → Export     │
└────────────────────────┬──────────────────────┬──────────────────────────┘
                         │ REST API              │ Socket.IO
┌────────────────────────▼──────────────────────▼──────────────────────────┐
│                        FastAPI + Socket.IO (ASGI)                        │
│  New Routes: /document-creator/*                                         │
├──────────────────────────────────────────────────────────────────────────┤
│                     Document Creator Pipeline                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Outline  │→│ Section  │→│ Review   │→│ Assemble │→│ Export   │      │
│  │Generator │ │Generator │ │ Engine   │ │ Engine   │ │ Renderer │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│        ↕              ↕                                                  │
│  ┌──────────┐  ┌──────────┐                                             │
│  │ RAG      │  │invoke_llm│  ← Reused from existing core               │
│  │Retriever │  │ + Schemas│                                              │
│  └──────────┘  └──────────┘                                             │
├──────────────────────────────────────────────────────────────────────────┤
│                         Data Layer                                       │
│  MongoDB (Document State) · ChromaDB (RAG) · File System (Outputs)      │
├──────────────────────────────────────────────────────────────────────────┤
│                         LLM Serving                                      │
│  Ollama (Qwen3-14B on A6000 48GB) — Ports 11434/11435                   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **Reuse existing infrastructure** — `invoke_llm()`, ChromaDB retriever, Pydantic output schemas, Socket.IO streaming, generation status utilities, file-based caching
2. **Section-by-section generation** — never attempt whole-document generation in a single LLM call; fits 8K-32K context windows; enables per-section iteration
3. **Sliding context pattern** — each LLM call receives: compact outline + previous section summary + per-section RAG chunks (not the full document)
4. **Template-based assembly** — LLM generates structured content (JSON); Python code renders it into document formats using template files
5. **Stateful pipeline** — generation state is persisted to allow interruption, resumption, and iterative refinement

---

## 2. Directory Structure

```
core/
├── document_creator/                    # New module
│   ├── __init__.py
│   ├── pipeline.py                      # Pipeline orchestrator
│   ├── outline_generator.py             # Phase 1: Outline generation
│   ├── section_generator.py             # Phase 2: Section-by-section content
│   ├── review_engine.py                 # Phase 3: Self-review & quality check
│   ├── state.py                         # DocumentCreatorState model
│   ├── context_manager.py              # Sliding context & terminology tracking
│   │
│   ├── assemblers/                      # Format-specific document assembly
│   │   ├── __init__.py
│   │   ├── base.py                      # Abstract assembler interface
│   │   ├── pptx_assembler.py            # python-pptx based PPTX generation
│   │   ├── docx_assembler.py            # python-docx based DOCX generation
│   │   └── pdf_assembler.py             # FPDF2 / WeasyPrint based PDF generation
│   │
│   └── templates/                       # Document template files
│       ├── default_presentation.pptx    # PPTX template with slide layouts
│       ├── default_report.docx          # DOCX template with styles
│       └── pdf/                         # PDF template assets
│           ├── report.html              # Jinja2 HTML template
│           └── styles.css               # PDF stylesheet
│
├── llm/
│   ├── output_schemas/
│   │   └── document_creator.py          # New Pydantic schemas
│   └── prompts/
│       └── document_creator_prompts.py  # New prompt templates
│
app/routes/
│   └── document_creator.py              # New REST API endpoints
│
frontend/src/
│   ├── components/
│   │   ├── DocumentCreatorModal.tsx      # Main modal component
│   │   ├── OutlineEditor.tsx            # Outline editing component
│   │   ├── DocumentPreview.tsx          # HTML preview renderer
│   │   └── SectionToolbar.tsx           # Per-section action controls
│   └── lib/
│       └── document-creator-api.ts      # API client functions
│
data/{user_id}/threads/{thread_id}/
│   └── document_creator/                # Generated document data
│       ├── state_{doc_gen_id}.json       # Pipeline state
│       ├── outline_{doc_gen_id}.json     # Approved outline
│       ├── sections_{doc_gen_id}.json    # Generated sections + version history
│       └── exports/                     # Generated output files
│           ├── output.pptx
│           ├── output.docx
│           └── output.pdf
```

---

## 3. Data Models

### 3.1 Pipeline State

```python
# core/document_creator/state.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    PRESENTATION = "presentation"
    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL_REPORT = "technical_report"
    RESEARCH_BRIEF = "research_brief"
    PROJECT_PROPOSAL = "project_proposal"
    COMPARISON_REPORT = "comparison_report"


class Audience(str, Enum):
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    GENERAL = "general"


class Tone(str, Enum):
    FORMAL = "formal"
    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    ACADEMIC = "academic"


class ContentFormat(str, Enum):
    PROSE = "prose"
    BULLETS = "bullets"
    TABLE = "table"
    MIXED = "mixed"


class SectionStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    FAILED = "failed"


class SectionSpec(BaseModel):
    """A section in the document outline."""
    section_id: str
    title: str
    description: str                          # 1-2 sentence description of intended content
    content_format: ContentFormat             # prose, bullets, table, mixed
    heading_level: int = 1                    # 1, 2, or 3
    guidance: Optional[str] = None            # user-provided per-section guidance
    source_document_ids: List[str] = []       # which source docs are relevant
    order: int = 0                            # position in document


class SectionVersion(BaseModel):
    """A single generated version of a section."""
    version_id: str
    content: str                              # main text content
    bullet_points: Optional[List[str]] = None
    table_data: Optional[Dict] = None         # {headers: [], rows: [[]]}
    speaker_notes: Optional[str] = None       # for PPTX
    key_takeaway: Optional[str] = None
    sources_used: List[Dict] = []             # [{document_id, title, page_no}]
    feedback_used: Optional[str] = None       # feedback that produced this version
    generated_at: str


class SectionState(BaseModel):
    """Full state of a section including version history."""
    spec: SectionSpec
    status: SectionStatus = SectionStatus.PENDING
    versions: List[SectionVersion] = []
    selected_version_index: int = 0           # which version is active


class DocumentCreatorConfig(BaseModel):
    """User-provided configuration for document generation."""
    document_type: DocumentType
    audience: Audience
    tone: Tone
    source_document_ids: Optional[List[str]] = None   # None = all docs in thread
    custom_instructions: Optional[str] = None
    length_preference: str = "medium"                  # short, medium, detailed


class DocumentCreatorState(BaseModel):
    """Full pipeline state — persisted to JSON file."""
    doc_gen_id: str                          # unique generation ID
    user_id: str
    thread_id: str
    config: DocumentCreatorConfig

    # Pipeline phase tracking
    phase: str = "initialized"                # initialized → outline → generating →
                                              # review → ready → exported
    created_at: str
    updated_at: str

    # Outline
    document_title: Optional[str] = None
    document_subtitle: Optional[str] = None
    sections: List[SectionState] = []

    # Global context (maintained across section generation)
    terminology: Dict[str, str] = {}          # {term: definition}
    narrative_summary: Optional[str] = None   # rolling summary of generated content
    style_excerpt: Optional[str] = None       # excerpt from first section for style matching

    # Review
    review_result: Optional[Dict] = None      # quality review output
    review_issues: List[Dict] = []            # flagged issues
```

### 3.2 LLM Output Schemas

```python
# core/llm/output_schemas/document_creator.py

from core.llm.output_schemas.base import LLMOutputBase
from pydantic import Field
from typing import List, Optional, Dict


class OutlineSectionOutput(LLMOutputBase):
    """A single section in the generated outline."""
    title: str = Field(description="Section heading title")
    description: str = Field(description="1-2 sentence description of section content")
    content_format: str = Field(description="One of: prose, bullets, table, mixed")
    key_points: List[str] = Field(description="3-5 key points this section should cover")


class DocumentOutlineOutput(LLMOutputBase):
    """Complete document outline generated by LLM."""
    document_title: str = Field(description="Title of the document")
    document_subtitle: Optional[str] = Field(
        default=None, description="Optional subtitle"
    )
    sections: List[OutlineSectionOutput] = Field(
        description="Ordered list of document sections"
    )
    executive_summary_needed: bool = Field(
        default=True, description="Whether an executive summary section is recommended"
    )


class SectionContentOutput(LLMOutputBase):
    """Generated content for a single section."""
    heading: str = Field(description="Section heading (may be refined from outline)")
    content: str = Field(description="Main section content as formatted text")
    bullet_points: Optional[List[str]] = Field(
        default=None, description="Bullet points if content_format is bullets or mixed"
    )
    table_data: Optional[Dict] = Field(
        default=None,
        description="Table data as {headers: [str], rows: [[str]]} if content_format is table"
    )
    speaker_notes: Optional[str] = Field(
        default=None, description="Speaker notes for presentation slides"
    )
    key_takeaway: Optional[str] = Field(
        default=None, description="One-sentence key takeaway from this section"
    )


class SectionIterationOutput(LLMOutputBase):
    """Regenerated section content based on user feedback."""
    heading: str = Field(description="Section heading")
    content: str = Field(description="Revised section content")
    bullet_points: Optional[List[str]] = Field(default=None)
    table_data: Optional[Dict] = Field(default=None)
    speaker_notes: Optional[str] = Field(default=None)
    key_takeaway: Optional[str] = Field(default=None)
    changes_made: str = Field(
        description="Brief description of what was changed based on feedback"
    )


class DocumentReviewOutput(LLMOutputBase):
    """Quality review of the generated document."""
    overall_score: int = Field(description="Quality score 1-10")
    coherence_score: int = Field(description="Section flow and transitions 1-10")
    completeness_score: int = Field(description="Coverage of outline points 1-10")
    consistency_score: int = Field(description="Terminology and tone consistency 1-10")
    issues: List[Dict] = Field(
        default=[],
        description="List of {section_title, issue_type, description, suggestion}"
    )
    approved: bool = Field(description="Whether the document passes quality review")


class DocumentEnhancementOutput(LLMOutputBase):
    """Enhanced section content after whole-document enhancement."""
    heading: str = Field(description="Section heading")
    content: str = Field(description="Enhanced section content")
    bullet_points: Optional[List[str]] = Field(default=None)
    table_data: Optional[Dict] = Field(default=None)
    speaker_notes: Optional[str] = Field(default=None)
    key_takeaway: Optional[str] = Field(default=None)
```

---

## 4. Pipeline Implementation

### 4.1 Pipeline Orchestrator

```python
# core/document_creator/pipeline.py

class DocumentCreatorPipeline:
    """
    Orchestrates the multi-phase document generation pipeline.

    Phases:
    1. Outline Generation — LLM creates structured outline from RAG context
    2. Outline Approval — User reviews/edits outline (interactive pause)
    3. Section Generation — Section-by-section content generation with per-section RAG
    4. Quality Review — Optional LLM self-review
    5. Assembly — Render to target format (PPTX/DOCX/PDF)
    """

    async def generate_outline(
        self, config: DocumentCreatorConfig,
        user_id: str, thread_id: str
    ) -> DocumentCreatorState:
        """
        Phase 1: Generate document outline.

        1. Retrieve broad context from ChromaDB (top-K across all source docs)
        2. Build outline prompt with document type, audience, tone
        3. Call invoke_llm() with DocumentOutlineOutput schema
        4. Return outline for user review
        """
        ...

    async def generate_sections(
        self, state: DocumentCreatorState
    ) -> DocumentCreatorState:
        """
        Phase 2: Generate content section-by-section.

        For each section in approved outline:
        1. Perform section-specific RAG retrieval
        2. Build section prompt with:
           - Full outline (compact)
           - Previous section summary (sliding context)
           - Section-specific RAG chunks
           - Section spec + user guidance
           - Terminology registry
           - Style excerpt (from first generated section)
        3. Call invoke_llm() with SectionContentOutput schema
        4. Update terminology registry and narrative summary
        5. Emit progress via Socket.IO
        """
        ...

    async def regenerate_section(
        self, state: DocumentCreatorState,
        section_id: str, feedback: Optional[str] = None
    ) -> DocumentCreatorState:
        """
        Regenerate a single section, optionally with user feedback.

        1. Build iteration prompt with feedback context
        2. Call invoke_llm() with SectionIterationOutput schema
        3. Append new version to section's version history
        4. Update selected_version_index
        """
        ...

    async def enhance_document(
        self, state: DocumentCreatorState,
        enhancement_instruction: str
    ) -> DocumentCreatorState:
        """
        Whole-document enhancement: regenerate all non-approved sections
        with an enhancement instruction applied.
        """
        ...

    async def review_document(
        self, state: DocumentCreatorState
    ) -> DocumentCreatorState:
        """
        Phase 3: Quality self-review.

        1. Assemble section summaries
        2. Call invoke_llm() with DocumentReviewOutput schema
        3. Flag issues per section
        4. Optionally auto-fix (1-2 rounds max)
        """
        ...

    async def export_document(
        self, state: DocumentCreatorState,
        output_format: str  # "pptx" | "docx" | "pdf"
    ) -> str:
        """
        Phase 4: Assemble and export.

        1. Select appropriate assembler
        2. Pass sections (selected versions) + template
        3. Generate file
        4. Return file path
        """
        ...
```

### 4.2 Sliding Context Manager

```python
# core/document_creator/context_manager.py

class DocumentContextManager:
    """
    Maintains sliding context across section generation calls.

    Ensures each LLM call receives enough context for coherence
    without exceeding context window limits.

    Budget per section-generation call (~6K-7K tokens):
    - System prompt + instructions:      ~500 tokens
    - Document outline (compact):         ~300-500 tokens
    - Previous section summary:           ~200-300 tokens
    - RAG context for this section:       ~2000-3000 tokens
    - Section spec + user feedback:       ~200-400 tokens
    - Terminology registry:               ~100-200 tokens
    - Style excerpt:                      ~100-200 tokens
    - Output budget:                      ~2000-3000 tokens
    """

    def __init__(self, state: DocumentCreatorState):
        self.state = state
        self.terminology: Dict[str, str] = {}
        self.narrative_summary: str = ""
        self.style_excerpt: Optional[str] = None

    def get_compact_outline(self) -> str:
        """Compact representation of the full outline (~300 tokens)."""
        ...

    def get_previous_section_summary(self, current_index: int) -> str:
        """Summary of the previous section's content (~200 tokens)."""
        ...

    def get_terminology_context(self) -> str:
        """Key terms and definitions extracted so far (~100 tokens)."""
        ...

    async def update_after_section(self, section_index: int, content: str):
        """Update rolling context after generating a section."""
        ...

    async def extract_terminology(self, content: str) -> Dict[str, str]:
        """Extract key terms from generated content (lightweight LLM call)."""
        ...
```

### 4.3 Per-Section RAG Retrieval

```python
# Integration with existing core/embeddings/retriever.py

async def retrieve_for_section(
    section_spec: SectionSpec,
    user_id: str,
    thread_id: str,
    source_document_ids: Optional[List[str]] = None,
    k: int = 8
) -> List[Dict]:
    """
    Retrieve context chunks relevant to a specific document section.

    Uses the existing hybrid retriever (vector + BM25 + RRF + reranking)
    but with a section-specific query constructed from:
    - Section title
    - Section description
    - Section key points (from outline)

    Filters:
    - thread_id match
    - source_document_ids (if specified)

    Returns top-K chunks with source metadata for attribution.
    """
    query = f"{section_spec.title}: {section_spec.description}"

    # Reuse existing retrieval infrastructure
    chunks = await retrieve_hybrid(
        query=query,
        user_id=user_id,
        thread_id=thread_id,
        document_ids=source_document_ids,
        k=k
    )

    return chunks
```

---

## 5. LLM Prompt Architecture

### 5.1 Outline Generation Prompt

```python
# core/llm/prompts/document_creator_prompts.py

def build_outline_prompt(
    config: DocumentCreatorConfig,
    rag_context: str,
    document_titles: List[str],
    existing_insights: Optional[str] = None
) -> list[dict]:
    schema_json = json.dumps(
        DocumentOutlineOutput.model_json_schema(), indent=2
    )

    return [
        {
            "role": "system",
            "parts": (
                "You are an expert document architect. Your task is to create "
                "a structured outline for a document based on provided source materials.\n\n"
                f"DOCUMENT TYPE: {config.document_type.value}\n"
                f"TARGET AUDIENCE: {config.audience.value}\n"
                f"TONE: {config.tone.value}\n"
                f"LENGTH: {config.length_preference}\n\n"
                "Guidelines:\n"
                "- Create sections that logically flow from introduction to conclusion\n"
                "- Each section should have a clear purpose and not overlap with others\n"
                "- Suggest appropriate content formats (prose for narratives, "
                "bullets for key points, tables for comparisons)\n"
                "- Ensure the outline covers the key themes from the source materials\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n\n"
                "OUTPUT RULES:\n"
                "- Output must be valid JSON only, no markdown fencing.\n"
                "- Newlines inside string values must be written as \\n.\n"
                "- Include all required fields.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"SOURCE DOCUMENTS: {', '.join(document_titles)}\n\n"
                f"RELEVANT CONTENT FROM SOURCES:\n{rag_context}\n\n"
                + (f"EXISTING ANALYSIS:\n{existing_insights}\n\n" if existing_insights else "")
                + (f"CUSTOM INSTRUCTIONS: {config.custom_instructions}\n\n"
                   if config.custom_instructions else "")
                + "Create a structured outline for this document."
            ),
        },
    ]
```

### 5.2 Section Generation Prompt

```python
def build_section_prompt(
    section_spec: SectionSpec,
    rag_context: str,
    compact_outline: str,
    previous_summary: str,
    terminology: str,
    style_excerpt: Optional[str],
    config: DocumentCreatorConfig
) -> list[dict]:
    schema_json = json.dumps(
        SectionContentOutput.model_json_schema(), indent=2
    )

    style_guidance = ""
    if style_excerpt:
        style_guidance = (
            f"\nSTYLE REFERENCE (match this writing style):\n"
            f'"""{style_excerpt}"""\n'
        )

    return [
        {
            "role": "system",
            "parts": (
                "You are generating one section of a larger document. "
                "Write content that fits naturally within the document structure.\n\n"
                f"DOCUMENT OUTLINE:\n{compact_outline}\n\n"
                f"PREVIOUS SECTION SUMMARY:\n{previous_summary}\n\n"
                f"KEY TERMINOLOGY:\n{terminology}\n\n"
                f"AUDIENCE: {config.audience.value}\n"
                f"TONE: {config.tone.value}\n"
                + style_guidance +
                "\nGuidelines:\n"
                "- Write content that flows naturally from the previous section\n"
                "- Use consistent terminology as defined above\n"
                "- Ground all claims in the provided source context\n"
                "- Match the specified content format (prose/bullets/table/mixed)\n"
                "- Do NOT include content that belongs in other sections\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"SECTION TO GENERATE:\n"
                f"Title: {section_spec.title}\n"
                f"Description: {section_spec.description}\n"
                f"Content Format: {section_spec.content_format.value}\n"
                + (f"Additional Guidance: {section_spec.guidance}\n"
                   if section_spec.guidance else "")
                + f"\nSOURCE CONTEXT:\n{rag_context}\n\n"
                "Generate the content for this section."
            ),
        },
    ]
```

### 5.3 Section Iteration Prompt

```python
def build_section_iteration_prompt(
    section_spec: SectionSpec,
    current_content: SectionVersion,
    feedback: str,
    rag_context: str,
    config: DocumentCreatorConfig
) -> list[dict]:
    """
    Build prompt for regenerating a section based on user feedback.

    Inspired by worklet-gen's iteration prompt pattern:
    - Include current content as context
    - Include user's feedback as the modification instruction
    - Request the same schema output with changes_made field
    """
    schema_json = json.dumps(
        SectionIterationOutput.model_json_schema(), indent=2
    )

    return [
        {
            "role": "system",
            "parts": (
                "You are revising a section of a document based on user feedback. "
                "Preserve the section's purpose and factual grounding while "
                "applying the requested changes.\n\n"
                f"AUDIENCE: {config.audience.value}\n"
                f"TONE: {config.tone.value}\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"SECTION: {section_spec.title}\n\n"
                f"CURRENT CONTENT:\n{current_content.content}\n\n"
                f"USER FEEDBACK: {feedback}\n\n"
                f"SOURCE CONTEXT:\n{rag_context}\n\n"
                "Revise this section according to the feedback."
            ),
        },
    ]
```

---

## 6. Document Assembly (Format-Specific)

### 6.1 Assembler Interface

```python
# core/document_creator/assemblers/base.py

from abc import ABC, abstractmethod

class BaseDocumentAssembler(ABC):
    """Base class for format-specific document assembly."""

    @abstractmethod
    async def assemble(
        self,
        title: str,
        subtitle: Optional[str],
        sections: List[SectionState],
        config: DocumentCreatorConfig,
        output_path: str
    ) -> str:
        """
        Assemble sections into a document file.
        Returns the file path of the generated document.
        """
        ...
```

### 6.2 PPTX Assembler

```python
# core/document_creator/assemblers/pptx_assembler.py

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

class PptxAssembler(BaseDocumentAssembler):
    """
    Assembles sections into a PowerPoint presentation using python-pptx.

    Uses a .pptx template file with predefined slide layouts:
    - Title Slide (layout index 0)
    - Section Header (layout index 1)
    - Title and Content (layout index 2)
    - Two Content / Comparison (layout index 3)
    - Blank (layout index 4)

    Dependencies: python-pptx >= 0.6.23
    """

    TEMPLATE_PATH = "core/document_creator/templates/default_presentation.pptx"

    # Layout mapping — content_format → slide layout strategy
    LAYOUT_MAP = {
        "prose": "content",          # Title + body text
        "bullets": "content",        # Title + bullet list
        "table": "content",          # Title + table (or two-column)
        "mixed": "content",          # Title + body + bullets
    }

    async def assemble(self, title, subtitle, sections, config, output_path):
        prs = Presentation(self.TEMPLATE_PATH)

        # 1. Title slide
        self._add_title_slide(prs, title, subtitle)

        # 2. Content slides (one per section, potentially split long sections)
        for section_state in sections:
            version = section_state.versions[section_state.selected_version_index]
            self._add_content_slide(prs, section_state.spec, version)

        # 3. Save
        prs.save(output_path)
        return output_path

    def _add_title_slide(self, prs, title, subtitle):
        slide_layout = prs.slide_layouts[0]  # Title Slide layout
        slide = prs.slides.add_slide(slide_layout)
        slide.placeholders[0].text = title
        if subtitle and len(slide.placeholders) > 1:
            slide.placeholders[1].text = subtitle

    def _add_content_slide(self, prs, spec, version):
        slide_layout = prs.slide_layouts[2]  # Title and Content
        slide = prs.slides.add_slide(slide_layout)

        # Title
        slide.placeholders[0].text = spec.title

        # Content body
        tf = slide.placeholders[1].text_frame
        tf.clear()

        if version.bullet_points:
            for i, bullet in enumerate(version.bullet_points):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = bullet
                p.level = 0
                p.font.size = Pt(16)
        elif version.content:
            # Split content into manageable paragraphs
            paragraphs = version.content.split("\n")
            for i, para_text in enumerate(paragraphs):
                if not para_text.strip():
                    continue
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = para_text.strip()
                p.font.size = Pt(14)

        # Speaker notes
        if version.speaker_notes:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = version.speaker_notes
```

### 6.3 DOCX Assembler

```python
# core/document_creator/assemblers/docx_assembler.py

from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

class DocxAssembler(BaseDocumentAssembler):
    """
    Assembles sections into a Word document using python-docx.

    Uses a .docx template file with predefined styles:
    - Title, Subtitle
    - Heading 1, Heading 2, Heading 3
    - Body Text, List Bullet
    - Table styles

    Dependencies: python-docx >= 1.1.0
    """

    TEMPLATE_PATH = "core/document_creator/templates/default_report.docx"

    HEADING_STYLE_MAP = {
        1: "Heading 1",
        2: "Heading 2",
        3: "Heading 3",
    }

    async def assemble(self, title, subtitle, sections, config, output_path):
        doc = Document(self.TEMPLATE_PATH)

        # 1. Title page
        doc.add_paragraph(title, style="Title")
        if subtitle:
            doc.add_paragraph(subtitle, style="Subtitle")
        doc.add_page_break()

        # 2. Table of Contents placeholder
        # (Requires Word to update field codes on open)
        doc.add_paragraph("Table of Contents", style="Heading 1")
        self._add_toc_field(doc)
        doc.add_page_break()

        # 3. Sections
        for section_state in sections:
            version = section_state.versions[section_state.selected_version_index]
            self._add_section(doc, section_state.spec, version)

        # 4. Save
        doc.save(output_path)
        return output_path

    def _add_section(self, doc, spec, version):
        heading_style = self.HEADING_STYLE_MAP.get(spec.heading_level, "Heading 1")
        doc.add_paragraph(version.heading or spec.title, style=heading_style)

        # Key takeaway callout
        if version.key_takeaway:
            p = doc.add_paragraph()
            p.style = doc.styles["Intense Quote"] if "Intense Quote" in [
                s.name for s in doc.styles
            ] else doc.styles["Body Text"]
            p.text = f"Key Takeaway: {version.key_takeaway}"

        # Content
        if version.content:
            for para_text in version.content.split("\n"):
                if para_text.strip():
                    doc.add_paragraph(para_text.strip(), style="Body Text")

        # Bullet points
        if version.bullet_points:
            for bullet in version.bullet_points:
                doc.add_paragraph(bullet, style="List Bullet")

        # Table
        if version.table_data:
            self._add_table(doc, version.table_data)

    def _add_table(self, doc, table_data):
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        if not headers:
            return

        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = "Light Grid Accent 1"

        # Header row
        for i, header in enumerate(headers):
            table.cell(0, i).text = str(header)

        # Data rows
        for row_idx, row_data in enumerate(rows):
            for col_idx, cell_value in enumerate(row_data):
                if col_idx < len(headers):
                    table.cell(row_idx + 1, col_idx).text = str(cell_value)

    def _add_toc_field(self, doc):
        """Add a TOC field code (Word auto-updates on open)."""
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        paragraph = doc.add_paragraph()
        run = paragraph.add_run()
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "begin")
        run._r.append(fldChar)

        run2 = paragraph.add_run()
        instrText = OxmlElement("w:instrText")
        instrText.set(qn("xml:space"), "preserve")
        instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
        run2._r.append(instrText)

        run3 = paragraph.add_run()
        fldChar2 = OxmlElement("w:fldChar")
        fldChar2.set(qn("w:fldCharType"), "end")
        run3._r.append(fldChar2)
```

### 6.4 PDF Assembler

```python
# core/document_creator/assemblers/pdf_assembler.py

class PdfAssembler(BaseDocumentAssembler):
    """
    Assembles sections into a PDF document.

    Strategy: Jinja2 HTML template → WeasyPrint renders to PDF.
    Fallback: FPDF2 for environments without WeasyPrint system dependencies.

    Primary Dependencies: weasyprint >= 62.0, jinja2
    Fallback Dependencies: fpdf2 >= 2.8.0
    """

    TEMPLATE_DIR = "core/document_creator/templates/pdf/"

    async def assemble(self, title, subtitle, sections, config, output_path):
        try:
            return await self._assemble_weasyprint(
                title, subtitle, sections, config, output_path
            )
        except ImportError:
            return await self._assemble_fpdf2(
                title, subtitle, sections, config, output_path
            )

    async def _assemble_weasyprint(self, title, subtitle, sections, config, output_path):
        from weasyprint import HTML
        from jinja2 import Environment, FileSystemLoader

        env = Environment(loader=FileSystemLoader(self.TEMPLATE_DIR))
        template = env.get_template("report.html")

        # Build template context
        section_data = []
        for section_state in sections:
            version = section_state.versions[section_state.selected_version_index]
            section_data.append({
                "title": version.heading or section_state.spec.title,
                "level": section_state.spec.heading_level,
                "content": version.content,
                "bullet_points": version.bullet_points,
                "table_data": version.table_data,
                "key_takeaway": version.key_takeaway,
            })

        html_content = template.render(
            title=title,
            subtitle=subtitle,
            sections=section_data,
            audience=config.audience.value,
            generated_date=datetime.now().strftime("%B %d, %Y"),
        )

        HTML(string=html_content).write_pdf(output_path)
        return output_path

    async def _assemble_fpdf2(self, title, subtitle, sections, config, output_path):
        """Fallback: FPDF2 for simpler PDF generation."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title page
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 24)
        pdf.cell(0, 60, title, new_x="LMARGIN", new_y="NEXT", align="C")
        if subtitle:
            pdf.set_font("Helvetica", "", 14)
            pdf.cell(0, 10, subtitle, new_x="LMARGIN", new_y="NEXT", align="C")

        # Content pages
        for section_state in sections:
            version = section_state.versions[section_state.selected_version_index]
            pdf.add_page()

            # Section heading
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(
                0, 10, version.heading or section_state.spec.title,
                new_x="LMARGIN", new_y="NEXT"
            )
            pdf.ln(4)

            # Content
            if version.content:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, version.content)
                pdf.ln(4)

            # Bullets
            if version.bullet_points:
                pdf.set_font("Helvetica", "", 11)
                for bullet in version.bullet_points:
                    pdf.cell(10)
                    pdf.multi_cell(0, 6, f"• {bullet}")

        pdf.output(output_path)
        return output_path
```

---

## 7. API Endpoints

### 7.1 Route Definitions

```python
# app/routes/document_creator.py

from fastapi import APIRouter, Request, Body, HTTPException
from fastapi.responses import JSONResponse, FileResponse

router = APIRouter(prefix="/document-creator", tags=["Document Creator"])


# ─── Phase 1: Generate Outline ───────────────────────────────────────────

@router.post("/outline")
async def generate_outline(request: Request, body: OutlineRequest = Body(...)):
    """
    Generate a document outline from source documents.

    Request: { thread_id, document_type, audience, tone, length_preference,
               source_document_ids?, custom_instructions? }
    Response: { doc_gen_id, status, outline? }

    Pattern: Same as existing studio features — write pending status,
    schedule background task, return immediately. Frontend polls for result.
    """
    ...


# ─── Phase 1b: Update Outline (User Edits) ───────────────────────────────

@router.put("/outline/{doc_gen_id}")
async def update_outline(
    request: Request, doc_gen_id: str, body: OutlineUpdateRequest = Body(...)
):
    """
    Save user's edited outline (reordered/added/removed sections).

    Request: { sections: [{ title, description, content_format, guidance? }] }
    Response: { doc_gen_id, status: "outline_approved", sections }
    """
    ...


# ─── Phase 2: Generate Sections ──────────────────────────────────────────

@router.post("/generate/{doc_gen_id}")
async def generate_sections(request: Request, doc_gen_id: str):
    """
    Start section-by-section content generation.

    Response: { doc_gen_id, status: "generating", total_sections }

    Progress emitted via Socket.IO:
      {user_id}/{thread_id}/doc_creator/progress
      { section_index, section_title, phase: "generating"|"completed"|"failed" }
    """
    ...


# ─── Phase 2b: Get Generation Status ─────────────────────────────────────

@router.get("/status/{doc_gen_id}")
async def get_status(request: Request, doc_gen_id: str):
    """
    Poll for generation status.

    Response: {
        doc_gen_id, phase,
        sections: [{ section_id, title, status }],
        completed_count, total_count
    }
    """
    ...


# ─── Phase 3: Get Full Document Preview ──────────────────────────────────

@router.get("/preview/{doc_gen_id}")
async def get_preview(request: Request, doc_gen_id: str):
    """
    Get the full document state for preview rendering.

    Response: {
        doc_gen_id, title, subtitle, config,
        sections: [{ spec, status, selected_content, version_count }]
    }
    """
    ...


# ─── Iteration: Regenerate a Section ─────────────────────────────────────

@router.post("/iterate/{doc_gen_id}/{section_id}")
async def iterate_section(
    request: Request, doc_gen_id: str, section_id: str,
    body: IterateSectionRequest = Body(...)
):
    """
    Regenerate a specific section, optionally with user feedback.

    Request: { feedback?: string }
    Response: { section_id, new_version, version_count, selected_index }
    """
    ...


# ─── Iteration: Select Section Version ───────────────────────────────────

@router.post("/select-version/{doc_gen_id}/{section_id}")
async def select_version(
    request: Request, doc_gen_id: str, section_id: str,
    body: SelectVersionRequest = Body(...)
):
    """
    Select a specific version for a section.

    Request: { version_index: int }
    Response: { section_id, selected_index }
    """
    ...


# ─── Iteration: Approve Section ──────────────────────────────────────────

@router.post("/approve/{doc_gen_id}/{section_id}")
async def approve_section(
    request: Request, doc_gen_id: str, section_id: str
):
    """
    Mark a section as approved (locked from enhancement).

    Response: { section_id, status: "approved" }
    """
    ...


# ─── Enhancement: Whole-Document Enhancement ─────────────────────────────

@router.post("/enhance/{doc_gen_id}")
async def enhance_document(
    request: Request, doc_gen_id: str,
    body: EnhanceRequest = Body(...)
):
    """
    Apply an enhancement instruction to all non-approved sections.

    Request: { instruction: string }
    Response: { doc_gen_id, status: "enhancing", sections_affected }
    """
    ...


# ─── Export: Generate Document File ───────────────────────────────────────

@router.post("/export/{doc_gen_id}")
async def export_document(
    request: Request, doc_gen_id: str,
    body: ExportRequest = Body(...)
):
    """
    Assemble and export the document in the requested format.

    Request: { format: "pptx" | "docx" | "pdf" }
    Response: { download_url, format, file_size }
    """
    ...


# ─── Export: Download Generated File ──────────────────────────────────────

@router.get("/download/{doc_gen_id}/{filename}")
async def download_file(request: Request, doc_gen_id: str, filename: str):
    """Serve the generated document file for download."""
    ...
```

### 7.2 Socket.IO Events

| Event | Direction | Payload | Purpose |
|-------|-----------|---------|---------|
| `{user_id}/{thread_id}/doc_creator/progress` | Server → Client | `{ doc_gen_id, section_index, section_title, phase, total }` | Per-section generation progress |
| `{user_id}/{thread_id}/doc_creator/section_complete` | Server → Client | `{ doc_gen_id, section_id, preview_content }` | Section content ready for preview |
| `{user_id}/{thread_id}/doc_creator/error` | Server → Client | `{ doc_gen_id, section_id?, error }` | Generation error |
| `{user_id}/{thread_id}/doc_creator/export_ready` | Server → Client | `{ doc_gen_id, download_url, format }` | Export file ready for download |

---

## 8. GPU & LLM Configuration

### 8.1 New GPU Model Config

```python
# Addition to core/constants.py

GPU_DOC_OUTLINE_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_DOC_SECTION_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT2)
GPU_DOC_REVIEW_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT1)
GPU_DOC_ITERATE_LLM = GPULLMConfig(model=MAIN_MODEL, port=PORT2)
```

**Port distribution strategy**: Outline and review calls go to PORT1 (11434), section generation goes to PORT2 (11435). This allows section generation to not compete with other studio features on PORT1.

### 8.2 VRAM Budget

```
48GB A6000 VRAM Budget:

Qwen3-14B (Q5_K_M quantization):     ~14GB per instance
  × 2 Ollama instances:               ~28GB
  + KV cache (4 concurrent slots):    ~8GB
  + Embedding model (nomic):          ~0.5GB
  + Cross-encoder (reranking):        ~0.1GB
                                      ──────
  Total estimated:                    ~36.6GB
  Headroom:                           ~11.4GB
```

With `OLLAMA_NUM_PARALLEL=4` per instance, the system can handle section generation (PORT2) while other features (Q&A, insights) run on PORT1.

### 8.3 Feature Switch

```python
# Addition to SWITCHES in core/constants.py
SWITCHES["DOCUMENT_CREATOR"] = True
```

---

## 9. Dependencies

### 9.1 New Python Dependencies

```
# Document generation
python-pptx>=0.6.23          # PowerPoint generation
python-docx>=1.1.0           # Word document generation
fpdf2>=2.8.0                 # PDF generation (lightweight, no system deps)

# Optional (for higher-quality PDF)
weasyprint>=62.0             # HTML-to-PDF (requires system libs: pango, cairo)
jinja2>=3.1.0                # HTML templating for PDF (likely already installed via FastAPI)
```

### 9.2 System Dependencies (Optional, for WeasyPrint)

```bash
# Ubuntu/Debian
apt-get install libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0

# Or skip WeasyPrint and use FPDF2 only (no system deps needed)
```

### 9.3 Frontend Dependencies

No new frontend dependencies required. The Document Creator frontend uses:
- Existing shadcn/ui components (Dialog, Button, ScrollArea, Tabs)
- Existing Socket.IO client for progress streaming
- Standard HTML/CSS for document preview rendering

Export to PPTX/DOCX/PDF happens **server-side** (Python assemblers), so no frontend document libraries needed. The frontend only downloads the generated file.

---

## 10. Data Storage

### 10.1 File System Layout

```
data/{user_id}/threads/{thread_id}/document_creator/
├── state_{doc_gen_id}.json           # Full pipeline state (DocumentCreatorState)
├── exports/
│   ├── {doc_gen_id}.pptx             # Generated PPTX (after export)
│   ├── {doc_gen_id}.docx             # Generated DOCX (after export)
│   └── {doc_gen_id}.pdf              # Generated PDF (after export)
```

### 10.2 MongoDB Integration

Document creator metadata is stored in the thread object:

```javascript
// Addition to thread schema
threads[thread_id].document_creator = {
    generations: [{
        doc_gen_id: string,
        document_type: string,
        title: string,
        created_at: date,
        phase: string,                  // current pipeline phase
        section_count: number,
        exports: [{
            format: "pptx" | "docx" | "pdf",
            file_path: string,
            exported_at: date
        }]
    }]
}
```

---

## 11. Error Handling & Resilience

### 11.1 Per-Section Failure Isolation

If a section generation fails (LLM timeout, invalid JSON, etc.):
- Mark that section as `failed`
- Continue generating remaining sections
- Report failed sections in the status response
- User can retry individual failed sections

### 11.2 State Persistence

Pipeline state is saved to disk after each phase transition and after each section completes. This means:
- If the server crashes mid-generation, the pipeline can resume from the last completed section
- The frontend can poll the status endpoint to discover the current state

### 11.3 Stale Generation Detection

Reuse PRISM's existing stale detection pattern from `core/utils/generation_status.py`:
- If a generation has been "pending" for > 8 minutes, mark as failed
- Frontend timeout: 60 polls × 5 seconds = 5 minutes client-side

### 11.4 LLM Retry Strategy

Reuse `invoke_llm()` directly — it already handles:
- 4 retries per provider
- Port failover (11434 → 11435)
- JSON repair and Pydantic validation fallback
- Gemini/OpenAI fallback (disabled by default, respecting the no-external-API constraint)

---

## 12. Testing Strategy

### 12.1 Unit Tests

```
tests/unit/
├── test_document_creator_state.py     # State model validation
├── test_outline_generator.py          # Outline generation with mock LLM
├── test_section_generator.py          # Section generation with mock LLM
├── test_context_manager.py            # Sliding context logic
├── test_pptx_assembler.py             # PPTX assembly
├── test_docx_assembler.py             # DOCX assembly
├── test_pdf_assembler.py              # PDF assembly
```

### 12.2 Integration Tests

```
tests/integration/
├── test_document_creator_pipeline.py  # Full pipeline E2E with mock LLM
├── test_document_creator_api.py       # API endpoint tests
```

### 12.3 Test Fixtures

```python
# In tests/conftest.py

@pytest.fixture
def sample_document_creator_state():
    return DocumentCreatorState(
        doc_gen_id="test-doc-gen-1",
        user_id="test-user",
        thread_id="test-thread",
        config=DocumentCreatorConfig(
            document_type=DocumentType.TECHNICAL_REPORT,
            audience=Audience.TECHNICAL,
            tone=Tone.PROFESSIONAL,
        ),
        phase="generating",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        sections=[...],  # pre-populated test sections
    )

@pytest.fixture
def mock_doc_creator_llm(mock_invoke_llm):
    """Configure mock LLM responses for document creator schemas."""
    mock_invoke_llm.side_effect = lambda *args, **kwargs: ...
```

---

## 13. Implementation Plan

### Phase 1: Core Pipeline (MVP)

**Goal**: User can generate a DOCX report from uploaded documents.

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 1.1 | Define data models (state, config, enums) | `core/document_creator/state.py` | — |
| 1.2 | Define LLM output schemas | `core/llm/output_schemas/document_creator.py` | 1.1 |
| 1.3 | Write outline generation prompt | `core/llm/prompts/document_creator_prompts.py` | 1.2 |
| 1.4 | Write section generation prompt | `core/llm/prompts/document_creator_prompts.py` | 1.2 |
| 1.5 | Implement outline generator | `core/document_creator/outline_generator.py` | 1.3 |
| 1.6 | Implement context manager | `core/document_creator/context_manager.py` | 1.1 |
| 1.7 | Implement section generator | `core/document_creator/section_generator.py` | 1.4, 1.6 |
| 1.8 | Implement pipeline orchestrator | `core/document_creator/pipeline.py` | 1.5, 1.7 |
| 1.9 | Implement DOCX assembler | `core/document_creator/assemblers/docx_assembler.py` | 1.1 |
| 1.10 | Create DOCX template file | `core/document_creator/templates/default_report.docx` | — |
| 1.11 | Add GPU config + feature switch | `core/constants.py` | — |
| 1.12 | Implement API routes (outline, generate, status, export) | `app/routes/document_creator.py` | 1.8, 1.9 |
| 1.13 | Register routes in FastAPI app | `app/main.py` | 1.12 |
| 1.14 | Frontend: Configure modal + outline editor | `frontend/src/components/DocumentCreator*.tsx` | 1.12 |
| 1.15 | Frontend: Progress view + preview + download | `frontend/src/components/DocumentCreator*.tsx` | 1.14 |
| 1.16 | Unit tests for models + assembler | `tests/unit/test_document_creator_*.py` | 1.9 |
| 1.17 | Integration test for pipeline | `tests/integration/test_document_creator_*.py` | 1.12 |

### Phase 2: Multi-Format + Iteration

**Goal**: Add PPTX + PDF export, section-level iteration with feedback.

| Step | Task | Files |
|------|------|-------|
| 2.1 | Implement PPTX assembler | `core/document_creator/assemblers/pptx_assembler.py` |
| 2.2 | Create PPTX template file | `core/document_creator/templates/default_presentation.pptx` |
| 2.3 | Implement PDF assembler (FPDF2 + optional WeasyPrint) | `core/document_creator/assemblers/pdf_assembler.py` |
| 2.4 | Create PDF HTML template | `core/document_creator/templates/pdf/report.html` |
| 2.5 | Write section iteration prompt | `core/llm/prompts/document_creator_prompts.py` |
| 2.6 | Implement `regenerate_section()` in pipeline | `core/document_creator/pipeline.py` |
| 2.7 | Add iteration API routes | `app/routes/document_creator.py` |
| 2.8 | Add version history API route | `app/routes/document_creator.py` |
| 2.9 | Frontend: Section toolbar (approve/regenerate/feedback) | `frontend/src/components/SectionToolbar.tsx` |
| 2.10 | Frontend: Version history selector | `frontend/src/components/DocumentCreator*.tsx` |
| 2.11 | Frontend: Format selection on export | `frontend/src/components/DocumentCreator*.tsx` |
| 2.12 | Tests for PPTX + PDF assemblers | `tests/unit/test_*_assembler.py` |

### Phase 3: Advanced Features

**Goal**: Enhancement mode, quality review, existing feature integration.

| Step | Task | Files |
|------|------|-------|
| 3.1 | Implement self-review engine | `core/document_creator/review_engine.py` |
| 3.2 | Write review prompt | `core/llm/prompts/document_creator_prompts.py` |
| 3.3 | Implement `enhance_document()` | `core/document_creator/pipeline.py` |
| 3.4 | Write enhancement prompt | `core/llm/prompts/document_creator_prompts.py` |
| 3.5 | Add enhancement + review API routes | `app/routes/document_creator.py` |
| 3.6 | Integration with existing Insights/Roadmaps as section inputs | `core/document_creator/section_generator.py` |
| 3.7 | Frontend: Enhancement mode UI | `frontend/src/components/DocumentCreator*.tsx` |
| 3.8 | Frontend: Inline text editing in preview | `frontend/src/components/DocumentPreview.tsx` |
| 3.9 | Full E2E tests | `tests/e2e/test_document_creator_e2e.py` |

---

## 14. Key Integration Points with Existing Code

| Existing Module | Integration |
|----------------|-------------|
| `core/llm/client.py` → `invoke_llm()` | Direct reuse for all LLM calls |
| `core/llm/output_schemas/base.py` → `LLMOutputBase` | All new schemas inherit from this (Unicode sanitization) |
| `core/embeddings/retriever.py` | Reuse hybrid retrieval for per-section RAG |
| `core/utils/generation_status.py` | Reuse `read_generation_status()`, `write_pending_status()`, stale detection |
| `core/constants.py` → `SWITCHES`, `GPULLMConfig` | Add new GPU configs + feature switch |
| `core/utils/token_counter.py` | Token counting for context budget management |
| `core/utils/sanitize.py` | LLM output sanitization |
| `app/socket_handler.py` | Socket.IO server for progress events |
| `core/studio_features/*.py` | Pattern reference for service layer implementation |
| `app/routes/insights.py` | Pattern reference for API route structure |

---

## 15. worklet-gen Integration Mapping

Patterns adopted from [worklet-gen](https://github.com/bugslayer01/worklet-gen), adapted for PRISM's architecture:

| worklet-gen Component | Adaptation for PRISM |
|-----------------------|---------------------|
| `pipeline/state.py` → `AgentState` | `core/document_creator/state.py` → `DocumentCreatorState` (standalone, not extending agent state) |
| `pipeline/builder.py` → Linear LangGraph pipeline | `core/document_creator/pipeline.py` → Python orchestrator (no LangGraph needed — the pipeline is simpler than the Q&A agent) |
| `pipeline/graph_nodes.py` → `generate_worklets()` | `core/document_creator/section_generator.py` → per-section generation with RAG |
| `core/models/worklet.py` → `TransformedWorklet` with `StringAttribute`/`ArrayAttribute` (version history) | `core/document_creator/state.py` → `SectionState` with `versions: List[SectionVersion]` + `selected_version_index` |
| `app/routes/iterate.py` → Field-level iteration endpoint | `app/routes/document_creator.py` → Section-level iteration endpoint |
| `app/routes/worklet_iterations.py` → `enhance` endpoint | `app/routes/document_creator.py` → `enhance` endpoint for whole-document refinement |
| `app/routes/select.py` → Version selection per field | `app/routes/document_creator.py` → Version selection per section |
| `core/llm/prompts/iteration_prompt.py` → Per-field iteration prompt | `core/llm/prompts/document_creator_prompts.py` → Per-section iteration prompt |
| `core/llm/prompts/worklet_enhancement_prompt.py` → Whole-object enhancement | `core/llm/prompts/document_creator_prompts.py` → Whole-document enhancement |
| `app/broadcast.py` → WebSocket status updates | Existing `app/socket_handler.py` → Socket.IO events |

**Key architectural differences from worklet-gen:**
1. **No LangGraph for the pipeline** — Document Creator's pipeline is a simpler linear flow (outline → sections → export) orchestrated by Python async functions, not a state graph. LangGraph is overkill here since there are no conditional routing decisions.
2. **RAG integration** — worklet-gen uses web scraping (Tavily, Selenium); PRISM uses its existing ChromaDB vector store and hybrid retriever.
3. **Server-side document assembly** — worklet-gen appears to use simpler file generation; PRISM uses template-based assembly with python-pptx, python-docx, and WeasyPrint/FPDF2.
4. **No external LLM dependency** — worklet-gen has Gemini/OpenAI fallbacks; PRISM's Document Creator runs exclusively on local Ollama.
