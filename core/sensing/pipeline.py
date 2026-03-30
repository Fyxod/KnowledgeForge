"""
Tech Sensing Pipeline — orchestrates Ingest -> Dedup -> Extract -> Classify -> Report -> Verify -> Movement.

Main entry point called by the route handler.
"""

import asyncio
import logging
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
from core.sensing.movement import detect_radar_movements
from core.sensing.report_generator import generate_report
from core.sensing.signal_score import compute_signal_strengths
from core.sensing.sources.arxiv_search import fetch_arxiv_papers
from core.sensing.sources.github_trending import fetch_github_trending
from core.sensing.sources.hackernews import fetch_hackernews
from core.sensing.verifier import verify_report

logger = logging.getLogger("sensing.pipeline")


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
    must_include: Optional[List[str]] = None,
    dont_include: Optional[List[str]] = None,
    lookback_days: int = LOOKBACK_DAYS,
    progress_callback: Optional[Callable] = None,
    user_id: Optional[str] = None,
) -> SensingPipelineResult:
    """
    Full tech sensing pipeline execution.

    Args:
        domain: Target domain (e.g., "Generative AI", "Robotics", "Quantum Computing").
        custom_requirements: User-provided additional guidance.
        feed_urls: Override default RSS feeds.
        search_queries: Override default search queries.
        must_include: Keywords that articles should contain (boosts relevance).
        dont_include: Keywords to filter out from results.
        lookback_days: Number of days to look back for articles.
        progress_callback: Async callable(stage, progress_pct, detail_msg).
    """
    start = time.time()

    def _elapsed():
        return f"{time.time() - start:.1f}s"

    async def _emit(stage: str, pct: int, msg: str = ""):
        if progress_callback:
            await progress_callback(stage, pct, msg)

    logger.info(
        f"========== SENSING PIPELINE START (domain={domain}, "
        f"lookback={lookback_days}d, must_include={must_include}, "
        f"dont_include={dont_include}) =========="
    )

    # Build keyword filter instructions for prompts
    keyword_instructions = _build_keyword_instructions(
        domain, must_include, dont_include
    )
    full_requirements = custom_requirements
    if keyword_instructions:
        full_requirements = (
            f"{custom_requirements}\n\n{keyword_instructions}"
            if custom_requirements
            else keyword_instructions
        )

    # --- Stage 1: Ingest ---
    logger.info(f"[Stage 1/7] INGEST — starting RSS feeds... [{_elapsed()}]")
    await _emit("ingest", 10, "Fetching RSS feeds...")
    rss_articles = await fetch_rss_feeds(
        feed_urls, lookback_days=lookback_days, domain=domain
    )
    logger.info(
        f"[Stage 1/7] RSS done: {len(rss_articles)} articles [{_elapsed()}]"
    )

    await _emit("ingest", 18, "Searching DuckDuckGo...")
    logger.info(f"[Stage 1/7] INGEST — starting DuckDuckGo... [{_elapsed()}]")
    ddg_articles = await search_duckduckgo(
        search_queries, domain,
        lookback_days=lookback_days,
        must_include=must_include,
    )
    logger.info(
        f"[Stage 1/7] DDG done: {len(ddg_articles)} articles [{_elapsed()}]"
    )

    # GitHub trending repos
    await _emit("ingest", 19, "Searching GitHub trending...")
    logger.info(f"[Stage 1/7] INGEST — starting GitHub... [{_elapsed()}]")
    github_articles = await fetch_github_trending(domain, lookback_days=lookback_days)
    logger.info(f"[Stage 1/7] GitHub done: {len(github_articles)} repos [{_elapsed()}]")

    # arXiv papers
    await _emit("ingest", 20, "Searching arXiv...")
    logger.info(f"[Stage 1/7] INGEST — starting arXiv... [{_elapsed()}]")
    arxiv_articles = await fetch_arxiv_papers(
        domain, lookback_days=lookback_days, must_include=must_include,
    )
    logger.info(f"[Stage 1/7] arXiv done: {len(arxiv_articles)} papers [{_elapsed()}]")

    # Hacker News
    await _emit("ingest", 21, "Searching Hacker News...")
    logger.info(f"[Stage 1/7] INGEST — starting HN... [{_elapsed()}]")
    hn_articles = await fetch_hackernews(domain, lookback_days=lookback_days)
    logger.info(f"[Stage 1/7] HN done: {len(hn_articles)} stories [{_elapsed()}]")

    all_raw = rss_articles + ddg_articles + github_articles + arxiv_articles + hn_articles
    await _emit("ingest", 22, f"Found {len(all_raw)} raw articles from 5 sources")
    logger.info(
        f"[Stage 1/7] INGEST COMPLETE: {len(all_raw)} total raw articles "
        f"(RSS={len(rss_articles)}, DDG={len(ddg_articles)}, "
        f"GitHub={len(github_articles)}, arXiv={len(arxiv_articles)}, HN={len(hn_articles)}) [{_elapsed()}]"
    )

    # --- Stage 2: Dedup ---
    logger.info(f"[Stage 2/7] DEDUP — starting... [{_elapsed()}]")
    await _emit("dedup", 25, "Deduplicating...")
    unique_articles = deduplicate_articles(all_raw)

    # Apply dont_include keyword filter
    if dont_include:
        before_filter = len(unique_articles)
        dont_lower = [kw.lower() for kw in dont_include]
        unique_articles = [
            a for a in unique_articles
            if not _matches_exclusion(a, dont_lower)
        ]
        filtered_out = before_filter - len(unique_articles)
        logger.info(
            f"[Stage 2/7] Keyword filter removed {filtered_out} articles "
            f"(dont_include={dont_include})"
        )

    await _emit("dedup", 30, f"{len(unique_articles)} unique articles")
    logger.info(
        f"[Stage 2/7] DEDUP COMPLETE: {len(all_raw)} -> {len(unique_articles)} unique [{_elapsed()}]"
    )

    # --- Stage 3: Extract full text (parallel, throttled) ---
    logger.info(
        f"[Stage 3/7] EXTRACT — extracting full text for {len(unique_articles)} articles... [{_elapsed()}]"
    )
    await _emit("extract", 35, "Extracting article text...")
    sem = asyncio.Semaphore(5)  # Max 5 concurrent HTTP fetches

    async def _extract_with_sem(article: RawArticle) -> RawArticle:
        async with sem:
            return await extract_full_text(article)

    enriched = await asyncio.gather(
        *[_extract_with_sem(a) for a in unique_articles]
    )

    content_count = sum(1 for a in enriched if a.content and len(a.content) > 50)
    await _emit("extract", 45, "Text extraction complete")
    logger.info(
        f"[Stage 3/7] EXTRACT COMPLETE: {content_count}/{len(enriched)} with substantial content [{_elapsed()}]"
    )

    # --- Stage 4: Classify ---
    logger.info(
        f"[Stage 4/7] CLASSIFY — classifying {len(enriched)} articles via LLM... [{_elapsed()}]"
    )
    await _emit("classify", 50, "Classifying articles with LLM...")
    classified = await classify_articles(
        list(enriched), domain=domain, custom_requirements=full_requirements
    )
    await _emit("classify", 65, f"{len(classified)} articles classified")
    logger.info(
        f"[Stage 4/7] CLASSIFY COMPLETE: {len(classified)} classified articles [{_elapsed()}]"
    )

    # --- Stage 5: Generate report ---
    logger.info(f"[Stage 5/7] REPORT — generating final report via LLM... [{_elapsed()}]")
    await _emit("report", 70, "Generating report with LLM...")
    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(days=lookback_days)
    date_range = f"{lookback_start.strftime('%b %d')} - {now.strftime('%b %d, %Y')}"

    # Load org context for personalized recommendations
    org_context_str = ""
    if user_id:
        try:
            from core.sensing.org_context import build_org_context_prompt, load_org_context
            org_ctx = await load_org_context(user_id)
            if org_ctx:
                org_context_str = build_org_context_prompt(org_ctx)
                logger.info(f"[Stage 5/7] Org context loaded for {user_id}")
        except Exception as e:
            logger.warning(f"Failed to load org context: {e}")

    report = await generate_report(
        classified_articles=classified,
        domain=domain,
        date_range=date_range,
        custom_requirements=full_requirements,
        org_context=org_context_str,
    )
    await _emit("report", 85, "Report generated, verifying relevance...")
    logger.info(
        f"[Stage 5/7] REPORT COMPLETE [{_elapsed()}]"
    )

    # --- Stage 6: Verify relevance ---
    logger.info(
        f"[Stage 6/7] VERIFY — checking report relevance against '{domain}'... [{_elapsed()}]"
    )
    await _emit("verify", 88, "Verifying report relevance...")
    report = await verify_report(
        report=report,
        domain=domain,
        must_include=must_include,
        dont_include=dont_include,
    )
    await _emit("verify", 92, "Verification complete")
    logger.info(f"[Stage 6/7] VERIFY COMPLETE [{_elapsed()}]")

    # --- Stage 7: Movement detection ---
    if user_id:
        logger.info(
            f"[Stage 7/7] MOVEMENT — detecting radar movements... [{_elapsed()}]"
        )
        await _emit("movement", 95, "Detecting technology movements...")
        report = await detect_radar_movements(
            new_report=report,
            user_id=user_id,
            domain=domain,
        )
        logger.info(f"[Stage 7/7] MOVEMENT COMPLETE [{_elapsed()}]")
    else:
        logger.info("[Stage 7/7] MOVEMENT — skipped (no user_id)")

    # Signal strength scoring
    logger.info(f"Computing signal strengths... [{_elapsed()}]")
    await _emit("scoring", 98, "Computing signal strengths...")
    report = compute_signal_strengths(report, classified)

    await _emit("complete", 100, "Report ready")

    elapsed = time.time() - start
    logger.info(
        f"========== SENSING PIPELINE COMPLETE in {elapsed:.1f}s =========="
    )
    logger.info(
        f"  Raw={len(all_raw)} | Deduped={len(unique_articles)} | "
        f"Classified={len(classified)} | Trends={len(report.key_trends)} | "
        f"Radar items={len(report.radar_items)}"
    )

    return SensingPipelineResult(
        report=report,
        raw_article_count=len(all_raw),
        deduped_article_count=len(unique_articles),
        classified_article_count=len(classified),
        execution_time_seconds=round(elapsed, 2),
    )


def _matches_exclusion(article: RawArticle, dont_lower: list[str]) -> bool:
    """Check if an article matches any exclusion keyword."""
    text = f"{article.title} {article.snippet} {article.content}".lower()
    return any(kw in text for kw in dont_lower)


def _build_keyword_instructions(
    domain: str,
    must_include: list[str] | None,
    dont_include: list[str] | None,
) -> str:
    """Build keyword filter instructions for LLM prompts."""
    parts = []
    if must_include:
        kw_list = ", ".join(must_include)
        parts.append(
            f"MUST INCLUDE: Prioritize articles and technologies related to "
            f"these keywords: {kw_list}. Give higher relevance scores to "
            f"articles mentioning these topics."
        )
    if dont_include:
        kw_list = ", ".join(dont_include)
        parts.append(
            f"DON'T INCLUDE: Exclude or deprioritize articles and technologies "
            f"related to these keywords: {kw_list}. Give low relevance scores "
            f"to articles primarily about these topics."
        )
    return "\n".join(parts)
