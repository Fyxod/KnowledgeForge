"""
YouTube Trending Videos — searches for trending videos related to radar technologies.

Uses DDGS().videos() (DuckDuckGo video search) — no API key required.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("sensing.sources.youtube")

# Handle ddgs package rename: try new name first, fall back to old
try:
    from ddgs import DDGS  # type: ignore
except ImportError:
    from duckduckgo_search import DDGS  # type: ignore

# Defaults
MAX_VIDEOS_PER_TECH = 3
MAX_TECHNOLOGIES = 10
CONCURRENCY_LIMIT = 3


@dataclass
class TrendingVideo:
    """A single trending video result for a radar technology."""

    technology_name: str
    title: str
    url: str
    description: str
    uploader: str  # channel name
    duration: str  # e.g., "12:34"
    published: str  # date string
    view_count: int
    thumbnail_url: str


def _ddgs_video_search(query: str, max_results: int) -> list:
    """Synchronous DuckDuckGo video search wrapper."""
    with DDGS() as ddgs:
        return list(ddgs.videos(query, max_results=max_results))


async def fetch_youtube_videos(
    technology_names: List[str],
    max_videos_per_tech: int = MAX_VIDEOS_PER_TECH,
    max_technologies: int = MAX_TECHNOLOGIES,
) -> List[TrendingVideo]:
    """
    Search for trending YouTube videos for each technology name.

    Args:
        technology_names: Radar item names to search for.
        max_videos_per_tech: Max videos per technology (default 3).
        max_technologies: Max technologies to search (default 10).

    Returns:
        List of TrendingVideo results across all technologies.
    """
    techs_to_search = technology_names[:max_technologies]
    all_videos: List[TrendingVideo] = []
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async def _search_one(tech_name: str) -> List[TrendingVideo]:
        async with sem:
            try:
                results = await asyncio.to_thread(
                    _ddgs_video_search, tech_name, max_videos_per_tech + 2
                )
                videos = []
                for r in results:
                    content_url = r.get("content", "")
                    if (
                        "youtube.com" not in content_url
                        and "youtu.be" not in content_url
                    ):
                        continue

                    # Parse view count from statistics
                    stats = r.get("statistics", {})
                    view_count = 0
                    if isinstance(stats, dict):
                        vc = stats.get("viewCount", 0)
                        try:
                            view_count = int(vc)
                        except (ValueError, TypeError):
                            view_count = 0

                    # Get thumbnail
                    images = r.get("images", {})
                    thumbnail = ""
                    if isinstance(images, dict):
                        thumbnail = images.get(
                            "medium", images.get("small", images.get("large", ""))
                        )

                    videos.append(
                        TrendingVideo(
                            technology_name=tech_name,
                            title=r.get("title", ""),
                            url=content_url,
                            description=r.get("description", "")[:300],
                            uploader=r.get("uploader", ""),
                            duration=r.get("duration", ""),
                            published=r.get("published", ""),
                            view_count=view_count,
                            thumbnail_url=thumbnail,
                        )
                    )

                    if len(videos) >= max_videos_per_tech:
                        break

                logger.info(f"YouTube: found {len(videos)} videos for '{tech_name}'")
                return videos
            except Exception as e:
                logger.warning(f"YouTube search failed for '{tech_name}': {e}")
                return []

    results = await asyncio.gather(*[_search_one(t) for t in techs_to_search])
    for video_list in results:
        all_videos.extend(video_list)

    logger.info(
        f"YouTube: total {len(all_videos)} videos for "
        f"{len(techs_to_search)} technologies"
    )
    return all_videos
