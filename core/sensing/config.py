"""
Configuration for the Tech Sensing module.
Curated RSS feeds, default search queries, and pipeline parameters.
"""

from typing import List

DEFAULT_DOMAIN = "Generative AI"
LOOKBACK_DAYS = 7
MAX_ARTICLES_PER_FEED = 20
MAX_SEARCH_RESULTS = 30
ARTICLE_BATCH_SIZE = 6  # Articles per LLM classification call
MIN_RELEVANCE_SCORE = 0.3
DEDUP_SIMILARITY_THRESHOLD = 0.85

# ── General technology / broad tech RSS feeds ──
# These are domain-agnostic and always included.
GENERAL_RSS_FEEDS = [
    "https://www.technologyreview.com/feed/",
    "https://techcrunch.com/feed/",
    "https://venturebeat.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://arstechnica.com/feed/",
]

# ── Domain-specific RSS feed presets ──
# Keyed by lowercase domain keywords. Matched if any keyword appears in the user domain.
DOMAIN_RSS_FEEDS = {
    "ai": [
        "http://arxiv.org/rss/cs.AI",
        "http://arxiv.org/rss/cs.CL",
        "http://arxiv.org/rss/cs.LG",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://the-decoder.com/feed/",
        "https://www.marktechpost.com/feed/",
        "https://hnrss.org/newest?q=LLM+OR+GPT+OR+AI+OR+generative",
        "https://www.reddit.com/r/MachineLearning/.rss",
        "https://blog.google/technology/ai/rss/",
        "https://openai.com/blog/rss.xml",
    ],
    "robotics": [
        "http://arxiv.org/rss/cs.RO",
        "https://www.therobotreport.com/feed/",
        "https://spectrum.ieee.org/feeds/topic/robotics.rss",
        "https://www.reddit.com/r/robotics/.rss",
    ],
    "quantum": [
        "http://arxiv.org/rss/quant-ph",
        "https://www.reddit.com/r/QuantumComputing/.rss",
        "https://quantumcomputingreport.com/feed/",
    ],
    "cybersecurity": [
        "https://www.darkreading.com/rss.xml",
        "https://feeds.feedburner.com/TheHackersNews",
        "https://krebsonsecurity.com/feed/",
        "https://www.bleepingcomputer.com/feed/",
        "https://www.reddit.com/r/netsec/.rss",
    ],
    "blockchain": [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://www.reddit.com/r/CryptoCurrency/.rss",
    ],
    "cloud": [
        "https://aws.amazon.com/blogs/aws/feed/",
        "https://cloud.google.com/blog/rss",
        "https://azure.microsoft.com/en-us/blog/feed/",
        "https://www.reddit.com/r/cloudcomputing/.rss",
    ],
}


def get_feeds_for_domain(domain: str) -> List[str]:
    """
    Return RSS feeds relevant to the user's domain.
    Always includes general tech feeds + domain-specific feeds if matched.
    """
    feeds = list(GENERAL_RSS_FEEDS)
    domain_lower = domain.lower()

    for keyword, domain_feeds in DOMAIN_RSS_FEEDS.items():
        if keyword in domain_lower:
            feeds.extend(domain_feeds)

    # If no domain-specific match, add AI feeds as fallback only if
    # domain contains generic tech terms
    if len(feeds) == len(GENERAL_RSS_FEEDS):
        # Add HackerNews broad search for the domain
        safe_domain = domain.replace(" ", "+")
        feeds.append(f"https://hnrss.org/newest?q={safe_domain}")

    return feeds


def get_search_queries_for_domain(
    domain: str,
    must_include: List[str] | None = None,
) -> List[str]:
    """
    Generate DuckDuckGo search queries tailored to the user's domain.
    """
    queries = [
        f"{domain} latest developments this week",
        f"{domain} breakthrough news this week",
        f"{domain} new technology announcements",
        f"{domain} industry trends this week",
        f"{domain} open source news this week",
    ]

    # Add must-include keyword queries
    if must_include:
        for kw in must_include[:5]:  # Cap at 5 extra queries
            queries.append(f"{domain} {kw} news this week")

    return queries
