"""Message formatting for Telegram bot responses."""

from __future__ import annotations

from datetime import datetime, timezone

from src.storage.models import Article, Draft


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram's HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_digest_header(article_count: int, feed_count: int) -> str:
    """Format the digest header message."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return (
        f"📰 <b>Daily News Digest — {today}</b>\n"
        f"Found <b>{article_count}</b> top articles across {feed_count} feeds\n"
        f"{'─' * 30}"
    )


def format_article_card(
    article: Article,
    index: int,
    total: int,
) -> str:
    """Format a single article card for the digest.

    Args:
        article: The article to format.
        index: 1-based index in the digest.
        total: Total number of articles in the digest.

    Returns:
        Formatted HTML string for Telegram.
    """
    title = _escape_html(article.title)
    source = _escape_html(article.source)

    # Calculate relative time
    age = article.age_hours
    if age < 1:
        age_str = f"{int(age * 60)}m ago"
    elif age < 24:
        age_str = f"{int(age)}h ago"
    else:
        age_str = f"{int(age / 24)}d ago"

    # Truncate summary
    summary = _escape_html(article.summary[:200])
    if len(article.summary) > 200:
        summary += "..."

    return (
        f"<b>{index}/{total}: {title}</b>\n"
        f"🔗 <a href=\"{article.url}\">Read article</a> | "
        f"📡 {source} | ⏱ {age_str}\n\n"
        f"{summary}"
    )


def format_twitter_draft(draft: Draft) -> str:
    """Format a Twitter draft for display in Telegram."""
    text = _escape_html(draft.draft_text)
    char_count = len(draft.draft_text)
    status = "✅" if char_count <= 280 else "⚠️"

    return (
        f"<b>📱 Twitter/X Draft</b> {status} ({char_count}/280 chars)\n"
        f"{'─' * 25}\n\n"
        f"{text}\n\n"
        f"{'─' * 25}\n"
        f"🔗 {draft.article_url}"
    )


def format_linkedin_draft(draft: Draft) -> str:
    """Format a LinkedIn draft for display in Telegram."""
    text = _escape_html(draft.draft_text)
    word_count = len(draft.draft_text.split())

    return (
        f"<b>💼 LinkedIn Draft</b> ({word_count} words)\n"
        f"{'─' * 25}\n\n"
        f"{text}\n\n"
        f"{'─' * 25}\n"
        f"🔗 {draft.article_url}"
    )


def format_draft_view(draft: Draft) -> str:
    """Format a draft for viewing based on its platform."""
    if draft.platform == "twitter":
        return format_twitter_draft(draft)
    return format_linkedin_draft(draft)


def format_approved_message(draft: Draft) -> str:
    """Format the confirmation message after approving a draft."""
    platform = "Twitter/X" if draft.platform == "twitter" else "LinkedIn"
    text = _escape_html(draft.draft_text)

    return (
        f"✅ <b>{platform} draft APPROVED</b>\n\n"
        f"<code>{text}</code>\n\n"
        f"🔗 {draft.article_url}\n\n"
        f"<i>Copy the text above and post it when ready!</i>"
    )


def format_edit_prompt(draft: Draft) -> str:
    """Format the message asking the user for edit feedback."""
    platform = "Twitter/X" if draft.platform == "twitter" else "LinkedIn"

    return (
        f"✏️ <b>Editing {platform} draft</b>\n\n"
        f"Current draft:\n"
        f"<code>{_escape_html(draft.draft_text)}</code>\n\n"
        f"Send me your feedback — what would you like changed?"
    )


def format_skip_message() -> str:
    """Format the message after skipping an article."""
    return "⏭️ <i>Article skipped</i>"


def format_regenerated_draft(draft: Draft) -> str:
    """Format a regenerated draft after user feedback."""
    platform = "Twitter/X" if draft.platform == "twitter" else "LinkedIn"

    return (
        f"✏️ <b>Revised {platform} Draft</b>\n\n"
        f"{format_draft_view(draft)}"
    )


def format_no_articles_message() -> str:
    """Format the message when no new articles are found."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return (
        f"📰 <b>Daily News Digest — {today}</b>\n\n"
        f"No new articles found today. All feeds returned previously seen content.\n"
        f"Try again later or check back tomorrow!"
    )


def format_error_message(error: str) -> str:
    """Format an error message for the user."""
    return (
        f"⚠️ <b>Something went wrong</b>\n\n"
        f"<code>{_escape_html(error)}</code>\n\n"
        f"Please try again or use /scan to trigger a new digest."
    )
