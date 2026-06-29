"""
News search tool — provider routing layer.

Supported providers (set SEARCH_API_PROVIDER in .env):

  Free / no API key required:
    - duckduckgo  DuckDuckGo News — no key, no account, rate-limited by IP
                  Uses the `duckduckgo-search` package (already installed)
    - hackernews  Hacker News via Algolia API — unlimited, no key
                  https://hn.algolia.com/api
    - reddit      Reddit search via the public JSON API — no key needed
                  Searches r/worldnews + r/news by default
    - qwant       Qwant News — undocumented internal API, no key, server-side only
                  https://api.qwant.com/v3/search/news  (CORS-blocked in browsers)
    - gnews       GNews public API — 100 req/day free tier, no key needed
                  https://gnews.io  (set SEARCH_API_KEY to unlock higher limits)

  Not supported:
    - ecosia      No public API; search page is Cloudflare-protected HTML only

  Paid / registration required (SEARCH_API_KEY required):
    - newsapi     NewsAPI.org — 100 req/day free developer tier
                  https://newsapi.org
    - brave       Brave Search API — 2k req/month free tier
                  https://brave.com/search/api
    - serper      Serper.dev — Google News via API (2.5k free credits on signup)
                  https://serper.dev
    - tavily      Tavily — LLM-optimised search with news topic support
                  https://tavily.com

Note: article full-text extraction (newspaper3k / newspaper4k) is a scraping
concern, handled separately in tools/scrape.py, not a search provider.

All providers return a list of dicts with keys: title, url, snippet.
"""

import asyncio
import os
from datetime import datetime

import httpx
from duckduckgo_search import DDGS


_FREE_PROVIDERS = {"duckduckgo", "hackernews", "reddit", "qwant", "gnews"}


async def search_news(
    query: str,
    num_results: int = 5,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Search for news articles using the configured search provider.

    Args:
        query: Search query string.
        num_results: Maximum number of results to return.
        date_from: Earliest publish date (inclusive). None means no lower bound.
        date_to: Latest publish date (inclusive). None means no upper bound.

    Returns a list of dicts with keys: title, url, snippet.
    """
    provider = os.environ.get("SEARCH_API_PROVIDER", "duckduckgo").lower()
    api_key = os.environ.get("SEARCH_API_KEY", "") if provider not in _FREE_PROVIDERS else ""

    if provider not in _FREE_PROVIDERS and not api_key:
        raise EnvironmentError(
            f"SEARCH_API_KEY is required for provider {provider!r}. "
            "Use a free provider (duckduckgo, hackernews, reddit, gnews) or set SEARCH_API_KEY."
        )

    _handlers = {
        "duckduckgo": lambda: _duckduckgo_search(query, num_results, date_from, date_to),
        "hackernews": lambda: _hackernews_search(query, num_results, date_from, date_to),
        "reddit": lambda: _reddit_search(query, num_results, date_from, date_to),
        "qwant": lambda: _qwant_search(query, num_results),
        "gnews": lambda: _gnews_search(query, num_results, api_key, date_from, date_to),
        "newsapi": lambda: _newsapi_search(query, num_results, api_key, date_from, date_to),
        "brave": lambda: _brave_search(query, num_results, api_key, date_from, date_to),
        "serper": lambda: _serper_search(query, num_results, api_key, date_from, date_to),
        "tavily": lambda: _tavily_search(query, num_results, api_key, date_from, date_to),
    }
    if provider not in _handlers:
        raise ValueError(
            f"Unsupported SEARCH_API_PROVIDER: {provider!r}. "
            f"Valid options: {', '.join(_handlers)}"
        )
    return await _handlers[provider]()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _in_date_range(
    value: str | float | int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    is_timestamp: bool = False,
) -> bool:
    """Return True if *value* falls within [date_from, date_to].

    Accepts ISO-8601 strings or Unix timestamps (when is_timestamp=True).
    Returns True when value is None or both bounds are None (no filtering).
    """
    if date_from is None and date_to is None:
        return True
    if value is None:
        return True
    try:
        if is_timestamp:
            dt = datetime.utcfromtimestamp(float(value))
        else:
            dt = datetime.fromisoformat(str(value).rstrip("Z").replace("Z", ""))
    except (ValueError, TypeError):
        return True
    if date_from and dt < date_from:
        return False
    if date_to and dt > date_to:
        return False
    return True


# ---------------------------------------------------------------------------
# Free providers
# ---------------------------------------------------------------------------

async def _duckduckgo_search(
    query: str, num_results: int, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    """DuckDuckGo News — no API key required. Uses the duckduckgo-search package."""
    # DDGS.news() is synchronous; run it in a thread to avoid blocking the event loop.
    results = await asyncio.to_thread(
        lambda: list(DDGS().news(query, max_results=num_results))
    )
    return [
        {"title": r["title"], "url": r["url"], "snippet": r.get("body", "")}
        for r in results
        if _in_date_range(r.get("date"), date_from, date_to)
    ]


async def _hackernews_search(
    query: str, num_results: int, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    """Hacker News via Algolia — completely free, no key needed."""
    params: dict = {"query": query, "tags": "story", "hitsPerPage": num_results}
    if date_from:
        params["numericFilters"] = f"created_at_i>{int(date_from.timestamp())}"
        if date_to:
            params["numericFilters"] += f",created_at_i<{int(date_to.timestamp())}"
    elif date_to:
        params["numericFilters"] = f"created_at_i<{int(date_to.timestamp())}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://hn.algolia.com/api/v1/search",
            params=params,
        )
        response.raise_for_status()
        hits = response.json().get("hits", [])
        return [
            {
                "title": h.get("title", ""),
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
                "snippet": h.get("story_text") or "",
            }
            for h in hits
            if h.get("title")
        ]


async def _reddit_search(
    query: str, num_results: int, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    """Reddit public JSON search across r/worldnews and r/news — no key needed."""
    async with httpx.AsyncClient(headers={"User-Agent": "sing-sing-newsbot/1.0"}) as client:
        response = await client.get(
            "https://www.reddit.com/search.json",
            params={"q": query, "restrict_sr": False, "sort": "new", "limit": num_results, "type": "link"},
        )
        response.raise_for_status()
        posts = response.json().get("data", {}).get("children", [])
        return [
            {
                "title": p["data"]["title"],
                "url": p["data"].get("url") or f"https://reddit.com{p['data'].get('permalink', '')}",
                "snippet": p["data"].get("selftext", "")[:300],
            }
            for p in posts
            if p["data"].get("title")
            and _in_date_range(p["data"].get("created_utc"), date_from, date_to, is_timestamp=True)
        ]


async def _qwant_search(query: str, num_results: int, locale: str = "en_US") -> list[dict]:
    """Qwant News — undocumented internal v3 API, no key needed, server-side only.

    The /news endpoint bypasses Qwant's DataDome bot protection (unlike /web).
    CORS blocks browser-side requests from non-qwant.com origins; use server-side only.
    Response fields used: title, url, desc (full snippet), press_name, date (Unix ts).
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.qwant.com/v3/search/news",
            params={"q": query, "locale": locale, "count": num_results, "offset": 0},
            headers={"User-Agent": "Mozilla/5.0 (compatible; sing-sing-newsbot/1.0)"},
        )
        response.raise_for_status()
        items = response.json().get("data", {}).get("result", {}).get("items", [])
        return [
            {
                "title": r["title"],
                "url": r["url"],
                "snippet": r.get("desc") or r.get("desc_short", ""),
            }
            for r in items
            if r.get("title") and r.get("url")
        ]


