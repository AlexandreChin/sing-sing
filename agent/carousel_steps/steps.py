"""The eight adapt steps: each proposes options, the author keeps some, and the
kept ones become a deck fragment. Pure and model-free — the runner calls the
model; this module defines the steps, checks the picks and assembles the deck.

`fragments` are keyed by step name ("question", "enjeu", …); the question step's
thesis frame travels beside them in `fragments["question_frame"]`."""
import copy
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from models.instagram_carousel_presentation import (
    CarouselGoFurtherItem,
    KeyTakeaway,
    Pictogram,
)

StepName = Literal["question", "enjeu", "idees", "moments", "contexte", "socle", "hook", "writing"]


class Option(BaseModel):
    """One proposal. `fields` holds the step's option model; `reason` is never rendered."""
    id: str
    slot: str
    reason: str
    fields: dict[str, Any]
    edited: bool = False
    flags: list[str] = Field(default_factory=list)


# ── Option models ───────────────────────────────────────────────────────────

class TextOption(BaseModel):
    text: str


class MomentOption(BaseModel):
    moment: str
    quote: str
    quote_original: str = ""
    lens_ref: str
    factcheck: str = ""
    theme: str = ""
    centrality: int = 0
    kind: str = ""
    role: str = ""
    rationale: str = ""


class ContexteOption(BaseModel):
    label: str
    text: str


class SocleOption(BaseModel):
    """Headline and présupposé options carry `text`; objection options the rest."""
    text: str = ""
    argument: str = ""
    alternative: str = ""
    targets_slot: str = ""


class HookOption(BaseModel):
    topic: str
    sub_topic: str
    subtitle: str
    headline: str


class BeatCopy(BaseModel):
    """The writing step's copy for one selected beat, `index` into the pool."""
    index: int
    lens_question: str
    note: str
    answer: str
    figure: str = ""
    figure_label: str = ""
    figure_caption: str = ""
    pictogram: Pictogram | None = None


class WritingCopy(BaseModel):
    beats: list[BeatCopy]
    why_selected: str
    selection_headline: str
    key_takeaways: list[KeyTakeaway]
    go_further: list[CarouselGoFurtherItem]
    where_to_look: list[str]
    caption: str


@dataclass(frozen=True)
class Step:
    n: int
    name: StepName
    option_model: type[BaseModel] | None            # None for writing
    slots: dict[str, tuple[int, int, int]]          # slot → (min offered, max offered, kept)
    text_field: str
    analysis_slice: int
    keep_range: tuple[int, int] | None = None       # replaces `kept` when the count is a range


STEPS: tuple[Step, ...] = (
    Step(1, "question", TextOption, {"question": (3, 4, 1)}, "text", 1),
    Step(2, "enjeu", TextOption, {"enjeu": (3, 4, 1)}, "text", 1),
    Step(3, "idees", TextOption, {s: (2, 3, 1) for s in "123"}, "text", 1),
    Step(4, "moments", MomentOption, {s: (1, 4, 1) for s in "123"}, "moment", 2),
    Step(5, "contexte", ContexteOption, {"fact": (4, 5, 2)}, "text", 3, keep_range=(2, 3)),
    Step(6, "socle", SocleOption,
         {"headline": (1, 3, 1), "p1": (2, 2, 1), "p2": (2, 2, 1), "p3": (2, 2, 1), "objection": (2, 3, 1)},
         "text", 2),
    Step(7, "hook", HookOption, {"hook": (3, 4, 1)}, "sub_topic", 3),
    Step(8, "writing", None, {}, "", 3),
)
STEP_BY_NAME: dict[str, Step] = {s.name: s for s in STEPS}


# ── Picks ───────────────────────────────────────────────────────────────────

def check_picks(step: Step, options: list[Option], picked: list[str]) -> list[str]:
    """The blocking slot errors: keep counts per slot."""
    by_id = {o.id: o for o in options}
    errors = [f"{step.name}: unknown option {p!r}" for p in picked if p not in by_id]
    errors += [f"{step.name}: option {p!r} is picked twice" for p in dict.fromkeys(picked) if picked.count(p) > 1]
    counts = {slot: 0 for slot in step.slots}
    for p in picked:
        if p in by_id:
            counts[by_id[p].slot] = counts.get(by_id[p].slot, 0) + 1
    for slot, n in counts.items():
        if slot not in step.slots:
            errors.append(f"{step.name}: option slot {slot!r} does not exist")
            continue
        lo, hi = step.keep_range or (step.slots[slot][2],) * 2
        if not lo <= n <= hi:
            want = str(lo) if lo == hi else f"{lo}–{hi}"
            errors.append(f"{step.name}: slot {slot!r} keeps {n} option(s), must keep {want}")
    return errors


def default_picks(step: Step, options: list[Option]) -> list[str]:
    """The first option of each slot (the first `keep_range` minimum for a range)."""
    taken: dict[str, int] = {}
    picks = []
    for o in options:
        want = step.keep_range[0] if step.keep_range else step.slots.get(o.slot, (0, 0, 1))[2]
        if taken.get(o.slot, 0) < want:
            taken[o.slot] = taken.get(o.slot, 0) + 1
            picks.append(o.id)
    return picks


# ── Fragments ───────────────────────────────────────────────────────────────

def _picked(options: list[Option], picked: list[str]) -> list[Option]:
    return [o for o in options if o.id in picked]


