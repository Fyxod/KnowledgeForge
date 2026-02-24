from typing import List, Optional

from pydantic import BaseModel, Field

from core.llm.output_schemas.base import LLMOutputBase


class StrategicIntent(BaseModel):
    vision_statement: str = Field(
        description="The vision or aspiration described or implied in the document."
    )
    stated_objectives: List[str] = Field(
        description="Explicit strategic objectives mentioned in the document."
    )
    implicit_aspirations: List[str] = Field(
        description="Aspirations implied but not explicitly stated in the document."
    )


class StrategicPositioning(BaseModel):
    current_position: str = Field(
        description="Where the organization or project currently stands based on the document."
    )
    target_position: str = Field(
        description="Where the organization or project aims to be."
    )
    competitive_landscape: str = Field(
        description="Competitive context or market positioning mentioned or implied."
    )


class StrategicTheme(BaseModel):
    theme: str = Field(description="Name of the strategic theme identified.")
    description: str = Field(description="What this theme covers and its significance.")
    evidence_from_document: str = Field(
        description="Supporting evidence or quotes from the document."
    )


class StakeholderInsight(BaseModel):
    stakeholder: str = Field(description="Stakeholder name or group.")
    role_or_interest: str = Field(
        description="Their role, interest, or relationship to the strategy."
    )
    influence_level: str = Field(
        description="Level of influence: high, medium, or low."
    )


class ResourceAndCapability(BaseModel):
    resource: str = Field(description="Resource or capability identified.")
    current_state: str = Field(
        description="Current availability or maturity of this resource."
    )
    strategic_relevance: str = Field(
        description="Why this resource matters strategically."
    )


class IdentifiedRisk(BaseModel):
    risk: str = Field(description="Risk described or implied in the document.")
    severity: str = Field(description="Severity level: high, medium, or low.")
    context: str = Field(description="Context from the document supporting this risk.")


class ForwardLookingAssessment(BaseModel):
    opportunities: List[str] = Field(
        description="Opportunities identified by the analyst based on the document content."
    )
    recommended_next_steps: List[str] = Field(
        description="Recommended strategic next steps."
    )
    potential_challenges: List[str] = Field(
        description="Potential challenges or obstacles foreseen."
    )
    overall_assessment: str = Field(
        description="Overall analytical commentary on the document's strategic content."
    )


class LLMInferredAddition(BaseModel):
    section_title: str = Field(description="Custom section name added by the model.")
    content: str = Field(description="Model-added insight or recommendation.")


class StrategicAnalysisLLMOutput(LLMOutputBase):
    analysis_title: str = Field(
        description="Concise, professional title summarizing the strategic analysis."
    )
    executive_overview: str = Field(
        description="Brief overview of the document's strategic content and purpose."
    )
    strategic_intent: StrategicIntent = Field(
        description="The document creator's strategic intent, vision, and objectives."
    )
    strategic_positioning: StrategicPositioning = Field(
        description="Current and target strategic positioning described in the document."
    )
    key_strategic_themes: List[StrategicTheme] = Field(
        description="Key strategic themes identified in the document with evidence."
    )
    stakeholder_insights: List[StakeholderInsight] = Field(
        description="Stakeholders identified and their roles or interests."
    )
    resources_and_capabilities: List[ResourceAndCapability] = Field(
        description="Resources and capabilities described in the document."
    )
    identified_risks: List[IdentifiedRisk] = Field(
        description="Risks described or implied in the document."
    )
    strategic_gaps_and_observations: List[str] = Field(
        description="Gaps, inconsistencies, or notable observations in the strategic content."
    )
    forward_looking_assessment: ForwardLookingAssessment = Field(
        description="Analyst's forward-looking commentary: opportunities, recommendations, and challenges."
    )
    llm_inferred_additions: Optional[List[LLMInferredAddition]] = Field(
        default=None,
        description="Optional model-inferred additional sections with insights.",
    )
