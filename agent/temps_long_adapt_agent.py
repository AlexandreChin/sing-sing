"""Adapt agent for the TEMPS LONG carousel (6 slides, 7 once `position` is written).

A guided cascade for a hot-news piece, read through the lens of time: first the
axe (step 0, never rendered: the hook's title — the raw fact —, the question the deck
tests and the move that answers it — forme, seuil, séquence, nouveauté, délai, mémoire —,
fixed context of every later step), then `position` (the author's stand, shown as slide 2,
in the article's own frame), then the tournants (the laws, doctrine texts and statements
that changed the rules over fifty years), then the episodes people remember from the last
ten years, then the lecture slide (which answers the axe's question, leaning on the two
timelines), the traps (pieges), then the hook (its promise, from the axe, and its tagline);
`writing` finishes with the caption, without pausing.
Each step proposes options with a reason and a ★, the author picks, edits or
asks for others (`choose`), and a pick feeds the later steps. Steps are cached
in `<format>/adapt_steps/` with a stamp of the inputs and the earlier picks.

An option's fields are flat strings so that `choose --edit ID.field=TEXT` and
`fix` can rewrite any of them: a reference point, a reading, a trap are
one line each, their parts separated by « | » (see `to_fragment`).

Same guided semantics as `agent/cadrage_adapt_agent.py`, whose pure helpers and
step-file model are imported; the files, the rules and the prompts are this
archetype's own.
"""
import copy
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from agent._base import _call_with_retry, _j, medium_directive
from agent.cadrage_adapt_agent import (
    AwaitingChoice, ChoiceError, StepFile, _ACCUSING, _HASHTAG, _QUOTED, _failed, _merge, _norm, _parts,
    _response_model, _to_options, _words, base_inputs, format_options,
)
from agent.carousel_steps.steps import Option
from agent.carousel_steps.store import log_choice, stamp_for
from agent.instagram_carousel_adapt_agent import _full_analysis_context, _plain, _stems
from models.full_analysis import ArticleFullAnalysis
from models.temps_long_presentation import TempsLongPresentation

_PROMPTS = Path(__file__).parent / "prompts" / "temps_long_steps"


# ── Option models and the step table ────────────────────────────────────────

class FriseOption(BaseModel):
    title: str
    lead: str
    rep1: str    # « date | repère | remarque » — oldest first
    rep2: str
    rep3: str
    rep4: str    # empty when three points are enough
    rep5: str
    key: str = ""   # optional: one or two lines under the rows saying what the pills mean


class AxeOption(BaseModel):
    fait: str        # the hook's title: the raw fact, attributed, in the media's words, ≤64 characters, one key word in gold
    title: str       # the question the deck tests, ≤100 characters, ends with « ? »: the hook's promise starts from it
    move: str        # forme | seuil | sequence | nouveaute | delai | memoire
    mot: str         # the word or claim of the media the question tests (found in the source)
    reponse: str     # what the deck gives the reader as the answer, in one line
    criteres: str = ""   # « A, B, C »: the three cards' names on the lecture slide (forme, seuil); empty for the other moves
    criteres2: str = ""  # seuil: the second voice's sign names, « A, B, … » (2–7, ≤10 characters each): the pills of the timelines


class LectureOption(BaseModel):
    title: str
    lead: str
    card1: str         # « nom | question ? | texte avec un **passage en gras** » — the first of the slide's three cards
    card2: str
    card3: str
    question: str      # the neutral closing question: not drawn on the slide, taken up by the sign-off
    where: str = ""    # one line under the lead (where to find the series, or what the media does not give), shown once
    where_label: str = ""   # the bold label of that line; empty = « Où regarder »
    kicker: str = ""        # the label above the title; empty = « La lecture du temps »
    author: str = ""        # one line under the cards, ≤60 characters; empty = none
    head1: str = ""         # the move seuil: a decision table — the name of its first column, the title's first word (« Maintien de l'ordre »)
    head2: str = ""         # ... and of its second (« « Répression » »)
    aside_heading: str = ""  # ... the line above the second voice's signs (« Amnesty juge autrement : un « glissement » sur sept signes »)
    # ... the second voice's signs, 2 to 7, each « nom | phrase | icône »: a short name (≤10 characters, also the pill on the
    # timelines), the explicit phrase as the media words it (≤34), an icon key of the deck's pictograms (optional)
    aside1: str = ""
    aside2: str = ""
    aside3: str = ""
    aside4: str = ""
    aside5: str = ""
    aside6: str = ""
    aside7: str = ""


class PiegesOption(BaseModel):
    title: str        # the slide's headline; no sub-line is drawn any more
    lead: str = ""
    piege1: str  # « titre | question »
    piege2: str
    piege3: str
    piege4: str


class HookOption(BaseModel):
    promise: str
    tagline: str = ""   # the second paragraph, two lines at most, key words in gold; empty = the archetype's default


class PositionOption(BaseModel):
    title: str        # the claim in a few plain words (the lead names the author)
    lead: str         # the summary of the position
    ecarte: str       # card 1 — what the author sets aside
    diagnostic: str   # card 2 — his own reading
    mecanisme: str    # card 3 — why it lasted, why it breaks
    issue: str        # card 4 — his conclusion
    kicker: str = ""             # the label above the title (empty = « Ce que dit l'auteur »)
    ecarte_label: str = ""       # each card's heading, specific to the article (empty = the default one)
    diagnostic_label: str = ""
    mecanisme_label: str = ""
    issue_label: str = ""


class WritingCopy(BaseModel):
    caption: str


@dataclass(frozen=True)
class Step:
    n: int
    name: str
    option_model: type[BaseModel] | None     # None for writing
    text_field: str                           # the field that names an option
    analysis_slice: int
    offered: tuple[int, int] = (3, 4)         # options per generation


STEPS: tuple[Step, ...] = (
    Step(0, "axe", AxeOption, "title", 3),
    Step(1, "position", PositionOption, "title", 3),
    Step(2, "tournants", FriseOption, "title", 3),
    Step(3, "episodes", FriseOption, "title", 3),
    Step(4, "lecture", LectureOption, "title", 3),
    Step(5, "pieges", PiegesOption, "title", 3),
    Step(6, "hook", HookOption, "promise", 3),
    Step(7, "writing", None, "", 3, (1, 1)),
)
STEP_BY_NAME: dict[str, Step] = {s.name: s for s in STEPS}
STEP_NAMES = [s.name for s in STEPS[:-1]]
_REPERES = ("rep1", "rep2", "rep3", "rep4", "rep5")
_READINGS = ("rupture", "continuite", "cycle")   # the cards of an older deck
_CARDS = ("card1", "card2", "card3")
_MOVES = ("forme", "seuil", "sequence", "nouveaute", "delai", "memoire")
# the slides between the hook and the sign-off, in reading order, for a move that does not keep the archetype's own order
_MOVE_ORDER = {"seuil": ["position", "lecture", "episodes", "tournants", "pieges"]}
_FORME_LABELS = "Rupture, Continuité, Cycle"
_KNOWN_KINDS = ("rupture", "continuite", "cycle", "cible", "proportion", "effet")   # card names that have their own pictogram
_OLD_LABELS = {"rupture": "Rupture", "continuite": "Continuité", "cycle": "Cycle"}
_PIEGES = ("piege1", "piege2", "piege3", "piege4")
_FRISE_STEPS = ("tournants", "episodes")
_LAYOUTS = {"episodes": "annees", "tournants": "axe"}   # the episodes read as large years, the texts on a spine (see the renderer)
_POSITION_CARDS = ("ecarte", "diagnostic", "mecanisme", "issue")


