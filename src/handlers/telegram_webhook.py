"""Lambda handler for Telegram webhook callbacks.

Receives POST requests from Telegram via API Gateway.
Routes callback queries (button presses) and text messages
to the appropriate handler functions.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.config.settings import Settings, load_settings
from src.core.claude_client import ClaudeClient
from src.storage.dynamodb import DynamoDBStorage
from src.telegram.bot import TelegramBot
from src.telegram.keyboards import (
    after_approve_keyboard,
    after_edit_keyboard,
    article_keyboard,
    draft_view_keyboard,
)
from src.telegram.message_formatter import (
    format_approved_message,
    format_draft_view,
    format_edit_prompt,
    format_error_message,
    format_regenerated_draft,
    format_skip_message,
)

logger = logging.getLogger(__name__)


# ── Callback Query Handlers ──────────────────────────────────────────


def handle_view(
    bot: TelegramBot,
    db: DynamoDBStorage,
    chat_id: int,
    message_id: int,
    draft_id: str,
    platform_code: str,
) -> None:
    """Handle 'view' callback — show the draft text for a platform."""
    platform = "twitter" if platform_code == "tw" else "linkedin"
    draft = db.get_draft(draft_id, platform)

    if not draft:
        bot.edit_message_text(chat_id, message_id, "⚠️ Draft not found.")
        return

    text = format_draft_view(draft)
    keyboard = draft_view_keyboard(draft_id, platform_code)
    bot.edit_message_text(chat_id, message_id, text, reply_markup=keyboard)


def handle_approve(
    bot: TelegramBot,
    db: DynamoDBStorage,
    chat_id: int,
    message_id: int,
    draft_id: str,
    platform_code: str,
) -> None:
    """Handle 'approve' callback — mark draft as approved."""
    platform = "twitter" if platform_code == "tw" else "linkedin"
    draft = db.get_draft(draft_id, platform)

    if not draft:
        bot.edit_message_text(chat_id, message_id, "⚠️ Draft not found.")
        return

    # Update state to approved
    db.update_draft_state(draft_id, platform, "approved")
    draft.state = "approved"

    text = format_approved_message(draft)
    keyboard = after_approve_keyboard(draft_id, platform_code)
    bot.edit_message_text(chat_id, message_id, text, reply_markup=keyboard)


def handle_edit(
    bot: TelegramBot,
    db: DynamoDBStorage,
    chat_id: int,
    message_id: int,
    draft_id: str,
    platform_code: str,
) -> None:
    """Handle 'edit' callback — put draft in editing mode, ask for feedback."""
    platform = "twitter" if platform_code == "tw" else "linkedin"
    draft = db.get_draft(draft_id, platform)

    if not draft:
        bot.edit_message_text(chat_id, message_id, "⚠️ Draft not found.")
        return

    # Set state to editing
    db.update_draft_state(draft_id, platform, "editing")

    # Send the edit prompt as a new message (so the user can reply)
    bot.send_message(chat_id, format_edit_prompt(draft))


def handle_skip(
    bot: TelegramBot,
    db: DynamoDBStorage,
    chat_id: int,
    message_id: int,
    draft_id: str,
) -> None:
    """Handle 'skip' callback — mark both platform drafts as skipped."""
    for platform in ("twitter", "linkedin"):
        try:
            db.update_draft_state(draft_id, platform, "skipped")
        except Exception:
            logger.warning("Failed to skip draft %s/%s", draft_id, platform)

    bot.edit_message_text(chat_id, message_id, format_skip_message())


def handle_back(
    bot: TelegramBot,
    db: DynamoDBStorage,
    chat_id: int,
    message_id: int,
    draft_id: str,
) -> None:
    """Handle 'back' callback — return to the main article keyboard."""
    # Get the draft to show the article card again
    draft = db.get_draft(draft_id, "twitter") or db.get_draft(draft_id, "linkedin")

    if not draft:
        bot.edit_message_text(chat_id, message_id, "⚠️ Draft not found.")
        return

    from src.telegram.message_formatter import _escape_html

    title = _escape_html(draft.article_title)
    text = (
        f"<b>{title}</b>\n"
        f"🔗 <a href=\"{draft.article_url}\">Read article</a>"
    )
    keyboard = article_keyboard(draft_id)
    bot.edit_message_text(chat_id, message_id, text, reply_markup=keyboard)


# ── Text Message Handler ─────────────────────────────────────────────


def handle_text_message(
    bot: TelegramBot,
    db: DynamoDBStorage,
    claude: ClaudeClient,
    chat_id: int,
    text: str,
) -> None:
    """Handle a plain text message — check if the user is in edit mode.

    If a draft is in 'editing' state for this chat, treat the text as
    feedback and regenerate the draft via Claude.
    """
    # Check for active edit session
    editing_draft = db.find_editing_draft(chat_id)

    if not editing_draft:
        bot.send_message(
            chat_id,
            "💡 Use /scan to trigger a new digest, or tap a button on an existing article.",
        )
        return

    # Regenerate the draft with feedback
    try:
        bot.send_message(chat_id, "🔄 Regenerating draft with your feedback...")

        previous_text = editing_draft.draft_text
        new_text = claude.regenerate_draft(editing_draft, feedback=text)

        # Update the draft in DynamoDB
        db.update_draft_text(
            draft_id=editing_draft.draft_id,
            platform=editing_draft.platform,
            new_text=new_text,
            feedback=text,
            previous_text=previous_text,
        )

        # Update the draft object for formatting
        editing_draft.draft_text = new_text
        editing_draft.state = "pending"

        # Send the revised draft with action buttons
        platform_code = "tw" if editing_draft.platform == "twitter" else "li"
        response_text = format_regenerated_draft(editing_draft)
        keyboard = after_edit_keyboard(editing_draft.draft_id, platform_code)
        bot.send_message(chat_id, response_text, reply_markup=keyboard)

    except Exception as e:
        logger.exception("Failed to regenerate draft")
        bot.send_message(
            chat_id,
            format_error_message(f"Failed to regenerate: {e}"),
        )


# ── Command Handlers ──────────────────────────────────────────────────


def handle_command(
    bot: TelegramBot,
    db: DynamoDBStorage,
    settings: Settings,
    chat_id: int,
    command: str,
) -> None:
    """Handle Telegram bot commands (/start, /help, /scan)."""
    if command in ("/start", "/help"):
        help_text = (
            "🤖 <b>Claude News Bot</b>\n\n"
            "I scan RSS feeds daily and suggest social media posts "
            "for Twitter/X and LinkedIn.\n\n"
            "<b>Commands:</b>\n"
            "/scan — Trigger a news scan now\n"
            "/help — Show this help message\n\n"
            "<b>How it works:</b>\n"
            "1. I fetch news from crypto, tech, and macro feeds\n"
            "2. Claude AI generates tweet and LinkedIn post drafts\n"
            "3. You review each draft with the buttons below\n"
            "4. Approve, edit with feedback, or skip\n\n"
            "A daily digest is sent automatically at 08:00 UTC."
        )
        bot.send_message(chat_id, help_text)

    elif command == "/scan":
        bot.send_message(chat_id, "🔍 Starting news scan... (running in background)")
        try:
            import boto3
            import os

            lambda_client = boto3.client("lambda")
            scanner_fn = os.environ.get(
                "SCANNER_FUNCTION_NAME", "claude-tg-bot-scanner-prod"
            )
            lambda_client.invoke(
                FunctionName=scanner_fn,
                InvocationType="Event",  # async — don't wait
                Payload=json.dumps(
                    {
                        "source": "telegram.scan_command",
                        "detail-type": "Scheduled Event",
                        "detail": {},
                    }
                ),
            )
            logger.info("Invoked scanner Lambda asynchronously")
        except Exception as e:
            logger.exception("Failed to invoke scanner")
            bot.send_message(chat_id, format_error_message(str(e)))


# ── Main Lambda Handler ──────────────────────────────────────────────


def lambda_handler(event: dict, context: Any) -> dict:
    """AWS Lambda entry point for Telegram webhook (via API Gateway).

    Args:
        event: API Gateway event with Telegram update in body.
        context: Lambda context (ignored).

    Returns:
        Response dict with 200 status code.
    """
    settings = load_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        # Parse the Telegram update from the request body
        body = event.get("body", "{}")
        if isinstance(body, str):
            update = json.loads(body)
        else:
            update = body

        logger.debug("Received update: %s", json.dumps(update)[:500])

        bot = TelegramBot(settings.telegram_bot_token)
        db = DynamoDBStorage(settings)
        claude = ClaudeClient(settings)

        # Handle callback queries (inline keyboard button presses)
        if "callback_query" in update:
            callback = update["callback_query"]
            callback_id = callback["id"]
            data = callback.get("data", "")
            message = callback.get("message", {})
            chat_id = message.get("chat", {}).get("id", 0)
            message_id = message.get("message_id", 0)

            logger.info("Callback query: %s from chat %s", data, chat_id)

            # Acknowledge the callback immediately
            bot.answer_callback_query(callback_id)

            # Parse callback data: action:draft_id:platform
            parts = data.split(":")
            action = parts[0] if len(parts) >= 1 else ""
            draft_id = parts[1] if len(parts) >= 2 else ""
            platform_code = parts[2] if len(parts) >= 3 else ""

            if action == "view":
                handle_view(bot, db, chat_id, message_id, draft_id, platform_code)
            elif action == "approve":
                handle_approve(bot, db, chat_id, message_id, draft_id, platform_code)
            elif action == "edit":
                handle_edit(bot, db, chat_id, message_id, draft_id, platform_code)
            elif action == "skip":
                handle_skip(bot, db, chat_id, message_id, draft_id)
            elif action == "back":
                handle_back(bot, db, chat_id, message_id, draft_id)
            else:
                logger.warning("Unknown callback action: %s", action)

        # Handle text messages
        elif "message" in update:
            message = update["message"]
            chat_id = message.get("chat", {}).get("id", 0)
            text = message.get("text", "").strip()

            if not text:
                return {"statusCode": 200, "body": "ok"}

            logger.info("Text message from chat %s: %s", chat_id, text[:100])

            # Check if it's a command
            if text.startswith("/"):
                handle_command(bot, db, settings, chat_id, text.split()[0].lower())
            else:
                handle_text_message(bot, db, claude, chat_id, text)

    except Exception:
        logger.exception("Webhook handler error")

    # Always return 200 to Telegram to prevent retries
    return {"statusCode": 200, "body": "ok"}
