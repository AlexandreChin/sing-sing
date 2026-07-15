import pytest
from agent.program_steps import _gather


@pytest.mark.asyncio
async def test_gather_corpus_merges_and_tolerates_failure(monkeypatch):
    async def fake_search(query, num_results=5):
        return [{"title": f"T-{query}", "url": f"https://ex/{query}", "snippet": f"snip-{query}"}]

    async def fake_scrape(url):
        if "boom" in url:
            raise RuntimeError("scrape failed")
        return {"url": url, "title": "t", "body": f"BODY::{url}"}

    monkeypatch.setattr(_gather, "search_news", fake_search)
    monkeypatch.setattr(_gather, "scrape_article", fake_scrape)

    corpus, sources = await _gather.gather_corpus(["retraites", "boom"], per_query=1)

    assert len(sources) == 2
    assert "BODY::https://ex/retraites" in corpus
    # failed scrape falls back to the snippet, does not raise
    assert "snip-boom" in corpus