async def _gnews_search(
    query: str, num_results: int, api_key: str, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    """GNews — 100 req/day free without a key; set SEARCH_API_KEY for higher limits."""
    params: dict = {"q": query, "max": num_results, "lang": "en"}
    if api_key:
        params["token"] = api_key
        # Date filtering requires an API key on GNews
        if date_from:
            params["from"] = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
        if date_to:
            params["to"] = date_to.strftime("%Y-%m-%dT%H:%M:%SZ")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://gnews.io/api/v4/search", params=params)
        response.raise_for_status()
        results = response.json().get("articles", [])
        return [
            {"title": r["title"], "url": r["url"], "snippet": r.get("description", "")}
            for r in results
            if _in_date_range(r.get("publishedAt"), date_from, date_to)
        ]


# ---------------------------------------------------------------------------
# Paid / registration-required providers
# ---------------------------------------------------------------------------

async def _newsapi_search(
    query: str, num_results: int, api_key: str, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    """NewsAPI.org — 100 req/day on the free developer tier."""
    params: dict = {"q": query, "pageSize": num_results, "sortBy": "publishedAt", "language": "en"}
    if date_from:
        params["from"] = date_from.strftime("%Y-%m-%dT%H:%M:%S")
    if date_to:
        params["to"] = date_to.strftime("%Y-%m-%dT%H:%M:%S")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://newsapi.org/v2/everything",
            params=params,
            headers={"X-Api-Key": api_key},
        )
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [
            {"title": a["title"], "url": a["url"], "snippet": a.get("description", "")}
            for a in articles
        ]


async def _brave_search(
    query: str, num_results: int, api_key: str, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    params: dict = {"q": query, "count": num_results}
    if date_from:
        params["freshness"] = date_from.strftime("%Y-%m-%d")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/news/search",
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            params=params,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return [
            {"title": r["title"], "url": r["url"], "snippet": r.get("description", "")}
            for r in results
            if _in_date_range(r.get("page_age"), date_from, date_to)
        ]


async def _serper_search(
    query: str, num_results: int, api_key: str, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    payload: dict = {"q": query, "num": num_results}
    if date_from:
        payload["tbs"] = f"cdr:1,cd_min:{date_from.strftime('%m/%d/%Y')}"
        if date_to:
            payload["tbs"] += f",cd_max:{date_to.strftime('%m/%d/%Y')}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        results = response.json().get("news", [])
        return [{"title": r["title"], "url": r["link"], "snippet": r.get("snippet", "")} for r in results]


async def _tavily_search(
    query: str, num_results: int, api_key: str, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    payload: dict = {"api_key": api_key, "query": query, "max_results": num_results, "topic": "news"}
    if date_from:
        payload["days"] = max(1, (datetime.utcnow() - date_from).days)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json=payload,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return [
            {"title": r["title"], "url": r["url"], "snippet": r.get("content", "")}
            for r in results
            if _in_date_range(r.get("published_date"), date_from, date_to)
        ]
