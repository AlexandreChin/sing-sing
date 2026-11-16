"""Checks the sources named in the clues of a `trois_regards` deck against the web, once the author has picked them.

Each card of the tensions grid ends on a clue, « source | ce qu'on y lit » (`indiceN`):
the source is the model's general knowledge, not the article's. After a pick on `tensions`,
each named source becomes a one-sentence claim, searched with the repo's claim verifier (`tools/verify.py`: news and
public databases, a stance per source). A source with no supporting result, or one a result contradicts, comes back as
a ⚠ naming the field to fix — advisory, the author has the last word. The result is kept beside the step
(`<n>_<step>.verification.json`, outside the stamp) and in the choice log; no slide shows it.

The search is built for news: it may miss well-known institutions, so « no source found » means exactly that.
"""
import asyncio
import json
from pathlib import Path
from typing import Awaitable, Callable


def points(fields_by_slot: dict[str, dict]) -> list[tuple[str, str, str, str]]:
    """(slot, field, topic, source) of each clue of the picked tensions, the source being the part of `indiceN`
    before « | » (a clue with no source is skipped); the topic is the card's `topicN`, the claim's context."""
    out = []
    for slot, fields in fields_by_slot.items():
        for k in (1, 2, 3):
            source = str(fields.get(f"indice{k}", "")).split("|", 1)[0].strip()
            if source:
                out.append((slot, f"indice{k}", str(fields.get(f"topic{k}", "")).strip() or slot, source))
    return out


def claim_text(topic: str, source: str, subject: str) -> str:
    """One sentence a search can test: the source publishes reference material on the subject."""
    return f"{source} publie des séries ou des études de référence sur {subject} ({topic})"


async def _search(text: str):
    from models.article import Claim
    from tools.verify import find_sources_for_claim
    return await find_sources_for_claim(Claim(text=text), num_results=4, num_results_per_db=0, scrape=False)


async def verify_sources(pts: list[tuple[str, str, str]], subject: str,
                         search: Callable[[str], Awaitable] | None = None) -> list[dict]:
    """One result per source: {slot, field, source, claim, status: confirmed | unconfirmed | contradicted | unavailable,
    source_ref, reason}. A search that fails (no key, no network, provider down) is `unavailable`, never an error."""
    search = search or _search

    async def one(slot: str, field: str, topic: str, source: str) -> dict:
        text = claim_text(topic, source, subject)
        base = {"slot": slot, "field": field, "source": source, "claim": text}
        try:
            found = await search(text)
        except Exception as exc:
            return {**base, "status": "unavailable", "source_ref": None, "reason": str(exc)[:120]}
        for status, hits in (("contradicted", found.contradicting), ("confirmed", found.confirming)):
            if hits:
                s = hits[0]
                return {**base, "status": status, "source_ref": {"title": s.title, "url": s.url},
                        "reason": s.stance_reason}
        return {**base, "status": "unconfirmed", "source_ref": None, "reason": "no supporting result found"}

    return list(await asyncio.gather(*(one(*p) for p in pts)))


def warnings(step: str, results: list[dict]) -> list[str]:
    """The ⚠ lines for the author: what is not confirmed, what is contradicted, a search that could not run."""
    out = []
    for r in results:
        where = f"{step}.{r['field']}"          # the field as `fix` names it: « tensions.indice1 »
        if r["status"] == "unconfirmed":
            out.append(f"{where}: no result found for « {r['source']} » — the search is built for news and may miss "
                       "well-known institutions: check it before keeping it")
        elif r["status"] == "contradicted":
            ref = r["source_ref"]
            out.append(f"{where}: a result contradicts « {r['claim']} » — {r['reason']} ({ref['url']})")
        elif r["status"] == "unavailable":
            out.append(f"{where}: « {r['source']} » could not be checked ({r['reason']})")
    return out


def save(steps_dir: Path, step_n: int, step: str, results: list[dict]) -> Path:
    path = steps_dir / f"{step_n}_{step}.verification.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
