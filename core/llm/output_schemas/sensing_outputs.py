from typing import List, Optional

from pydantic import BaseModel, Field

from core.llm.output_schemas.base import LLMOutputBase


# --- Stage: Classification (per-batch) ---


class ClassifiedArticle(BaseModel):
    title: str = Field(description="Article title.")
    source: str = Field(description="Source name (e.g., 'TechCrunch', 'arXiv').")
    url: str = Field(description="Original article URL.")
    published_date: str = Field(description="Publication date in ISO format.")
    summary: str = Field(description="2-3 sentence summary of the article content.")
    relevance_score: float = Field(
        description="Relevance score 0.0-1.0 to the target domain."
    )
    quadrant: str = Field(
        description="Technology Radar quadrant: 'Techniques', 'Platforms', 'Tools', or 'Languages & Frameworks'."
    )
    ring: str = Field(
        description="Technology Radar ring: 'Adopt', 'Trial', 'Assess', or 'Hold'."
    )
    technology_name: str = Field(
        description="Short name of the technology or technique (for radar blip label)."
    )
    reasoning: str = Field(
        description="Brief reasoning for quadrant and ring placement."
    )


class ArticleBatchClassification(LLMOutputBase):
    articles: List[ClassifiedArticle] = Field(
        description="List of classified articles from the batch."
    )


# --- Stage: Final report ---


class TrendItem(BaseModel):
    trend_name: str = Field(description="Name of the identified trend.")
    description: str = Field(
        description="Description of the trend and its significance."
    )
    evidence: List[str] = Field(
        description="Article titles or sources supporting this trend."
    )
    impact_level: str = Field(
        description="Impact level: 'High', 'Medium', or 'Low'."
    )
    time_horizon: str = Field(
        description="Expected time to mainstream: 'Immediate (0-6mo)', 'Near-term (6-18mo)', 'Medium-term (1-3yr)', 'Long-term (3+yr)'."
    )


class RadarItem(BaseModel):
    name: str = Field(description="Technology or technique name (radar blip label).")
    quadrant: str = Field(
        description="One of: 'Techniques', 'Platforms', 'Tools', 'Languages & Frameworks'."
    )
    ring: str = Field(
        description="One of: 'Adopt', 'Trial', 'Assess', 'Hold'."
    )
    description: str = Field(description="One-sentence description for tooltip.")
    is_new: bool = Field(
        description="Whether this is a new entry (appeared this week)."
    )
    moved_in: Optional[str] = Field(
        default=None,
        description="If moved, the previous ring. None if unchanged.",
    )


class ReportSection(BaseModel):
    section_title: str = Field(description="Section heading.")
    content: str = Field(description="Section body content in markdown format.")


class Recommendation(BaseModel):
    title: str = Field(description="Recommendation title.")
    description: str = Field(description="Actionable recommendation description.")
    priority: str = Field(
        description="Priority: 'Critical', 'High', 'Medium', 'Low'."
    )
    related_trends: List[str] = Field(
        description="Names of trends this recommendation relates to."
    )


class TechSensingReport(LLMOutputBase):
    report_title: str = Field(description="Report title including date range.")
    executive_summary: str = Field(
        description="Executive summary paragraph (150-250 words)."
    )
    domain: str = Field(description="The domain analyzed (e.g., 'Generative AI').")
    date_range: str = Field(
        description="Date range covered (e.g., 'Mar 20-27, 2026')."
    )
    total_articles_analyzed: int = Field(
        description="Total number of articles analyzed."
    )
    key_trends: List[TrendItem] = Field(
        description="List of 5-10 key trends identified."
    )
    report_sections: List[ReportSection] = Field(
        description="3-6 detailed report sections in markdown."
    )
    radar_items: List[RadarItem] = Field(
        description="Technology radar entries (15-30 items)."
    )
    recommendations: List[Recommendation] = Field(
        description="3-7 actionable recommendations."
    )
    notable_articles: List[ClassifiedArticle] = Field(
        description="Top 5-10 most notable articles with full classification."
    )