def _presupposes(moments: dict, options: list[Option], picked: list[str]) -> list[tuple[str, str]]:
    """(slot, text) of the picked présupposé of each selected moment, in pool order."""
    chosen = {o.slot: o for o in _picked(options, picked)}
    beats = moments.get("display", {}).get("reading_beats", [])
    out = []
    for b in beats:
        slot = f"p{b.get('spine_ref', 0)}"
        if b.get("selected") and slot in chosen:
            out.append((slot, chosen[slot].fields["text"]))
    return out


def to_fragment(step: Step, options: list[Option], picked: list[str], fragments: dict[str, dict]) -> dict:
    """The deck fragment a step's picks make. Writing takes its single option,
    whose fields are a `WritingCopy`. Assumes `picked` passed `check_picks`."""
    kept = _picked(options, picked)
    if step.name == "question":
        return {"display": {"thesis_frame": fragments.get("question_frame", {})},
                "cta": {"engagement_sentence": kept[0].fields["text"]}}
    if step.name == "enjeu":
        return {"display": {"root_issue": kept[0].fields["text"]}}
    if step.name == "idees":
        return {"display": {"essentiel": [o.fields["text"] for o in sorted(kept, key=lambda o: o.slot)]}}
    if step.name == "moments":
        return {"display": {"reading_beats": [
            {**o.fields, "selected": o.id in picked, "spine_ref": int(o.slot), "axis_link": o.reason}
            for o in options]}}
    if step.name == "contexte":
        return {"display": {"reperes_facts": [{"label": o.fields["label"], "text": o.fields["text"]} for o in kept]}}
    if step.name == "socle":
        pres = _presupposes(fragments.get("moments", {}), options, picked)
        headline = next(o for o in kept if o.slot == "headline")
        objection = next(o for o in kept if o.slot == "objection")
        slots = [s for s, _ in pres]
        target = slots.index(objection.fields.get("targets_slot", "")) + 1 if objection.fields.get("targets_slot") in slots else 0
        return {"display": {
            "global_analysis": {"headline": headline.fields["text"],
                                "core_recap": ["Ses présupposés : " + " ; ".join(t for _, t in pres)]},
            "steel_man": {"argument": objection.fields["argument"],
                          "alternative": objection.fields["alternative"], "targets": target}}}
    if step.name == "hook":
        return {"hook": {k: kept[0].fields[k] for k in ("topic", "sub_topic", "subtitle", "headline")}}
    w = WritingCopy.model_validate(options[0].fields)
    return {"beat_copy": [b.model_dump() for b in w.beats],
            "display": {"why_selected": w.why_selected, "selection_headline": w.selection_headline,
                        "key_takeaways": [t.model_dump() for t in w.key_takeaways]},
            "go_further": [g.model_dump() for g in w.go_further],
            "cta": {"where_to_look": w.where_to_look}, "caption": w.caption}


# ── Which step owns an error ────────────────────────────────────────────────

_COPY_BEAT_FIELDS = {"lens_question", "note", "answer", "figure", "figure_label", "figure_caption", "pictogram"}
_BEAT_LABEL = re.compile(r"display\.reading_beats(?:\[\d+\])?(?:\.(\w+))?")
_EXCEPTIONS = (
    ("restates the lede", "writing"), ("shares no **gilded** word", "enjeu"),
    ("slide 1 (hook)", "hook"), ("slide 2 (en bref)", "idees"), ("slide socle", "socle"),
    ("slide prise de recul", "enjeu"),
)
_PREFIXES = (
    ("display.thesis_frame", "question"), ("cta.engagement_sentence", "question"),
    ("display.root_issue", "enjeu"), ("display.essentiel", "idees"),
    ("display.reperes_facts", "contexte"),
    ("display.global_analysis", "socle"), ("display.steel_man", "socle"),
    ("hook.", "hook"), ("beats: index", "writing"),
)


def step_of(error: str) -> StepName:
    """The step that repairs `error`: the one that owns the field it names."""
    for needle, name in _EXCEPTIONS:
        if needle in error:
            return name
    if re.match(r"beat \d+", error):
        return "writing"
    if (m := _BEAT_LABEL.match(error)):
        if m.group(1):
            return "writing" if m.group(1) in _COPY_BEAT_FIELDS else "moments"
        return "writing" if re.search(r"lens_question|figure|pictogram", error) else "moments"
    return next((name for prefix, name in _PREFIXES if error.startswith(prefix)), "writing")


# ── Assembly ────────────────────────────────────────────────────────────────

def _merge(into: dict, frag: dict) -> None:
    """Deep merge; lists replace."""
    for k, v in frag.items():
        if isinstance(v, dict) and isinstance(into.get(k), dict):
            _merge(into[k], v)
        else:
            into[k] = v


def assemble(fragments: dict[str, dict]) -> dict:
    """The deck as far as the fragments go; later steps' fields stay empty."""
    deck: dict = {"hook": {"topic": "", "sub_topic": "", "headline": ""}, "go_further": [],
                  "cta": {"engagement_sentence": ""},
                  "display": {"why_selected": "", "selection_headline": ""}}
    for step in STEPS:
        if step.name in fragments:
            frag = copy.deepcopy(fragments[step.name])  # the caller's fragments stay untouched
            # writing's beat copy merges into the pool's beats by `index`
            beats = deck["display"].get("reading_beats", [])
            for c in frag.pop("beat_copy", []):
                if 0 <= c["index"] < len(beats):
                    beats[c["index"]].update({f: x for f, x in c.items() if f != "index"})
            _merge(deck, frag)
    return deck
