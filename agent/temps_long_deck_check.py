"""Deck-level check of a finished `temps_long` carousel (`python main.py check <extract.json>`).

The step rules judge one step at a time, on its own fields. This looks across the slides, for what only the finished deck
shows: every criterion and sign of the lecture slide reaches a timeline, the tagline names the camps, the two timelines
do not open the same way, the pills are explained, the unverified outside facts are listed. Hard rules (a tag that names
nothing) fail the run; the rest is advisory — editorial advice for the author, who has the last word.
"""
import json
import re
from pathlib import Path

from agent.instagram_carousel_adapt_agent import _plain, _stems
from models.temps_long_presentation import TempsLongPresentation

_NAME = re.compile(r"\b[A-ZÉÈ][\wÉÈéèêàç'’-]{2,}")
_VAGUE_VERB = re.compile(r"avant de (?:trancher|classer)\s*$", re.I)


def _key(text: str) -> str:
    return re.sub(r"\W+", "", _plain(text).lower())


def _lecture_names(pres: TempsLongPresentation) -> tuple[list[str], list[str]]:
    """The first voice's criteria (the table's rows, the cards) and the second voice's signs, as the lecture slide names them."""
    first = [(r.label or r.kind) for r in pres.lecture.readings if (r.label or r.kind)]
    second = [c.label for c in pres.lecture.aside_cards]
    return first, second


def check_deck(pres: TempsLongPresentation, steps_dir: Path | None = None) -> dict[str, list[str]]:
    """{family: problems}. `rules` fail the run; `editorial (advisory)` is advice."""
    rules: list[str] = []
    advice: list[str] = []
    first, second = _lecture_names(pres)
    named = {_key(n): n for n in first + second}
    timelines = {"episodes": pres.episodes, "tournants": pres.tournants}

    # tags: each names a criterion or a sign of the lecture slide (rule); each criterion and sign is used (advice)
    used: set[str] = set()
    for step, frise in timelines.items():
        for point in frise.reperes:
            for tag in point.tags:
                if named and _key(tag) not in named:
                    rules.append(f"{step} « {point.date} » carries the tag « {tag} », which names no criterion or sign of the lecture slide")
                used.add(_key(tag))
        if any(p.tags for p in frise.reperes) and not frise.key.strip():
            advice.append(f"{step}: its points carry tags but nothing explains them — add the note under the rows")
        if len(frise.reperes) < 3:
            rules.append(f"{step} has {len(frise.reperes)} point(s), at least 3 are needed")
    unused = [n for k, n in named.items() if k not in used]
    if first and unused:
        advice.append("never used as a tag on the timelines: " + ", ".join(unused) +
                      " — keep it only if no event bears on it, and say so in the caption")

    # the two timelines do not open the same way
    a, b = _stems(_plain(pres.episodes.lead)), _stems(_plain(pres.tournants.lead))
    if a and b and len(a & b) >= 4:
        advice.append("the leads of the episodes and of the texts share most of their words — each should say its own thing")

    # the tagline names the camps
    if pres.lecture.aside_cards or pres.lecture.heads:
        camps = set()
        for source in (pres.lecture.lead, pres.lecture.aside_heading, pres.position.lead if pres.position else ""):
            camps |= {_key(w) for w in _NAME.findall(source)}
        camps -= {_key(w) for w in ("Pour", "Selon", "Les", "Une", "Des")}
        tag = _key(pres.hook.tagline)
        if camps and not any(c and c in tag for c in camps):
            advice.append("the hook's tagline names none of the camps of the lecture slide — « deux camps » alone tells the reader nothing")

    # the traps slide
    if _VAGUE_VERB.search(re.sub(r"\*\*", "", pres.pieges.title)):
        advice.append("the traps title ends on « avant de trancher / classer » alone — say what, or use the hook's verb")
    titles = [_key(p.title) for p in pres.pieges.pieges]
    if len(set(titles)) != len(titles):
        rules.append("two traps carry the same title")

    # the outside facts nobody could confirm (kept beside the steps by the web check)
    if steps_dir is not None and steps_dir.exists():
        for path in sorted(steps_dir.glob("*.verification.json")):
            step = path.name.split("_", 1)[1].split(".")[0]
            for r in json.loads(path.read_text(encoding="utf-8")):
                if r["status"] in ("unconfirmed", "contradicted"):
                    advice.append(f"{step}.{r['field']} is not confirmed by the web check ({r['status']}): « {r['claim']} »")
    return {"temps_long rules": rules, "editorial (advisory)": advice}
