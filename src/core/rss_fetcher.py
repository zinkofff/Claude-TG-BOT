"""RSS feed fetching and parsing."""

from __future__ import annotations

import logging
from datetime import datetime
from time import mktime

import feedparser

from src.config.feeds import ALL_FEEDS
from src.storage.models import Article

logger = logging.getLogger(__name__)

# Default timeout for fetching feeds (seconds)
FETCH_TIMEOUT_SECONDS = 15


def parse_published_date(entry: dict) -> datetime:
    """Extract and parse the publication date from a feed entry."""
    for date_field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(date_field)
        if parsed:
            try:
                return datetime.utcfromtimestamp(mktime(parsed))
            except (ValueError, OverflowError, OSError):
                continue

    # Fallback: use current time if no date found
    logger.warning("No valid date found for entry: %s", entry.get("title", "unknown"))
    return datetime.utcnow()


def parse_summary(entry: dict) -> str:
    """Extract the best available summary from a feed entry."""
    # Try summary first, then content, then description
    if entry.get("summary"):
        return _strip_html(entry["summary"])

    if entry.get("content"):
        for content in entry["content"]:
            if content.get("value"):
                return _strip_html(content["value"])

    if entry.get("description"):
        return _strip_html(entry["description"])

    return ""


def _strip_html(text: str) -> str:
    """Remove HTML tags and clean up whitespace."""
    import re

    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", "", text)
    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    # Truncate to a reasonable summary length
    if len(clean) > 1000:
        clean = clean[:1000] + "..."
    return clean


def parse_categories(entry: dict) -> list[str]:
    """Extract category/tag labels from a feed entry."""
    categories = []
    for tag in entry.get("tags", []):
        term = tag.get("term", "").strip()
        if term:
            categories.append(term.lower())
    return categories


def fetch_feed(feed_info: dict) -> list[Article]:
    """Fetch and parse a single RSS feed into Article objects.

    Args:
        feed_info: Dict with 'name', 'url', and 'category' keys.

    Returns:
        List of Article objects parsed from the feed.
    """
    name = feed_info["name"]
    url = feed_info["url"]
    category = feed_info.get("category", "general")

    logger.info("Fetching feed: %s (%s)", name, url)

    try:
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": "Claude-TG-BOT/0.1 (+https://github.com/zinkofff/Claude-TG-BOT)"},
        )

        if feed.bozo and not feed.entries:
            logger.warning(
                "Feed %s returned an error: %s", name, feed.bozo_exception
            )
            return []

        articles = []
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            article = Article(
                url=link,
                title=title,
                summary=parse_summary(entry),
                source=name,
                category=category,
                published_at=parse_published_date(entry),
                categories=parse_categories(entry),
            )
            articles.append(article)

        logger.info("Fetched %d articles from %s", len(articles), name)
        return articles

    except Exception:
        logger.exception("Failed to fetch feed: %s", name)
        return []


def fetch_all_feeds(
    feeds: list[dict] | None = None,
) -> list[Article]:
    """Fetch all configured RSS feeds and return combined articles.

    Args:
        feeds: Optional list of feed dicts. Defaults to ALL_FEEDS.

    Returns:
        Combined list of Article objects from all feeds, sorted by publish date.
    """
    if feeds is None:
        feeds = ALL_FEEDS

    all_articles: list[Article] = []

    for feed_info in feeds:
        articles = fetch_feed(feed_info)
        all_articles.extend(articles)

    # Sort by most recent first
    all_articles.sort(key=lambda a: a.published_at, reverse=True)

    logger.info("Total articles fetched across all feeds: %d", len(all_articles))
    return all_articles
