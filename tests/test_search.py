"""
Tests for tools/search.py.

Strategy:
- Unit tests mock all HTTP calls and the DDGS object so no network is needed.
- Each private provider function gets its own test with a realistic fixture
  matching the actual API response shape documented in the module.
- search_news() routing is tested via env-var patching.
- Error / edge-case paths are covered separately.
"""

import json
import re
import pytest
from unittest.mock import MagicMock, patch
from pytest_httpx import HTTPXMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.search import (
    search_news,
    _duckduckgo_search,
    _hackernews_search,
    _reddit_search,
    _qwant_search,
    _gnews_search,
    _newsapi_search,
    _brave_search,
    _serper_search,
    _tavily_search,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_result_shape(results: list[dict], min_count: int = 1) -> None:
    """Every provider must return dicts with title, url, snippet."""
    assert isinstance(results, list)
    assert len(results) >= min_count
    for r in results:
        assert "title" in r and r["title"]
        assert "url" in r and r["url"]
        assert "snippet" in r


def _hn_response(n: int = 2) -> dict:
    return {
        "hits": [
            {"title": f"HN Story {i}", "url": f"https://example.com/{i}", "objectID": str(i), "story_text": f"Snippet {i}"}
            for i in range(n)
        ]
    }


# ---------------------------------------------------------------------------
# search_news() routing
# ---------------------------------------------------------------------------

async def test_routing_unknown_provider(monkeypatch):
    monkeypatch.setenv("SEARCH_API_PROVIDER", "doesnotexist")
    monkeypatch.setenv("SEARCH_API_KEY", "key")  # prevent EnvironmentError masking ValueError
    with pytest.raises(ValueError, match="Unsupported SEARCH_API_PROVIDER"):
        await search_news("test")


async def test_routing_paid_provider_missing_key(monkeypatch):
    monkeypatch.setenv("SEARCH_API_PROVIDER", "brave")
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="SEARCH_API_KEY is required"):
        await search_news("test")


