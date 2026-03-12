"""Tests for RSS feed fetching and parsing."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

from src.core.rss_fetcher import fetch_all_feeds, fetch_feed


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(filename: str) -> str:
    with open(os.path.join(FIXTURES_DIR, filename)) as f:
        return f.read()


def test_fetch_feed_parses_articles():
    """Test that a single feed is fetched and parsed correctly."""
    feed_xml = _load_fixture("sample_feed.xml")
    url = "https://example.com/feed.xml"

    # feedparser uses urllib internally, so we mock feedparser.parse directly
    import feedparser

    parsed = feedparser.parse(feed_xml)

    with patch("src.core.rss_fetcher.feedparser.parse", return_value=parsed):
        feed_info = {"name": "TestFeed", "url": url, "category": "crypto"}
        articles = fetch_feed(feed_info)

    assert len(articles) == 4
    assert articles[0].title == "Bitcoin Hits New All-Time High Above $100K"
    assert articles[0].source == "TestFeed"
    assert articles[0].category == "crypto"
    assert articles[0].url == "https://example.com/articles/btc-100k"
    assert "bitcoin" in articles[0].categories
    assert len(articles[0].summary) > 0


def test_fetch_feed_handles_failure_gracefully():
    """Test that a failed feed returns empty list, not exception."""
    # Simulate a completely broken feed
    broken_result = MagicMock()
    broken_result.bozo = True
    broken_result.bozo_exception = Exception("Connection error")
    broken_result.entries = []

    with patch("src.core.rss_fetcher.feedparser.parse", return_value=broken_result):
        feed_info = {"name": "BrokenFeed", "url": "https://example.com/broken", "category": "crypto"}
        articles = fetch_feed(feed_info)

    # Should return empty list, not raise
    assert articles == []


def test_fetch_all_feeds_combines_results():
    """Test that multiple feeds are combined and sorted."""
    feed_xml = _load_fixture("sample_feed.xml")
    import feedparser

    parsed = feedparser.parse(feed_xml)

    with patch("src.core.rss_fetcher.feedparser.parse", return_value=parsed):
        feeds = [
            {"name": "Feed1", "url": "https://feed1.com/rss", "category": "crypto"},
            {"name": "Feed2", "url": "https://feed2.com/rss", "category": "tech"},
        ]

        articles = fetch_all_feeds(feeds)

    # 4 articles from each feed = 8 total
    assert len(articles) == 8
    # Should be sorted by date (most recent first)
    for i in range(len(articles) - 1):
        assert articles[i].published_at >= articles[i + 1].published_at


def test_article_url_hash_is_deterministic(sample_articles):
    """Test that URL hashes are consistent."""
    article = sample_articles[0]
    hash1 = article.url_hash
    hash2 = article.url_hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex


def test_article_title_hash_normalizes(sample_articles):
    """Test that title hashes normalize casing and punctuation."""
    from src.storage.models import Article
    from datetime import datetime

    a1 = Article(
        url="https://a.com/1",
        title="Bitcoin Hits $100K!",
        summary="",
        source="A",
        category="crypto",
        published_at=datetime.utcnow(),
    )
    a2 = Article(
        url="https://b.com/2",
        title="bitcoin hits 100k",
        summary="",
        source="B",
        category="crypto",
        published_at=datetime.utcnow(),
    )

    # Normalized titles should produce the same hash
    assert a1.title_hash == a2.title_hash
