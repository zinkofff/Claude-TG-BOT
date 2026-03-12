"""Inline keyboard builders for Telegram bot interactions."""

from __future__ import annotations


def _button(text: str, callback_data: str) -> dict:
    """Create a single inline keyboard button."""
    return {"text": text, "callback_data": callback_data}


def article_keyboard(draft_id: str) -> dict:
    """Build the main inline keyboard for an article in the digest.

    Shows view, approve, edit, and skip buttons for both platforms.

    Args:
        draft_id: The 8-char draft ID.

    Returns:
        InlineKeyboardMarkup dict.
    """
    return {
        "inline_keyboard": [
            # Row 1: View drafts
            [
                _button("📱 View Twitter", f"view:{draft_id}:tw"),
                _button("💼 View LinkedIn", f"view:{draft_id}:li"),
            ],
            # Row 2: Approve
            [
                _button("✅ Approve TW", f"approve:{draft_id}:tw"),
                _button("✅ Approve LI", f"approve:{draft_id}:li"),
            ],
            # Row 3: Edit
            [
                _button("✏️ Edit TW", f"edit:{draft_id}:tw"),
                _button("✏️ Edit LI", f"edit:{draft_id}:li"),
            ],
            # Row 4: Skip
            [
                _button("⏭️ Skip Article", f"skip:{draft_id}"),
            ],
        ]
    }


def draft_view_keyboard(draft_id: str, platform: str) -> dict:
    """Keyboard shown when viewing a specific draft.

    Args:
        draft_id: The 8-char draft ID.
        platform: "tw" or "li".

    Returns:
        InlineKeyboardMarkup dict.
    """
    platform_label = "Twitter" if platform == "tw" else "LinkedIn"
    return {
        "inline_keyboard": [
            [
                _button(f"✅ Approve {platform_label}", f"approve:{draft_id}:{platform}"),
                _button(f"✏️ Edit {platform_label}", f"edit:{draft_id}:{platform}"),
            ],
            [
                _button("⬅️ Back", f"back:{draft_id}"),
            ],
        ]
    }


def after_approve_keyboard(draft_id: str, approved_platform: str) -> dict:
    """Keyboard shown after approving one platform's draft.

    Shows the option to view/approve the other platform.

    Args:
        draft_id: The 8-char draft ID.
        approved_platform: The platform that was just approved ("tw" or "li").

    Returns:
        InlineKeyboardMarkup dict.
    """
    other = "li" if approved_platform == "tw" else "tw"
    other_label = "LinkedIn" if other == "li" else "Twitter"

    return {
        "inline_keyboard": [
            [
                _button(f"📱 View {other_label}", f"view:{draft_id}:{other}"),
                _button(f"✅ Approve {other_label}", f"approve:{draft_id}:{other}"),
            ],
        ]
    }


def after_edit_keyboard(draft_id: str, platform: str) -> dict:
    """Keyboard shown after receiving a re-drafted post.

    Args:
        draft_id: The 8-char draft ID.
        platform: "tw" or "li".

    Returns:
        InlineKeyboardMarkup dict.
    """
    platform_label = "Twitter" if platform == "tw" else "LinkedIn"
    return {
        "inline_keyboard": [
            [
                _button(f"✅ Approve {platform_label}", f"approve:{draft_id}:{platform}"),
                _button(f"✏️ Edit Again", f"edit:{draft_id}:{platform}"),
            ],
            [
                _button("⬅️ Back", f"back:{draft_id}"),
            ],
        ]
    }
