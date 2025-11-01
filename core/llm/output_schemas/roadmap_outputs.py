from pydantic import BaseModel, Field
from typing import List


class VisionAndEndGoal(BaseModel):
    description: str = Field(
        description="Ultimate goal state for a target year (e.g., Year <n>)."
    )
    success_criteria: List[str] = Field(
        description="List of measurable outcomes indicating success."
    )


class SWOT(BaseModel):
    strengths: List[str] = Field(description="List of current strengths.")
    weaknesses: List[str] = Field(description="List of current weaknesses.")
    opportunities: List[str] = Field(description="List of opportunities.")
    threats: List[str] = Field(description="List of threats.")


class CurrentBaseline(BaseModel):
    summary: str = Field(description="Current situation overview.")
    swot: SWOT = Field(description="SWOT analysis for the current baseline.")


class StrategicPillar(BaseModel):
    pillar_name: str = Field(description="Name of the strategic pillar.")
    description: str = Field(description="Core intent or driver of the pillar.")


class PhasedRoadmapItem(BaseModel):
    phase: str = Field(description="Phase label, e.g., 'Phase 1'.")
    time_frame: str = Field(description="Time frame, e.g., 'Year 1'.")
    key_objectives: List[str] = Field(description="List of key objectives.")
    key_initiatives: List[str] = Field(description="List of major actions.")
    expected_outcomes: List[str] = Field(
        description="List of measurable expected results."
    )


class EnablersAndDependencies(BaseModel):
    technologies: List[str] = Field(description="Enabling technologies.")
    skills_and_resources: List[str] = Field(
        description="Key capabilities or assets required."
    )
    stakeholders: List[str] = Field(
        description="Key partners, stakeholders, or ecosystem elements."
    )


class RiskAndMitigation(BaseModel):
    risk: str = Field(description="Identified risk.")
    mitigation_strategy: str = Field(description="Mitigation strategy for the risk.")


class KeyMetricsAndMilestone(BaseModel):
    year_or_phase: str = Field(description="Year or phase indicator.")
    metrics: List[str] = Field(description="List of KPIs or milestones.")


class LLMInferredAddition(BaseModel):
    section_title: str = Field(description="Custom section name added by the model.")
    content: str = Field(description="Model-added insight or recommendation.")


class StrategicRoadmapLLMOutput(BaseModel):
    roadmap_title: str = Field(description="Concise and visionary roadmap title.")
    vision_and_end_goal: VisionAndEndGoal = Field(
        description="Vision description and success criteria for the end goal."
    )
    current_baseline: CurrentBaseline = Field(
        description="Current baseline overview and SWOT analysis."
    )
    strategic_pillars: List[StrategicPillar] = Field(
        description="List of strategic pillars."
    )
    phased_roadmap: List[PhasedRoadmapItem] = Field(
        description="Phased roadmap with objectives, initiatives, and outcomes."
    )
    enablers_and_dependencies: EnablersAndDependencies = Field(
        description="Enabling technologies, skills/resources, and stakeholders."
    )
    risks_and_mitigation: List[RiskAndMitigation] = Field(
        description="List of risks and corresponding mitigation strategies."
    )
    key_metrics_and_milestones: List[KeyMetricsAndMilestone] = Field(
        description="Key metrics and milestones by year or phase."
    )
    future_opportunities: List[str] = Field(
        description="Opportunities or emerging trends beyond the roadmap horizon."
    )
    llm_inferred_additions: List[LLMInferredAddition] = Field(
        description="Model-inferred additional sections with insights."
    )