async def test_routing_free_provider_does_not_require_key(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("SEARCH_API_PROVIDER", "hackernews")
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    httpx_mock.add_response(url=re.compile(r"https://hn\.algolia\.com"), json=_hn_response(1))
    results = await search_news("test")
    _assert_result_shape(results)


async def test_routing_dispatches_to_reddit(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("SEARCH_API_PROVIDER", "reddit")
    httpx_mock.add_response(
        url=re.compile(r"https://www\.reddit\.com/search"),
        json={"data": {"children": [{"data": {"title": "T", "url": "https://example.com", "permalink": "/r/news/1", "selftext": ""}}]}},
    )
    results = await search_news("test")
    _assert_result_shape(results)


# ---------------------------------------------------------------------------
# DuckDuckGo
# ---------------------------------------------------------------------------

def _mock_ddgs(results: list[dict]):
    mock = MagicMock()
    mock.return_value.__enter__ = MagicMock(return_value=mock.return_value)
    mock.return_value.__exit__ = MagicMock(return_value=False)
    mock.return_value.news = MagicMock(return_value=results)
    return mock


async def test_duckduckgo_returns_results():
    fake = [
        {"title": "Article A", "url": "https://example.com/a", "body": "Snippet A"},
        {"title": "Article B", "url": "https://example.com/b", "body": "Snippet B"},
    ]
    with patch("tools.search.DDGS", _mock_ddgs(fake)):
        results = await _duckduckgo_search("climate", num_results=2)

    _assert_result_shape(results, min_count=2)
    assert results[0]["title"] == "Article A"
    assert results[0]["snippet"] == "Snippet A"


async def test_duckduckgo_empty_results():
    with patch("tools.search.DDGS", _mock_ddgs([])):
        results = await _duckduckgo_search("xyzzy", num_results=5)
    assert results == []


async def test_duckduckgo_missing_body_field():
    """body is optional — falls back to empty string."""
    fake = [{"title": "T", "url": "https://example.com", "source": "BBC"}]
    with patch("tools.search.DDGS", _mock_ddgs(fake)):
        results = await _duckduckgo_search("test", num_results=1)
    assert results[0]["snippet"] == ""


# ---------------------------------------------------------------------------
# Hacker News
# ---------------------------------------------------------------------------

async def test_hackernews_normal(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://hn\.algolia\.com"),
        json={
            "hits": [
                {"title": "HN Story", "url": "https://hn.com/1", "objectID": "1", "story_text": "HN snippet"},
                {"title": "HN Story 2", "url": None, "objectID": "2", "story_text": ""},
            ]
        },
    )
    results = await _hackernews_search("python", num_results=2)
    _assert_result_shape(results, min_count=2)
    # Second hit has no url — should fall back to HN permalink
    assert "news.ycombinator.com" in results[1]["url"]


async def test_hackernews_filters_titleless_hits(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://hn\.algolia\.com"),
        json={"hits": [{"title": "", "url": "https://example.com", "objectID": "1", "story_text": ""}]},
    )
    results = await _hackernews_search("test", num_results=5)
    assert results == []


async def test_hackernews_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=re.compile(r"https://hn\.algolia\.com"), status_code=503)
    with pytest.raises(Exception):
        await _hackernews_search("test", num_results=5)


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------

async def test_reddit_normal(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://www\.reddit\.com/search"),
        json={
            "data": {
                "children": [
                    {"data": {"title": "Reddit Post", "url": "https://bbc.com/article", "permalink": "/r/news/1", "selftext": "Details"}},
                    {"data": {"title": "Self Post", "url": None, "permalink": "/r/news/123", "selftext": "Body"}},
                ]
            }
        },
    )
    results = await _reddit_search("news", num_results=2)
    _assert_result_shape(results, min_count=2)
    assert results[0]["url"] == "https://bbc.com/article"
    assert "reddit.com" in results[1]["url"]


async def test_reddit_snippet_truncated(httpx_mock: HTTPXMock):
    long_text = "x" * 500
    httpx_mock.add_response(
        url=re.compile(r"https://www\.reddit\.com/search"),
        json={"data": {"children": [{"data": {"title": "T", "url": "https://example.com", "permalink": "/r/news/1", "selftext": long_text}}]}},
    )
    results = await _reddit_search("test", num_results=1)
    assert len(results[0]["snippet"]) <= 300


async def test_reddit_filters_titleless_posts(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://www\.reddit\.com/search"),
        json={"data": {"children": [{"data": {"title": "", "url": "https://example.com", "permalink": "/r/news/1", "selftext": ""}}]}},
    )
    results = await _reddit_search("test", num_results=5)
    assert results == []


# ---------------------------------------------------------------------------
# Qwant
# ---------------------------------------------------------------------------

async def test_qwant_normal(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://api\.qwant\.com"),
        json={
            "status": "success",
            "data": {
                "result": {
                    "items": [
                        {"title": "Qwant Article", "url": "https://lemonde.fr/1", "desc": "Full snippet", "desc_short": "Short"},
                        {"title": "Qwant Article 2", "url": "https://lemonde.fr/2", "desc": "", "desc_short": "Fallback"},
                    ]
                }
            },
        },
    )
    results = await _qwant_search("technology", num_results=2)
    _assert_result_shape(results, min_count=2)
    assert results[0]["snippet"] == "Full snippet"
    # desc is empty → should fall back to desc_short
    assert results[1]["snippet"] == "Fallback"


async def test_qwant_filters_items_missing_title_or_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://api\.qwant\.com"),
        json={
            "status": "success",
            "data": {
                "result": {
                    "items": [
                        {"title": "", "url": "https://example.com", "desc": "x"},
                        {"title": "T", "url": "", "desc": "x"},
                        {"title": "Good", "url": "https://example.com/good", "desc": "snippet"},
                    ]
                }
            },
        },
    )
    results = await _qwant_search("test", num_results=5)
    assert len(results) == 1
    assert results[0]["title"] == "Good"


