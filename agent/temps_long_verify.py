"""Checks the reference points of a `temps_long` timeline against the web, once the author has picked them.

The episodes and the texts are the model's general knowledge, not the article's: a date, a law, an event it may recall
wrongly. After a pick on `tournants` or `episodes`, each point becomes a one-sentence claim, searched with the repo's
claim verifier (`tools/verify.py`: news and public databases, a stance per source). A point with no supporting source,
or one a source contradicts, comes back as a ⚠ — advisory, the author has the last word. The result is kept beside the
step (`<n>_<step>.verification.json`, outside the stamp) and in the choice log; no slide shows it.

The search is built for news: it finds events well and laws less reliably, so « no source found » means exactly that.
"""
import asyncio
import json
from pathlib import Path
from typing import Awaitable, Callable

VERIFIED_STEPS = ("tournants", "episodes")
_REPERES = ("rep1", "rep2", "rep3", "rep4", "rep5")


def points(fields: dict) -> list[tuple[str, str, str, str]]:
    """(field name, date, label, remark) of each reference point of a picked option."""
    out = []
    for name in _REPERES:
        value = str(fields.get(name, "")).strip()
        if value:
            date, label, remark = (value.split("|") + ["", ""])[:3]
            out.append((name, date.strip(), label.strip(), remark.strip()))
    return out


def claim_text(date: str, label: str, remark: str) -> str:
    """One sentence a search can test: the point, dated, with what the remark says of it."""
    return f"{label} ({date})" + (f" : {remark}" if remark else "")


async def _search(text: str):
    from models.article import Claim
    from tools.verify import find_sources_for_claim
    return await find_sources_for_claim(Claim(text=text), num_results=4, num_results_per_db=0, scrape=False)


async def verify_points(fields: dict, search: Callable[[str], Awaitable] | None = None) -> list[dict]:
    """One result per point: {field, claim, status: confirmed | unconfirmed | contradicted, source, reason}."""
    search = search or _search

    async def one(name: str, date: str, label: str, remark: str) -> dict:
        text = claim_text(date, label, remark)
        try:
            found = await search(text)
        except Exception as exc:    # no key, no network, a provider down: say so, never block the author
            return {"field": name, "claim": text, "status": "unavailable", "source": None, "reason": str(exc)[:120]}
        if found.contradicting:
            s = found.contradicting[0]
            return {"field": name, "claim": text, "status": "contradicted", "source": {"title": s.title, "url": s.url},
                    "reason": s.stance_reason}
        if found.confirming:
            s = found.confirming[0]
            return {"field": name, "claim": text, "status": "confirmed", "source": {"title": s.title, "url": s.url},
                    "reason": s.stance_reason}
        return {"field": name, "claim": text, "status": "unconfirmed", "source": None, "reason": "no supporting source found"}

    return list(await asyncio.gather(*(one(*p) for p in points(fields))))


def warnings(step: str, results: list[dict]) -> list[str]:
    """The ⚠ lines for the author: what is not confirmed, what is contradicted, a search that could not run."""
    out = []
    for r in results:
        where = f"{step}.{r['field']}"
        if r["status"] == "unconfirmed":
            out.append(f"{where}: no source found for « {r['claim']} » — check it before keeping it (the search covers news best)")
        elif r["status"] == "contradicted":
            out.append(f"{where}: a source contradicts « {r['claim']} » — {r['reason']} ({r['source']['url']})")
        elif r["status"] == "unavailable":
            out.append(f"{where}: could not be checked ({r['reason']})")
    return out


def save(steps_dir: Path, step_n: int, step: str, results: list[dict]) -> Path:
    path = steps_dir / f"{step_n}_{step}.verification.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
