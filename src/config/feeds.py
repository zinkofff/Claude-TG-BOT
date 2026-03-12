"""RSS feed registry organized by topic category."""

from __future__ import annotations

FEED_REGISTRY: dict[str, list[dict[str, str]]] = {
    "crypto": [
        {
            "name": "CoinDesk",
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        },
        {
            "name": "CoinTelegraph",
            "url": "https://cointelegraph.com/rss",
        },
        {
            "name": "Decrypt",
            "url": "https://decrypt.co/feed",
        },
        {
            "name": "The Block",
            "url": "https://www.theblock.co/rss.xml",
        },
        {
            "name": "Bitcoin Magazine",
            "url": "https://bitcoinmagazine.com/feed",
        },
    ],
    "digital_assets": [
        {
            "name": "Blockworks",
            "url": "https://blockworks.com/feed",
        },
        {
            "name": "The Defiant",
            "url": "https://thedefiant.io/feed",
        },
    ],
    "tech": [
        {
            "name": "TechCrunch",
            "url": "https://techcrunch.com/feed/",
        },
    ],
    "macro": [
        {
            "name": "CNBC",
            "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        },
        {
            "name": "Investing.com",
            "url": "https://www.investing.com/rss/news.rss",
        },
    ],
}

# Flattened list of all feeds for convenience
ALL_FEEDS: list[dict[str, str]] = [
    {**feed, "category": category}
    for category, feeds in FEED_REGISTRY.items()
    for feed in feeds
]

# Keywords used for topic relevance scoring in article_ranker
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "crypto": [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
        "blockchain", "defi", "nft", "web3", "stablecoin", "altcoin",
    ],
    "digital_assets": [
        "digital asset", "tokenisation", "tokenization", "security token",
        "real world asset", "rwa", "staking", "custody", "digital securities",
    ],
    "tech": [
        "artificial intelligence", "ai", "machine learning", "startup",
        "fintech", "cybersecurity", "cloud", "saas",
    ],
    "macro": [
        "interest rate", "inflation", "federal reserve", "fed", "gdp",
        "employment", "treasury", "central bank", "monetary policy",
        "fiscal", "recession", "yield",
    ],
}

# Source priority weights (higher = more important)
SOURCE_WEIGHTS: dict[str, float] = {
    "CoinDesk": 1.0,
    "The Block": 1.0,
    "CoinTelegraph": 0.9,
    "Blockworks": 0.9,
    "Decrypt": 0.8,
    "The Defiant": 0.8,
    "TechCrunch": 0.9,
    "CNBC": 1.0,
    "Investing.com": 0.7,
    "Bitcoin Magazine": 0.7,
}
