"""
Configuration for the Tech Sensing module.
Curated RSS feeds, default search queries, and pipeline parameters.
"""

DEFAULT_DOMAIN = "Generative AI"
LOOKBACK_DAYS = 7
MAX_ARTICLES_PER_FEED = 20
MAX_SEARCH_RESULTS = 30
ARTICLE_BATCH_SIZE = 6  # Articles per LLM classification call
MIN_RELEVANCE_SCORE = 0.3
DEDUP_SIMILARITY_THRESHOLD = 0.85

# Curated RSS feeds for GenAI / AI technology news
DEFAULT_RSS_FEEDS = [
    # Academic / Research
    "http://arxiv.org/rss/cs.AI",
    "http://arxiv.org/rss/cs.CL",  # Computation and Language (NLP/LLM)
    "http://arxiv.org/rss/cs.LG",  # Machine Learning
    # Industry news
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.technologyreview.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://the-decoder.com/feed/",
    "https://www.marktechpost.com/feed/",
    # Community
    "https://hnrss.org/newest?q=LLM+OR+GPT+OR+AI+OR+generative",
    "https://www.reddit.com/r/MachineLearning/.rss",
    # Company blogs
    "https://blog.google/technology/ai/rss/",
    "https://openai.com/blog/rss.xml",
]

# DuckDuckGo search queries (run in addition to RSS)
DEFAULT_SEARCH_QUERIES = [
    "generative AI latest developments this week",
    "LLM breakthrough news this week",
    "AI agents framework news this week",
    "RAG retrieval augmented generation news",
    "open source AI model release this week",
]
