"""Article deduplication logic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.storage.models import Article

if TYPE_CHECKING:
    from src.storage.dynamodb import DynamoDBStorage

logger = logging.getLogger(__name__)


def filter_seen(
    articles: list[Article],
    db: DynamoDBStorage,
) -> list[Article]:
    """Remove articles that have already been processed.

    Uses two dedup strategies:
    1. URL-based: exact match on the canonical article URL hash
    2. Title-based: SHA-256 of normalized title to catch same story from different sources

    Args:
        articles: List of candidate articles.
        db: DynamoDB storage instance for checking seen articles.

    Returns:
        List of articles not previously seen.
    """
    if not articles:
        return []

    # Batch-check which article hashes already exist
    url_hashes = [a.url_hash for a in articles]
    seen_url_hashes = db.get_seen_article_hashes(url_hashes)

    # Also check title hashes for cross-source dedup
    title_hashes = [a.title_hash for a in articles]
    seen_title_hashes = db.get_seen_title_hashes(title_hashes)

    new_articles: list[Article] = []
    seen_titles_this_batch: set[str] = set()

    for article in articles:
        # Skip if URL already seen
        if article.url_hash in seen_url_hashes:
            logger.debug("Skipping (URL seen): %s", article.title)
            continue

        # Skip if title already seen (cross-source dedup)
        if article.title_hash in seen_title_hashes:
            logger.debug("Skipping (title seen): %s from %s", article.title, article.source)
            continue

        # Skip if we've already accepted an article with the same title in this batch
        if article.title_hash in seen_titles_this_batch:
            logger.debug(
                "Skipping (duplicate in batch): %s from %s", article.title, article.source
            )
            continue

        seen_titles_this_batch.add(article.title_hash)
        new_articles.append(article)

    logger.info(
        "Deduplication: %d articles in, %d new articles out",
        len(articles),
        len(new_articles),
    )
    return new_articles


def mark_as_seen(
    articles: list[Article],
    db: DynamoDBStorage,
) -> None:
    """Mark articles as seen in the database.

    Args:
        articles: Articles to mark as processed.
        db: DynamoDB storage instance.
    """
    for article in articles:
        db.put_seen_article(article)
    logger.info("Marked %d articles as seen", len(articles))
