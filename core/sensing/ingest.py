"""
Data ingestion: RSS feeds + DuckDuckGo search.
Returns a list of RawArticle dataclass instances.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import feedparser
import trafilatura

from core.sensing.config import (
    DEFAULT_RSS_FEEDS,
    DEFAULT_SEARCH_QUERIES,
    LOOKBACK_DAYS,
    MAX_ARTICLES_PER_FEED,
    MAX_SEARCH_RESULTS,
)

logger = logging.getLogger("sensing.ingest")

# Handle ddgs package rename: try new name first, fall back to old
try:
    from ddgs import DDGS  # type: ignore

    logger.info("Using 'ddgs' package for DuckDuckGo search")
except ImportError:
    from duckduckgo_search import DDGS  # type: ignore

    logger.info("Using 'duckduckgo_search' package for DuckDuckGo search")


@dataclass
class RawArticle:
    title: str
    url: str
    source: str
    published_date: Optional[str] = None  # ISO format
    content: str = ""  # Full extracted text
    snippet: str = ""  # Short excerpt


async def fetch_rss_feeds(
    feed_urls: Optional[List[str]] = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> List[RawArticle]:
    """Parse RSS feeds and return articles from the last N days."""
    urls = feed_urls or DEFAULT_RSS_FEEDS
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    articles: List[RawArticle] = []

    logger.info(f"[RSS] Fetching {len(urls)} feeds (lookback={lookback_days}d)")

    for i, url in enumerate(urls):
        try:
            logger.info(f"[RSS {i+1}/{len(urls)}] Parsing: {url}")
            feed = await asyncio.to_thread(feedparser.parse, url)
            source_name = feed.feed.get("title", url)[:50]
            count_before = len(articles)

            for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
                pub_date = _parse_feed_date(entry)
                if pub_date and pub_date < cutoff:
                    continue

                articles.append(
                    RawArticle(
                        title=entry.get("title", "Untitled"),
                        url=entry.get("link", ""),
                        source=source_name,
                        published_date=(
                            pub_date.isoformat() if pub_date else None
                        ),
                        snippet=entry.get("summary", "")[:500],
                    )
                )

            added = len(articles) - count_before
            logger.info(
                f"[RSS {i+1}/{len(urls)}] '{source_name}': {added} articles "
                f"(total entries: {len(feed.entries)})"
            )
        except Exception as e:
            logger.warning(f"[RSS {i+1}/{len(urls)}] FAILED ({url}): {e}")

    logger.info(f"[RSS] Done. Total articles from RSS: {len(articles)}")
    return articles


async def search_duckduckgo(
    queries: Optional[List[str]] = None,
    domain: str = "Generative AI",
) -> List[RawArticle]:
    """Run DuckDuckGo searches and return results as RawArticle."""
    search_queries = queries or [
        q.replace("generative AI", domain) if domain != "Generative AI" else q
        for q in DEFAULT_SEARCH_QUERIES
    ]
    articles: List[RawArticle] = []

    logger.info(f"[DDG] Running {len(search_queries)} searches")

    for i, query in enumerate(search_queries):
        try:
            logger.info(f"[DDG {i+1}/{len(search_queries)}] Query: '{query}'")
            results = await asyncio.to_thread(
                _ddgs_search, query, MAX_SEARCH_RESULTS
            )
            for r in results:
                articles.append(
                    RawArticle(
                        title=r.get("title", "Untitled"),
                        url=r.get("href", r.get("link", "")),
                        source="DuckDuckGo",
                        snippet=r.get("body", "")[:500],
                    )
                )
            logger.info(
                f"[DDG {i+1}/{len(search_queries)}] Got {len(results)} results"
            )
        except Exception as e:
            logger.warning(
                f"[DDG {i+1}/{len(search_queries)}] FAILED ('{query}'): {e}"
            )

    logger.info(f"[DDG] Done. Total articles from DDG: {len(articles)}")
    return articles


async def extract_full_text(article: RawArticle) -> RawArticle:
    """Extract full article text using trafilatura with snippet fallback."""
    if article.content:
        return article
    try:
        downloaded = await asyncio.to_thread(trafilatura.fetch_url, article.url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                article.content = text[:5000]  # Cap to avoid token overflow
                return article
    except Exception:
        pass

    # Fallback: use snippet
    article.content = article.snippet or article.title
    return article


def _ddgs_search(query: str, max_results: int) -> list:
    """Synchronous DuckDuckGo search wrapper."""
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results, timelimit="w"))


def _parse_feed_date(entry) -> Optional[datetime]:
    """Parse feedparser entry date into UTC datetime."""
    for date_field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(date_field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None
