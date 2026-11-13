"""Adapt agent for the TROIS REGARDS carousel (6 slides).

A guided cascade: first the axe (the wide question, the narrower one the article answers
and the three prisms that read it, never rendered as such), then in slide order the
article's position, the three prism slides, the matrix of what each prism would measure,
and the hook; `writing` finishes with the caption, without pausing. Each step proposes
options with a reason and a ★, the author picks, edits or asks for others (`choose`),
and a pick feeds the later steps. The `prismes` step is picked slot by slot (one option
per prism). Steps are cached in `<format>/adapt_steps/` with a stamp of the inputs and
the earlier picks.

An option's fields are flat strings so that `choose --edit ID.field=TEXT` and `fix`
can rewrite any of them: a card, a matrix column are one line each, their parts
separated by « | » (see `to_fragment`).

Same guided semantics as `agent/anatomie_chiffre_adapt_agent.py`, kept as a module of its own.
"""
import copy
import json
import re
import string
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, create_model

from agent._base import _call_with_retry, _j, medium_directive
from agent.carousel_steps.steps import Option
from agent.carousel_steps.store import digest, log_choice, stamp_for
from agent.instagram_carousel_adapt_agent import _full_analysis_context
from agent.trois_regards_prisms import PRISM_IDS, PRISMS, catalogue_text
from models.full_analysis import ArticleFullAnalysis
from models.trois_regards_presentation import TroisRegardsPresentation

_PROMPTS = Path(__file__).parent / "prompts" / "trois_regards_steps"


class ChoiceError(ValueError):
    """A choice, a request for more options or a fix that cannot be applied."""


class AwaitingChoice(Exception):
    def __init__(self, step: str):
        super().__init__(step)
        self.step = step


# ── Option models and the step table ────────────────────────────────────────

class AxeOption(BaseModel):
    question: str            # the wide question the deck asks
    article_question: str    # the narrower question the article answers
    subject: str             # « la crise du logement »
    prism1: str              # prism ids (see agent.trois_regards_prisms)
    prism2: str
    prism3: str
    media: str               # the prism the article itself takes (one of the three)
    media_grounding: str     # why the article belongs to that prism
    closing: str             # the closing question naming the three prisms


class PositionOption(BaseModel):
    kicker: str
    title: str
    lead: str
    card1: str               # « libellé | texte »
    card2: str
    card3: str
    card4: str


class PrismesOption(BaseModel):
    question: str
    line1: str
    line2: str
    line3: str
    line4: str               # optional
    sources: str             # names separated by « ; »
    media_note: str          # only on the prism the article takes; empty otherwise


class MatriceOption(BaseModel):
    title: str
    col1: str                # « variable | indicateur » — one column per prism, in the axe's order
    col2: str
    col3: str


class HookOption(BaseModel):
    title: str
    promise: str


class WritingCopy(BaseModel):
    caption: str


@dataclass(frozen=True)
class Step:
    n: int
    name: str
    option_model: type[BaseModel] | None     # None for writing
    text_field: str                           # the field that names an option
    analysis_slice: int
    offered: tuple[int, int] = (3, 4)         # options per generation (per slot)
    slots: tuple[str, ...] = ("a",)           # one pick per slot


STEPS: tuple[Step, ...] = (
    Step(1, "axe", AxeOption, "question", 3),
    Step(2, "position", PositionOption, "title", 3),
    Step(3, "prismes", PrismesOption, "question", 3, (2, 3), ("p1", "p2", "p3")),
    Step(4, "matrice", MatriceOption, "title", 3),
    Step(5, "hook", HookOption, "title", 3),
    Step(6, "writing", None, "", 3, (1, 1)),
)
STEP_BY_NAME: dict[str, Step] = {s.name: s for s in STEPS}
STEP_NAMES = [s.name for s in STEPS[:-1]]


class StepFile(BaseModel):
    step: str
    options: list[Option] = Field(default_factory=list)
    rejected: list[Option] = Field(default_factory=list)
    recommended: list[str] = Field(default_factory=list)
    picked: list[str] = Field(default_factory=list)   # empty = awaiting a choice
    fragment: dict = Field(default_factory=dict)
    remarks: list[str] = Field(default_factory=list)


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


def base_inputs(full: ArticleFullAnalysis, article_text: str | None) -> str:
    return digest(full.model_dump_json(), (article_text or "").strip())


def _parts(value: str, n: int) -> list[str]:
    """`value` cut at « | » into `n` trimmed parts, the last one keeping any further bar."""
    parts = [p.strip() for p in value.split("|", n - 1)]
    return parts + [""] * (n - len(parts))


# ── Fragments and assembly ──────────────────────────────────────────────────

def _axe_prisms(fragments: dict[str, dict]) -> list[str]:
    return list(fragments.get("axe", {}).get("axe", {}).get("prisms", []))


