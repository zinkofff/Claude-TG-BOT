"""Thin wrapper around the Telegram Bot API using httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramBot:
    """Minimal Telegram Bot API client for Lambda-compatible usage."""

    def __init__(self, token: str) -> None:
        self.base_url = TELEGRAM_API_BASE.format(token=token)
        self._client = httpx.Client(timeout=30.0)

    def _request(self, method: str, **kwargs: Any) -> dict:
        """Make a request to the Telegram Bot API."""
        url = f"{self.base_url}/{method}"
        response = self._client.post(url, json=kwargs)
        data = response.json()

        if not data.get("ok"):
            logger.error(
                "Telegram API error: %s %s -> %s",
                method,
                kwargs,
                data.get("description", "Unknown error"),
            )
        return data

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: dict | None = None,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True,
    ) -> dict:
        """Send a text message to a chat.

        Returns the API response including the sent message.
        """
        params: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            params["reply_markup"] = reply_markup

        result = self._request("sendMessage", **params)
        return result

    def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: dict | None = None,
        parse_mode: str = "HTML",
    ) -> dict:
        """Edit the text of an existing message."""
        params: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_markup:
            params["reply_markup"] = reply_markup

        return self._request("editMessageText", **params)

    def edit_message_reply_markup(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: dict | None = None,
    ) -> dict:
        """Edit only the inline keyboard of a message."""
        params: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if reply_markup:
            params["reply_markup"] = reply_markup

        return self._request("editMessageReplyMarkup", **params)

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: str = "",
        show_alert: bool = False,
    ) -> dict:
        """Answer a callback query (acknowledge button press)."""
        return self._request(
            "answerCallbackQuery",
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert,
        )

    def set_webhook(self, url: str) -> dict:
        """Register a webhook URL with Telegram."""
        return self._request("setWebhook", url=url)

    def delete_webhook(self) -> dict:
        """Remove the current webhook."""
        return self._request("deleteWebhook")

    def get_me(self) -> dict:
        """Get basic info about the bot."""
        return self._request("getMe")