# ── Files ───────────────────────────────────────────────────────────────────

def _path(steps_dir: Path, step: Step) -> Path:
    return steps_dir / f"{step.n}_{step.name}.json"


def _load(steps_dir: Path, step: Step) -> tuple[StepFile | None, str]:
    path = _path(steps_dir, step)
    if not path.exists():
        return None, ""
    stamp = path.with_suffix(".sha256")
    return (StepFile.model_validate_json(path.read_text(encoding="utf-8")),
            stamp.read_text().strip() if stamp.exists() else "")


def _save(steps_dir: Path, sf: StepFile, stamp: str) -> None:
    step = STEP_BY_NAME[sf.step]
    steps_dir.mkdir(parents=True, exist_ok=True)
    _path(steps_dir, step).write_text(sf.model_dump_json(indent=2), encoding="utf-8")
    _path(steps_dir, step).with_suffix(".sha256").write_text(stamp)


def _retire(steps_dir: Path, step: Step, stamp: str) -> None:
    dest = steps_dir / f"stale_{(stamp or 'unstamped')[:8]}"
    for p in (_path(steps_dir, step), _path(steps_dir, step).with_suffix(".sha256")):
        if p.exists():
            dest.mkdir(parents=True, exist_ok=True)
            p.replace(dest / p.name)


# The order the steps are written in, once the axe has fixed the move. `seuil` writes the lecture slide (the table and the
# signs) BEFORE the timelines — its rows are then chosen to bear on its criteria and signs, and the writing order is the
# reading order; the other moves keep the default order (their cards hang on the timelines' rows).
_WRITE_ORDER = {"seuil": ("axe", "position", "lecture", "episodes", "tournants", "pieges", "hook", "writing")}


def steps_in_order(move: str | None) -> list[Step]:
    names = _WRITE_ORDER.get(move or "")
    return [STEP_BY_NAME[n] for n in names] if names else list(STEPS)


def _move_of(steps_dir: Path | None) -> str | None:
    """The move the axe has fixed (None until it is picked)."""
    if steps_dir is None:
        return None
    sf, _ = _load(steps_dir, STEP_BY_NAME["axe"])
    return _axe({"axe": sf.fragment}).get("move") if sf is not None and sf.fragment else None


# ── Rules ───────────────────────────────────────────────────────────────────
# Hard: a generated option repairs itself; on the author's own pick they come
# back as warnings. Flags are advisory.

# (step, field) → ("words" | "chars", cap)
_CAPS: dict[tuple[str, str], tuple[str, int]] = {
    **{(s, "title"): ("chars", 44) for s in ("lecture", "pieges")},   # two lines at most, whatever the words
    **{(s, "title"): ("chars", 36) for s in ("tournants", "episodes")},   # the headline of the timelines, 70 px, centred: two lines at most
    **{(s, "lead"): ("chars", 92) for s in ("tournants", "episodes")},   # two lines at most, beside the bird perched on the first row
    ("lecture", "lead"): ("chars", 140),
    ("lecture", "question"): ("chars", 96),
    ("lecture", "where"): ("chars", 48),   # the shared « Où regarder » line: one line under the lead
    ("axe", "criteres2"): ("chars", 90), ("axe", "fait"): ("chars", 64), ("axe", "title"): ("chars", 100), ("axe", "mot"): ("chars", 40), ("axe", "reponse"): ("chars", 120), ("axe", "criteres"): ("chars", 40),
    ("lecture", "kicker"): ("chars", 30), ("lecture", "author"): ("chars", 60), ("lecture", "where_label"): ("chars", 20),
    ("lecture", "head1"): ("chars", 20), ("lecture", "head2"): ("chars", 20), ("lecture", "aside_heading"): ("chars", 60), 
    ("hook", "tagline"): ("chars", 110),   # two lines at 34 px under the promise
    ("hook", "promise"): ("chars", 100),   # the headline: three lines at 84 px; the promise: three lines at 52 px, then the fixed tagline
    ("position", "title"): ("chars", 46), ("position", "lead"): ("chars", 90),   # slide 2: the title is the claim (70 px, two lines), the lead the sentence that names the author (34 px, two lines)
    **{("position", c): ("chars", 108) for c in _POSITION_CARDS},   # two lines in a card, three at the very worst
    ("position", "kicker"): ("chars", 30),   # the kicker above the title, one line, capitals spaced out
    **{("position", f"{c}_label"): ("chars", 30) for c in _POSITION_CARDS},   # a row's heading, two lines in its column beside the icon
}
_DATE_MAX = 14      # characters: the date is drawn big, in gold, in a narrow column
_LABEL_MAX = 64     # characters: a reference point's label takes two lines at most
_REMARK_MAX = 46    # characters: an episode's remark takes one line
_TOURNANTS_LABEL_MAX = 50    # characters: a turning point's label takes two lines at most — the `axe` layout gives it half the slide
_TOURNANTS_REMARK_MAX = 56   # characters: a turning point's remark takes two lines at half width (what it changes, and what it could change)
_SIGNATURE_MAX = 36    # characters: a card's question takes one line after its name (a name of 10 characters, then ' : ', then this)
_CARD_LABEL_MAX = 10   # characters: a card's name, before its question
_ASIDE_NAME_MAX = 10     # characters: a sign's short name — the pill on the timelines
_ASIDE_PHRASE_MAX = 34   # ... and its explicit phrase, two lines at most in its small card
_ASIDE_CARDS = (2, 7)    # signs; four rows of two small cards, each two lines at most, fit under the table
_DUO_QUESTION_MAX = 28   # characters: a table row's question under its name — what the test looks at, as a complement — two lines at most
_DUO_CELL_MAX = 30       # ... and each of its two outcomes, two lines at most
_TAGS_MAX = 2            # pills a timeline point may carry
_KEY_MAX = 100           # characters: the key under the rows, two lines at most
_ASIDES = ("aside1", "aside2", "aside3", "aside4", "aside5", "aside6", "aside7")
_DUO_LEAD_MAX = 100      # characters: beside an aside the lead takes two lines, not three — the columns need the room
_INDICATOR_MAX = 100    # characters: a reading's test takes two lines at most
_WHERE_MAX = 44         # characters: where to find the series, one line after « Où regarder »
_URL = re.compile(r"https?://|www\.", re.I)
_PIEGE_TITLE_MAX = 38   # characters: a trap's name, one line
_PIEGE_QUESTION_MAX = 92   # characters: a trap's question, two lines at most
_FIGURE = re.compile(r"\d[\d  .,]*\s*(?:%|€|M€|Md€|milliards?|millions?|points?\b|×)?|×\s*\d", re.I)
_YEAR = re.compile(r"\b(?:1[89]|20)\d{2}\b")
# a trend figure: a percentage, an amount, a multiple — never in a dated reference point
_TREND_FIGURE = re.compile(r"\d[\d  .,]*\s*(?:%|€|M€|Md€|milliards?|millions?|points?\b|×)|×\s*\d", re.I)
_REQUIRED = {"axe": ("fait", "title", "move", "mot", "reponse"),
             "tournants": ("title", "lead", "rep1", "rep2", "rep3"),
             "episodes": ("title", "lead", "rep1", "rep2", "rep3", "rep4"),   # 4 or 5 episodes
             "lecture": ("title", "lead", "question"),
             "pieges": ("title", "piege1", "piege2", "piege3", "piege4"),
             "position": ("title", "lead", "ecarte", "diagnostic", "mecanisme", "issue")}