def to_fragment(step: Step, picks: list[Option], fragments: dict[str, dict]) -> dict:
    """One pick, or three for `prismes` (slot `pN` takes the Nth prism of the axe)."""
    f = picks[0].fields
    if step.name == "axe":
        prisms = [str(f.get(f"prism{i}", "")).strip() for i in (1, 2, 3)]
        return {"axe": {"question": f.get("question", ""), "article_question": f.get("article_question", ""),
                        "subject": f.get("subject", ""), "prisms": prisms,
                        "media": f.get("media", ""), "media_grounding": f.get("media_grounding", ""),
                        "closing": f.get("closing", "")}}
    if step.name == "position":
        cards = []
        for n in ("card1", "card2", "card3", "card4"):
            if str(f.get(n, "")).strip():
                label, text = _parts(str(f[n]), 2)
                cards.append({"label": label, "text": text})
        return {"position": {"kicker": f.get("kicker", ""), "title": f.get("title", ""),
                             "lead": f.get("lead", ""), "cards": cards}}
    if step.name == "prismes":
        axe_prisms = _axe_prisms(fragments)
        slides = []
        for pick in picks:
            g = pick.fields
            n = int(pick.slot[1:])
            slide = {"prism": axe_prisms[n - 1] if n <= len(axe_prisms) else "",
                     "question": g.get("question", ""),
                     "lines": [str(g[k]).strip() for k in ("line1", "line2", "line3", "line4")
                               if str(g.get(k, "")).strip()],
                     "sources": [s.strip() for s in str(g.get("sources", "")).split(";") if s.strip()]}
            if str(g.get("media_note", "")).strip():
                slide["media_note"] = str(g["media_note"]).strip()
            slides.append(slide)
        return {"prisms": slides}
    if step.name == "matrice":
        axe_prisms = _axe_prisms(fragments)
        columns = []
        for i in (1, 2, 3):
            variable, indicator = _parts(str(f.get(f"col{i}", "")), 2)
            columns.append({"prism": axe_prisms[i - 1] if i <= len(axe_prisms) else "",
                            "variable": variable, "indicator": indicator})
        return {"matrix": {"title": f.get("title", ""), "columns": columns}}
    if step.name == "hook":
        return {"hook": {"title": f.get("title", ""), "promise": f.get("promise", "")}}
    return {"caption": f.get("caption", "")}


def _merge(into: dict, frag: dict) -> None:
    for k, v in frag.items():
        if isinstance(v, dict) and isinstance(into.get(k), dict):
            _merge(into[k], v)
        else:
            into[k] = v


def assemble(fragments: dict[str, dict]) -> dict:
    deck: dict = {}
    for step in STEPS:
        if step.name in fragments:
            _merge(deck, copy.deepcopy(fragments[step.name]))
    return deck


# ── Hard rules, flags and caps ──────────────────────────────────────────────

# (step, field) -> ("chars" | "words", cap); a cap is never typed in a prompt: `{{cap:step.field}}` (see `fill_caps`)
_CAPS: dict[tuple[str, str], tuple[str, int]] = {
    ("axe", "question"): ("chars", 60), ("axe", "subject"): ("chars", 36),
    ("axe", "closing"): ("chars", 110), ("axe", "media_grounding"): ("chars", 120),
    ("position", "kicker"): ("chars", 30), ("position", "title"): ("chars", 46), ("position", "lead"): ("chars", 90),
    ("prismes", "question"): ("chars", 64),
    **{("prismes", f"line{i}"): ("chars", 80) for i in (1, 2, 3, 4)},
    ("prismes", "media_note"): ("chars", 90),
    ("matrice", "title"): ("chars", 34),
    ("hook", "title"): ("chars", 70), ("hook", "promise"): ("chars", 100),
}
# (step, field) -> the parts of a « a | b » field, each with its cap in characters
_PART_CAPS: dict[tuple[str, str], tuple[tuple[str, int], ...]] = {
    **{("position", f"card{i}"): (("label", 30), ("text", 108)) for i in (1, 2, 3, 4)},
    **{("matrice", f"col{i}"): (("variable", 60), ("indicator", 40)) for i in (1, 2, 3)},
}
_SOURCE_MAX = 30       # characters in one source name
_SOURCES_MAX = 3       # names on one prism slide
_REQUIRED = {"axe": ("question", "article_question", "subject", "prism1", "prism2", "prism3", "media",
                     "media_grounding", "closing"),
             "position": ("kicker", "title", "lead", "card1", "card2", "card3"),
             "prismes": ("question", "line1", "line2", "line3", "sources"),
             "matrice": ("title", "col1", "col2", "col3"),
             "hook": ("title", "promise")}
_ACCUSING = re.compile(r"\b(biais|manipulation|manipul\w+|mensonges?|trompeu\w+|fallacieu\w+|sophismes?)\b", re.I)
_BLAMING = re.compile(r"\b(oublie(?:nt|s)?|ignore(?:nt|s)?|omet(?:s|tent)?|néglige(?:nt|s)?|ne (?:dit|disent) pas)\b", re.I)
_PRESCRIPTIVE = re.compile(r"\b(il faut|doit|doivent|devrait|devraient)\b", re.I)
_QUOTED = re.compile(r"«[^»]*»")
_HASHTAG = re.compile(r"#\w+")
_DIGIT = re.compile(r"\d")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_YEAR = re.compile(r"(?:1[5-9]|20)\d\d")
_URL = re.compile(r"https?:|www\.|\.com/|\.fr/", re.I)
_PROMISE = re.compile(r"Trois regards sur (\S.*?) ; à vous d'en juger\.")
_NO_DOMINANT = re.compile(r"aucun\b.{0,30}\bdomin|pas de prisme dominant|ne domine pas", re.I)
_NEAR_IDENTICAL = 0.6
_STOP = frozenset("""alors après aussi autre autres avant avoir avons cette celle celui comme comment dans donc elle elles
entre être leur leurs mais même moins plus pour quel quelle quelles quels sont sous tout toute toutes tous très vers
vous nous cela ceux dont lors quand quoi sans selon peut peuvent faire fait ainsi encore depuis""".split())


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("’", "'")).lower()
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w']+", " ", s)).strip()


