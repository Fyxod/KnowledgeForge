"""
Final report generation via LLM.
Takes classified articles and produces the complete TechSensingReport.

Uses a two-phase approach to stay within output token limits:
  Phase 1 (Skeleton): executive_summary, key_trends, radar_items, market_signals,
                       report_sections, recommendations, notable_articles
  Phase 2 (Details):  radar_item_details for every radar item

The two phases are merged into the final TechSensingReport.
"""

import json
import logging
import time
from typing import List

from core.constants import GPU_SENSING_REPORT_LLM
from core.llm.client import invoke_llm
from core.llm.output_schemas.sensing_outputs import (
    ClassifiedArticle,
    RadarDetailsOutput,
    TechSensingReport,
    TechSensingReportSkeleton,
)
from core.llm.prompts.sensing_prompts import (
    sensing_details_prompt,
    sensing_report_prompt,
)

logger = logging.getLogger("sensing.report")


async def generate_report(
    classified_articles: List[ClassifiedArticle],
    domain: str = "Generative AI",
    date_range: str = "",
    custom_requirements: str = "",
    org_context: str = "",
    article_content_map: dict[str, str] | None = None,
) -> TechSensingReport:
    """
    Generate the complete Tech Sensing Report from classified articles.

    Two-phase generation:
      Phase 1 — Skeleton (everything except radar_item_details)
      Phase 2 — Radar item details (detailed write-up for each radar item)
    """
    # Truncate to top 50 by relevance if too many (avoid context overflow)
    sorted_articles = sorted(
        classified_articles, key=lambda a: a.relevance_score, reverse=True
    )[:50]

    logger.info(
        f"Generating report from {len(sorted_articles)} articles "
        f"(domain={domain}, range={date_range})"
    )

    # Merge content excerpts from extracted articles for grounding
    article_dicts = []
    for a in sorted_articles:
        d = a.model_dump()
        if article_content_map and a.url in article_content_map:
            d["content_excerpt"] = article_content_map[a.url]
        article_dicts.append(d)

    articles_json = json.dumps(
        article_dicts,
        indent=2,
        ensure_ascii=False,
    )
    logger.info(f"Articles JSON payload size: {len(articles_json)} chars")

    # ── Phase 1: Skeleton ──────────────────────────────────────────────
    skeleton_prompt = sensing_report_prompt(
        classified_articles_json=articles_json,
        domain=domain,
        date_range=date_range,
        custom_requirements=custom_requirements,
        org_context=org_context,
    )

    phase1_start = time.time()
    logger.info("[Phase 1/2] Generating report skeleton...")

    skeleton_result = await invoke_llm(
        gpu_model=GPU_SENSING_REPORT_LLM.model,
        response_schema=TechSensingReportSkeleton,
        contents=skeleton_prompt,
        port=GPU_SENSING_REPORT_LLM.port,
    )

    skeleton = TechSensingReportSkeleton.model_validate(skeleton_result)
    phase1_time = time.time() - phase1_start

    logger.info(
        f"[Phase 1/2] Skeleton generated in {phase1_time:.1f}s — "
        f"trends={len(skeleton.key_trends)}, radar_items={len(skeleton.radar_items)}, "
        f"signals={len(skeleton.market_signals)}, sections={len(skeleton.report_sections)}"
    )

    # ── Phase 2: Radar item details ────────────────────────────────────
    radar_items_json = json.dumps(
        [
            {"name": item.name, "quadrant": item.quadrant, "ring": item.ring}
            for item in skeleton.radar_items
        ],
        indent=2,
        ensure_ascii=False,
    )

    details_prompt = sensing_details_prompt(
        radar_items_json=radar_items_json,
        classified_articles_json=articles_json,
        domain=domain,
    )

    phase2_start = time.time()
    logger.info(
        f"[Phase 2/2] Generating details for {len(skeleton.radar_items)} radar items..."
    )

    details_result = await invoke_llm(
        gpu_model=GPU_SENSING_REPORT_LLM.model,
        response_schema=RadarDetailsOutput,
        contents=details_prompt,
        port=GPU_SENSING_REPORT_LLM.port,
    )

    details = RadarDetailsOutput.model_validate(details_result)
    phase2_time = time.time() - phase2_start

    logger.info(
        f"[Phase 2/2] Details generated in {phase2_time:.1f}s — "
        f"{len(details.radar_item_details)} detail entries"
    )

    # ── Merge into final report ────────────────────────────────────────
    report = TechSensingReport(
        report_title=skeleton.report_title,
        executive_summary=skeleton.executive_summary,
        domain=skeleton.domain,
        date_range=skeleton.date_range,
        total_articles_analyzed=skeleton.total_articles_analyzed,
        key_trends=skeleton.key_trends,
        report_sections=skeleton.report_sections,
        radar_items=skeleton.radar_items,
        radar_item_details=details.radar_item_details,
        market_signals=skeleton.market_signals,
        recommendations=skeleton.recommendations,
        notable_articles=skeleton.notable_articles,
    )

    total_time = phase1_time + phase2_time
    logger.info(
        f"Report complete in {total_time:.1f}s (phase1={phase1_time:.1f}s, phase2={phase2_time:.1f}s) — "
        f"trends={len(report.key_trends)}, radar_items={len(report.radar_items)}, "
        f"details={len(report.radar_item_details)}, recommendations={len(report.recommendations)}"
    )

    return report
