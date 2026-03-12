"""Tests for Telegram bot and keyboards."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from src.telegram.bot import TelegramBot
from src.telegram.keyboards import (
    after_approve_keyboard,
    after_edit_keyboard,
    article_keyboard,
    draft_view_keyboard,
)
from src.telegram.message_formatter import (
    format_approved_message,
    format_article_card,
    format_digest_header,
    format_draft_view,
    format_edit_prompt,
    format_skip_message,
)


# ── Keyboard Tests ────────────────────────────────────────────────────


def test_article_keyboard_has_correct_structure():
    """Test that the article keyboard has all expected buttons."""
    kb = article_keyboard("abc12345")
    rows = kb["inline_keyboard"]

    assert len(rows) == 4

    # Row 1: View buttons
    assert rows[0][0]["callback_data"] == "view:abc12345:tw"
    assert rows[0][1]["callback_data"] == "view:abc12345:li"

    # Row 2: Approve buttons
    assert rows[1][0]["callback_data"] == "approve:abc12345:tw"
    assert rows[1][1]["callback_data"] == "approve:abc12345:li"

    # Row 3: Edit buttons
    assert rows[2][0]["callback_data"] == "edit:abc12345:tw"
    assert rows[2][1]["callback_data"] == "edit:abc12345:li"

    # Row 4: Skip
    assert rows[3][0]["callback_data"] == "skip:abc12345"


def test_callback_data_fits_in_64_bytes():
    """Test that all callback data strings fit in Telegram's 64-byte limit."""
    draft_id = "a" * 8  # Max 8 chars
    kb = article_keyboard(draft_id)

    for row in kb["inline_keyboard"]:
        for button in row:
            data = button["callback_data"]
            assert len(data.encode("utf-8")) <= 64, f"Callback data too long: {data}"


def test_draft_view_keyboard_shows_platform():
    """Test platform-specific view keyboard."""
    kb = draft_view_keyboard("abc12345", "tw")
    rows = kb["inline_keyboard"]

    assert "Approve Twitter" in rows[0][0]["text"]
    assert "back:abc12345" in rows[1][0]["callback_data"]


def test_after_approve_keyboard_shows_other_platform():
    """Test that after approving Twitter, LinkedIn is shown."""
    kb = after_approve_keyboard("abc12345", "tw")
    rows = kb["inline_keyboard"]

    assert "LinkedIn" in rows[0][0]["text"]
    assert ":li" in rows[0][0]["callback_data"]


# ── Message Formatter Tests ───────────────────────────────────────────


def test_format_digest_header():
    """Test digest header formatting."""
    header = format_digest_header(5, 10)
    assert "Daily News Digest" in header
    assert "5" in header
    assert "10" in header


def test_format_article_card(sample_articles):
    """Test article card formatting."""
    card = format_article_card(sample_articles[0], 1, 5)
    assert "1/5" in card
    assert "Bitcoin" in card
    assert "CoinDesk" in card
    assert "Read article" in card


def test_format_draft_view_twitter(sample_draft):
    """Test Twitter draft view formatting."""
    text = format_draft_view(sample_draft)
    assert "Twitter" in text
    assert "/280" in text
    assert sample_draft.article_url in text


def test_format_draft_view_linkedin(sample_draft):
    """Test LinkedIn draft view formatting."""
    sample_draft.platform = "linkedin"
    sample_draft.draft_text = "This is a longer LinkedIn post about Bitcoin reaching new heights."
    text = format_draft_view(sample_draft)
    assert "LinkedIn" in text
    assert "words" in text


def test_format_approved_message(sample_draft):
    """Test approved message includes copy-friendly text."""
    msg = format_approved_message(sample_draft)
    assert "APPROVED" in msg
    assert "Copy the text above" in msg


def test_format_edit_prompt(sample_draft):
    """Test edit prompt asks for feedback."""
    msg = format_edit_prompt(sample_draft)
    assert "feedback" in msg.lower()
    assert sample_draft.draft_text in msg


# ── Telegram Bot API Tests ────────────────────────────────────────────


def test_bot_send_message():
    """Test that send_message calls the correct API endpoint."""
    token = "123:ABC"

    # Mock httpx.Client.post
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": {"message_id": 42}}

    with patch("src.telegram.bot.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        bot = TelegramBot(token)
        result = bot.send_message(999, "Hello!")

    assert result["ok"] is True
    assert result["result"]["message_id"] == 42

    # Verify the request was made to the correct URL
    call_args = mock_client.post.call_args
    assert f"/bot{token}/sendMessage" in call_args[0][0]
    assert call_args[1]["json"]["chat_id"] == 999
    assert call_args[1]["json"]["text"] == "Hello!"


def test_bot_answer_callback_query():
    """Test callback query acknowledgment."""
    token = "123:ABC"

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}

    with patch("src.telegram.bot.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        bot = TelegramBot(token)
        result = bot.answer_callback_query("query_id_123")

    assert result["ok"] is True