def _key_words(s: str) -> set[str]:
    """Stems (first five letters) of the words of 5+ letters that are not a stop word."""
    return {w[:5] for w in re.findall(r"[a-z]{5,}", _plain(s)) if w not in _STOP}


def _bare(s: str) -> str:
    return re.sub(r"\*\*", "", s)


def _axe(fragments: dict[str, dict]) -> dict:
    return fragments.get("axe", {}).get("axe", {})


def field_errors(step: str, fields: dict[str, Any], fragments: dict[str, dict], article: str | None,
                 slot: str = "a") -> tuple[list[str], list[str]]:
    """(hard, flags) on one step's fields (`slot` is the prism slot for `prismes`), given the earlier fragments."""
    hard, flags = [], []
    axe = _axe(fragments)
    question_words = _key_words(str(axe.get("question", "")))
    for name, value in fields.items():
        if not isinstance(value, str):
            continue
        if (rule := _CAPS.get((step, name))):
            kind, cap = rule
            n = len(_bare(value)) if kind == "chars" else len(_bare(value).split())
            if n > cap:
                hard.append(f"{step}.{name} is {n} {kind} (max {cap})")
        if step == "writing":
            continue
        outside = _QUOTED.sub("", value)
        if (m := _ACCUSING.search(outside)):
            hard.append(f"{step}.{name} uses an accusing word « {m.group(0)} » — the carousel gives tools, not verdicts")
        if (m := _BLAMING.search(outside)):
            hard.append(f"{step}.{name} blames the article (« {m.group(0)} ») — say what a prism looks at, never what the article lacks")
        if step == "matrice" and (m := _PRESCRIPTIVE.search(outside)):
            hard.append(f"{step}.{name} is prescriptive (« {m.group(0)} ») — the matrix says what to measure, never what to do")
        if step == "matrice" and _DIGIT.search(value):
            hard.append(f"{step}.{name} holds a digit — the matrix is outside the article's frame and adds no figure")
    for (st, name), caps in _PART_CAPS.items():
        if st == step and str(fields.get(name, "")).strip():
            parts = _parts(fields[name], len(caps))
            for (part_name, cap), part in zip(caps, parts):
                if len(_bare(part)) > cap:
                    hard.append(f"{step}.{name}: the {part_name} is {len(_bare(part))} characters (max {cap})")
            if not all(parts):
                hard.append(f"{step}.{name} must read « {' | '.join(n for n, _ in caps)} »")
    for name in _REQUIRED.get(step, ()):
        if not str(fields.get(name, "")).strip():
            hard.append(f"{step}.{name} is empty")

    def question(name: str, value: str) -> None:
        if value.strip() and not value.strip().endswith("?"):
            hard.append(f"{step}.{name} must be a question ending in « ? »")

    if step == "axe":
        prisms = [str(fields.get(f"prism{i}", "")).strip() for i in (1, 2, 3)]
        named = [p for p in prisms if p]
        if len(set(named)) < len(named):
            hard.append("axe: the three prisms must be distinct")
        hard += [f"axe.prism{i} « {p} » is not in the catalogue ({', '.join(PRISM_IDS)})"
                 for i, p in enumerate(prisms, 1) if p and p not in PRISM_IDS]
        media = str(fields.get("media", "")).strip()
        if media and media not in prisms:
            hard.append(f"axe.media « {media} » is not one of the three prisms")
        question("question", str(fields.get("question", "")))
        question("closing", str(fields.get("closing", "")))
        closing = str(fields.get("closing", ""))
        if _NO_DOMINANT.search(str(fields.get("media_grounding", ""))):
            flags.append("axe: no prism clearly dominates the article — the media's prism is the closest one; "
                         "the « regard du média » line will say only what the article does with it")
        if re.search(r"\bou\b", closing):
            flags.append("axe.closing contains « ou » — it may read as a binary choice; the question should stay open")
        if closing.strip() and not _key_words(closing) & _key_words(str(fields.get("question", ""))):
            flags.append("axe.closing shares no key word with the axe's question")
        low = _plain(closing)
        missing = [PRISMS[p].name for p in prisms if p in PRISMS and _plain(PRISMS[p].name)[:6] not in low]
        if closing.strip() and missing:
            flags.append(f"axe.closing does not name the prism(s) {', '.join(missing)} — the closing line names the three")
    if step == "position":
        for name in ("title", "card1", "card2", "card3", "card4", "lead"):
            value = str(fields.get(name, ""))
            if article:
                flags += [f"position.{name}: {q} does not appear word for word in the source"
                          for q in _QUOTED.findall(value) if _norm(q.strip("« »  ")) not in _norm(article)]
    if step == "prismes":
        lines = [str(fields.get(f"line{i}", "")) for i in (1, 2, 3, 4)]
        for label, text in (("question", str(fields.get("question", ""))), *((f"line{i}", t) for i, t in enumerate(lines, 1))):
            if any(not _YEAR.fullmatch(n) for n in _NUMBER.findall(text)):
                hard.append(f"prismes.{label} holds a digit — only a year (1500–2099) is allowed outside the article's frame")
        raw = str(fields.get("sources", ""))
        names = [s.strip() for s in raw.split(";") if s.strip()]
        if raw.strip() and not names:
            hard.append("prismes.sources names no source — it takes 1 to 3 organisations or series, separated by « ; »")
        if len(names) > _SOURCES_MAX:
            hard.append(f"prismes.sources has {len(names)} names (max {_SOURCES_MAX})")
        hard += [f"prismes.sources: « {n} » is {len(_bare(n))} characters (max {_SOURCE_MAX})"
                 for n in names if len(_bare(n)) > _SOURCE_MAX]
        if _URL.search(raw):
            hard.append("prismes.sources holds a URL — name the organisation or series, never a link")
        if _DIGIT.search(raw):
            hard.append("prismes.sources holds a digit — name an organisation or a series, never a figure")
        note = str(fields.get("media_note", "")).strip()
        axe_prisms = _axe_prisms(fragments)
        n = int(slot[1:]) if re.fullmatch(r"p\d", slot) else 0
        if axe.get("media") and 1 <= n <= len(axe_prisms):
            is_media = axe_prisms[n - 1] == axe["media"]
            if is_media and not note:
                hard.append("prismes.media_note is empty — this is the media's prism, it carries the « regard du média » line")
            if not is_media and note:
                hard.append("prismes.media_note must be empty — only the media's prism carries it")
        if article:
            flags += [f"prismes.media_note: {q} does not appear word for word in the source"
                      for q in _QUOTED.findall(note) if _norm(q.strip("« »  ")) not in _norm(article)]
        if question_words and str(fields.get("question", "")).strip() \
                and not _key_words(str(fields.get("question", ""))) & question_words:
            flags.append("prismes.question shares no key word with the axe's question — the prism should answer that question")
        mine = _key_words(" ".join([str(fields.get("question", "")), *lines]))
        for k, other in enumerate(fragments.get("prismes", {}).get("prisms", []), 1):
            if k == n:
                continue
            theirs = _key_words(" ".join([other.get("question", ""), *other.get("lines", [])]))
            if mine and theirs and len(mine & theirs) / min(len(mine), len(theirs)) >= _NEAR_IDENTICAL:
                flags.append(f"prismes: this slide and the one of slot p{k} say nearly the same thing — "
                             "each prism should bring its own reading")
    if step == "matrice":
        question("title", str(fields.get("title", "")))
        if re.search(r"\bou\b", str(fields.get("title", ""))):
            flags.append("matrice.title contains « ou » — it may read as a binary choice; the question should stay open")
        for name in ("col1", "col2", "col3"):
            value = str(fields.get(name, "")).strip()
            if value and question_words and not _key_words(value) & question_words:
                flags.append(f"matrice.{name} shares no key word with the axe's question — it should say where the prism "
                             "starts to answer that question")
    if step == "hook":
        question("title", str(fields.get("title", "")))
        promise = str(fields.get("promise", "")).strip()
        m = _PROMISE.fullmatch(_bare(promise)) if promise else None
        if promise and not m:
            hard.append("hook.promise must read « Trois regards sur <sujet> ; à vous d'en juger. » with a subject")
        elif m and axe.get("subject") and _norm(axe["subject"]) != _norm(m.group(1)):
            flags.append(f"hook.promise names « {m.group(1)} » but the axe's subject is « {axe['subject']} » — same subject as the question")
    if step == "writing":
        tags = _HASHTAG.findall(fields.get("caption", ""))
        if len(tags) != 4:
            hard.append(f"writing.caption has {len(tags)} hashtag(s), must have 4")
    return hard, flags


