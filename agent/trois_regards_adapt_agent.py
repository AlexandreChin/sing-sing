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
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from agent.carousel_steps.steps import Option
from agent.carousel_steps.store import digest
from models.full_analysis import ArticleFullAnalysis


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
