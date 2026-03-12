"""Claude API client for generating social media post drafts."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import anthropic

from src.config.settings import Settings
from src.core.prompt_templates import (
    DRAFT_FROM_TOPIC_USER_PROMPT,
    GENERATE_DRAFTS_USER_PROMPT,
    REGENERATE_DRAFT_USER_PROMPT,
    SYSTEM_PROMPT,
)
from src.storage.models import Article, Draft, DraftPair

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper around the Anthropic SDK for generating post drafts."""

    def __init__(self, settings: Settings) -> None:
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    def _call_claude(
        self,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Make a call to the Claude API and return the response text."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.content[0].text

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from Claude's response, with fallback handling.

        Handles cases where Claude wraps JSON in markdown code fences.
        """
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (with optional language tag)
            lines = cleaned.split("\n")
            lines = lines[1:]  # Remove first line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove closing ```
            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Claude response as JSON: %s", e)
            logger.debug("Raw response: %s", text[:500])
            raise

    def generate_drafts(self, article: Article) -> DraftPair:
        """Generate Twitter and LinkedIn post drafts for an article.

        Args:
            article: The news article to generate posts for.

        Returns:
            DraftPair with Twitter and LinkedIn drafts.

        Raises:
            ValueError: If Claude's response cannot be parsed.
        """
        user_prompt = GENERATE_DRAFTS_USER_PROMPT.format(
            source=article.source,
            title=article.title,
            published_at=article.published_at.isoformat(),
            summary=article.summary[:800],  # Limit summary length
            url=article.url,
        )

        logger.info("Generating drafts for: %s", article.title[:80])

        # Try up to 2 times (initial + one retry)
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response_text = self._call_claude(user_prompt, temperature=0.7)
                parsed = self._parse_json_response(response_text)

                twitter_text = parsed.get("twitter", "")
                linkedin_text = parsed.get("linkedin", "")

                if not twitter_text or not linkedin_text:
                    raise ValueError("Missing 'twitter' or 'linkedin' key in response")

                # Validate Twitter length
                if len(twitter_text) > 280:
                    logger.warning(
                        "Twitter draft exceeds 280 chars (%d), will retry",
                        len(twitter_text),
                    )
                    if attempt == 0:
                        continue

                now = datetime.now(timezone.utc).isoformat()
                draft_id = uuid.uuid4().hex[:8]

                return DraftPair(
                    twitter=Draft(
                        draft_id=draft_id,
                        article_hash=article.url_hash,
                        article_url=article.url,
                        article_title=article.title,
                        article_summary=article.summary[:500],
                        platform="twitter",
                        draft_text=twitter_text,
                        created_at=now,
                        updated_at=now,
                    ),
                    linkedin=Draft(
                        draft_id=draft_id,
                        article_hash=article.url_hash,
                        article_url=article.url,
                        article_title=article.title,
                        article_summary=article.summary[:500],
                        platform="linkedin",
                        draft_text=linkedin_text,
                        created_at=now,
                        updated_at=now,
                    ),
                )

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                last_error = e
                logger.warning("Attempt %d failed: %s", attempt + 1, e)
                continue

        raise ValueError(f"Failed to generate drafts after 2 attempts: {last_error}")

    def generate_from_topic(
        self,
        user_input: str,
        extra_context: str = "",
    ) -> DraftPair:
        """Generate Twitter and LinkedIn drafts from a user-provided topic or headline.

        Args:
            user_input: A headline, topic, or URL provided by the user.
            extra_context: Optional extra context (e.g. fetched article text).

        Returns:
            DraftPair with Twitter and LinkedIn drafts.
        """
        user_prompt = DRAFT_FROM_TOPIC_USER_PROMPT.format(
            user_input=user_input,
            extra_context=extra_context,
        )

        logger.info("Generating drafts from topic: %s", user_input[:80])

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response_text = self._call_claude(user_prompt, temperature=0.7)
                parsed = self._parse_json_response(response_text)

                twitter_text = parsed.get("twitter", "")
                linkedin_text = parsed.get("linkedin", "")

                if not twitter_text or not linkedin_text:
                    raise ValueError("Missing 'twitter' or 'linkedin' key in response")

                if len(twitter_text) > 280:
                    logger.warning(
                        "Twitter draft exceeds 280 chars (%d), will retry",
                        len(twitter_text),
                    )
                    if attempt == 0:
                        continue

                now = datetime.now(timezone.utc).isoformat()
                draft_id = uuid.uuid4().hex[:8]

                return DraftPair(
                    twitter=Draft(
                        draft_id=draft_id,
                        article_hash="topic_" + draft_id,
                        article_url="",
                        article_title=user_input[:200],
                        article_summary="",
                        platform="twitter",
                        draft_text=twitter_text,
                        created_at=now,
                        updated_at=now,
                    ),
                    linkedin=Draft(
                        draft_id=draft_id,
                        article_hash="topic_" + draft_id,
                        article_url="",
                        article_title=user_input[:200],
                        article_summary="",
                        platform="linkedin",
                        draft_text=linkedin_text,
                        created_at=now,
                        updated_at=now,
                    ),
                )

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                last_error = e
                logger.warning("Attempt %d failed: %s", attempt + 1, e)
                continue

        raise ValueError(f"Failed to generate topic drafts after 2 attempts: {last_error}")

    def regenerate_draft(
        self,
        draft: Draft,
        feedback: str,
    ) -> str:
        """Regenerate a single platform draft incorporating user feedback.

        Args:
            draft: The existing draft to revise.
            feedback: The user's feedback text.

        Returns:
            The regenerated draft text.
        """
        platform_name = "Twitter/X" if draft.platform == "twitter" else "LinkedIn"

        user_prompt = REGENERATE_DRAFT_USER_PROMPT.format(
            platform=platform_name,
            source="",  # Source info stored with draft
            title=draft.article_title,
            summary=draft.article_summary,
            url=draft.article_url,
            previous_draft=draft.draft_text,
            feedback=feedback,
        )

        logger.info(
            "Regenerating %s draft for: %s", draft.platform, draft.article_title[:60]
        )

        response_text = self._call_claude(user_prompt, temperature=0.5)
        parsed = self._parse_json_response(response_text)

        # The response should have either the platform key or the platform name key
        new_text = (
            parsed.get(draft.platform)
            or parsed.get(platform_name)
            or parsed.get("twitter")
            or parsed.get("linkedin")
            or ""
        )

        if not new_text:
            raise ValueError(f"No draft text found in regeneration response: {parsed}")

        # Validate Twitter length
        if draft.platform == "twitter" and len(new_text) > 280:
            logger.warning("Regenerated Twitter draft exceeds 280 chars: %d", len(new_text))

        return new_text