_EPISODES_MAX_AGE = 12   # years before the article: an episode older than this is no longer what people remember
_TOURNANTS_MIN_AGE = 25  # the tournants reach back at least this far (10 for the move seuil: the question is about the present line)
_TOURNANTS_MIN_AGE_SEUIL = 10
_TOURNANTS_RECENT = 3      # ... and include a point from the last few years, a bill under discussion included


def _ref_year(article: str | None) -> int | None:
    """The article's own year: the latest one it mentions."""
    years = [int(y) for y in _YEAR.findall(article or "")]
    return max(years) if years else None


def _label_key(label: str) -> str:
    """A card's name as a key: lowercase, no accent (« Continuité » → « continuite »)."""
    return unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower().strip()


def _axe(fragments: dict[str, dict]) -> dict:
    return fragments.get("axe", {}).get("axe", {})


def _criteres(axe: dict) -> list[str]:
    return [c.strip() for c in str(axe.get("criteres", "")).split(",") if c.strip()]


def _criteres2(axe: dict) -> list[str]:
    return [c.strip() for c in str(axe.get("criteres2", "")).split(",") if c.strip()]


def _aside(fields: dict[str, Any]) -> list[dict]:
    """The second voice's signs as written, « nom | phrase | icône » each (`aside1`…`aside7`)."""
    out = []
    for name in _ASIDES:
        if (value := str(fields.get(name, "")).strip()):
            label, text, icon = _parts(value, 3)
            out.append({"name": name, "label": label, "text": text, "icon": icon})
    return out


def _cards(fields: dict[str, Any]) -> list[dict]:
    """The lecture's cards as written: « nom | question ? | texte » (`card1`…`card3`), or, in an older deck,
    « hypothèse ? | test | où regarder » under the name of its reading (`rupture`, `continuite`, `cycle`)."""
    out = []
    if any(str(fields.get(k, "")).strip() for k in _CARDS):
        for name in _CARDS:
            if (value := str(fields.get(name, "")).strip()):
                label, question, text = _parts(value, 3)
                out.append({"name": name, "label": label, "question": question, "text": text, "where": "", "old": False})
    else:
        for kind in _READINGS:
            if (value := str(fields.get(kind, "")).strip()):
                question, text, where = _parts(value, 3)
                out.append({"name": kind, "label": _OLD_LABELS[kind], "question": question, "text": text,
                            "where": where, "old": True})
    return out