_CAP = re.compile(r"\{\{cap:([\w.]+)\}\}")


def prompt_caps() -> dict[str, int]:
    """Every cap a prompt may quote, by name (« {{cap:prismes.line1}} »): the prompts never write the numbers,
    so they cannot drift from the rules the options are checked against."""
    caps = {f"{s}.{f}": n for (s, f), (_, n) in _CAPS.items()}
    for (s, f), parts in _PART_CAPS.items():
        for part, n in parts:
            caps[f"{s}.{f}.{part}"] = n
            caps[f"{s}.{re.sub(r'\d+$', '', f)}.{part}"] = n
    return caps | {"prismes.source": _SOURCE_MAX, "prismes.sources": _SOURCES_MAX}


def fill_caps(text: str) -> str:
    caps = prompt_caps()
    return _CAP.sub(lambda m: str(caps[m.group(1)]), text)


# ── Picks and slots ─────────────────────────────────────────────────────────

def _multi(step: Step) -> bool:
    return len(step.slots) > 1


def _by_slot(step: Step, options: list[Option]) -> list[Option]:
    """`options` in the step's slot order (stable inside a slot)."""
    order = {s: i for i, s in enumerate(step.slots)}
    return sorted(options, key=lambda o: order.get(o.slot, len(order)))


def _complete(step: Step, sf: StepFile) -> bool:
    """The step holds one pick per slot (a `more` on one prism leaves the others' picks only)."""
    slot_of = {o.id: o.slot for o in sf.options}
    return bool(sf.picked) and sorted(slot_of.get(p, "") for p in sf.picked) == sorted(step.slots)


