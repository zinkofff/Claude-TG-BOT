"""Tests for article ranking."""

from __future__ import annotations

from src.core.article_ranker import rank, score_article


def test_rank_returns_top_n(sample_articles):
    """Test that rank returns exactly top_n articles."""
    top = rank(sample_articles, top_n=3)
    assert len(top) == 3


def test_rank_prefers_recent_articles(sample_articles):
    """Test that more recent articles score higher."""
    top = rank(sample_articles, top_n=5)

    # The most recent article (1h old) should be first or near the top
    assert top[0].url == "https://example.com/btc-100k"


def test_rank_handles_empty_list():
    """Test that rank handles empty input gracefully."""
    top = rank([], top_n=5)
    assert top == []


def test_score_article_is_between_0_and_1(sample_articles):
    """Test that all scores fall within expected range."""
    for article in sample_articles:
        score = score_article(article)
        assert 0.0 <= score <= 1.0, f"Score {score} out of range for {article.title}"


def test_rank_topic_relevant_articles_score_higher(sample_articles):
    """Test that articles with topic keywords score higher."""
    btc_article = sample_articles[0]  # Bitcoin article
    old_article = sample_articles[4]  # Old generic crypto article

    btc_score = score_article(btc_article)
    old_score = score_article(old_article)

    # Recent + topic-relevant should beat old + generic
    assert btc_score > old_score
