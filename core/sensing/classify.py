"""
LLM-based article classification for Technology Radar placement.
"""

from typing import List

from core.constants import GPU_SENSING_CLASSIFY_LLM
from core.llm.client import invoke_llm
from core.llm.output_schemas.sensing_outputs import (
    ArticleBatchClassification,
    ClassifiedArticle,
)
from core.llm.prompts.sensing_prompts import sensing_classify_prompt
from core.sensing.config import ARTICLE_BATCH_SIZE, MIN_RELEVANCE_SCORE
from core.sensing.ingest import RawArticle


async def classify_articles(
    articles: List[RawArticle],
    domain: str = "Generative AI",
    custom_requirements: str = "",
) -> List[ClassifiedArticle]:
    """
    Classify articles into Technology Radar quadrants/rings via LLM.
    Processes in batches to stay within context window.
    """
    all_classified: List[ClassifiedArticle] = []

    for i in range(0, len(articles), ARTICLE_BATCH_SIZE):
        batch = articles[i : i + ARTICLE_BATCH_SIZE]
        articles_text = _format_batch_for_prompt(batch)

        prompt = sensing_classify_prompt(
            articles_text=articles_text,
            domain=domain,
            custom_requirements=custom_requirements,
        )

        try:
            result = await invoke_llm(
                gpu_model=GPU_SENSING_CLASSIFY_LLM.model,
                response_schema=ArticleBatchClassification,
                contents=prompt,
                port=GPU_SENSING_CLASSIFY_LLM.port,
            )

            validated = ArticleBatchClassification.model_validate(result)

            for article in validated.articles:
                if article.relevance_score >= MIN_RELEVANCE_SCORE:
                    all_classified.append(article)

        except Exception as e:
            print(
                f"[Sensing:classify] Batch {i // ARTICLE_BATCH_SIZE} failed: {e}"
            )
            continue

    return all_classified


def _format_batch_for_prompt(articles: List[RawArticle]) -> str:
    """Format a batch of articles for the classification prompt."""
    parts = []
    for idx, a in enumerate(articles, 1):
        parts.append(
            f"--- Article {idx} ---\n"
            f"Title: {a.title}\n"
            f"Source: {a.source}\n"
            f"URL: {a.url}\n"
            f"Date: {a.published_date or 'Unknown'}\n"
            f"Content:\n{a.content[:2000]}\n"
        )
    return "\n".join(parts)