def _chosen(step: Step, sf: StepFile) -> list[Option]:
    by_id = {o.id: o for o in sf.options}
    return _by_slot(step, [by_id[p] for p in sf.picked if p in by_id])


def _pick_error(step: Step, options: list[Option], picks: list[str]) -> str | None:
    slot_of = {o.id: o.slot for o in options}
    if (unknown := [p for p in picks if p not in slot_of]):
        return f"{step.name}: unknown option(s) {', '.join(unknown)} — options: {', '.join(slot_of)}"
    if _multi(step):
        if sorted(slot_of[p] for p in picks) != sorted(step.slots):
            return f"{step.name}: keep exactly one option per prism ({', '.join(step.slots)})"
    elif len(picks) != 1:
        return f"{step.name}: keep exactly one of {', '.join(slot_of)}"
    return None


def _pick(step: Step, sf: StepFile, picks: list[str], fragments: dict[str, dict]) -> None:
    sf.picked = list(picks)
    chosen = _chosen(step, sf)
    sf.picked = [o.id for o in chosen]
    sf.fragment = to_fragment(step, chosen, fragments)


def _fill(step: Step, sf: StepFile) -> list[str]:
    """The picks kept, completed with the recommended option of every slot left without one."""
    slot_of = {o.id: o.slot for o in sf.options}
    taken = {slot_of.get(p) for p in sf.picked}
    return [p for p in sf.picked if p in slot_of] + [r for r in sf.recommended if slot_of.get(r) not in taken]


def _pick_rules(step: Step, sf: StepFile, fragments: dict[str, dict], article_text: str | None) -> tuple[list[str], list[str]]:
    """(hard, flags) of the picked options, given the other steps' fragments; a prism's are
    prefixed with its slot, and checked against the other prism slides of the pick."""
    others = {k: v for k, v in fragments.items() if k != step.name}
    if _multi(step) and sf.fragment:
        others[step.name] = sf.fragment
    hard, flags = [], []
    for o in _chosen(step, sf):
        h, o.flags = field_errors(step.name, o.fields, others, article_text, o.slot)
        tag = f"{o.slot}: " if _multi(step) else ""
        hard += [tag + e for e in h]
        flags += [tag + f for f in o.flags]
    return hard, flags


# ── Generating a step ───────────────────────────────────────────────────────

def _response_model(step: Step, slots: tuple[str, ...] | None = None):
    if step.option_model is None:
        return WritingCopy
    extra: dict[str, Any] = {"reason": (str, ...)}
    if _multi(step):
        extra["slot"] = (Literal[tuple(slots or step.slots)], ...)
    proposal = create_model(f"{step.name.title()}Proposal", __base__=step.option_model, **extra)
    return create_model(f"{step.name.title()}Response", options=(list[proposal], ...), recommended=(list[int], ...))


def _prompt(step: Step) -> str:
    body = (_PROMPTS / f"{step.n}_{step.name}.md").read_text(encoding="utf-8")
    if step.option_model is None:
        return body
    return (_PROMPTS / "0_options.md").read_text(encoding="utf-8") + "\n" + body


def _to_options(step: Step, proposals: list, rejected: list[Option]) -> list[Option]:
    """Ids `a`, `b`, … (one slot) or `<slot><letter>` (`p1a`, `p2c`), continuing after `rejected`."""
    used = {o.id for o in rejected}
    out = []
    for p in proposals:
        slot = getattr(p, "slot", "a")
        prefix = slot if _multi(step) else ""
        oid = next(prefix + c for c in string.ascii_lowercase if prefix + c not in used)
        used.add(oid)
        out.append(Option(id=oid, slot=slot, reason=p.reason,
                          fields=p.model_dump(mode="json", exclude={"slot", "reason"})))
    return out


def _slots_note(step: Step, fragments: dict, only_slot: str | None) -> str:
    """For `prismes`: which prism each slot writes, and how many options per slot."""
    prisms = _axe_prisms(fragments)
    media = _axe(fragments).get("media", "")
    named = [f"- {s} = {p} ({PRISMS[p].name if p in PRISMS else p})" + (" — le prisme du média" if p == media else "")
             for s, p in zip(step.slots, prisms)]
    lo, hi = step.offered
    if only_slot:
        ask = (f"Écris {lo} à {hi} options pour l'emplacement {only_slot} SEULEMENT (les autres prismes sont gardés), "
               f"chacune avec `slot` = « {only_slot} » ; `recommended` : un seul indice.")
    else:
        ask = (f"Écris {lo} à {hi} options PAR emplacement ({', '.join(step.slots)}), chacune avec son `slot` ; "
               f"`recommended` : {len(step.slots)} indices, un par emplacement.")
    return "PRISMES PAR EMPLACEMENT :\n" + "\n".join(named) + "\n" + ask


