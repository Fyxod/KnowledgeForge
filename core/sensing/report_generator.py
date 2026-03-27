"""
Final report generation via LLM.
Takes classified articles and produces the complete TechSensingReport.
"""

import json
from typing import List

from core.constants import GPU_SENSING_REPORT_LLM
from core.llm.client import invoke_llm
from core.llm.output_schemas.sensing_outputs import (
    ClassifiedArticle,
    TechSensingReport,
)
from core.llm.prompts.sensing_prompts import sensing_report_prompt


async def generate_report(
    classified_articles: List[ClassifiedArticle],
    domain: str = "Generative AI",
    date_range: str = "",
    custom_requirements: str = "",
) -> TechSensingReport:
    """
    Generate the complete Tech Sensing Report from classified articles.
    """
    # Truncate to top 50 by relevance if too many (avoid context overflow)
    sorted_articles = sorted(
        classified_articles, key=lambda a: a.relevance_score, reverse=True
    )[:50]

    articles_json = json.dumps(
        [a.model_dump() for a in sorted_articles],
        indent=2,
        ensure_ascii=False,
    )

    prompt = sensing_report_prompt(
        classified_articles_json=articles_json,
        domain=domain,
        date_range=date_range,
        custom_requirements=custom_requirements,
    )

    result = await invoke_llm(
        gpu_model=GPU_SENSING_REPORT_LLM.model,
        response_schema=TechSensingReport,
        contents=prompt,
        port=GPU_SENSING_REPORT_LLM.port,
    )

    report = TechSensingReport.model_validate(result)
    return report
