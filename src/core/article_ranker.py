"""Article scoring and ranking."""

from __future__ import annotations

import logging
import math

from src.config.feeds import SOURCE_WEIGHTS, TOPIC_KEYWORDS
from src.storage.models import Article

logger = logging.getLogger(__name__)

# Scoring weights
RECENCY_WEIGHT = 0.35
TOPIC_WEIGHT = 0.40
SOURCE_WEIGHT = 0.25

# Articles older than this many hours get zero recency score
MAX_AGE_HOURS = 48.0

# Topic categories that are core to Bron's positioning get a bonus.
# Articles matching these categories receive an extra score boost.
HIGH_PRIORITY_TOPICS = {"security_custody", "privacy_sovereignty", "regulation"}
HIGH_PRIORITY_BONUS = 0.15


def _recency_score(article: Article) -> float:
    """Score based on how recent the article is (0.0 to 1.0).

    Uses exponential decay: articles lose ~50% score every 12 hours.
    """
    age = article.age_hours
    if age <= 0:
        return 1.0
    if age >= MAX_AGE_HOURS:
        return 0.0
    # Exponential decay with half-life of 12 hours
    return math.exp(-0.0578 * age)  # ln(2)/12 ≈ 0.0578


def _topic_relevance_score(article: Article) -> tuple[float, bool]:
    """Score based on how many topic keywords match (0.0 to 1.0).

    Checks title, summary, and RSS categories against configured keywords.

    Returns:
        Tuple of (score, is_high_priority) where is_high_priority is True
        if the article matches any Bron-core topic category.
    """
    text = f"{article.title} {article.summary}".lower()
    categories_text = " ".join(article.categories)
    combined = f"{text} {categories_text}"

    matched_categories = 0
    total_categories = len(TOPIC_KEYWORDS)
    hit_high_priority = False

    for category, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                matched_categories += 1
                if category in HIGH_PRIORITY_TOPICS:
                    hit_high_priority = True
                break  # One match per category is enough

    if total_categories == 0:
        return 0.0, False
    score = min(matched_categories / max(total_categories * 0.5, 1), 1.0)
    return score, hit_high_priority


def _source_score(article: Article) -> float:
    """Score based on source priority (0.0 to 1.0)."""
    return SOURCE_WEIGHTS.get(article.source, 0.5)


def score_article(article: Article) -> float:
    """Calculate a composite score for an article.

    Returns:
        Float score between 0.0 and 1.0 (may slightly exceed 1.0 with bonus).
    """
    recency = _recency_score(article)
    topic, is_high_priority = _topic_relevance_score(article)
    source = _source_score(article)

    composite = (
        RECENCY_WEIGHT * recency
        + TOPIC_WEIGHT * topic
        + SOURCE_WEIGHT * source
    )

    # Boost articles about self-custody, privacy, regulation
    if is_high_priority:
        composite += HIGH_PRIORITY_BONUS

    logger.debug(
        "Score %.3f for '%s' (recency=%.2f, topic=%.2f, source=%.2f, priority=%s)",
        composite,
        article.title[:60],
        recency,
        topic,
        source,
        is_high_priority,
    )
    return composite


def rank(articles: list[Article], top_n: int = 5) -> list[Article]:
    """Score and return the top N articles.

    Args:
        articles: List of candidate articles (already deduplicated).
        top_n: Number of articles to return.

    Returns:
        Top N articles sorted by score descending.
    """
    if not articles:
        return []

    scored = [(score_article(a), a) for a in articles]
    scored.sort(key=lambda x: x[0], reverse=True)

    top_articles = [article for _score, article in scored[:top_n]]

    logger.info(
        "Ranked %d articles, returning top %d",
        len(articles),
        len(top_articles),
    )
    for i, (score, article) in enumerate(scored[:top_n]):
        logger.info(
            "  #%d (%.3f): [%s] %s", i + 1, score, article.source, article.title[:80]
        )

    return top_articles
