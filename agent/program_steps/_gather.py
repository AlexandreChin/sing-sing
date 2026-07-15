"""Specialist-source gathering for the expert-grounding program steps.

Runs the configured news search for each query concurrently, scrapes each
result's body (falling back to the snippet on failure), and returns a merged
corpus plus the flat source list. Used by steps 3 (contre-expertise), 4
(failles) and 5 (incidence). Step 1 does not gather — it reads the document."""
import asyncio

from tools.search import search_news
from tools.scrape import scrape_article


async def _one_query(query: str, per_query: int) -> list[dict]:
    try:
        return await search_news(query, num_results=per_query)
    except Exception:
        return []


async def gather_corpus(queries: list[str], per_query: int = 5) -> tuple[str, list[dict]]:
    result_lists = await asyncio.gather(*(_one_query(q, per_query) for q in queries))

    sources: list[dict] = []
    seen: set[str] = set()
    for results in result_lists:
        for r in results:
            url = r.get("url", "")
            if url and url not in seen:
                seen.add(url)
                sources.append(r)

    async def _body(src: dict) -> str:
        try:
            scraped = await scrape_article(src["url"])
            body = (scraped.get("body") or "").strip()
            if body:
                return body
        except Exception:
            pass
        return src.get("snippet", "")

    bodies = await asyncio.gather(*(_body(s) for s in sources))
    corpus = "\n\n".join(f"[{s.get('title', '')}] ({s.get('url', '')})\n{b}" for s, b in zip(sources, bodies))
    return corpus, sources
