from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ChunksUsed(BaseModel):
    document_id: str = Field(
        description="The ID of the document used to which the chunk belongs."
    )
    # title: str = Field(description="The title of the document used.")
    page_no: int = Field(description="The page_no of the document used.")


class MainLLMOutputInternal(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal[
        "answer",
        "document_summarizer",  # requires document id of the document to summarize
        "global_summarizer",
        "failure",
    ] = Field(description="The action to take based on the answer.")
    chunks_used: Optional[List[ChunksUsed]] = Field(
        default=None,
        description="List of chunks used to generate the answer, if applicable.",
    )
    document_id: Optional[str] = Field(
        description="The ID of the document to summarize if using document_summarizer, if applicable."
    )


class MainLLMOutputExternal(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal[
        "answer",
        "web_search",
        "document_summarizer",  # requires document id of the document to summarize
        "global_summarizer",
        "failure",
    ] = Field(description="The action to take based on the answer.")
    chunks_used: Optional[List[ChunksUsed]] = Field(
        default=None,
        description="List of chunks used to generate the answer, if applicable.",
    )
    web_search_queries: Optional[List[str]] = Field(
        default=None,
        description="List of 2-3 web search queries used to generate the answer, if applicable.",
    )
    document_id: Optional[str] = Field(
        description="The ID of the document to summarize if using document_summarizer, if applicable."
    )


class SelfKnowledgeLLMOutput(BaseModel):
    answer: str = Field(description="The answer to the user's question.")


class DecompositionLLMOutput(BaseModel):
    requires_decomposition: bool = Field(
        description="Indicates whether the query requires decomposition."
    )
    resolved_query: str = Field(
        description="The resolved query after context resolution."
    )
    sub_queries: List[str] = Field(
        description="List of standalone sub-queries generated from the original query."
    )


class CombinationLLMOutput(BaseModel):
    answer: str = Field(description="The combined answer from multiple sub-answers.")


class SummarizerLLMOutputSingle(BaseModel):
    summary: str = Field(description="The summary of the document.")


class SummarizerLLMOutputCombination(BaseModel):
    summary: str = Field(description="The summary of the document.")


class SummarizerLLMOutput(BaseModel):
    summaries: List[SummarizerLLMOutputSingle] = Field(
        description="List of summaries for each document."
    )


class GlobalSummarizerLLMOutput(BaseModel):
    title: str = Field(
        description="A concise and descriptive title for the collection of documents."
    )
    summary: str = Field(
        description="The global summary of all provided document summaries."
    )


class Node(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    children: List["Node"] = []

    class Config:
        arbitrary_types_allowed = True


class FlatNode(BaseModel):
    id: str
    title: str
    parent_id: Optional[str] = None


class MindMapOutput(BaseModel):
    mind_map: List[FlatNode] = Field(description="The generated mind map structure.")


class FlatNodeWithDescription(BaseModel):
    id: str
    title: str
    description: str


class FlatNodeWithDescriptionOutput(BaseModel):
    mind_map: List[FlatNodeWithDescription]


class MindMap(BaseModel):
    user_id: str
    thread_id: str
    document_id: str
    roots: List[Node]


class GlobalMindMap(BaseModel):
    user_id: str
    thread_id: str
    roots: List[Node]


# =============================
# Strategic Roadmap Structures
# =============================


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


# =============================
# Insights Structures
# =============================


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
    pseudocode_or_technical_outline: Optional[List[PseudocodeOrTechnicalOutline]] = Field(
        description="Algorithmic or procedural outlines tied to sections."
    )
    llm_inferred_additions: Optional[List[LLMInferredAddition]] = Field(
        description="Model-inferred relevant sections and additional insights."
    )

