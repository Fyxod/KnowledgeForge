"""
Hacker News — fetches recent stories from the Algolia HN Search API.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List

import httpx

from core.sensing.ingest import RawArticle

logger = logging.getLogger("sensing.sources.hackernews")

HN_MAX_RESULTS = 20
HN_API_URL = "https://hn.algolia.com/api/v1/search_by_date"


async def fetch_hackernews(
    domain: str,
    lookback_days: int = 7,
    max_results: int = HN_MAX_RESULTS,
) -> List[RawArticle]:
    """Fetch recent HN stories for a domain."""
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=lookback_days)).timestamp())

    articles: List[RawArticle] = []

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                HN_API_URL,
                params={
                    "query": domain,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff_ts}",
                    "hitsPerPage": max_results,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for hit in data.get("hits", [])[:max_results]:
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                points = hit.get("points", 0)
                comments = hit.get("num_comments", 0)
                created = hit.get("created_at", "")

                articles.append(RawArticle(
                    title=hit.get("title", ""),
                    url=url,
                    source="Hacker News",
                    published_date=created,
                    snippet=f"{points} points, {comments} comments",
                    content=hit.get("story_text", "") or hit.get("title", ""),
                ))

        logger.info(f"HN: fetched {len(articles)} stories for '{domain}'")

    except Exception as e:
        logger.warning(f"HN fetch failed: {e}")

    return articles