def _message(step: Step, full: ArticleFullAnalysis, fragments: dict, article_text: str | None,
             rejected: list[Option], remarks: list[str], only_slot: str | None = None) -> str:
    parts = [_full_analysis_context(full, step.analysis_slice)]
    if article_text:
        parts.append(f"MÉDIA (transcription ou texte) :\n{article_text.strip()}")
    if fragments:
        parts.append(f"CHOIX FIXÉS (ne les réécris pas) :\n{_j(fragments)}")
    parts.append(f"CATALOGUE DES PRISMES :\n{catalogue_text()}")
    parts += [(_PROMPTS / "0_shared.md").read_text(encoding="utf-8"), _prompt(step)]
    if _multi(step):
        parts.append(_slots_note(step, fragments, only_slot))
    if rejected:
        parts.append(f"DÉJÀ PROPOSÉES ET ÉCARTÉES :\n{_j([o.fields for o in rejected])}")
    if remarks:
        parts.append("REMARQUES DE L'AUTEUR :\n" + "\n".join(f"- {r}" for r in remarks))
    if (directive := medium_directive(full.article_metadata.medium)):
        parts.append(directive)
    return "\n\n---\n\n".join(parts)


def _failed(step: Step, steps_dir: Path | None, data, errors: list[str]) -> RuntimeError:
    where = ""
    if steps_dir is not None:
        steps_dir.mkdir(parents=True, exist_ok=True)
        path = steps_dir / f"{step.n}_{step.name}.failed.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        where = f" (raw answer saved to {path})"
    return RuntimeError(f"step {step.n} ({step.name}): the model's answer is still invalid after the retries"
                        f"{where}:\n" + "\n".join(f"- {e}" for e in errors))


def _coverage_errors(step: Step, options: list[Option], slots: tuple[str, ...]) -> list[str]:
    lo, hi = step.offered
    if not _multi(step):
        n = len(options)
        return [] if lo <= n <= hi else [f"options: {n} option(s), must have {lo}–{hi}"]
    errors = [f"options: slot {o.slot!r} is not asked for" for o in options if o.slot not in slots]
    for slot in slots:
        n = sum(o.slot == slot for o in options)
        if not lo <= n <= hi:
            errors.append(f"options: slot {slot!r} has {n} option(s), must have {lo}–{hi}")
    return errors