def field_errors(step: str, fields: dict[str, Any], fragments: dict[str, dict],
                 article: str | None) -> tuple[list[str], list[str]]:
    """(hard, flags) on one step's fields, given the earlier fragments."""
    hard, flags = [], []
    for name, value in fields.items():
        if not isinstance(value, str):
            continue
        if (rule := _CAPS.get((step, name))):
            kind, cap = rule
            n = len(re.sub(r"\*\*", "", value)) if kind == "chars" else _words(value)
            if n > cap:
                hard.append(f"{step}.{name} is {n} {kind} (max {cap})")
        if (m := _ACCUSING.search(_QUOTED.sub("", value))):
            hard.append(f"{step}.{name} uses an accusing word « {m.group(0)} » — the carousel gives tools, not verdicts")
        if step not in ("writing", "position") and (m := _TREND_FIGURE.search(_QUOTED.sub("", value))):
            hard.append(f"{step}.{name} gives a figure « {m.group(0).strip()} » — dated reference points only, never a trend figure")
    for name in _REQUIRED.get(step, ()):
        if not str(fields.get(name, "")).strip():
            hard.append(f"{step}.{name} is empty")
    if step in _FRISE_STEPS:
        years = []
        quoted_stems = {w for q in _QUOTED.findall(str(fields.get("lead", ""))) for w in _stems(q)}
        earlier_remarks: list[tuple[str, set[str]]] = []
        for name in _REPERES:
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            date, label, remark, tag_text = _parts(value, 4)
            if not label or not _YEAR.search(date):
                hard.append(f"{step}.{name} must read « date | repère | remarque » (the date holds a year)")
                continue
            if tag_text:
                allowed = [_label_key(c) for c in _criteres(_axe(fragments)) + _criteres2(_axe(fragments))]
                tags_here = [t.strip() for t in tag_text.split(",") if t.strip()]
                if len(tags_here) > _TAGS_MAX:
                    hard.append(f"{step}.{name}: {len(tags_here)} tags — a point carries {_TAGS_MAX} at most")
                for tag in tags_here:
                    if _label_key(tag) not in allowed:
                        hard.append(f"{step}.{name}: the tag « {tag} » is not one of the axe's criteria "
                                    f"({', '.join(allowed) or 'the axe has none'})")
            if len(date) > _DATE_MAX:
                hard.append(f"{step}.{name}: the date is {len(date)} characters (max {_DATE_MAX}) — it is drawn big")
            label_max = _TOURNANTS_LABEL_MAX if step == "tournants" else _LABEL_MAX
            if len(label) > label_max:
                hard.append(f"{step}.{name}: the label is {len(label)} characters (max {label_max}) — two lines at most")
            cap = _TOURNANTS_REMARK_MAX if step == "tournants" else _REMARK_MAX
            if len(remark) > cap:
                hard.append(f"{step}.{name}: the remark is {len(remark)} characters (max {cap}) — "
                            f"{'two lines' if step == 'tournants' else 'one line'}")
            if not remark:
                flags.append(f"{step}.{name} has no remark — say what the point lets the reader check in the lead")
            else:
                mine = _stems(_plain(remark))
                if mine & quoted_stems:
                    flags.append(f"{step}.{name}: the remark only echoes the lead's quoted word — say what this point shows")
                own = mine & _stems(_plain(label))
                if len(own) >= 2 or (own and len(own) * 2 >= len(mine)):
                    flags.append(f"{step}.{name}: the remark repeats the label — say something the label does not")
                for other, theirs in earlier_remarks:
                    common = mine & theirs
                    if len(common) >= 2 and len(common) * 2 >= min(len(mine), len(theirs)):
                        flags.append(f"{step}.{name}: the remark repeats {other}'s — each point needs its own")
                        break
                earlier_remarks.append((name, mine))
            years += [int(y) for y in _YEAR.findall(date)]
            if step == "episodes":
                mine = _stems(_plain(label))
                for other in fragments.get("tournants", {}).get("tournants", {}).get("reperes", []):
                    theirs = _stems(_plain(other["label"]))
                    common = mine & theirs
                    if len(common) >= 2 and len(common) * 2 >= min(len(mine), len(theirs)):
                        flags.append(f"episodes.{name} looks like the point « {other['date']} » of the tournants — "
                                     "each slide needs its own events")
                        break
        # when the other timeline and the lecture slide are written, every criterion and sign should be tagged somewhere
        other = "episodes" if step == "tournants" else "tournants"
        lecture_frag = fragments.get("lecture", {}).get("lecture", {})
        if other in fragments and lecture_frag:
            names = [(r.get("label") or r.get("kind") or "") for r in lecture_frag.get("readings", [])]
            names += [c.get("label", "") for c in lecture_frag.get("aside_cards", [])]
            names = [n for n in names if n]
            used = {t for p in fragments[other].get(other, {}).get("reperes", []) for t in p.get("tags", [])}
            for name in _REPERES:
                if str(fields.get(name, "")).strip():
                    used |= {_label_key(t) for t in _parts(str(fields[name]), 4)[3].split(",") if t.strip()}
            used = {_label_key(t) for t in used}
            if (unused := [n for n in names if _label_key(n) not in used]):
                flags.append(f"{step}: no point of the two timelines is tagged " + ", ".join(unused) +
                             " — pick points that bear on them, or accept that none does")
        key = str(fields.get("key", "")).strip()
        if len(key) > _KEY_MAX:
            hard.append(f"{step}.key is {len(key)} characters (max {_KEY_MAX}) — two lines at most")
        if step == "tournants" and str(fields.get("rep5", "")).strip():
            hard.append("tournants.rep5: this slide takes 3 or 4 points")
        lead = str(fields.get("lead", ""))
        quotes = _QUOTED.findall(lead)
        if lead.strip() and not quotes:
            hard.append(f"{step}.lead must quote a word of the media between « »")
        if article:
            hard += [f"{step}.lead quotes {q} but the source does not say it"
                     for q in quotes if _norm(q.strip("« »\u00a0 ")) not in _norm(article)]
        if (ref := _ref_year(article)) and years:
            if step == "episodes" and min(years) < ref - _EPISODES_MAX_AGE:
                flags.append(f"episodes reaches back to {min(years)}, over {_EPISODES_MAX_AGE} years before the article — "
                             "an older point belongs to the tournants")
            min_age = _TOURNANTS_MIN_AGE_SEUIL if _axe(fragments).get("move") == "seuil" else _TOURNANTS_MIN_AGE
            if step == "tournants" and min(years) > ref - min_age:
                flags.append(f"tournants starts in {min(years)}, less than {min_age} years before the article — "
                             "it should reach further back")
            if step == "tournants" and max(years) < ref - _TOURNANTS_RECENT:
                flags.append(f"tournants ends in {max(years)}, over {_TOURNANTS_RECENT} years before the article — "
                             "add the most recent text, a bill under discussion included")
    if step == "lecture":
        if _URL.search(str(fields.get("where", ""))):
            hard.append("lecture.where names an organisation, never a URL")
        cards = _cards(fields)
        aside = _aside(fields)
        q_max, t_max = _SIGNATURE_MAX, _INDICATOR_MAX
        if len(cards) < 3:
            hard.append("lecture needs three cards (card1, card2, card3)")
        if aside:
            if not _ASIDE_CARDS[0] <= len(aside) <= _ASIDE_CARDS[1]:
                hard.append(f"lecture has {len(aside)} signs (aside1…aside7) — it takes {_ASIDE_CARDS[0]} to {_ASIDE_CARDS[1]}")
            for a in aside:
                if not (a["label"] and a["text"]):
                    hard.append(f"lecture.{a['name']} must read « nom | phrase | icône facultative »")
                    continue
                if len(a["label"]) > _ASIDE_NAME_MAX:
                    hard.append(f"lecture.{a['name']}: the name is {len(a['label'])} characters (max {_ASIDE_NAME_MAX}) — it is the pill on the timelines")
                if len(a["text"]) > _ASIDE_PHRASE_MAX:
                    hard.append(f"lecture.{a['name']}: the phrase is {len(a['text'])} characters (max {_ASIDE_PHRASE_MAX}) — two lines at most")
            wanted2 = _criteres2(_axe(fragments))
            if wanted2 and [_label_key(a["label"]) for a in aside] != [_label_key(c) for c in wanted2]:
                hard.append(f"lecture: the signs must be named {', '.join(wanted2)}, in this order (the axe's second voice)")
            if len(re.sub(r"\*\*", "", str(fields.get("lead", "")))) > _DUO_LEAD_MAX:
                hard.append(f"lecture.lead is over {_DUO_LEAD_MAX} characters — beside an aside it takes two lines")
            hard += [f"lecture.{n} is empty — the table's two columns and the line above the signs are named"
                     for n in ("head1", "head2", "aside_heading") if not str(fields.get(n, "")).strip()]
            hard += [f"lecture.{n} must stay empty beside an aside — the two columns leave no room for it"
                     for n in ("where", "author") if str(fields.get(n, "")).strip()]
        shared = bool(str(fields.get("where", "")).strip())   # the series is named once, under the lead: a card needs no « où regarder »
        known = _stems(_plain(str(fields.get("lead", ""))))
        known_years: set[str] = set()
        for other in ("episodes", "tournants"):
            for pt in fragments.get(other, {}).get(other, {}).get("reperes", []):
                known |= _stems(_plain(pt["label"]))
                known_years |= set(_YEAR.findall(pt["date"]))
        for card in cards:
            name, label, question, text, where = (card[k] for k in ("name", "label", "question", "text", "where"))
            if aside:   # a row of the decision table: « critère | question | issue 1 | issue 2 »
                left, right = _parts(text, 2)
                if not (label and question and left and right):
                    hard.append(f"lecture.{name} must read « critère | question | première issue | seconde issue »")
                else:
                    if len(label) > _CARD_LABEL_MAX:
                        hard.append(f"lecture.{name}: the name is {len(label)} characters (max {_CARD_LABEL_MAX})")
                    if len(question) > _DUO_QUESTION_MAX:
                        hard.append(f"lecture.{name}: the question is {len(question)} characters (max {_DUO_QUESTION_MAX}) — two lines at most")
                    for side, value in (("first", left), ("second", right)):
                        if len(value.replace("**", "")) > _DUO_CELL_MAX:
                            hard.append(f"lecture.{name}: the {side} outcome is {len(value.replace('**', ''))} characters (max {_DUO_CELL_MAX}) — two lines at most")
                continue
            if card["old"]:
                if not all((question, text) if shared else (question, text, where)):
                    hard.append("lecture." + name + " must read « hypothèse ? | test avec un **passage en gras**"
                                + ("" if shared else " | où regarder") + " »")
                    continue
            elif not (label and question and text):
                hard.append(f"lecture.{name} must read « nom | " + ("affirmation | détail" if aside else "question ? | texte avec un **passage en gras**") + " »")
                continue
            elif len(label) > _CARD_LABEL_MAX:
                hard.append(f"lecture.{name}: the name is {len(label)} characters (max {_CARD_LABEL_MAX}) — it sits before the question")
            if len(question.replace("**", "")) > q_max:
                hard.append(f"lecture.{name}: the {'claim' if aside else 'question'} is {len(question.replace('**', ''))} characters "
                            f"(max {q_max}) — one line")
            if not aside and not question.endswith("?"):
                hard.append(f"lecture.{name}: the question must end with « ? »")
            if len(re.sub(r"\*\*", "", text)) > t_max:
                hard.append(f"lecture.{name}: the {'detail' if aside else 'text'} is {len(re.sub(r'[*][*]', '', text))} characters (max {t_max}) — two lines at most")
            if not aside and text.count("**") < 2:
                hard.append(f"lecture.{name}: the text must put one passage in bold (**…**)")
            if len(where) > _WHERE_MAX:
                hard.append(f"lecture.{name}: « où regarder » is {len(where)} characters (max {_WHERE_MAX}) — one line")
            if _URL.search(where):
                hard.append(f"lecture.{name}: « où regarder » names an organisation, never a URL")
            if known and not (_stems(_plain(text)) & known or set(_YEAR.findall(text)) & known_years):
                flags.append(f"lecture.{name}: the text refers to nothing of the lead or of the episodes and texts of the timelines")
        wanted = _criteres(_axe(fragments))
        if wanted and cards and not cards[0]["old"]:
            if [_label_key(c["label"]) for c in cards] != [_label_key(c) for c in wanted]:
                hard.append(f"lecture: the cards must be named {', '.join(wanted)}, in this order (the axe's criteria)")
        if fields.get("question", "").strip() and not fields["question"].strip().endswith("?"):
            hard.append("lecture.question must be a question")
    if step == "pieges":
        lecture = fragments.get("lecture", {}).get("lecture", {})
        measure = _stems(_plain(" ".join([lecture.get("lead", "")] + [r.get("label", "") for r in lecture.get("readings", [])])))
        for name in _PIEGES:
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            title, question = _parts(value, 2)
            if not title or not question:
                hard.append(f"pieges.{name} must read « titre | texte »")
                continue
            if len(title) > _PIEGE_TITLE_MAX:
                hard.append(f"pieges.{name}: the title is {len(title)} characters (max {_PIEGE_TITLE_MAX}) — one line")
            if len(question) > _PIEGE_QUESTION_MAX:
                hard.append(f"pieges.{name}: the text is {len(question)} characters (max {_PIEGE_QUESTION_MAX}) — two lines at most")
            if measure and not _stems(_plain(value)) & measure:
                flags.append(f"pieges.{name} cites nothing of what the lecture slide tests — tie the trap to it")
    if step == "position":
        if "**" not in str(fields.get("title", "")):
            hard.append("position.title needs at least one key passage in gold bold (**…**)")
        for name in ("title", *_POSITION_CARDS, "lead"):
            value = str(fields.get(name, ""))
            if article:
                hard += [f"position.{name} quotes {q} but the source does not say it"
                         for q in _QUOTED.findall(value) if _norm(q.strip("« »\u00a0 ")) not in _norm(article)]
                flags += [f"position.{name} gives the figure « {n.strip(" .,")} » that the source does not carry — check it"
                          for n in _FIGURE.findall(_QUOTED.sub("", value)) if _norm(n.strip(" .,")) not in _norm(article)]
    if step == "hook":
        promise = str(fields.get("promise", "")).strip()
        if not promise.lower().startswith("prendre du recul") and not promise.endswith("?"):
            flags.append("hook.promise reads « Prendre du recul sur … » or is the question the deck tests (« …est-elle nouvelle ? »)")
        if (axe := _axe(fragments)):
            if not str(fields.get("tagline", "")).strip():
                hard.append("hook.tagline is empty — one line under the promise, key words in gold")
            if promise and not _stems(_plain(promise)) & _stems(_plain(str(axe.get("title", "")))):
                flags.append("hook.promise shares no key word with the axe's question")
            if (quoted := _QUOTED.findall(str(axe.get("fait", "")))) and promise \
                    and not _stems(_plain(promise)) & {w for q in quoted for w in _stems(q)}:
                flags.append("hook.promise reuses no word of the title's quoted passages — the promise should read as the title's next line")
        if str(fields.get("tagline", "")).strip() and "**" not in fields["tagline"]:
            hard.append("hook.tagline puts no key words in gold (**…**)")
    if step == "axe":
        if article:
            hard += [f"axe.fait quotes {q} but the source does not say it"
                     for q in _QUOTED.findall(str(fields.get("fait", ""))) if _norm(q.strip("« »\u00a0 ")) not in _norm(article)]
        move = str(fields.get("move", "")).strip()
        if move and move not in _MOVES:
            hard.append(f"axe.move is « {move} » — one of {', '.join(_MOVES)}")
        if fields.get("title", "").strip() and not str(fields["title"]).strip().endswith("?"):
            hard.append("axe.title must be a question")
        mot = str(fields.get("mot", "")).strip()
        if article and mot and _norm(mot.strip("« »\u00a0 ")) not in _norm(article):
            hard.append(f"axe.mot « {mot} » is not in the source — it is a word or claim of the media")
        labels = _criteres(fields)
        if move in ("forme", "seuil") and len(labels) != 3:
            hard.append(f"axe.criteres names the three cards of the lecture slide (« A, B, C ») for the move {move}")
        if move == "forme" and labels and ", ".join(labels) != _FORME_LABELS:
            hard.append(f"axe.criteres for the move forme is « {_FORME_LABELS} »")
        if any(len(c) > _CARD_LABEL_MAX for c in labels):
            hard.append(f"axe.criteres: each name is {_CARD_LABEL_MAX} characters at most")
        names2 = _criteres2(fields)
        if names2 and move != "seuil":
            hard.append("axe.criteres2 is the second voice's signs: only for the move seuil")
        if names2 and not _ASIDE_CARDS[0] <= len(names2) <= _ASIDE_CARDS[1]:
            hard.append(f"axe.criteres2 names {len(names2)} signs — it takes {_ASIDE_CARDS[0]} to {_ASIDE_CARDS[1]}")
        if any(len(c) > _ASIDE_NAME_MAX for c in names2):
            hard.append(f"axe.criteres2: each name is {_ASIDE_NAME_MAX} characters at most — it is a pill")
    if step == "writing":
        tags = _HASHTAG.findall(fields.get("caption", ""))
        if len(tags) != 4:
            hard.append(f"writing.caption has {len(tags)} hashtag(s), must have 4")
        if not 100 <= _words(fields.get("caption", "")) <= 190:
            hard.append(f"writing.caption is {_words(fields.get('caption', ''))} words (aim for about 150)")
    return hard, flags


