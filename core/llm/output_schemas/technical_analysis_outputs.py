from pydantic import BaseModel, Field
from typing import List, Optional

from core.llm.output_schemas.base import LLMOutputBase


class TechnicalScope(BaseModel):
    domains_covered: List[str] = Field(
        description="Technical domains addressed in the document."
    )
    technology_stack: List[str] = Field(
        description="Technologies, frameworks, and tools mentioned."
    )
    architecture_overview: str = Field(
        description="Architecture described or implied in the document."
    )


class TechnicalDecision(BaseModel):
    decision: str = Field(description="A technical decision identified in the document.")
    rationale: str = Field(description="The rationale behind this decision.")
    implications: str = Field(
        description="Implications of this decision going forward."
    )


class TechnicalStrength(BaseModel):
    aspect: str = Field(description="A technical strength identified.")
    evidence: str = Field(description="Supporting evidence from the document.")


class TechnicalConcern(BaseModel):
    concern: str = Field(
        description="Technical debt, concern, or limitation identified."
    )
    impact: str = Field(description="Potential impact of this concern.")
    evidence: str = Field(description="Evidence from the document.")


class TechnicalInnovation(BaseModel):
    element: str = Field(description="Innovation element identified.")
    description: str = Field(description="How it is described in the document.")
    maturity: str = Field(
        description="Maturity level: experimental, prototype, or production."
    )


class TechnicalAspirations(BaseModel):
    stated_goals: List[str] = Field(
        description="Explicit technical goals stated in the document."
    )
    implied_direction: str = Field(
        description="Implied technical direction not explicitly stated."
    )
    alignment_assessment: str = Field(
        description="How well stated goals align with the current technical state."
    )


class ImplementationReadiness(BaseModel):
    ready_components: List[str] = Field(
        description="Components or systems ready for implementation."
    )
    gaps_to_address: List[str] = Field(
        description="Technical gaps that need to be addressed."
    )
    dependencies: List[str] = Field(
        description="Key dependencies for implementation."
    )


class TechnicalForwardAssessment(BaseModel):
    scalability_outlook: str = Field(
        description="Assessment of scalability based on the document content."
    )
    technology_evolution: str = Field(
        description="How the technology approach might evolve."
    )
    recommended_focus_areas: List[str] = Field(
        description="Recommended technical focus areas."
    )
    overall_assessment: str = Field(
        description="Overall analytical commentary on the document's technical content."
    )


class LLMInferredAddition(BaseModel):
    section_title: str = Field(description="Custom section name added by the model.")
    content: str = Field(description="Model-added insight or recommendation.")


class TechnicalAnalysisLLMOutput(LLMOutputBase):
    analysis_title: str = Field(
        description="Concise, professional title summarizing the technical analysis."
    )
    executive_overview: str = Field(
        description="Brief overview of the document's technical content and purpose."
    )
    technical_scope: TechnicalScope = Field(
        description="Technical domains, technology stack, and architecture overview."
    )
    technical_decisions: List[TechnicalDecision] = Field(
        description="Key technical decisions identified with rationale and implications."
    )
    technical_strengths: List[TechnicalStrength] = Field(
        description="Technical strengths with supporting evidence."
    )
    technical_concerns: List[TechnicalConcern] = Field(
        description="Technical concerns, debt, or limitations with impact assessment."
    )
    innovation_elements: List[TechnicalInnovation] = Field(
        description="Innovation elements with maturity assessment."
    )
    technical_aspirations: TechnicalAspirations = Field(
        description="Technical goals, implied direction, and alignment assessment."
    )
    implementation_readiness: ImplementationReadiness = Field(
        description="Readiness assessment: ready components, gaps, and dependencies."
    )
    forward_looking_assessment: TechnicalForwardAssessment = Field(
        description="Analyst's forward-looking commentary: scalability, evolution, and recommendations."
    )
    llm_inferred_additions: Optional[List[LLMInferredAddition]] = Field(
        default=None,
        description="Optional model-inferred additional sections with insights.",
    )
