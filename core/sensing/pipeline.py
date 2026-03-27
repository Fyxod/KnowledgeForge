"""
Tech Sensing Pipeline — orchestrates Ingest -> Dedup -> Extract -> Classify -> Report.

Main entry point called by the route handler.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional

from core.llm.output_schemas.sensing_outputs import TechSensingReport
from core.sensing.classify import classify_articles
from core.sensing.config import DEFAULT_DOMAIN, LOOKBACK_DAYS
from core.sensing.dedup import deduplicate_articles
from core.sensing.ingest import (
    RawArticle,
    extract_full_text,
    fetch_rss_feeds,
    search_duckduckgo,
)
from core.sensing.report_generator import generate_report


@dataclass
class SensingPipelineResult:
    """Result of a complete tech sensing run."""

    report: TechSensingReport
    raw_article_count: int
    deduped_article_count: int
    classified_article_count: int
    execution_time_seconds: float


async def run_sensing_pipeline(
    domain: str = DEFAULT_DOMAIN,
    custom_requirements: str = "",
    feed_urls: Optional[List[str]] = None,
    search_queries: Optional[List[str]] = None,
    progress_callback: Optional[Callable] = None,
) -> SensingPipelineResult:
    """
    Full tech sensing pipeline execution.

    Args:
        domain: Target domain (default: "Generative AI").
        custom_requirements: User-provided additional guidance.
        feed_urls: Override default RSS feeds.
        search_queries: Override default DuckDuckGo queries.
        progress_callback: Async callable(stage, progress_pct, detail_msg).
    """
    start = time.time()

    async def _emit(stage: str, pct: int, msg: str = ""):
        if progress_callback:
            await progress_callback(stage, pct, msg)

    # --- Stage 1: Ingest ---
    await _emit("ingest", 10, "Fetching RSS feeds...")
    rss_articles = await fetch_rss_feeds(feed_urls)
    await _emit("ingest", 20, "Searching DuckDuckGo...")
    ddg_articles = await search_duckduckgo(search_queries, domain)
    all_raw = rss_articles + ddg_articles
    await _emit("ingest", 25, f"Found {len(all_raw)} raw articles")

    # --- Stage 2: Dedup ---
    await _emit("dedup", 30, "Deduplicating...")
    unique_articles = deduplicate_articles(all_raw)
    await _emit("dedup", 35, f"{len(unique_articles)} unique articles")

    # --- Stage 3: Extract full text (parallel, throttled) ---
    await _emit("extract", 40, "Extracting article text...")
    sem = asyncio.Semaphore(5)  # Max 5 concurrent HTTP fetches

    async def _extract_with_sem(article: RawArticle) -> RawArticle:
        async with sem:
            return await extract_full_text(article)

    enriched = await asyncio.gather(
        *[_extract_with_sem(a) for a in unique_articles]
    )
    await _emit("extract", 50, "Text extraction complete")

    # --- Stage 4: Classify ---
    await _emit("classify", 55, "Classifying articles with LLM...")
    classified = await classify_articles(
        list(enriched), domain=domain, custom_requirements=custom_requirements
    )
    await _emit("classify", 75, f"{len(classified)} articles classified")

    # --- Stage 5: Generate report ---
    await _emit("report", 80, "Generating report with LLM...")
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=LOOKBACK_DAYS)
    date_range = f"{week_ago.strftime('%b %d')} - {now.strftime('%b %d, %Y')}"

    report = await generate_report(
        classified_articles=classified,
        domain=domain,
        date_range=date_range,
        custom_requirements=custom_requirements,
    )
    await _emit("complete", 100, "Report ready")

    elapsed = time.time() - start

    return SensingPipelineResult(
        report=report,
        raw_article_count=len(all_raw),
        deduped_article_count=len(unique_articles),
        classified_article_count=len(classified),
        execution_time_seconds=round(elapsed, 2),
    )