# ── Fragments and assembly ──────────────────────────────────────────────────

def to_fragment(step: Step, option: Option) -> dict:
    f = option.fields
    if step.name == "axe":
        return {"axe": {k: f.get(k, "") for k in ("title", "move", "mot", "reponse", "criteres", "criteres2")},
                "hook": {"title": f.get("fait", "")}}
    if step.name in _FRISE_STEPS:
        reperes = []
        for name in _REPERES:
            if str(f.get(name, "")).strip():
                date, label, remark, tag_text = _parts(f[name], 4)
                reperes.append({"date": date, "label": label, "remark": remark,
                                "tags": [t.strip().lower() for t in tag_text.split(",") if t.strip()]})
        return {step.name: {"title": f.get("title", ""), "lead": f.get("lead", ""), "reperes": reperes, "key": f.get("key", ""),
                            "layout": _LAYOUTS[step.name]}}
    if step.name == "lecture":
        duo = bool(_aside(f))   # beside an aside a card is a table row: « critère | question | issue 1 | issue 2 »
        readings = [{"kind": key if (key := _label_key(c["label"])) in _KNOWN_KINDS else "", "label": c["label"],
                     "signature": c["question"], "indicator": _parts(c["text"], 2)[0] if duo else c["text"],
                     "other": _parts(c["text"], 2)[1] if duo else "", "where": c["where"]}
                    for c in _cards(f)]
        return {"lecture": {"title": f.get("title", ""), "lead": f.get("lead", ""), "readings": readings,
                            "question": f.get("question", ""), "where": f.get("where", ""),
                            "where_label": f.get("where_label", ""), "kicker": f.get("kicker", ""),
                            "author": f.get("author", ""),
                            "heads": [f.get("head1", ""), f.get("head2", "")] if duo else [],
                            "aside_heading": f.get("aside_heading", ""),
                            "aside_cards": [{"label": a["label"], "text": a["text"], "icon": a["icon"]} for a in _aside(f)]}}
    if step.name == "pieges":
        pieges = []
        for name in _PIEGES:
            if str(f.get(name, "")).strip():
                title, question = _parts(f[name], 2)
                pieges.append({"title": title, "question": question})
        return {"pieges": {"title": f.get("title", ""), "lead": f.get("lead", ""), "pieges": pieges}}
    if step.name == "hook":
        return {"hook": {"promise": f.get("promise", ""), "tagline": f.get("tagline", "")}}
    if step.name == "position":
        return {"position": {k: f.get(k, "") for k in ("title", "lead", "kicker", *_POSITION_CARDS,
                                                   *(f"{c}_label" for c in _POSITION_CARDS))}}
    return {"caption": f.get("caption", "")}


