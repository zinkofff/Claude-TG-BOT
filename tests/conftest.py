"""Shared test fixtures."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import boto3
import pytest
from moto import mock_aws

from src.config.settings import Settings
from src.storage.dynamodb import DynamoDBStorage
from src.storage.models import Article, Draft


@pytest.fixture
def settings() -> Settings:
    """Test settings with mock values."""
    return Settings(
        anthropic_api_key="sk-ant-test-key",
        claude_model="claude-haiku-4-5",
        telegram_bot_token="123456:ABC-DEF",
        telegram_chat_id="999888777",
        digest_article_count=3,
        articles_table="test-articles",
        drafts_table="test-drafts",
        aws_region="us-east-1",
        log_level="DEBUG",
    )


@pytest.fixture
def dynamodb_tables():
    """Create mock DynamoDB tables using moto."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create articles table
        dynamodb.create_table(
            TableName="test-articles",
            KeySchema=[
                {"AttributeName": "article_hash", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "article_hash", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create drafts table
        dynamodb.create_table(
            TableName="test-drafts",
            KeySchema=[
                {"AttributeName": "draft_id", "KeyType": "HASH"},
                {"AttributeName": "platform", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "draft_id", "AttributeType": "S"},
                {"AttributeName": "platform", "AttributeType": "S"},
                {"AttributeName": "chat_id", "AttributeType": "N"},
                {"AttributeName": "state", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "chat-editing-index",
                    "KeySchema": [
                        {"AttributeName": "chat_id", "KeyType": "HASH"},
                        {"AttributeName": "state", "KeyType": "RANGE"},
                    ],
                    "Projection": {
                        "ProjectionType": "ALL",
                    },
                }
            ],
        )

        yield dynamodb


@pytest.fixture
def db(settings, dynamodb_tables) -> DynamoDBStorage:
    """DynamoDB storage instance with mocked tables."""
    return DynamoDBStorage(settings)


@pytest.fixture
def sample_articles() -> list[Article]:
    """Sample articles for testing."""
    now = datetime.utcnow()
    return [
        Article(
            url="https://example.com/btc-100k",
            title="Bitcoin Hits New All-Time High Above $100K",
            summary="Bitcoin has surged past $100,000 for the first time.",
            source="CoinDesk",
            category="crypto",
            published_at=now - timedelta(hours=1),
            categories=["bitcoin", "markets"],
        ),
        Article(
            url="https://example.com/eth-upgrade",
            title="Ethereum Foundation Announces Major Protocol Upgrade",
            summary="Major protocol upgrade to improve scalability.",
            source="CoinTelegraph",
            category="crypto",
            published_at=now - timedelta(hours=3),
            categories=["ethereum", "technology"],
        ),
        Article(
            url="https://example.com/blackrock-tokenisation",
            title="BlackRock Expands Tokenisation Platform",
            summary="BlackRock is expanding its tokenisation platform.",
            source="The Block",
            category="digital_assets",
            published_at=now - timedelta(hours=6),
            categories=["tokenisation", "digital assets"],
        ),
        Article(
            url="https://example.com/fed-rate",
            title="Federal Reserve Signals Rate Cut",
            summary="The Federal Reserve has signaled a potential rate cut.",
            source="CNBC",
            category="macro",
            published_at=now - timedelta(hours=12),
            categories=["macro", "federal reserve"],
        ),
        Article(
            url="https://example.com/old-news",
            title="Some Old Crypto Article",
            summary="This is very old news.",
            source="Bitcoin Magazine",
            category="crypto",
            published_at=now - timedelta(hours=36),
            categories=["crypto"],
        ),
    ]


@pytest.fixture
def sample_draft() -> Draft:
    """A sample draft for testing."""
    return Draft(
        draft_id="abc12345",
        article_hash="hash123",
        article_url="https://example.com/btc-100k",
        article_title="Bitcoin Hits New All-Time High",
        article_summary="Bitcoin has surged past $100,000.",
        platform="twitter",
        draft_text="Bitcoin just broke $100K! Institutional adoption is real. #Bitcoin #Crypto",
        state="pending",
        chat_id=999888777,
        message_id=42,
        created_at="2026-03-12T08:00:00Z",
        updated_at="2026-03-12T08:00:00Z",
    )
