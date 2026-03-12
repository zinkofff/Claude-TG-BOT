"""Data models for the application."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """A news article parsed from an RSS feed."""

    url: str
    title: str
    summary: str
    source: str
    category: str
    published_at: datetime
    categories: list[str] = field(default_factory=list)

    @property
    def url_hash(self) -> str:
        """SHA-256 hash of the normalized URL for deduplication."""
        normalized = self.url.strip().lower().rstrip("/")
        return hashlib.sha256(normalized.encode()).hexdigest()

    @property
    def title_hash(self) -> str:
        """SHA-256 hash of the normalized title for cross-source dedup."""
        normalized = re.sub(r"[^\w\s]", "", self.title.lower()).strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @property
    def age_hours(self) -> float:
        """Hours since publication."""
        delta = datetime.utcnow() - self.published_at
        return delta.total_seconds() / 3600


@dataclass
class Draft:
    """A social media post draft for one platform."""

    draft_id: str
    article_hash: str
    article_url: str
    article_title: str
    article_summary: str
    platform: str  # "twitter" or "linkedin"
    draft_text: str
    state: str = "pending"  # pending | approved | skipped | editing
    chat_id: int = 0
    message_id: int = 0
    feedback_history: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DraftPair:
    """A pair of drafts (Twitter + LinkedIn) for one article."""

    twitter: Draft
    linkedin: Draft
