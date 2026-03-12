"""Tests for Claude API client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.core.claude_client import ClaudeClient
from src.storage.models import Article, Draft


@pytest.fixture
def mock_claude_response():
    """Create a mock Claude API response."""
    def _make_response(text: str):
        response = MagicMock()
        content_block = MagicMock()
        content_block.text = text
        response.content = [content_block]
        return response
    return _make_response


@pytest.fixture
def claude_client(settings):
    """Claude client with mocked Anthropic SDK."""
    with patch("src.core.claude_client.anthropic.Anthropic") as mock_anthropic:
        client = ClaudeClient(settings)
        yield client, mock_anthropic.return_value


def test_generate_drafts_parses_json_response(claude_client, sample_articles, mock_claude_response):
    """Test that generate_drafts correctly parses Claude's JSON response."""
    client, mock_api = claude_client
    article = sample_articles[0]

    response_json = json.dumps({
        "twitter": "BTC just hit $100K! #Bitcoin #Crypto",
        "linkedin": "Bitcoin has reached a historic milestone, crossing $100,000 for the first time. This signals growing institutional adoption. #Bitcoin #Crypto",
    })

    mock_api.messages.create.return_value = mock_claude_response(response_json)

    result = client.generate_drafts(article)

    assert result.twitter.platform == "twitter"
    assert result.linkedin.platform == "linkedin"
    assert "BTC" in result.twitter.draft_text
    assert "Bitcoin" in result.linkedin.draft_text
    assert result.twitter.article_url == article.url
    assert result.linkedin.article_url == article.url


def test_generate_drafts_handles_code_fenced_json(claude_client, sample_articles, mock_claude_response):
    """Test that generate_drafts strips markdown code fences."""
    client, mock_api = claude_client
    article = sample_articles[0]

    response_text = '```json\n{"twitter": "Test tweet", "linkedin": "Test post"}\n```'
    mock_api.messages.create.return_value = mock_claude_response(response_text)

    result = client.generate_drafts(article)
    assert result.twitter.draft_text == "Test tweet"


def test_generate_drafts_retries_on_invalid_json(claude_client, sample_articles, mock_claude_response):
    """Test that generate_drafts retries when JSON parsing fails."""
    client, mock_api = claude_client
    article = sample_articles[0]

    # First call returns invalid JSON, second returns valid
    mock_api.messages.create.side_effect = [
        mock_claude_response("not json at all"),
        mock_claude_response('{"twitter": "Retry tweet", "linkedin": "Retry post"}'),
    ]

    result = client.generate_drafts(article)
    assert result.twitter.draft_text == "Retry tweet"
    assert mock_api.messages.create.call_count == 2


def test_regenerate_draft_sends_feedback(claude_client, sample_draft, mock_claude_response):
    """Test that regenerate_draft incorporates feedback."""
    client, mock_api = claude_client

    mock_api.messages.create.return_value = mock_claude_response(
        '{"twitter": "Updated tweet with feedback"}'
    )

    new_text = client.regenerate_draft(sample_draft, feedback="Make it more casual")

    assert new_text == "Updated tweet with feedback"

    # Verify the prompt included the feedback
    call_args = mock_api.messages.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    prompt = messages[0]["content"]
    assert "Make it more casual" in prompt
