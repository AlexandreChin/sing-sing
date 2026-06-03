"""
Claim verification tool.

Searches for sources that support or contradict a given claim by:
1. Searching news articles via search_news
2. Searching public databases (data.gouv.fr, WHO, Eurostat, PubMed)
3. Scraping each result's full text
4. Using Claude to assess each source's stance on the claim
5. Returning confirming and contradicting source lists
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Literal

import anthropic
import httpx

from models.article import Claim
from .search import search_news
from .scrape import scrape_article


SourceType = Literal["news", "public_database"]
Stance = Literal["supports", "contradicts", "neutral"]


@dataclass
class ClaimSource:
    title: str
    url: str
    snippet: str
    source_type: SourceType
    full_text: str = ""
    stance: Stance | None = None
    stance_reason: str = ""


@dataclass
class ClaimVerification:
    claim: str
    confirming: list[ClaimSource] = field(default_factory=list)
    contradicting: list[ClaimSource] = field(default_factory=list)
    neutral: list[ClaimSource] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public database search handlers
# ---------------------------------------------------------------------------

async def _search_datagouv(query: str, num_results: int) -> list[dict]:
    """data.gouv.fr dataset search — REST API, no key required."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.data.gouv.fr/api/1/datasets/",
            params={"q": query, "page_size": num_results},
        )
        response.raise_for_status()
        items = response.json().get("data", [])
        return [
            {
                "title": d.get("title", ""),
                "url": f"https://www.data.gouv.fr/fr/datasets/{d['id']}/",
                "snippet": (d.get("description") or "")[:300],
            }
            for d in items
            if d.get("title")
        ]


async def _search_who(query: str, num_results: int) -> list[dict]:
    """WHO publications search — public API, no key required."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.who.int/api/hubs/cms/api/wch/news/en/search",
            params={"q": query, "sf": "score desc", "rows": num_results},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        items = response.json().get("response", {}).get("docs", [])
        return [
            {
                "title": d.get("title", ""),
                "url": f"https://www.who.int{d['url']}" if d.get("url", "").startswith("/") else d.get("url", ""),
                "snippet": d.get("description", ""),
            }
            for d in items
            if d.get("title")
        ]


async def _search_eurostat(query: str, num_results: int) -> list[dict]:
    """Eurostat dataset search — public API, no key required."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://ec.europa.eu/eurostat/api/dissemination/catalogue/search",
            params={"query": query, "lang": "EN", "rows": num_results},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        items = response.json().get("results", [])
        return [
            {
                "title": d.get("title", ""),
                "url": f"https://ec.europa.eu/eurostat/databrowser/view/{d['code']}/default/table",
                "snippet": d.get("description", ""),
            }
            for d in items
            if d.get("title")
        ]


async def _search_pubmed(query: str, num_results: int) -> list[dict]:
    """PubMed article search — NCBI E-utilities, no key required."""
    async with httpx.AsyncClient() as client:
        # Step 1: search for IDs
        search_resp = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": num_results, "retmode": "json"},
        )
        search_resp.raise_for_status()
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        # Step 2: fetch summaries
        summary_resp = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        )
        summary_resp.raise_for_status()
        result = summary_resp.json().get("result", {})
        return [
            {
                "title": result[uid].get("title", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                "snippet": f"Authors: {', '.join(a['name'] for a in result[uid].get('authors', [])[:3])}. "
                           f"Published: {result[uid].get('pubdate', '')}.",
            }
            for uid in ids
            if uid in result and result[uid].get("title")
        ]


_PUBLIC_DB_HANDLERS = [
    _search_datagouv,
    _search_who,
    _search_eurostat,
    _search_pubmed,
]


async def _search_public_databases(query: str, num_results_per_db: int) -> list[dict]:
    """Query all registered public databases concurrently."""
    tasks = [handler(query, num_results_per_db) for handler in _PUBLIC_DB_HANDLERS]
    results_nested = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for r in results_nested:
        if isinstance(r, list):
            results.extend(r)
    return results


# ---------------------------------------------------------------------------
# Stance assessment via Claude
# ---------------------------------------------------------------------------

def _assess_stances(claim_text: str, sources: list[ClaimSource]) -> None:
    """Call Claude to assess each source's stance on the claim. Mutates sources in place."""
    if not sources:
        return

    sources_payload = [
        {"index": i, "title": s.title, "url": s.url, "text": (s.full_text or s.snippet)[:1000]}
        for i, s in enumerate(sources)
    ]

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=(
            "You are a fact-checking assistant. Given a claim and a list of sources, "
            "assess whether each source supports, contradicts, or is neutral on the claim. "
            "Reply with a JSON array of objects with keys: index (int), stance "
            "(\"supports\"|\"contradicts\"|\"neutral\"), reason (one sentence)."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Claim: {claim_text}\n\n"
                    f"Sources:\n{json.dumps(sources_payload, ensure_ascii=False, indent=2)}"
                ),
            }
        ],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    assessments = json.loads(text)
    for a in assessments:
        idx = a["index"]
        if 0 <= idx < len(sources):
            sources[idx].stance = a["stance"]
            sources[idx].stance_reason = a.get("reason", "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def find_sources_for_claim(
    claim: Claim,
    num_results: int = 5,
    num_results_per_db: int = 3,
    scrape: bool = True,
) -> ClaimVerification:
    """Search news and public databases for sources related to a claim,
    then use Claude to assess each source's stance.

    Args:
        claim: The Claim object whose .text is used as the search query.
        num_results: Number of news search results to fetch.
        num_results_per_db: Number of results to fetch per public database.
        scrape: Whether to fetch the full article body for news results.

    Returns:
        A ClaimVerification with confirming, contradicting, and neutral source lists.
    """
    # Gather news and public database results concurrently
    news_raw, db_raw = await asyncio.gather(
        search_news(claim.text, num_results=num_results),
        _search_public_databases(claim.text, num_results_per_db),
    )

    sources: list[ClaimSource] = []

    for r in news_raw:
        full_text = ""
        if scrape:
            try:
                scraped = await scrape_article(r["url"])
                full_text = scraped.get("body", "")
            except Exception:
                pass
        sources.append(ClaimSource(
            title=r["title"],
            url=r["url"],
            snippet=r["snippet"],
            source_type="news",
            full_text=full_text,
        ))

    for r in db_raw:
        sources.append(ClaimSource(
            title=r["title"],
            url=r["url"],
            snippet=r["snippet"],
            source_type="public_database",
        ))

    _assess_stances(claim.text, sources)

    verification = ClaimVerification(claim=claim.text)
    for s in sources:
        if s.stance == "supports":
            verification.confirming.append(s)
        elif s.stance == "contradicts":
            verification.contradicting.append(s)
        else:
            verification.neutral.append(s)

    return verification