def _recommended(step: Step, options: list[Option], indices: list[int],
                 slots: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """The recommended ids, one per slot in slot order, or the errors."""
    what = "exactly one valid index" if len(slots) == 1 else \
        f"{len(slots)} valid indices, one per slot ({', '.join(slots)})"
    if len(indices) != len(slots) or any(not 0 <= i < len(options) for i in indices):
        return [], [f"recommended: {what}"]
    chosen = [options[i] for i in indices]
    if sorted(o.slot for o in chosen) != sorted(slots):
        return [], [f"recommended: {what} — got slots {', '.join(o.slot for o in chosen)}"]
    return [o.id for o in _by_slot(step, chosen)], []


def generate(step: Step, full: ArticleFullAnalysis, fragments: dict[str, dict], article_text: str | None,
             no_api: bool, rejected: list[Option] = [], remarks: list[str] = [],
             steps_dir: Path | None = None, only_slot: str | None = None) -> StepFile:
    """One model call for `step`'s options (writing: its copy), checked against the
    rules. Nothing is picked. For `prismes`, 2–3 options per slot (or for `only_slot`
    alone) and one recommended per slot. An answer still breaking a hard rule after the
    retries raises RuntimeError."""
    slots = (only_slot,) if only_slot else step.slots
    model = _response_model(step, slots)
    message = _message(step, full, fragments, article_text, rejected, remarks, only_slot)
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

    def parse(data):
        resp = model.model_validate(data)
        options = _to_options(step, resp.options, rejected)
        return options, *_recommended(step, options, resp.recommended, slots)

    def validator(data):
        options, _, errors = parse(data)
        errors = _coverage_errors(step, options, slots) + errors
        for k, o in enumerate(options):
            errors += [f"options[{k}]: {e}" for e in
                       field_errors(step.name, o.fields, fragments, article_text, o.slot)[0]]
        return errors

    data = _call_with_retry(message, model.model_json_schema(), validator=validator, no_api=no_api, label=step.name)
    try:
        options, recommended, errors = parse(data)
    except ValidationError as exc:
        raise _failed(step, steps_dir, data, [str(exc)]) from None
    if not options or errors or any(not any(o.slot == s for o in options) for s in slots):
        raise _failed(step, steps_dir, data, errors or ["a slot has no option"])
    for o in options:
        o.flags = field_errors(step.name, o.fields, fragments, article_text, o.slot)[1]
    return StepFile(step=step.name, options=_by_slot(step, options), rejected=rejected,
                    recommended=recommended, remarks=remarks)


# ── Showing a step ──────────────────────────────────────────────────────────

def format_options(step: Step, sf: StepFile) -> str:
    """The options as the author reads them: one block per slot for `prismes`, ★ on the recommended."""
    lines = [f"[{step.name}]"]
    for slot in step.slots:
        opts = [o for o in sf.options if o.slot == slot]
        if not opts:
            continue
        if _multi(step):
            lines.append(f"[{slot}]")
        for o in opts:
            name = o.fields.get(step.text_field, "")
            lines.append(f"{o.id} — {name}" + (" ★" if o.id in sf.recommended else ""))
            lines += [f"   · {k} : {v}" for k, v in o.fields.items() if k != step.text_field]
            lines.append(f"   ↳ {o.reason}")
            lines += [f"   ⚠ {flag}" for flag in o.flags]
        if _multi(step):
            lines.append("")
    return "\n".join(lines).rstrip()


# ── The run ─────────────────────────────────────────────────────────────────

def pending_step(steps_dir: Path) -> str | None:
    for s in STEPS[:-1]:
        sf, _ = _load(steps_dir, s)
        if sf is not None and not _complete(s, sf):
            return s.name
    return None


def _run(full, no_api, article_text, steps_dir, stop_after, guided) -> TroisRegardsPresentation | None:
    base = base_inputs(full, article_text)
    fragments: dict[str, dict] = {}
    for step in STEPS:
        stamp = stamp_for(base, [fragments[s.name] for s in STEPS if s.n < step.n])
        sf, saved = _load(steps_dir, step) if steps_dir is not None else (None, "")
        tag = f"Adaptation trois_regards — étape {step.n}/{len(STEPS)} ({step.name})"
        if sf is None or saved != stamp:
            if sf is not None:
                _retire(steps_dir, step, saved)
            print(f"{tag}…", file=sys.stderr, flush=True)
            sf = generate(step, full, fragments, article_text, no_api, steps_dir=steps_dir)
            if not guided or step.option_model is None:    # writing offers no choice
                _pick(step, sf, sf.recommended, fragments)
        else:
            print(f"{tag} : {_path(steps_dir, step)} réutilisé", file=sys.stderr, flush=True)
            if not _complete(step, sf) and not guided:
                _pick(step, sf, _fill(step, sf), fragments)
            elif _complete(step, sf) and not sf.fragment:
                _pick(step, sf, sf.picked, fragments)
        if steps_dir is not None:
            _save(steps_dir, sf, stamp)
        if not _complete(step, sf):
            print(format_options(step, sf))
            raise AwaitingChoice(step.name)
        fragments[step.name] = sf.fragment
        hard, flags = _pick_rules(step, sf, fragments, article_text)
        for e in hard + flags:
            print(f"  ⚠  {e}", file=sys.stderr)
        if step.name == stop_after:
            return None
    return TroisRegardsPresentation.model_validate(assemble(fragments))


def adapt(full: ArticleFullAnalysis, no_api: bool = False, article_text: str | None = None,
          steps_dir: Path | None = None, stop_after: str | None = None,
          guided: bool = False) -> TroisRegardsPresentation | None:
    """The deck, step by step. Unattended, each step takes its recommended pick(s);
    guided, the run stops at the first step with no complete pick and prints its options.
    Returns None when it stops (`stop_after` reached, or a choice awaited)."""
    try:
        return _run(full, no_api, article_text, steps_dir, stop_after, guided)
    except AwaitingChoice as e:
        print(f"Awaiting a choice at step {STEP_BY_NAME[e.step].n} ({e.step})", file=sys.stderr)
        return None


# ── Choosing, asking for more, fixing ───────────────────────────────────────

def _earlier(full, steps_dir: Path, step: Step, article_text: str | None) -> tuple[dict, StepFile, str]:
    fragments: dict[str, dict] = {}
    for s in STEPS:
        if s.n >= step.n:
            break
        sf, _ = _load(steps_dir, s)
        if sf is None or not _complete(s, sf):
            raise ChoiceError(f"{s.name} has no pick: run `produce --guided` to reach step {step.n} ({step.name})")
        fragments[s.name] = sf.fragment
    sf, saved = _load(steps_dir, step)
    stamp = stamp_for(base_inputs(full, article_text), [fragments[s.name] for s in STEPS if s.n < step.n])
    if sf is None or saved != stamp:
        raise ChoiceError(f"step {step.n} ({step.name}) is missing or stale: run `produce --guided` to regenerate it")
    return fragments, sf, stamp


def _option_step(step: str) -> Step:
    st = STEP_BY_NAME.get(step)
    if st is None or st.option_model is None:
        raise ChoiceError(f"{step!r} offers no options — steps: {', '.join(STEP_NAMES)}")
    return st


def choose(full, steps_dir: Path, step: str, picks: list[str], edits: dict[str, str],
           reason: str = "", article_text: str | None = None) -> list[str]:
    """Keep `picks` at `step` — one id, or one per prism for `prismes` — with the author's
    rewrites (`ID` or `ID.field` → text). Only the pick itself blocks; hard-rule failures
    come back as warnings."""
    st = _option_step(step)
    fragments, sf, stamp = _earlier(full, steps_dir, st, article_text)
    by_id = {o.id: o for o in sf.options}
    valid = list(st.option_model.model_fields)
    for key in edits:
        oid, _, field = key.partition(".")
        if oid not in by_id:
            raise ChoiceError(f"{step}: unknown option {oid!r}")
        if field and field not in valid:
            raise ChoiceError(f"{step}: unknown field {field!r} — the options have {', '.join(valid)}")
    if (error := _pick_error(st, sf.options, picks)):
        raise ChoiceError(error)
    offered = [{"id": o.id, "slot": o.slot, "text": o.fields.get(st.text_field, "")} for o in sf.options]
    for key, text in edits.items():
        oid, _, field = key.partition(".")
        by_id[oid].fields[field or st.text_field] = text
        by_id[oid].edited = True
    _pick(st, sf, picks, fragments)
    hard, _ = _pick_rules(st, sf, fragments, article_text)
    _save(steps_dir, sf, stamp)
    log_choice(steps_dir.parent, {"step": step, "event": "pick", "offered": offered,
                                  "picked": sf.picked, "edits": edits, "reason": reason})
    return hard


def more(full, steps_dir: Path, step: str, remark: str = "", article_text: str | None = None,
         no_api: bool = False, slot: str | None = None) -> StepFile:
    """Set the options aside and generate others, told what was rejected and why. With
    `slot` (`p2`, or the prism id the axe puts there), only that prism's options are
    regenerated: the other slots keep their options and their picks, and the stamp is kept."""
    st = _option_step(step)
    fragments, sf, stamp = _earlier(full, steps_dir, st, article_text)
    if slot is not None:
        by_prism = dict(zip(_axe_prisms(fragments), st.slots))
        slot = by_prism.get(slot, slot)
        if not _multi(st) or slot not in st.slots:
            raise ChoiceError(f"{step}: unknown slot {slot!r} — "
                              + (f"slots: {', '.join(st.slots)}" if _multi(st) else "this step has a single slot"))
    remarks = sf.remarks + ([remark] if remark else [])
    if slot is None:
        new = generate(st, full, fragments, article_text, no_api, rejected=sf.rejected + sf.options,
                       remarks=remarks, steps_dir=steps_dir)
    else:
        slot_of = {o.id: o.slot for o in sf.options}
        old = [o for o in sf.options if o.slot == slot]
        gen = generate(st, full, fragments, article_text, no_api, rejected=sf.rejected + old,
                       remarks=remarks, steps_dir=steps_dir, only_slot=slot)
        kept = [o for o in sf.options if o.slot != slot]
        by_id = {o.id: o for o in kept + gen.options}
        recommended = [r for r in sf.recommended if slot_of.get(r) != slot] + gen.recommended
        new = StepFile(step=st.name, options=_by_slot(st, kept + gen.options), rejected=gen.rejected,
                       recommended=[o.id for o in _by_slot(st, [by_id[r] for r in recommended])],
                       picked=[p for p in sf.picked if slot_of.get(p) != slot], remarks=remarks)
    _save(steps_dir, new, stamp)
    log_choice(steps_dir.parent, {"step": step, "event": "more", "remark": remark, "slot": slot})
    return new


# deck field → (owning step, slot or None, option field): « <step>.<field> », « prismes.<slot>.<field> », the caption
_FIELD_OWNER: dict[str, tuple[str, str | None, str]] = {
    (f"{st.name}.{slot}.{name}" if _multi(st) else f"{st.name}.{name}"): (st.name, slot if _multi(st) else None, name)
    for st in STEPS if st.option_model is not None for slot in st.slots for name in st.option_model.model_fields}
_FIELD_OWNER["caption"] = ("writing", None, "caption")


def fix(full, steps_dir: Path, field: str, text: str, article_text: str | None = None) -> tuple[str, list[str]]:
    """Overwrite one field of the picked option of the step that owns it (« <step>.<field> »,
    « prismes.<slot>.<field> », or `caption`), and rebuild the fragments from that step on.
    Nothing is regenerated: the later steps are re-stamped. Returns the owner step and the
    hard-rule failures of the rewritten field and of every later step, as warnings: like
    `choose`, `fix` leaves the last word to the author."""
    if field not in _FIELD_OWNER:
        raise ChoiceError(f"{field!r} is not a deck field — fields: {', '.join(_FIELD_OWNER)}")
    owner_name, slot, option_field = _FIELD_OWNER[field]
    owner = STEP_BY_NAME[owner_name]
    sf, _ = _load(steps_dir, owner)
    if sf is None or not sf.fragment or not _complete(owner, sf):
        raise ChoiceError(f"{owner_name} has no fragment to fix: run `produce` first")
    picked = next(o for o in _chosen(owner, sf) if slot is None or o.slot == slot)
    before, picked.fields[option_field] = picked.fields.get(option_field, ""), text
    picked.edited = True
    base = base_inputs(full, article_text)
    fragments: dict[str, dict] = {}
    warnings: list[str] = []
    for s in STEPS:
        current, saved = _load(steps_dir, s)
        if s.n == owner.n:
            current = sf
        if current is None or not _complete(s, current):
            if s.n <= owner.n:
                raise ChoiceError(f"{s.name} has no pick: run `produce` first")
            break                                  # nothing later can be re-stamped
        if s.n < owner.n:
            fragments[s.name] = current.fragment
            continue
        if s.n > owner.n:
            saved = stamp_for(base, [fragments[t.name] for t in STEPS if t.n < s.n])
        current.fragment = to_fragment(s, _chosen(s, current), fragments)   # a prism id follows the axe
        fragments[s.name] = current.fragment
        warnings += _pick_rules(s, current, fragments, article_text)[0]
        _save(steps_dir, current, saved)
    log_choice(steps_dir.parent, {"step": owner_name, "event": "fix", "field": field,
                                  "before": before, "after": text})
    return owner_name, warnings
