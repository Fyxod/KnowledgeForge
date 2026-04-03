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
    topic_category: str = Field(
        default="",
        description="Topic category as defined in the classification prompt.",
    )
    industry_segment: str = Field(
        default="",
        description="Industry segment as defined in the classification prompt.",
    )


class ArticleBatchClassification(LLMOutputBase):
    articles: List[ClassifiedArticle] = Field(
        default_factory=list,
        description="List of classified articles from the batch.",
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
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs of articles supporting this trend.",
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
    signal_strength: float = Field(
        default=0.0,
        description="Composite signal confidence 0.0-1.0.",
    )
    source_count: int = Field(
        default=0,
        description="Number of distinct sources mentioning this technology.",
    )


class RadarItemDetail(BaseModel):
    technology_name: str = Field(
        description="Technology name (must match a RadarItem name)."
    )
    what_it_is: str = Field(
        description="Clear explanation of what this technology is and how it works (2-4 sentences)."
    )
    why_it_matters: str = Field(
        description="Why this technology is significant and what problems it solves (2-3 sentences)."
    )
    current_state: str = Field(
        description="Current maturity, adoption level, and key developments this week (2-3 sentences)."
    )
    key_players: List[str] = Field(
        description=(
            "Companies or organizations that actively develop, maintain, or officially "
            "release this technology. Do NOT include entities that only published the "
            "underlying research paper unless they also released the implementation."
        )
    )
    practical_applications: List[str] = Field(
        description="Real-world use cases and applications (2-4 items)."
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs of articles informing this technology write-up.",
    )


class TrendingVideoItem(BaseModel):
    """A trending YouTube video associated with a radar technology."""

    technology_name: str = Field(
        description="Radar item name this video is associated with."
    )
    title: str = Field(description="Video title.")
    url: str = Field(description="YouTube video URL.")
    description: str = Field(default="", description="Video description excerpt.")
    uploader: str = Field(default="", description="YouTube channel name.")
    duration: str = Field(default="", description="Video duration (e.g., '12:34').")
    published: str = Field(default="", description="Publication date.")
    view_count: int = Field(default=0, description="Number of views.")
    thumbnail_url: str = Field(default="", description="Thumbnail image URL.")


class HeadlineMove(BaseModel):
    """A top headline development of the week, ranked by significance."""

    headline: str = Field(description="1-2 sentence description of the move.")
    actor: str = Field(description="Person or organization that made this move.")
    segment: str = Field(
        description="Industry segment of the actor."
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs of articles reporting this move.",
    )


class MarketSignal(BaseModel):
    company_or_player: str = Field(
        description="Name of the company, major player, or key individual leader."
    )
    signal: str = Field(
        description="What they announced, released, or are doing (2-3 sentences)."
    )
    strategic_intent: str = Field(
        description="Why they are doing this — strategic reasoning (1-2 sentences)."
    )
    industry_impact: str = Field(
        description="How this affects the broader industry direction (1-2 sentences)."
    )
    segment: str = Field(
        default="",
        description="Industry segment of the company or player.",
    )
    related_technologies: List[str] = Field(
        description="Technology names related to this signal."
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs of articles reporting this signal.",
    )


class ReportSection(BaseModel):
    section_title: str = Field(description="Section heading.")
    content: str = Field(description="Section body content in markdown format.")
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs of articles referenced in this section.",
    )


class Recommendation(BaseModel):
    title: str = Field(description="Recommendation title.")
    description: str = Field(description="Actionable recommendation description.")
    priority: str = Field(
        description="Priority: 'Critical', 'High', 'Medium', 'Low'."
    )
    related_trends: List[str] = Field(
        description="Names of trends this recommendation relates to."
    )


class CompetitorEntry(BaseModel):
    name: str = Field(description="Competitor or alternative name.")
    approach: str = Field(description="Their approach or methodology.")
    strengths: str = Field(description="Key strengths.")
    weaknesses: str = Field(description="Key weaknesses.")


class KeyResource(BaseModel):
    title: str = Field(description="Resource title.")
    url: str = Field(default="", description="URL if available.")
    type: str = Field(description="Resource type: 'paper', 'repo', 'article', 'docs'.")


