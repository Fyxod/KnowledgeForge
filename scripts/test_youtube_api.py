"""
Quick standalone script to test YouTube Data API v3 connectivity and quota.

Usage:
    python scripts/test_youtube_api.py
    python scripts/test_youtube_api.py "Gemma 4" "vLLM"
    python scripts/test_youtube_api.py --key YOUR_API_KEY "LangGraph"
"""

import argparse
import json
import sys

import httpx

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def parse_iso_duration(iso: str) -> str:
    if not iso or not iso.startswith("PT"):
        return iso
    rest = iso[2:]
    h, m, s = 0, 0, 0
    if "H" in rest:
        h_part, rest = rest.split("H", 1)
        h = int(h_part)
    if "M" in rest:
        m_part, rest = rest.split("M", 1)
        m = int(m_part)
    if "S" in rest:
        s = int(rest.replace("S", ""))
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def load_api_key() -> str:
    """Try loading YOUTUBE_API_KEY from .env file."""
    try:
        from pathlib import Path

        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("YOUTUBE_API_KEY=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def test_search(api_key: str, query: str, max_results: int = 3) -> None:
    print(f"\n{'='*60}")
    print(f"  Searching YouTube for: \"{query}\"")
    print(f"{'='*60}")

    # Step 1: Search
    print(f"\n[1/2] Calling search endpoint...")
    resp = httpx.get(
        YOUTUBE_SEARCH_URL,
        params={
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "relevance",
            "maxResults": max_results,
            "key": api_key,
        },
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"  FAILED — HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        return

    search_data = resp.json()
    items = search_data.get("items", [])
    print(f"  OK — {len(items)} results returned")

    if not items:
        print("  No videos found for this query.")
        return

    video_ids = [
        item["id"]["videoId"]
        for item in items
        if item.get("id", {}).get("videoId")
    ]

    # Step 2: Get details (duration, views)
    print(f"\n[2/2] Fetching details for {len(video_ids)} video(s)...")
    details_resp = httpx.get(
        YOUTUBE_VIDEOS_URL,
        params={
            "part": "contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": api_key,
        },
        timeout=15,
    )

    stats_map = {}
    if details_resp.status_code == 200:
        for detail in details_resp.json().get("items", []):
            vid = detail["id"]
            duration = detail.get("contentDetails", {}).get("duration", "")
            views = detail.get("statistics", {}).get("viewCount", "0")
            stats_map[vid] = {
                "duration": parse_iso_duration(duration),
                "views": int(views) if views.isdigit() else 0,
            }
        print(f"  OK — details for {len(stats_map)} video(s)")
    else:
        print(f"  FAILED — HTTP {details_resp.status_code}: {details_resp.text[:300]}")

    # Display results
    print(f"\n{'─'*60}")
    for i, item in enumerate(items, 1):
        vid = item["id"].get("videoId", "")
        snippet = item.get("snippet", {})
        stats = stats_map.get(vid, {})
        print(f"\n  [{i}] {snippet.get('title', 'N/A')}")
        print(f"      Channel:  {snippet.get('channelTitle', 'N/A')}")
        print(f"      URL:      https://www.youtube.com/watch?v={vid}")
        print(f"      Duration: {stats.get('duration', 'N/A')}")
        print(f"      Views:    {stats.get('views', 'N/A'):,}")
        print(f"      Date:     {snippet.get('publishedAt', 'N/A')[:10]}")
    print()


def test_quota(api_key: str) -> None:
    """Make a minimal API call to verify key validity and quota."""
    print(f"\n{'='*60}")
    print(f"  Testing API key validity & quota")
    print(f"{'='*60}")
    print(f"  Key: {api_key[:8]}...{api_key[-4:]}")

    resp = httpx.get(
        YOUTUBE_SEARCH_URL,
        params={
            "part": "snippet",
            "q": "test",
            "type": "video",
            "maxResults": 1,
            "key": api_key,
        },
        timeout=15,
    )

    if resp.status_code == 200:
        print(f"  Status: OK (HTTP 200)")
        print(f"  API key is valid and has remaining quota.")
    elif resp.status_code == 403:
        error = resp.json().get("error", {})
        errors = error.get("errors", [{}])
        reason = errors[0].get("reason", "unknown") if errors else "unknown"
        print(f"  Status: FORBIDDEN (HTTP 403)")
        print(f"  Reason: {reason}")
        if reason == "quotaExceeded":
            print(f"  Your daily quota (10,000 units) is exhausted. Resets at midnight PT.")
        elif reason == "forbidden":
            print(f"  The API key may not have YouTube Data API v3 enabled.")
        print(f"  Full error: {json.dumps(error, indent=2)}")
    elif resp.status_code == 400:
        print(f"  Status: BAD REQUEST (HTTP 400)")
        print(f"  The API key may be malformed.")
        print(f"  Response: {resp.text[:300]}")
    else:
        print(f"  Status: HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:300]}")


def main():
    parser = argparse.ArgumentParser(description="Test YouTube Data API v3")
    parser.add_argument(
        "queries",
        nargs="*",
        default=["Generative AI", "LLM fine-tuning"],
        help="Search queries to test (default: 'Generative AI' 'LLM fine-tuning')",
    )
    parser.add_argument(
        "--key",
        default="",
        help="YouTube API key (default: reads from .env)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=3,
        help="Max videos per query (default: 3)",
    )
    args = parser.parse_args()

    api_key = args.key or load_api_key()
    if not api_key:
        print("ERROR: No API key found.")
        print("Either pass --key YOUR_KEY or set YOUTUBE_API_KEY in .env")
        sys.exit(1)

    # Test 1: Key validity
    test_quota(api_key)

    # Test 2: Actual searches
    for query in args.queries:
        test_search(api_key, query, max_results=args.max_results)

    print(f"{'='*60}")
    print(f"  Done — tested {len(args.queries)} query(ies)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