def assemble(fragments: dict[str, dict]) -> dict:
    deck: dict = {}
    for step in STEPS:
        if step.name in fragments:
            _merge(deck, copy.deepcopy(fragments[step.name]))
    if (move := _axe(fragments).get("move")):
        deck["move"] = move
        deck["order"] = list(_MOVE_ORDER.get(move, []))
    return deck


# ── Generating a step ───────────────────────────────────────────────────────

def prompt_caps() -> dict[str, int]:
    """Every character cap a prompt may quote, by name (« {{cap:tournants.label}} »): the prompts never write the numbers,
    so they cannot drift from the rules the options are checked against."""
    caps = {f"{s}.{f}": n for (s, f), (_, n) in _CAPS.items()}
    caps |= {"frise.date": _DATE_MAX, "episodes.label": _LABEL_MAX, "episodes.remark": _REMARK_MAX,
             "tournants.label": _TOURNANTS_LABEL_MAX, "tournants.remark": _TOURNANTS_REMARK_MAX, "frise.key": _KEY_MAX,
             "card.name": _CARD_LABEL_MAX, "card.question": _SIGNATURE_MAX, "card.text": _INDICATOR_MAX,
             "aside.name": _ASIDE_NAME_MAX, "aside.phrase": _ASIDE_PHRASE_MAX, "duo.question": _DUO_QUESTION_MAX,
             "duo.cell": _DUO_CELL_MAX, "duo.lead": _DUO_LEAD_MAX, "trap.title": _PIEGE_TITLE_MAX,
             "trap.text": _PIEGE_QUESTION_MAX, "lecture.where_short": _WHERE_MAX,
             "tournants.min_age": _TOURNANTS_MIN_AGE, "tournants.min_age_seuil": _TOURNANTS_MIN_AGE_SEUIL,
             "tournants.recent": _TOURNANTS_RECENT, "episodes.max_age": _EPISODES_MAX_AGE}
    return caps


_CAP = re.compile(r"\{\{cap:([\w.]+)\}\}")


def fill_caps(text: str) -> str:
    caps = prompt_caps()
    return _CAP.sub(lambda m: str(caps[m.group(1)]), text)


def _read_prompt(name: str) -> str:
    return fill_caps((_PROMPTS / name).read_text(encoding="utf-8"))


def _prompt(step: Step) -> str:
    body = _read_prompt(f"{step.n}_{step.name}.md")
    if step.option_model is None:
        return body
    return _read_prompt("0_options.md") + "\n" + body


def examples_for(step: Step) -> str:
    """The author's past decisions for this step (`examples/<n>_<step>.md`), "" when there are none."""
    path = _PROMPTS / "examples" / f"{step.n}_{step.name}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _order_note(step: Step, fragments: dict) -> str:
    """Which steps are already written and which come after, for the move the axe has fixed."""
    move = _axe(fragments).get("move")
    order = steps_in_order(move)
    if step not in order or step.name == "axe":
        return ""
    i = order.index(step)
    done = ", ".join(s.name for s in order[:i]) or "—"
    later = ", ".join(s.name for s in order[i + 1:]) or "—"
    return (f"ORDRE D'ÉCRITURE (mouvement {move}) : déjà écrit = {done} ; tu écris {step.name} ; à venir = {later}. "
            "Les étapes à venir s'écriront POUR ce que tu fixes ici, jamais l'inverse.")


