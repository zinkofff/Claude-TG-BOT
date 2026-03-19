"""Lambda handler for the scheduled daily news scan.

Triggered by EventBridge on a cron schedule.
Fetches RSS feeds, deduplicates, ranks, generates drafts via Claude,
and sends the digest to Telegram.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config.feeds import ALL_FEEDS
from src.config.settings import Settings, load_settings
from src.core.article_ranker import rank
from src.core.claude_client import ClaudeClient
from src.core.deduplication import filter_seen, mark_as_seen
from src.core.rss_fetcher import fetch_all_feeds
from src.storage.dynamodb import DynamoDBStorage
from src.telegram.bot import TelegramBot
from src.telegram.keyboards import article_keyboard
from src.telegram.message_formatter import (
    format_article_card,
    format_digest_header,
    format_error_message,
    format_no_articles_message,
)

logger = logging.getLogger(__name__)


def _setup_logging(settings: Settings) -> None:
    """Configure logging based on settings."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def run_scan(settings: Settings, chat_id: str | None = None) -> dict[str, Any]:
    """Execute the full news scan pipeline.

    This is the core logic, separated from the Lambda handler
    for easier local testing.

    Args:
        settings: Application settings.
        chat_id: Override chat to send results to. Defaults to settings.telegram_chat_id.

    Returns:
        Dict with scan results summary.
    """
    db = DynamoDBStorage(settings)
    bot = TelegramBot(settings.telegram_bot_token)
    claude = ClaudeClient(settings)
    chat_id = chat_id or settings.telegram_chat_id

    # Step 1: Fetch all RSS feeds
    logger.info("Step 1: Fetching RSS feeds...")
    all_articles = fetch_all_feeds(ALL_FEEDS)

    if not all_articles:
        logger.warning("No articles fetched from any feed")
        bot.send_message(chat_id, format_no_articles_message())
        return {"status": "no_articles", "fetched": 0}

    # Step 2: Deduplicate
    logger.info("Step 2: Deduplicating articles...")
    new_articles = filter_seen(all_articles, db)

    if not new_articles:
        logger.info("No new articles after deduplication")
        bot.send_message(chat_id, format_no_articles_message())
        return {"status": "all_seen", "fetched": len(all_articles), "new": 0}

    # Step 3: Rank and select top N
    logger.info("Step 3: Ranking articles...")
    top_articles = rank(new_articles, top_n=settings.digest_article_count)

    # Step 4: Send digest header
    logger.info("Step 4: Sending digest to Telegram...")
    bot.send_message(
        chat_id,
        format_digest_header(len(top_articles), len(ALL_FEEDS)),
    )

    # Step 5: Generate drafts and send each article
    drafts_generated = 0
    for i, article in enumerate(top_articles, start=1):
        try:
            # Generate drafts via Claude
            logger.info(
                "Generating drafts for article %d/%d: %s",
                i,
                len(top_articles),
                article.title[:60],
            )
            draft_pair = claude.generate_drafts(article)

            # Set the chat_id on both drafts
            draft_pair.twitter.chat_id = int(chat_id)
            draft_pair.linkedin.chat_id = int(chat_id)

            # Send article card with inline keyboard
            card_text = format_article_card(article, i, len(top_articles))
            result = bot.send_message(
                chat_id,
                card_text,
                reply_markup=article_keyboard(draft_pair.twitter.draft_id),
            )

            # Store the message_id so we can edit the message later
            sent_msg = result.get("result", {})
            message_id = sent_msg.get("message_id", 0)
            draft_pair.twitter.message_id = message_id
            draft_pair.linkedin.message_id = message_id

            # Save drafts to DynamoDB
            db.put_draft(draft_pair.twitter)
            db.put_draft(draft_pair.linkedin)

            drafts_generated += 1

        except Exception:
            logger.exception(
                "Failed to process article %d: %s", i, article.title[:60]
            )
            # Continue with next article — don't let one failure block others
            continue

    # Step 6: Mark all top articles as seen
    mark_as_seen(top_articles, db)

    summary = {
        "status": "success",
        "fetched": len(all_articles),
        "new": len(new_articles),
        "ranked": len(top_articles),
        "drafts_generated": drafts_generated,
    }
    logger.info("Scan complete: %s", summary)
    return summary


def lambda_handler(event: dict, context: Any) -> dict:
    """AWS Lambda entry point for EventBridge scheduled trigger.

    Args:
        event: EventBridge event (ignored).
        context: Lambda context (ignored).

    Returns:
        Response dict with status code and scan results.
    """
    settings = load_settings()
    _setup_logging(settings)

    logger.info("News scanner triggered: %s", event.get("detail-type", "manual"))

    # Use chat_id from the invoking command if provided
    override_chat_id = event.get("chat_id")
    if override_chat_id:
        override_chat_id = str(override_chat_id)

    try:
        result = run_scan(settings, chat_id=override_chat_id)
        return {
            "statusCode": 200,
            "body": result,
        }
    except Exception as e:
        logger.exception("News scanner failed")

        # Try to notify the user
        try:
            bot = TelegramBot(settings.telegram_bot_token)
            bot.send_message(
                settings.telegram_chat_id,
                format_error_message(str(e)),
            )
        except Exception:
            logger.exception("Failed to send error notification")

        return {
            "statusCode": 500,
            "body": {"status": "error", "error": str(e)},
        }
