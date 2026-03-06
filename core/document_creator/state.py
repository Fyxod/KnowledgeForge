from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
    description: str = Field(description="1-2 sentence description of intended content")
    content_format: ContentFormat = ContentFormat.MIXED
    heading_level: int = Field(default=1, description="Heading level: 1, 2, or 3")
    guidance: Optional[str] = Field(
        default=None, description="User-provided per-section guidance"
    )
    source_document_ids: List[str] = Field(default_factory=list)
    order: int = 0


class SectionVersion(BaseModel):
    """A single generated version of a section."""

    version_id: str
    content: str = Field(description="Main text content")
    bullet_points: Optional[List[str]] = None
    table_data: Optional[Dict] = Field(
        default=None,
        description="Table data as {headers: [str], rows: [[str]]}",
    )
    speaker_notes: Optional[str] = None
    key_takeaway: Optional[str] = None
    sources_used: List[Dict] = Field(default_factory=list)
    feedback_used: Optional[str] = Field(
        default=None, description="Feedback that produced this version"
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SectionState(BaseModel):
    """Full state of a section including version history."""

    spec: SectionSpec
    status: SectionStatus = SectionStatus.PENDING
    versions: List[SectionVersion] = Field(default_factory=list)
    selected_version_index: int = 0


class DocumentCreatorConfig(BaseModel):
    """User-provided configuration for document generation."""

    document_type: DocumentType = DocumentType.TECHNICAL_REPORT
    audience: Audience = Audience.GENERAL
    tone: Tone = Tone.PROFESSIONAL
    source_document_ids: Optional[List[str]] = Field(
        default=None, description="None = all docs in thread"
    )
    custom_instructions: Optional[str] = None
    length_preference: str = Field(
        default="medium", description="short, medium, or detailed"
    )


class DocumentCreatorState(BaseModel):
    """Full pipeline state — persisted to JSON file."""

    doc_gen_id: str
    user_id: str
    thread_id: str
    config: DocumentCreatorConfig

    # Pipeline phase tracking
    phase: str = Field(
        default="initialized",
        description="initialized, outline, outline_approved, generating, review, ready, exported",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Outline
    document_title: Optional[str] = None
    document_subtitle: Optional[str] = None
    sections: List[SectionState] = Field(default_factory=list)

    # Global context maintained across section generation
    terminology: Dict[str, str] = Field(
        default_factory=dict, description="term → definition"
    )
    narrative_summary: Optional[str] = Field(
        default=None, description="Rolling summary of generated content"
    )
    style_excerpt: Optional[str] = Field(
        default=None, description="Excerpt from first section for style matching"
    )

    # Review
    review_result: Optional[Dict] = None

    def touch(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()
