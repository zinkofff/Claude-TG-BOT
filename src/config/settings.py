"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""  # Primary chat for scanner broadcasts
    allowed_chat_ids: frozenset[int] = frozenset()  # All chats that can use the bot

    # Digest
    digest_article_count: int = 5

    # DynamoDB
    articles_table: str = "claude-tg-bot-articles"
    drafts_table: str = "claude-tg-bot-drafts"

    # AWS
    aws_region: str = "us-east-1"
    dynamodb_endpoint_url: str | None = None  # For local DynamoDB

    # Logging
    log_level: str = "INFO"


def _parse_chat_ids(raw: str) -> frozenset[int]:
    """Parse comma-separated chat IDs into a frozenset of ints."""
    if not raw.strip():
        return frozenset()
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                ids.add(int(part))
            except ValueError:
                pass
    return frozenset(ids)


def load_settings() -> Settings:
    """Load settings from environment variables.

    In local development, use python-dotenv to load .env before calling this.
    In Lambda, environment variables are set via SAM template.
    """
    return Settings(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        claude_model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5"),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        allowed_chat_ids=_parse_chat_ids(os.environ.get("ALLOWED_CHAT_IDS", "")),
        digest_article_count=int(os.environ.get("DIGEST_ARTICLE_COUNT", "5")),
        articles_table=os.environ.get("ARTICLES_TABLE", "claude-tg-bot-articles"),
        drafts_table=os.environ.get("DRAFTS_TABLE", "claude-tg-bot-drafts"),
        aws_region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        dynamodb_endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
