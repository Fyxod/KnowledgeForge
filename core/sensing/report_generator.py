"""
Final report generation via LLM.
Takes classified articles and produces the complete TechSensingReport.
"""

import json
import logging
import time
from typing import List

from core.constants import GPU_SENSING_REPORT_LLM
from core.llm.client import invoke_llm
from core.llm.output_schemas.sensing_outputs import (
    ClassifiedArticle,
    TechSensingReport,
)
from core.llm.prompts.sensing_prompts import sensing_report_prompt

logger = logging.getLogger("sensing.report")


async def generate_report(
    classified_articles: List[ClassifiedArticle],
    domain: str = "Generative AI",
    date_range: str = "",
    custom_requirements: str = "",
    org_context: str = "",
) -> TechSensingReport:
    """
    Generate the complete Tech Sensing Report from classified articles.
    """
    # Truncate to top 50 by relevance if too many (avoid context overflow)
    sorted_articles = sorted(
        classified_articles, key=lambda a: a.relevance_score, reverse=True
    )[:50]

    logger.info(
        f"Generating report from {len(sorted_articles)} articles "
        f"(domain={domain}, range={date_range})"
    )

    articles_json = json.dumps(
        [a.model_dump() for a in sorted_articles],
        indent=2,
        ensure_ascii=False,
    )
    logger.info(f"Articles JSON payload size: {len(articles_json)} chars")

    prompt = sensing_report_prompt(
        classified_articles_json=articles_json,
        domain=domain,
        date_range=date_range,
        custom_requirements=custom_requirements,
        org_context=org_context,
    )

    report_start = time.time()
    logger.info("Sending report generation request to LLM...")

    result = await invoke_llm(
        gpu_model=GPU_SENSING_REPORT_LLM.model,
        response_schema=TechSensingReport,
        contents=prompt,
        port=GPU_SENSING_REPORT_LLM.port,
    )

    report = TechSensingReport.model_validate(result)
    elapsed = time.time() - report_start

    logger.info(
        f"Report generated in {elapsed:.1f}s — "
        f"trends={len(report.key_trends)}, radar_items={len(report.radar_items)}, "
        f"sections={len(report.report_sections)}, recommendations={len(report.recommendations)}"
    )

    return report
