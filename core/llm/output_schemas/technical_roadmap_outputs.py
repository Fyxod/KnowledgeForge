from pydantic import BaseModel, Field
from typing import List, Optional


class OverallVision(BaseModel):
    goal: str = Field(
        description="What the technology aims to achieve in the long term"
    )
    success_metrics: List[str] = Field(
        description="List of measurable outcomes or KPIs"
    )


class CurrentStateAnalysis(BaseModel):
    summary: str = Field(
        description="Snapshot of current technology maturity or landscape"
    )
    key_challenges: List[str] = Field(description="Major pain points or blockers")
    existing_capabilities: List[str] = Field(
        description="Technologies, frameworks, or tools in use"
    )


class TechnologyDomain(BaseModel):
    domain_name: str = Field(
        description="Domain name, e.g., AI Infrastructure, Data Pipeline"
    )
    description: str = Field(description="Purpose and scope of this domain")


class Initiative(BaseModel):
    initiative: str = Field(description="Specific project or milestone")
    objective: str = Field(description="What the initiative aims to achieve")
    expected_outcome: str = Field(description="Measurable or visible result")


class PhasedRoadmapPhase(BaseModel):
    time_frame: str = Field(description="Time frame, e.g., '0-2 years' or '2-5 years'")
    focus_areas: List[str] = Field(description="List of focus areas for this phase")
    key_initiatives: List[Initiative] = Field(
        description="Key initiatives in this phase"
    )
    dependencies: List[str] = Field(
        description="Technologies, skills, or integrations required"
    )


class PhasedRoadmap(BaseModel):
    short_term: PhasedRoadmapPhase = Field(description="Short-term phase details")
    mid_term: PhasedRoadmapPhase = Field(description="Mid-term phase details")
    long_term: PhasedRoadmapPhase = Field(description="Long-term phase details")


class KeyTechnologyEnabler(BaseModel):
    enabler: str = Field(
        description="Technology, platform, or process that enables the roadmap"
    )
    impact: str = Field(description="Why this enabler is critical")


class RiskAndMitigation(BaseModel):
    risk: str = Field(description="Technical or operational risk")
    mitigation: str = Field(description="Mitigation or fallback plan")


class InnovationOpportunity(BaseModel):
    idea: str = Field(description="Novel or disruptive innovation idea")
    description: str = Field(
        description="Brief explanation of its relevance or potential"
    )
    maturity_level: str = Field(
        description="Maturity level: experimental / prototype / scalable"
    )


class TabularSummaryRow(BaseModel):
    time_frame: str = Field(description="Time frame description")
    key_points: List[str] = Field(description="3-5 main takeaways or deliverables")


class TabularSummary(BaseModel):
    short_term: TabularSummaryRow = Field(description="Short-term phase summary")
    mid_term: TabularSummaryRow = Field(description="Mid-term phase summary")
    long_term: TabularSummaryRow = Field(description="Long-term phase summary")


class LLMInferredAddition(BaseModel):
    section_title: str = Field(
        description="Model-inferred relevant addition, e.g., Ethical AI"
    )
    content: str = Field(description="Summarized insight or recommendation")


class TechnicalRoadmapLLMOutput(BaseModel):
    roadmap_title: str = Field(
        description="Concise, professional title summarizing the technology direction"
    )
    overall_vision: OverallVision = Field(
        description="Long-term vision and success metrics"
    )
    current_state_analysis: CurrentStateAnalysis = Field(
        description="Snapshot and gap analysis of the current state"
    )
    technology_domains: List[TechnologyDomain] = Field(
        description="List of technology domains and their scope"
    )
    phased_roadmap: PhasedRoadmap = Field(
        description="Phased roadmap detailing short-term, mid-term, and long-term plans"
    )
    key_technology_enablers: List[KeyTechnologyEnabler] = Field(
        description="Critical enablers for the roadmap"
    )
    risks_and_mitigations: List[RiskAndMitigation] = Field(
        description="List of risks and mitigation strategies"
    )
    innovation_opportunities: List[InnovationOpportunity] = Field(
        description="Potential innovations and their maturity"
    )
    tabular_summary: List[TabularSummaryRow] = Field(
        description="Condensed phase-by-phase summary"
    )
    llm_inferred_additions: Optional[List[LLMInferredAddition]] = Field(
        default=None,
        description="Optional model-inferred additions such as ethical AI or governance",
    )