async def test_qwant_empty_result_set(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://api\.qwant\.com"),
        json={"status": "success", "data": {"result": {"items": []}}},
    )
    results = await _qwant_search("xyzzy", num_results=5)
    assert results == []


# ---------------------------------------------------------------------------
# GNews
# ---------------------------------------------------------------------------

async def test_gnews_without_key(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://gnews\.io"),
        json={"articles": [{"title": "GNews Article", "url": "https://gnews.io/1", "description": "Desc"}]},
    )
    results = await _gnews_search("AI", num_results=1, api_key="")
    _assert_result_shape(results)
    request = httpx_mock.get_requests()[0]
    assert "token" not in str(request.url)


async def test_gnews_with_key_adds_token_param(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://gnews\.io"),
        json={"articles": [{"title": "T", "url": "https://gnews.io/1", "description": "D"}]},
    )
    await _gnews_search("AI", num_results=1, api_key="mykey")
    request = httpx_mock.get_requests()[0]
    assert "token=mykey" in str(request.url)


# ---------------------------------------------------------------------------
# NewsAPI
# ---------------------------------------------------------------------------

async def test_newsapi_normal(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://newsapi\.org"),
        json={"articles": [{"title": "NewsAPI Article", "url": "https://bbc.com/1", "description": "Desc"}]},
    )
    results = await _newsapi_search("climate", num_results=1, api_key="key123")
    _assert_result_shape(results)


async def test_newsapi_sends_api_key_header(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=re.compile(r"https://newsapi\.org"), json={"articles": []})
    await _newsapi_search("test", num_results=1, api_key="secret")
    request = httpx_mock.get_requests()[0]
    assert request.headers.get("x-api-key") == "secret"


# ---------------------------------------------------------------------------
# Brave
# ---------------------------------------------------------------------------

async def test_brave_normal(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://api\.search\.brave\.com"),
        json={"results": [{"title": "Brave Article", "url": "https://example.com/1", "description": "Desc"}]},
    )
    results = await _brave_search("tech", num_results=1, api_key="bravekey")
    _assert_result_shape(results)


async def test_brave_sends_auth_header(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=re.compile(r"https://api\.search\.brave\.com"), json={"results": []})
    await _brave_search("test", num_results=1, api_key="mybravekey")
    request = httpx_mock.get_requests()[0]
    assert request.headers.get("x-subscription-token") == "mybravekey"


# ---------------------------------------------------------------------------
# Serper
# ---------------------------------------------------------------------------

async def test_serper_normal(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://google\.serper\.dev"),
        json={"news": [{"title": "Serper Article", "link": "https://example.com/1", "snippet": "Snip"}]},
    )
    results = await _serper_search("finance", num_results=1, api_key="serperkey")
    _assert_result_shape(results)
    # 'link' field must be mapped to 'url'
    assert results[0]["url"] == "https://example.com/1"


async def test_serper_sends_api_key_header(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=re.compile(r"https://google\.serper\.dev"), json={"news": []})
    await _serper_search("test", num_results=1, api_key="myserperkey")
    request = httpx_mock.get_requests()[0]
    assert request.headers.get("x-api-key") == "myserperkey"


# ---------------------------------------------------------------------------
# Tavily
# ---------------------------------------------------------------------------

async def test_tavily_normal(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://api\.tavily\.com"),
        json={"results": [{"title": "Tavily Article", "url": "https://example.com/1", "content": "Content"}]},
    )
    results = await _tavily_search("AI", num_results=1, api_key="tavilykey")
    _assert_result_shape(results)
    assert results[0]["snippet"] == "Content"


async def test_tavily_sends_key_in_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=re.compile(r"https://api\.tavily\.com"), json={"results": []})
    await _tavily_search("test", num_results=1, api_key="secret")
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["api_key"] == "secret"
    assert body["topic"] == "news"
