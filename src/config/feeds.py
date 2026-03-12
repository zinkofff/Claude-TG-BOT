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
    "security_custody": [
        {
            "name": "Ledger Blog",
            "url": "https://www.ledger.com/blog/feed",
        },
    ],
    "regulation": [
        {
            "name": "CoinDesk Policy",
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss/category/policy/",
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

# Keywords used for topic relevance scoring in article_ranker.
# Categories with more keywords have proportionally more matching power.
# Bron-relevant topics (security_custody, self_custody, regulation) are
# listed first and intentionally keyword-rich to boost those articles.
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "security_custody": [
        "self-custody", "self custody", "non-custodial", "custodial",
        "custody", "seed phrase", "recovery phrase", "mnemonic",
        "private key", "key management", "wallet security", "hardware wallet",
        "cold storage", "hot wallet", "mpc", "multi-party computation",
        "seedless", "passkey", "biometric", "wallet hack", "wallet exploit",
        "digital inheritance", "inheritance", "succession",
    ],
    "privacy_sovereignty": [
        "privacy", "on-chain privacy", "shielding", "zero knowledge",
        "zk-proof", "mixer", "tornado", "user sovereignty",
        "data protection", "surveillance", "kyc", "aml",
    ],
    "regulation": [
        "regulation", "regulatory", "sec", "cftc", "mica", "eu regulation",
        "compliance", "enforcement", "lawsuit", "settlement", "sanction",
        "legislation", "policy", "framework", "license", "licensing",
        "consumer protection", "investor protection",
    ],
    "crypto": [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
        "blockchain", "defi", "nft", "web3", "stablecoin", "altcoin",
        "layer 2", "l2", "rollup", "solana", "ton",
    ],
    "digital_assets": [
        "digital asset", "tokenisation", "tokenization", "security token",
        "real world asset", "rwa", "staking", "digital securities",
        "institutional adoption", "institutional crypto",
    ],
    "tech": [
        "artificial intelligence", "ai", "machine learning", "startup",
        "fintech", "cybersecurity", "cloud", "saas",
    ],
    "macro": [
        "interest rate", "inflation", "federal reserve", "fed", "gdp",
        "employment", "treasury", "central bank", "monetary policy",
        "fiscal", "recession", "yield", "sovereign wealth fund",
    ],
}

# Source priority weights (higher = more important)
SOURCE_WEIGHTS: dict[str, float] = {
    "CoinDesk": 1.0,
    "CoinDesk Policy": 1.0,
    "The Block": 1.0,
    "CoinTelegraph": 0.9,
    "Blockworks": 0.9,
    "Decrypt": 0.8,
    "The Defiant": 0.8,
    "Ledger Blog": 0.8,
    "TechCrunch": 0.9,
    "CNBC": 1.0,
    "Investing.com": 0.7,
    "Bitcoin Magazine": 0.7,
}
