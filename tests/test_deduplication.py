"""Tests for article deduplication."""

from __future__ import annotations

from moto import mock_aws

from src.core.deduplication import filter_seen, mark_as_seen


@mock_aws
def test_filter_seen_removes_known_articles(db, sample_articles):
    """Test that previously seen articles are filtered out."""
    # Mark the first article as seen
    mark_as_seen([sample_articles[0]], db)

    # Filter should remove the first article
    new = filter_seen(sample_articles, db)

    urls = {a.url for a in new}
    assert sample_articles[0].url not in urls
    assert len(new) == len(sample_articles) - 1


@mock_aws
def test_filter_seen_allows_new_articles(db, sample_articles):
    """Test that new articles pass through the filter."""
    new = filter_seen(sample_articles, db)
    assert len(new) == len(sample_articles)


@mock_aws
def test_filter_seen_deduplicates_within_batch(db):
    """Test that duplicate titles within a single batch are deduplicated."""
    from datetime import datetime
    from src.storage.models import Article

    now = datetime.utcnow()

    articles = [
        Article(
            url="https://a.com/story",
            title="Same Story Different Source",
            summary="Summary A",
            source="Source A",
            category="crypto",
            published_at=now,
        ),
        Article(
            url="https://b.com/story",
            title="Same Story Different Source",  # Same title
            summary="Summary B",
            source="Source B",
            category="crypto",
            published_at=now,
        ),
    ]

    new = filter_seen(articles, db)
    # Should only keep one
    assert len(new) == 1


@mock_aws
def test_mark_as_seen_persists(db, sample_articles):
    """Test that marked articles are found on subsequent filter calls."""
    mark_as_seen(sample_articles[:2], db)

    # Now filter the same articles — the first 2 should be gone
    new = filter_seen(sample_articles, db)
    assert len(new) == len(sample_articles) - 2