def _message(step: Step, full: ArticleFullAnalysis, fragments: dict, article_text: str | None,
             rejected: list[Option], remarks: list[str]) -> str:
    parts = [_full_analysis_context(full, step.analysis_slice)]
    if article_text:
        parts.append(f"MÉDIA (transcription ou texte) :\n{article_text.strip()}")
    if fragments:
        parts.append(f"CHOIX FIXÉS (ne les réécris pas) :\n{_j(fragments)}")
    parts += [_read_prompt("0_shared.md"), _prompt(step)]
    if (note := _order_note(step, fragments)):
        parts.append(note)
    if step.option_model is not None and (examples := examples_for(step)):
        parts.append(f"EXEMPLES (décisions passées de l'auteur) :\n{examples}")
    if rejected:
        parts.append(f"DÉJÀ PROPOSÉES ET ÉCARTÉES :\n{_j([o.fields for o in rejected])}")
    if remarks:
        parts.append("REMARQUES DE L'AUTEUR :\n" + "\n".join(f"- {r}" for r in remarks))
    if (directive := medium_directive(full.article_metadata.medium)):
        parts.append(directive)
    return "\n\n---\n\n".join(parts)


def generate(step: Step, full: ArticleFullAnalysis, fragments: dict[str, dict], article_text: str | None,
             no_api: bool, rejected: list[Option] = [], remarks: list[str] = [],
             steps_dir: Path | None = None) -> StepFile:
    """One model call for `step`'s options (writing: its copy), checked against the
    rules. Nothing is picked. An answer still breaking a hard rule after the
    retries raises RuntimeError."""
    model = _response_model(step) if step.option_model else WritingCopy
    message = _message(step, full, fragments, article_text, rejected, remarks)
    if step.option_model is None:
        def check_writing(d):
            return field_errors(step.name, WritingCopy.model_validate(d).model_dump(), fragments, article_text)[0]
        data = _call_with_retry(message, model.model_json_schema(), validator=check_writing,
                                no_api=no_api, label=step.name)
        try:
            fields = WritingCopy.model_validate(data).model_dump()
        except ValidationError as exc:
            raise _failed(step, steps_dir, data, [str(exc)]) from None
        return StepFile(step=step.name, options=[Option(id="a", slot="a", reason="", fields=fields)],
                        recommended=["a"], rejected=rejected, remarks=remarks)

    lo, hi = step.offered

    def validator(data):
        resp = model.model_validate(data)
        errors = []
        if not lo <= len(resp.options) <= hi:
            errors.append(f"options: {len(resp.options)} option(s), must have {lo}–{hi}")
        if len(resp.recommended) != 1 or not 0 <= resp.recommended[0] < len(resp.options):
            errors.append("recommended: exactly one valid index")
        for k, o in enumerate(resp.options):
            errors += [f"options[{k}]: {e}" for e in
                       field_errors(step.name, o.model_dump(exclude={"reason"}), fragments, article_text)[0]]
        return errors

    data = _call_with_retry(message, model.model_json_schema(), validator=validator, no_api=no_api, label=step.name)
    try:
        resp = model.model_validate(data)
    except ValidationError as exc:
        raise _failed(step, steps_dir, data, [str(exc)]) from None
    options = _to_options(resp.options, rejected)
    if not options or len(resp.recommended) != 1 or not 0 <= resp.recommended[0] < len(options):
        raise _failed(step, steps_dir, data, ["no option, or no valid recommended index"])
    for o in options:
        o.flags = field_errors(step.name, o.fields, fragments, article_text)[1]
    return StepFile(step=step.name, options=options, rejected=rejected,
                    recommended=[options[resp.recommended[0]].id], remarks=remarks)


# ── The run ─────────────────────────────────────────────────────────────────

def _pick(step: Step, sf: StepFile, picks: list[str]) -> None:
    sf.picked = list(picks)
    sf.fragment = to_fragment(step, next(o for o in sf.options if o.id == picks[0]))


def pending_step(steps_dir: Path) -> str | None:
    for s in steps_in_order(_move_of(steps_dir))[:-1]:
        sf, _ = _load(steps_dir, s)
        if sf is not None and not sf.picked:
            return s.name
    return None


def _run(full, no_api, article_text, steps_dir, stop_after, guided) -> TempsLongPresentation | None:
    base = base_inputs(full, article_text)
    fragments: dict[str, dict] = {}
    order = steps_in_order(None)       # the axe is first in every order; the move it fixes then sets the rest
    i = 0
    while i < len(order):
        step = order[i]
        stamp = stamp_for(base, [fragments[s.name] for s in order[:i]])
        sf, saved = _load(steps_dir, step) if steps_dir is not None else (None, "")
        tag = f"Adaptation temps long — étape {i + 1}/{len(order)} ({step.name})"
        if sf is None or saved != stamp:
            if sf is not None:
                _retire(steps_dir, step, saved)
            print(f"{tag}…", file=sys.stderr, flush=True)
            sf = generate(step, full, fragments, article_text, no_api, steps_dir=steps_dir)
            if not guided or step.option_model is None:    # writing offers no choice
                _pick(step, sf, sf.recommended)
        else:
            print(f"{tag} : {_path(steps_dir, step)} réutilisé", file=sys.stderr, flush=True)
            if not sf.picked and not guided:
                _pick(step, sf, sf.recommended)
            elif sf.picked and not sf.fragment:
                _pick(step, sf, sf.picked)
        if steps_dir is not None:
            _save(steps_dir, sf, stamp)
        if not sf.picked:
            print(format_options(step, sf))
            raise AwaitingChoice(step.name)
        fragments[step.name] = sf.fragment
        hard, flags = field_errors(step.name, next(o for o in sf.options if o.id == sf.picked[0]).fields,
                                   fragments, article_text)
        for e in hard + flags:
            print(f"  ⚠  {e}", file=sys.stderr)
        if step.name == stop_after:
            return None
        if step.name == "axe":
            order = steps_in_order(_axe(fragments).get("move"))
        i += 1
    return TempsLongPresentation.model_validate(assemble(fragments))


def adapt(full: ArticleFullAnalysis, no_api: bool = False, article_text: str | None = None,
          steps_dir: Path | None = None, stop_after: str | None = None,
          guided: bool = False) -> TempsLongPresentation | None:
    """The deck, step by step. Unattended, each step takes its recommended pick;
    guided, the run stops at the first step with no pick and prints its options.
    Returns None when it stops (`stop_after` reached, or a choice awaited)."""
    try:
        return _run(full, no_api, article_text, steps_dir, stop_after, guided)
    except AwaitingChoice as e:
        print(f"Awaiting a choice at step {STEP_BY_NAME[e.step].n} ({e.step})", file=sys.stderr)
        return None


