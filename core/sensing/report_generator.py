"""
Final report generation via LLM.
Takes classified articles and produces the complete TechSensingReport.

Uses a three-phase approach to stay within output token limits:
  Phase 1 (Core):     report_title, executive_summary, headline_moves, key_trends
  Phase 2 (Analysis): radar_items, market_signals, report_sections,
                       recommendations, notable_articles
  Phase 3 (Details):  radar_item_details for every radar item

The three phases are merged into the final TechSensingReport.
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
    ReportAnalysis,
    ReportCore,
    TechSensingReport,
)
from core.llm.prompts.sensing_prompts import (
    sensing_details_prompt,
    sensing_report_analysis_prompt,
    sensing_report_core_prompt,
)
from core.sensing.config import get_preset_for_domain

logger = logging.getLogger("sensing.report")


async def generate_report(
    classified_articles: List[ClassifiedArticle],
    domain: str = "Generative AI",
    date_range: str = "",
    custom_requirements: str = "",
    org_context: str = "",
    article_content_map: dict[str, str] | None = None,
    key_people: list[str] | None = None,
) -> TechSensingReport:
    """
    Generate the complete Tech Sensing Report from classified articles.

    Three-phase generation:
      Phase 1 — Core (executive summary, headline moves, key trends)
      Phase 2 — Analysis (radar, signals, sections, recommendations)
      Phase 3 — Details (detailed write-up for each radar item)
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

    preset = get_preset_for_domain(domain)

    # ── Phase 1: Core (executive summary, headline moves, key trends) ──
    core_prompt = sensing_report_core_prompt(
        classified_articles_json=articles_json,
        domain=domain,
        date_range=date_range,
        custom_requirements=custom_requirements,
        org_context=org_context,
        key_people=key_people,
        industry_segments_text=preset.industry_segments,
    )

    phase1_start = time.time()
    logger.info("[Phase 1/3] Generating report core...")

    core_result = await invoke_llm(
        gpu_model=GPU_SENSING_REPORT_LLM.model,
        response_schema=ReportCore,
        contents=core_prompt,
        port=GPU_SENSING_REPORT_LLM.port,
    )

    core = ReportCore.model_validate(core_result)
    phase1_time = time.time() - phase1_start

    logger.info(
        f"[Phase 1/3] Core generated in {phase1_time:.1f}s — "
        f"headline_moves={len(core.headline_moves)}, trends={len(core.key_trends)}"
    )

    # ── Phase 2: Analysis (radar, signals, sections, recommendations) ──
    # Pass Phase 1 headline moves + key trends as grounding context
    core_context = {
        "headline_moves": [
            {"headline": m.headline, "actor": m.actor, "segment": m.segment}
            for m in core.headline_moves
        ],
        "key_trends": [
            {"trend_name": t.trend_name, "description": t.description}
            for t in core.key_trends
        ],
    }
    core_context_json = json.dumps(core_context, indent=2, ensure_ascii=False)

    analysis_prompt = sensing_report_analysis_prompt(
        classified_articles_json=articles_json,
        core_context_json=core_context_json,
        domain=domain,
        date_range=date_range,
        custom_requirements=custom_requirements,
        key_people=key_people,
        industry_segments_text=preset.industry_segments,
    )

    phase2_start = time.time()
    logger.info("[Phase 2/3] Generating report analysis...")

    analysis_result = await invoke_llm(
        gpu_model=GPU_SENSING_REPORT_LLM.model,
        response_schema=ReportAnalysis,
        contents=analysis_prompt,
        port=GPU_SENSING_REPORT_LLM.port,
    )

    analysis = ReportAnalysis.model_validate(analysis_result)
    phase2_time = time.time() - phase2_start

    logger.info(
        f"[Phase 2/3] Analysis generated in {phase2_time:.1f}s — "
        f"radar_items={len(analysis.radar_items)}, signals={len(analysis.market_signals)}, "
        f"sections={len(analysis.report_sections)}"
    )

    # ── Phase 3: Radar item details (batched to avoid output truncation) ─
    DETAILS_BATCH_SIZE = 5
    all_radar_items = list(analysis.radar_items)
    batches = [
        all_radar_items[i : i + DETAILS_BATCH_SIZE]
        for i in range(0, len(all_radar_items), DETAILS_BATCH_SIZE)
    ]

    phase3_start = time.time()
    logger.info(
        f"[Phase 3/3] Generating details for {len(all_radar_items)} radar items "
        f"in {len(batches)} batch(es) of ≤{DETAILS_BATCH_SIZE}..."
    )

    all_details = []
    for batch_idx, batch in enumerate(batches, 1):
        batch_json = json.dumps(
            [
                {"name": item.name, "quadrant": item.quadrant, "ring": item.ring}
                for item in batch
            ],
            indent=2,
            ensure_ascii=False,
        )

        batch_prompt = sensing_details_prompt(
            radar_items_json=batch_json,
            classified_articles_json=articles_json,
            domain=domain,
        )

        logger.info(
            f"[Phase 3/3] Batch {batch_idx}/{len(batches)}: "
            f"{', '.join(item.name for item in batch)}"
        )

        batch_result = await invoke_llm(
            gpu_model=GPU_SENSING_REPORT_LLM.model,
            response_schema=RadarDetailsOutput,
            contents=batch_prompt,
            port=GPU_SENSING_REPORT_LLM.port,
        )

        batch_details = RadarDetailsOutput.model_validate(batch_result)
        all_details.extend(batch_details.radar_item_details)
        logger.info(
            f"[Phase 3/3] Batch {batch_idx}/{len(batches)} done — "
            f"{len(batch_details.radar_item_details)} details"
        )

    details = RadarDetailsOutput(radar_item_details=all_details)
    phase3_time = time.time() - phase3_start

    logger.info(
        f"[Phase 3/3] Details generated in {phase3_time:.1f}s — "
        f"{len(details.radar_item_details)} detail entries across {len(batches)} batches"
    )

    # ── Merge into final report ────────────────────────────────────────
    report = TechSensingReport(
        **core.model_dump(),
        **analysis.model_dump(),
        radar_item_details=details.radar_item_details,
    )

    total_time = phase1_time + phase2_time + phase3_time
    logger.info(
        f"Report complete in {total_time:.1f}s "
        f"(p1={phase1_time:.1f}s, p2={phase2_time:.1f}s, p3={phase3_time:.1f}s) — "
        f"trends={len(report.key_trends)}, radar_items={len(report.radar_items)}, "
        f"details={len(report.radar_item_details)}, recommendations={len(report.recommendations)}"
    )

    return report
