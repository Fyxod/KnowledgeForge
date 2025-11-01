from pydantic import BaseModel, Field
from typing import List, Optional


class DocumentSummary(BaseModel):
    title: str = Field(description="Inferred or extracted title of the document(s).")
    purpose: str = Field(description="Main purpose or topic of the document(s).")
    key_themes: List[str] = Field(description="List of key themes or focus areas.")


class KeyDiscussionPoint(BaseModel):
    topic: str = Field(description="Main discussion point.")
    details: str = Field(description="Brief explanation or extracted insight.")


class StrengthItem(BaseModel):
    aspect: str = Field(description="What is strong about the document.")
    evidence_or_example: str = Field(
        description="Supporting detail, evidence, or reasoning."
    )


class ImprovementOrMissingArea(BaseModel):
    gap: str = Field(description="Issue or missing component identified.")
    suggested_improvement: str = Field(
        description="Clear, actionable suggestion to address the gap."
    )


class FutureConsideration(BaseModel):
    focus_area: str = Field(description="Domain or topic for future work.")
    recommendation: str = Field(description="What should be done or explored next.")


class InnovationAspect(BaseModel):
    innovation_title: str = Field(description="Name of idea or innovation.")
    description: str = Field(
        description="Explanation of how it improves or differentiates."
    )
    potential_impact: str = Field(
        description="Estimated qualitative benefit or impact."
    )


class PseudocodeOrTechnicalOutline(BaseModel):
    section: Optional[str] = Field(
        description="Which part of the document or idea the outline refers to."
    )
    pseudocode: Optional[str] = Field(
        description="Algorithmic outline or procedural logic, if applicable."
    )


class LLMInferredAddition(BaseModel):
    section_title: str = Field(description="Custom section name added by the model.")
    content: str = Field(description="Model-added insight or recommendation.")


class InsightsLLMOutput(BaseModel):
    document_summary: DocumentSummary = Field(
        description="Summary of the document(s) including title, purpose, and key themes."
    )
    key_discussion_points: List[KeyDiscussionPoint] = Field(
        description="List of main discussion points with brief details."
    )
    strengths: List[StrengthItem] = Field(
        description="List of strengths with supporting evidence or examples."
    )
    improvement_or_missing_areas: List[ImprovementOrMissingArea] = Field(
        description="List of issues or gaps with actionable improvements."
    )
    future_considerations: List[FutureConsideration] = Field(
        description="Future focus areas and recommendations."
    )
    innovation_aspects: List[InnovationAspect] = Field(
        description="Innovation ideas, descriptions, and potential impacts."
    )
    pseudocode_or_technical_outline: Optional[List[PseudocodeOrTechnicalOutline]] = (
        Field(description="Algorithmic or procedural outlines tied to sections.")
    )
    llm_inferred_additions: Optional[List[LLMInferredAddition]] = Field(
        description="Model-inferred relevant sections and additional insights."
    )
