"""
Report verifier — filters off-topic content from the generated report.

Uses a lightweight LLM call to check each radar item, market signal, and trend
against the user's specific domain/topic. Removes items that are only tangentially
related (e.g., general AI news when the user asked about "World Models").
"""

import json
import logging
import time
from typing import List

from pydantic import BaseModel, Field

from core.constants import GPU_SENSING_CLASSIFY_LLM
from core.llm.client import invoke_llm
from core.llm.output_schemas.base import LLMOutputBase
from core.llm.output_schemas.sensing_outputs import TechSensingReport

logger = logging.getLogger("sensing.verifier")


class VerifiedItems(LLMOutputBase):
    """LLM output: lists of item names/titles that are on-topic."""

    relevant_radar_items: List[str] = Field(
        description="Names of radar items that are directly relevant to the specific domain/topic."
    )
    relevant_market_signals: List[str] = Field(
        description="Company names of market signals that are directly relevant to the specific domain/topic."
    )
    relevant_trends: List[str] = Field(
        description="Names of trends that are directly relevant to the specific domain/topic."
    )


async def verify_report(
    report: TechSensingReport,
    domain: str,
    must_include: list[str] | None = None,
    dont_include: list[str] | None = None,
) -> TechSensingReport:
    """
    Verify report content against the user's domain and filter off-topic items.
    Returns a new report with only relevant items kept.
    """
    verify_start = time.time()

    # Build a compact summary of all items for the verifier
    radar_names = [item.name for item in report.radar_items]
    signal_companies = [s.company_or_player for s in report.market_signals]
    trend_names = [t.trend_name for t in report.key_trends]

    items_summary = {
        "radar_items": [
            {"name": item.name, "description": item.description}
            for item in report.radar_items
        ],
        "market_signals": [
            {"company": s.company_or_player, "signal": s.signal}
            for s in report.market_signals
        ],
        "trends": [
            {"name": t.trend_name, "description": t.description}
            for t in report.key_trends
        ],
    }

    schema_json = json.dumps(VerifiedItems.model_json_schema(), indent=2)

    must_str = f"\nMust-include keywords: {', '.join(must_include)}" if must_include else ""
    dont_str = f"\nDon't-include keywords: {', '.join(dont_include)}" if dont_include else ""

    prompt = [
        {
            "role": "system",
            "parts": (
                f"You are a relevance checker for a tech sensing report about '{domain}'.\n\n"
                "Your task is to review each item and determine if it is DIRECTLY relevant "
                f"to the specific topic of '{domain}'.\n\n"
                "STRICT RELEVANCE CRITERIA:\n"
                f"- Items must be specifically about or closely related to '{domain}'\n"
                "- General industry news that only tangentially mentions the domain should be EXCLUDED\n"
                "- Company announcements that are about other topics (not the domain) should be EXCLUDED\n"
                "- Broad AI/tech news that doesn't specifically relate to the domain should be EXCLUDED\n"
                f"- If '{domain}' is a specific sub-topic (e.g., 'World Models', 'Graph Neural Networks'), "
                "do NOT include general parent-topic items unless they directly discuss the sub-topic\n"
                + must_str + dont_str + "\n\n"
                "OUTPUT REQUIREMENT:\n"
                "Return ONLY a valid JSON object matching the schema below.\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n\n"
                "OUTPUT RULES:\n"
                "- Output must be valid JSON only.\n"
                "- List ONLY the names/companies of items that pass the relevance check.\n"
                "- Be strict — when in doubt, exclude the item.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"DOMAIN: {domain}\n\n"
                f"ITEMS TO VERIFY:\n{json.dumps(items_summary, indent=2, ensure_ascii=False)}\n\n"
                "Return ONLY the names of items that are directly relevant. Be strict."
            ),
        },
    ]

    try:
        logger.info(
            f"Verifying report relevance: {len(radar_names)} radar items, "
            f"{len(signal_companies)} signals, {len(trend_names)} trends"
        )

        result = await invoke_llm(
            gpu_model=GPU_SENSING_CLASSIFY_LLM.model,
            response_schema=VerifiedItems,
            contents=prompt,
            port=GPU_SENSING_CLASSIFY_LLM.port,
        )

        verified = VerifiedItems.model_validate(result)

        # Filter report items
        relevant_radar = set(verified.relevant_radar_items)
        relevant_signals = set(verified.relevant_market_signals)
        relevant_trends = set(verified.relevant_trends)

        orig_radar = len(report.radar_items)
        orig_signals = len(report.market_signals)
        orig_trends = len(report.key_trends)

        # Filter radar items and their details
        report.radar_items = [
            item for item in report.radar_items if item.name in relevant_radar
        ]
        report.radar_item_details = [
            item for item in report.radar_item_details
            if item.technology_name in relevant_radar
        ]

        # Filter market signals
        report.market_signals = [
            s for s in report.market_signals
            if s.company_or_player in relevant_signals
        ]

        # Filter trends
        report.key_trends = [
            t for t in report.key_trends if t.trend_name in relevant_trends
        ]

        # Filter notable articles: keep only those whose technology matches
        if report.notable_articles:
            report.notable_articles = [
                a for a in report.notable_articles
                if a.technology_name in relevant_radar
            ]

        elapsed = time.time() - verify_start
        logger.info(
            f"Verification complete in {elapsed:.1f}s — "
            f"radar: {orig_radar}->{len(report.radar_items)}, "
            f"signals: {orig_signals}->{len(report.market_signals)}, "
            f"trends: {orig_trends}->{len(report.key_trends)}"
        )

    except Exception as e:
        logger.warning(f"Verification failed (keeping original report): {e}")
        # On failure, return unmodified report

    return report