# ── Choosing, asking for more, fixing ───────────────────────────────────────

def _earlier(full, steps_dir: Path, step: Step, article_text: str | None) -> tuple[dict, StepFile, str]:
    fragments: dict[str, dict] = {}
    order = steps_in_order(_move_of(steps_dir))
    before = order[:order.index(step)] if step in order else [s for s in STEPS if s.n < step.n]
    for s in before:
        sf, _ = _load(steps_dir, s)
        if sf is None or not sf.picked:
            raise ChoiceError(f"{s.name} has no pick: run `produce --guided` to reach step {step.n} ({step.name})")
        fragments[s.name] = sf.fragment
    sf, saved = _load(steps_dir, step)
    stamp = stamp_for(base_inputs(full, article_text), [fragments[s.name] for s in before])
    if sf is None or saved != stamp:
        raise ChoiceError(f"step {step.n} ({step.name}) is missing or stale: run `produce --guided` to regenerate it")
    return fragments, sf, stamp


def choose(full, steps_dir: Path, step: str, picks: list[str], edits: dict[str, str],
           reason: str = "", article_text: str | None = None) -> list[str]:
    """Keep `picks[0]` at `step`, with the author's rewrites (`ID` or `ID.field` → text).
    Only the pick itself blocks; hard-rule failures come back as warnings."""
    st = STEP_BY_NAME.get(step)
    if st is None or st.option_model is None:
        raise ChoiceError(f"{step!r} offers no options — steps: {', '.join(STEP_NAMES)}")
    fragments, sf, stamp = _earlier(full, steps_dir, st, article_text)
    by_id = {o.id: o for o in sf.options}
    valid = list(st.option_model.model_fields)
    for key in edits:
        oid, _, field = key.partition(".")
        if oid not in by_id:
            raise ChoiceError(f"{step}: unknown option {oid!r}")
        if field and field not in valid:
            raise ChoiceError(f"{step}: unknown field {field!r} — the options have {', '.join(valid)}")
    if len(picks) != 1 or picks[0] not in by_id:
        raise ChoiceError(f"{step}: keep exactly one of {', '.join(by_id)}")
    offered = [{"id": o.id, "text": o.fields.get(st.text_field, "")} for o in sf.options]
    for key, text in edits.items():
        oid, _, field = key.partition(".")
        by_id[oid].fields[field or st.text_field] = text
        by_id[oid].edited = True
    _pick(st, sf, picks)
    chosen = by_id[picks[0]]
    hard, chosen.flags = field_errors(step, chosen.fields, fragments, article_text)
    _save(steps_dir, sf, stamp)
    log_choice(steps_dir.parent, {"step": step, "event": "pick", "offered": offered,
                                  "picked": picks, "edits": edits, "reason": reason})
    return hard


async def verify_pick(steps_dir: Path, step: str, search=None) -> list[str]:
    """Check the picked reference points of `tournants` / `episodes` against the web (see `temps_long_verify`):
    the ⚠ lines for the author, the results kept beside the step and in the choice log. Advisory, never blocking."""
    from agent import temps_long_verify as tv
    st = STEP_BY_NAME[step]
    sf, _ = _load(steps_dir, st)
    if step not in tv.VERIFIED_STEPS or sf is None or not sf.picked:
        return []
    picked = next(o for o in sf.options if o.id == sf.picked[0])
    results = await tv.verify_points(picked.fields, search)
    tv.save(steps_dir, st.n, step, results)
    log_choice(steps_dir.parent, {"step": step, "event": "verify",
                                  "results": [{k: r[k] for k in ("field", "status", "source")} for r in results]})
    return tv.warnings(step, results)


VERIFIED_STEPS = ("tournants", "episodes")


def more(full, steps_dir: Path, step: str, remark: str = "", article_text: str | None = None,
         no_api: bool = False) -> StepFile:
    """Set the options aside and generate others, told what was rejected and why."""
    st = STEP_BY_NAME.get(step)
    if st is None or st.option_model is None:
        raise ChoiceError(f"{step!r} offers no options — steps: {', '.join(STEP_NAMES)}")
    fragments, sf, stamp = _earlier(full, steps_dir, st, article_text)
    remarks = sf.remarks + ([remark] if remark else [])
    new = generate(st, full, fragments, article_text, no_api, rejected=sf.rejected + sf.options,
                   remarks=remarks, steps_dir=steps_dir)
    _save(steps_dir, new, stamp)
    log_choice(steps_dir.parent, {"step": step, "event": "more", "remark": remark})
    return new


# deck field → (owning step, option field): « <step>.<option field> », and the caption
_FIELD_OWNER = {f"{st.name}.{name}": (st.name, name)
                for st in STEPS if st.option_model is not None for name in st.option_model.model_fields}
_FIELD_OWNER["caption"] = ("writing", "caption")
_FIELD_OWNER |= {f"lecture.{k}": ("lecture", k) for k in _READINGS}   # the cards of an older deck


def fix(full, steps_dir: Path, field: str, text: str, article_text: str | None = None) -> str:
    """Overwrite one field of the picked option of the step that owns it (« <step>.<field> »,
    or `caption`), and rebuild that step's fragment. Nothing is regenerated: the later
    steps are re-stamped."""
    if field not in _FIELD_OWNER:
        raise ChoiceError(f"{field!r} is not a deck field — fields: {', '.join(_FIELD_OWNER)}")
    owner_name, option_field = _FIELD_OWNER[field]
    owner = STEP_BY_NAME[owner_name]
    sf, stamp = _load(steps_dir, owner)
    if sf is None or not sf.fragment:
        raise ChoiceError(f"{owner_name} has no fragment to fix: run `produce` first")
    picked = next(o for o in sf.options if o.id == sf.picked[0])
    before, picked.fields[option_field] = picked.fields.get(option_field, ""), text
    picked.edited = True
    sf.fragment = to_fragment(owner, picked)
    _save(steps_dir, sf, stamp)
    base = base_inputs(full, article_text)
    fragments = {s.name: (_load(steps_dir, s)[0].fragment if _load(steps_dir, s)[0] else None) for s in STEPS}
    order = steps_in_order(_move_of(steps_dir))
    for k, s in enumerate(order):
        if k > order.index(owner) and _path(steps_dir, s).exists():
            before_frags = [fragments[x.name] for x in order[:k]]
            if None in before_frags:
                break
            _path(steps_dir, s).with_suffix(".sha256").write_text(stamp_for(base, before_frags))
    log_choice(steps_dir.parent, {"step": owner_name, "event": "fix", "field": field,
                                  "before": before, "after": text})
    return owner_name
