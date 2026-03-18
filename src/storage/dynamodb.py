"""DynamoDB storage layer for articles and drafts."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key

from src.config.settings import Settings
from src.storage.models import Article, Draft

logger = logging.getLogger(__name__)

# Articles are kept for 30 days before TTL cleanup
ARTICLE_TTL_DAYS = 30


class DynamoDBStorage:
    """DynamoDB access layer for articles and drafts tables."""

    def __init__(self, settings: Settings) -> None:
        kwargs: dict[str, Any] = {"region_name": settings.aws_region}
        if settings.dynamodb_endpoint_url:
            kwargs["endpoint_url"] = settings.dynamodb_endpoint_url

        self.dynamodb = boto3.resource("dynamodb", **kwargs)
        self.articles_table = self.dynamodb.Table(settings.articles_table)
        self.drafts_table = self.dynamodb.Table(settings.drafts_table)

    # ── Articles ──────────────────────────────────────────────────────

    def get_seen_article_hashes(self, url_hashes: list[str]) -> set[str]:
        """Check which article URL hashes already exist in the database.

        Args:
            url_hashes: List of SHA-256 hashes to check.

        Returns:
            Set of hashes that are already in the database.
        """
        seen: set[str] = set()

        # DynamoDB BatchGetItem supports max 100 items per request
        for i in range(0, len(url_hashes), 100):
            batch = url_hashes[i : i + 100]
            keys = [{"article_hash": h} for h in batch]

            response = self.dynamodb.batch_get_item(
                RequestItems={
                    self.articles_table.name: {
                        "Keys": keys,
                        "ProjectionExpression": "article_hash",
                    }
                }
            )

            for item in response.get("Responses", {}).get(self.articles_table.name, []):
                seen.add(item["article_hash"])

        return seen

    def get_seen_title_hashes(self, title_hashes: list[str]) -> set[str]:
        """Check which title hashes already exist.

        Uses a scan with filter (not ideal for large tables, but with 30-day TTL
        and ~5 articles/day, the table stays small).
        """
        seen: set[str] = set()

        # Only check if we have hashes to check
        if not title_hashes:
            return seen

        title_hash_set = set(title_hashes)

        # Scan the table for matching title hashes
        response = self.articles_table.scan(
            ProjectionExpression="title_hash",
            FilterExpression=Attr("title_hash").exists(),
        )

        for item in response.get("Items", []):
            th = item.get("title_hash", "")
            if th in title_hash_set:
                seen.add(th)

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = self.articles_table.scan(
                ProjectionExpression="title_hash",
                FilterExpression=Attr("title_hash").exists(),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                th = item.get("title_hash", "")
                if th in title_hash_set:
                    seen.add(th)

        return seen

    def put_seen_article(self, article: Article) -> None:
        """Store an article as seen in the database."""
        now = datetime.now(timezone.utc)
        ttl = int(time.time()) + (ARTICLE_TTL_DAYS * 86400)

        self.articles_table.put_item(
            Item={
                "article_hash": article.url_hash,
                "url": article.url,
                "title": article.title,
                "title_hash": article.title_hash,
                "source": article.source,
                "published_at": article.published_at.isoformat(),
                "processed_at": now.isoformat(),
                "expires_at": ttl,
            }
        )

    # ── Drafts ────────────────────────────────────────────────────────

    def put_draft(self, draft: Draft) -> None:
        """Store a draft in the database."""
        item: dict[str, Any] = {
            "draft_id": draft.draft_id,
            "platform": draft.platform,
            "article_hash": draft.article_hash,
            "article_url": draft.article_url,
            "article_title": draft.article_title,
            "article_summary": draft.article_summary,
            "draft_text": draft.draft_text,
            "state": draft.state,
            "chat_id": draft.chat_id,
            "message_id": draft.message_id,
            "feedback_history": draft.feedback_history,
            "created_at": draft.created_at,
            "updated_at": draft.updated_at,
        }
        self.drafts_table.put_item(Item=item)

    def get_draft(self, draft_id: str, platform: str) -> Draft | None:
        """Retrieve a draft by ID and platform."""
        response = self.drafts_table.get_item(
            Key={"draft_id": draft_id, "platform": platform}
        )
        item = response.get("Item")
        if not item:
            return None
        return self._item_to_draft(item)

    def update_draft_state(
        self,
        draft_id: str,
        platform: str,
        state: str,
        **extra_attrs: Any,
    ) -> None:
        """Update the state of a draft and any extra attributes."""
        update_expr_parts = ["#s = :state", "updated_at = :now"]
        expr_values: dict[str, Any] = {
            ":state": state,
            ":now": datetime.now(timezone.utc).isoformat(),
        }
        expr_names = {"#s": "state"}

        for key, value in extra_attrs.items():
            safe_key = f"#{key}" if key in ("state", "source", "name") else key
            if safe_key.startswith("#"):
                expr_names[safe_key] = key
            update_expr_parts.append(f"{safe_key} = :{key}")
            expr_values[f":{key}"] = value

        self.drafts_table.update_item(
            Key={"draft_id": draft_id, "platform": platform},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names if expr_names else None,
        )

    def update_draft_text(
        self,
        draft_id: str,
        platform: str,
        new_text: str,
        feedback: str,
        previous_text: str,
    ) -> None:
        """Update draft text after a re-draft, preserving feedback history."""
        now = datetime.now(timezone.utc).isoformat()

        # Get current draft to append to feedback history
        current = self.get_draft(draft_id, platform)
        history = current.feedback_history if current else []
        history.append(
            {
                "feedback": feedback,
                "previous_draft": previous_text,
                "timestamp": now,
            }
        )

        self.drafts_table.update_item(
            Key={"draft_id": draft_id, "platform": platform},
            UpdateExpression=(
                "SET draft_text = :text, #s = :state, "
                "feedback_history = :history, updated_at = :now"
            ),
            ExpressionAttributeValues={
                ":text": new_text,
                ":state": "pending",
                ":history": history,
                ":now": now,
            },
            ExpressionAttributeNames={"#s": "state"},
        )

    def find_editing_draft(self, chat_id: int) -> Draft | None:
        """Find the draft currently in 'editing' state for a chat.

        Uses the GSI on chat_id + state.
        """
        try:
            response = self.drafts_table.query(
                IndexName="chat-editing-index",
                KeyConditionExpression=(
                    Key("chat_id").eq(chat_id) & Key("state").eq("editing")
                ),
                Limit=1,
            )
        except Exception:
            # Fallback: scan if GSI not available (local dev)
            logger.warning("GSI query failed, falling back to scan")
            response = self.drafts_table.scan(
                FilterExpression=(
                    Attr("chat_id").eq(chat_id) & Attr("state").eq("editing")
                ),
            )
            items = response.get("Items", [])
            if items:
                return self._item_to_draft(items[0])
            # Paginate through all items if needed
            while "LastEvaluatedKey" in response:
                response = self.drafts_table.scan(
                    FilterExpression=(
                        Attr("chat_id").eq(chat_id) & Attr("state").eq("editing")
                    ),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items = response.get("Items", [])
                if items:
                    return self._item_to_draft(items[0])
            return None

        items = response.get("Items", [])
        if not items:
            return None
        return self._item_to_draft(items[0])

    def _item_to_draft(self, item: dict[str, Any]) -> Draft:
        """Convert a DynamoDB item to a Draft object."""
        return Draft(
            draft_id=item["draft_id"],
            article_hash=item.get("article_hash", ""),
            article_url=item.get("article_url", ""),
            article_title=item.get("article_title", ""),
            article_summary=item.get("article_summary", ""),
            platform=item["platform"],
            draft_text=item.get("draft_text", ""),
            state=item.get("state", "pending"),
            chat_id=int(item.get("chat_id", 0)),
            message_id=int(item.get("message_id", 0)),
            feedback_history=item.get("feedback_history", []),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )
