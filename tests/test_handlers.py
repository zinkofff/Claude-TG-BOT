"""Tests for Lambda handler webhook routing."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.handlers.telegram_webhook import lambda_handler


@patch("src.handlers.telegram_webhook.load_settings")
@patch("src.handlers.telegram_webhook.TelegramBot")
@patch("src.handlers.telegram_webhook.DynamoDBStorage")
@patch("src.handlers.telegram_webhook.ClaudeClient")
def test_webhook_handles_callback_query(
    mock_claude_cls, mock_db_cls, mock_bot_cls, mock_settings
):
    """Test that callback queries are routed correctly."""
    mock_settings.return_value = MagicMock(
        log_level="DEBUG",
        telegram_bot_token="123:ABC",
        telegram_chat_id="999",
        anthropic_api_key="test",
        claude_model="claude-haiku-4-5",
    )

    mock_bot = MagicMock()
    mock_bot_cls.return_value = mock_bot

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_draft.return_value = MagicMock(
        draft_id="abc12345",
        platform="twitter",
        draft_text="Test tweet",
        article_url="https://example.com",
        state="pending",
    )

    update = {
        "callback_query": {
            "id": "query123",
            "data": "view:abc12345:tw",
            "message": {
                "chat": {"id": 999},
                "message_id": 42,
            },
        }
    }

    event = {"body": json.dumps(update)}
    result = lambda_handler(event, None)

    assert result["statusCode"] == 200
    mock_bot.answer_callback_query.assert_called_once_with("query123")


@patch("src.handlers.telegram_webhook.load_settings")
@patch("src.handlers.telegram_webhook.TelegramBot")
@patch("src.handlers.telegram_webhook.DynamoDBStorage")
@patch("src.handlers.telegram_webhook.ClaudeClient")
def test_webhook_handles_text_with_no_edit_session(
    mock_claude_cls, mock_db_cls, mock_bot_cls, mock_settings
):
    """Test that text messages without an edit session get a helpful reply."""
    mock_settings.return_value = MagicMock(
        log_level="DEBUG",
        telegram_bot_token="123:ABC",
        telegram_chat_id="999",
        anthropic_api_key="test",
        claude_model="claude-haiku-4-5",
    )

    mock_bot = MagicMock()
    mock_bot_cls.return_value = mock_bot

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.find_editing_draft.return_value = None

    update = {
        "message": {
            "chat": {"id": 999},
            "text": "some random text",
        }
    }

    event = {"body": json.dumps(update)}
    result = lambda_handler(event, None)

    assert result["statusCode"] == 200
    # Should send a helpful message
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert "/scan" in str(call_args)


@patch("src.handlers.telegram_webhook.load_settings")
@patch("src.handlers.telegram_webhook.TelegramBot")
@patch("src.handlers.telegram_webhook.DynamoDBStorage")
@patch("src.handlers.telegram_webhook.ClaudeClient")
def test_webhook_handles_help_command(
    mock_claude_cls, mock_db_cls, mock_bot_cls, mock_settings
):
    """Test that /help command returns help text."""
    mock_settings.return_value = MagicMock(
        log_level="DEBUG",
        telegram_bot_token="123:ABC",
        telegram_chat_id="999",
        anthropic_api_key="test",
        claude_model="claude-haiku-4-5",
    )

    mock_bot = MagicMock()
    mock_bot_cls.return_value = mock_bot

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db

    update = {
        "message": {
            "chat": {"id": 999},
            "text": "/help",
        }
    }

    event = {"body": json.dumps(update)}
    result = lambda_handler(event, None)

    assert result["statusCode"] == 200
    call_args = mock_bot.send_message.call_args
    assert "Claude News Bot" in str(call_args)


@patch("src.handlers.telegram_webhook.load_settings")
@patch("src.handlers.telegram_webhook.TelegramBot")
@patch("src.handlers.telegram_webhook.DynamoDBStorage")
@patch("src.handlers.telegram_webhook.ClaudeClient")
def test_webhook_returns_200_on_error(
    mock_claude_cls, mock_db_cls, mock_bot_cls, mock_settings
):
    """Test that the webhook always returns 200 even on errors."""
    mock_settings.return_value = MagicMock(
        log_level="DEBUG",
        telegram_bot_token="123:ABC",
        telegram_chat_id="999",
        anthropic_api_key="test",
        claude_model="claude-haiku-4-5",
    )

    # Make bot construction fail
    mock_bot_cls.side_effect = Exception("Connection failed")

    event = {"body": '{"message": {"chat": {"id": 999}, "text": "hi"}}'}
    result = lambda_handler(event, None)

    # Should still return 200 to prevent Telegram retries
    assert result["statusCode"] == 200