class DeepDiveReport(LLMOutputBase):
    technology_name: str = Field(description="Name of the technology analyzed.")
    comprehensive_analysis: str = Field(
        description="Detailed analysis (500-1000 words) in markdown format."
    )
    technical_architecture: str = Field(
        description="Technical architecture or how it works (200-400 words)."
    )
    competitive_landscape: List[CompetitorEntry] = Field(
        description="3-6 competitors or alternatives with comparison."
    )
    adoption_roadmap: str = Field(
        description="Recommended adoption roadmap for organizations (200-300 words)."
    )
    risk_assessment: str = Field(
        description="Risk assessment and mitigation strategies (150-300 words)."
    )
    key_resources: List[KeyResource] = Field(
        description="5-10 key resources (papers, repos, articles, docs)."
    )
    recommendations: List[str] = Field(
        description="3-5 actionable recommendations."
    )


class ReportCore(LLMOutputBase):
    """Phase 1 output: executive overview, headline moves, and key trends."""

    report_title: str = Field(description="Report title including date range.")
    executive_summary: str = Field(
        description="Executive summary in markdown (200-350 words). Use bold for key terms, bullet points for highlights, and separate paragraphs for readability."
    )
    domain: str = Field(description="The domain analyzed.")
    date_range: str = Field(
        description="Date range covered (e.g., 'Mar 20-27, 2026')."
    )
    total_articles_analyzed: int = Field(
        description="Total number of articles analyzed."
    )
    headline_moves: List[HeadlineMove] = Field(
        description="Top 10 most impactful developments of the week, ranked by significance."
    )
    key_trends: List[TrendItem] = Field(
        description="List of 5-10 key trends identified."
    )


class ReportAnalysis(LLMOutputBase):
    """Phase 2 output: radar, signals, deep-dive sections, recommendations."""

    radar_items: List[RadarItem] = Field(
        description="Technology radar entries (15-30 items)."
    )
    market_signals: List[MarketSignal] = Field(
        description="5-10 market signals from prominent companies/players showing where the industry is heading."
    )
    report_sections: List[ReportSection] = Field(
        description="3-6 detailed report sections in markdown."
    )
    recommendations: List[Recommendation] = Field(
        description="3-7 actionable recommendations."
    )
    notable_articles: List[ClassifiedArticle] = Field(
        description="Top 5-10 most notable articles with full classification."
    )


class RadarDetailsOutput(LLMOutputBase):

    """Phase 3 output: detailed write-ups for each radar item."""

    radar_item_details: List[RadarItemDetail] = Field(
        description="Detailed write-up for each radar item — what it is, why it matters, who is using it, practical applications."
    )


class TechSensingReport(LLMOutputBase):
    """Full report (assembled from Phase 1 core + Phase 2 analysis + Phase 3 details)."""

    report_title: str = Field(description="Report title including date range.")
    executive_summary: str = Field(
        description="Executive summary in markdown (200-350 words). Use bold for key terms, bullet points for highlights, and separate paragraphs for readability."
    )
    domain: str = Field(description="The domain analyzed (e.g., 'Generative AI').")
    date_range: str = Field(
        description="Date range covered (e.g., 'Mar 20-27, 2026')."
    )
    total_articles_analyzed: int = Field(
        description="Total number of articles analyzed."
    )
    headline_moves: List[HeadlineMove] = Field(
        description="Top 10 most impactful developments of the week, ranked by significance."
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
    radar_item_details: List[RadarItemDetail] = Field(
        description="Detailed write-up for each radar item — what it is, why it matters, who is using it, practical applications."
    )
    market_signals: List[MarketSignal] = Field(
        description="5-10 market signals from prominent companies/players showing where the industry is heading."
    )
    recommendations: List[Recommendation] = Field(
        description="3-7 actionable recommendations."
    )
    notable_articles: List[ClassifiedArticle] = Field(
        description="Top 5-10 most notable articles with full classification."
    )
    trending_videos: List[TrendingVideoItem] = Field(
        default_factory=list,
        description="Trending YouTube videos for radar technologies.",
    )
