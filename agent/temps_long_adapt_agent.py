"""Adapt agent for the TEMPS LONG carousel (6 slides).

A guided cascade for a hot-news piece, read through the lens of time: first the
tournants (the laws, doctrine texts and statements that changed the rules over
fifty years, slide 3), then the episodes people remember from the last ten years
(slide 2), then the temporal reading (rupture, continuité or cycle, slide 4,
which leans on the two timelines), the traps a time series sets (pieges,
slide 5), then the hook; `writing` finishes with the caption, without pausing.
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


class LectureOption(BaseModel):
    title: str
    lead: str
    rupture: str       # « signature | indicateur »
    continuite: str
    cycle: str
    question: str      # the neutral closing question: not drawn on slide 4, taken up by the sign-off


class PiegesOption(BaseModel):
    title: str
    lead: str
    piege1: str  # « titre | question »
    piege2: str
    piege3: str


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
    offered: tuple[int, int] = (3, 4)         # options per generation


STEPS: tuple[Step, ...] = (
    Step(1, "tournants", FriseOption, "title", 3),
    Step(2, "episodes", FriseOption, "title", 3),
    Step(3, "lecture", LectureOption, "title", 3),
    Step(4, "pieges", PiegesOption, "title", 3),
    Step(5, "hook", HookOption, "title", 3),
    Step(6, "writing", None, "", 3, (1, 1)),
)
STEP_BY_NAME: dict[str, Step] = {s.name: s for s in STEPS}
STEP_NAMES = [s.name for s in STEPS[:-1]]
_REPERES = ("rep1", "rep2", "rep3", "rep4", "rep5")
_READINGS = ("rupture", "continuite", "cycle")
_PIEGES = ("piege1", "piege2", "piege3")
_FRISE_STEPS = ("tournants", "episodes")


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


# ── Rules ───────────────────────────────────────────────────────────────────
# Hard: a generated option repairs itself; on the author's own pick they come
# back as warnings. Flags are advisory.

# (step, field) → ("words" | "chars", cap)
_CAPS: dict[tuple[str, str], tuple[str, int]] = {
    **{(s, "title"): ("chars", 44) for s in ("tournants", "episodes", "lecture", "pieges")},   # two lines at most, whatever the words
    **{(s, "lead"): ("chars", 84) for s in ("tournants", "episodes")},   # two lines at most, beside the bird perched on the first row
    **{(s, "lead"): ("chars", 94) for s in ("lecture", "pieges")},
    ("lecture", "question"): ("chars", 96),
    ("hook", "title"): ("chars", 64), ("hook", "promise"): ("chars", 64),   # two lines at most, before « En juger soi-même. »
}
_DATE_MAX = 14      # characters: the date is drawn big, in gold, in a narrow column
_LABEL_MAX = 64     # characters: a reference point's label takes two lines at most
_REMARK_MAX = 46    # characters: an episode's remark takes one line
_TOURNANTS_REMARK_MAX = 84   # characters: a turning point's remark takes two lines (what it changes, and what it could change)
_SIGNATURE_MAX = 86    # characters: a reading's signature takes two lines at most
_INDICATOR_MAX = 62     # characters: a reading's indicator takes one line
_PIEGE_TITLE_MAX = 38   # characters: a trap's name, one line
_PIEGE_QUESTION_MAX = 92   # characters: a trap's question, two lines at most
_YEAR = re.compile(r"\b(?:1[89]|20)\d{2}\b")
# a trend figure: a percentage, an amount, a multiple — never in a dated reference point
_TREND_FIGURE = re.compile(r"\d[\d  .,]*\s*(?:%|€|M€|Md€|milliards?|millions?|points?\b|×)|×\s*\d", re.I)
_REQUIRED = {"tournants": ("title", "lead", "rep1", "rep2", "rep3"),
             "episodes": ("title", "lead", "rep1", "rep2", "rep3", "rep4"),   # 4 or 5 episodes
             "lecture": ("title", "lead", "rupture", "continuite", "cycle", "question"),
             "pieges": ("title", "lead", "piege1", "piege2", "piege3")}
_EPISODES_MAX_AGE = 12   # years before the article: an episode older than this is no longer what people remember
_TOURNANTS_MIN_AGE = 25  # the tournants reach back at least this far
_TOURNANTS_RECENT = 3      # ... and include a point from the last few years, a bill under discussion included


def _ref_year(article: str | None) -> int | None:
    """The article's own year: the latest one it mentions."""
    years = [int(y) for y in _YEAR.findall(article or "")]
    return max(years) if years else None


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
        if step != "writing" and (m := _TREND_FIGURE.search(_QUOTED.sub("", value))):
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
            date, label, remark = _parts(value, 3)
            if not label or not _YEAR.search(date):
                hard.append(f"{step}.{name} must read « date | repère | remarque » (the date holds a year)")
                continue
            if len(date) > _DATE_MAX:
                hard.append(f"{step}.{name}: the date is {len(date)} characters (max {_DATE_MAX}) — it is drawn big")
            if len(label) > _LABEL_MAX:
                hard.append(f"{step}.{name}: the label is {len(label)} characters (max {_LABEL_MAX}) — two lines at most")
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
            if step == "tournants" and min(years) > ref - _TOURNANTS_MIN_AGE:
                flags.append(f"tournants starts in {min(years)}, less than {_TOURNANTS_MIN_AGE} years before the article — "
                             "it should reach further back")
            if step == "tournants" and max(years) < ref - _TOURNANTS_RECENT:
                flags.append(f"tournants ends in {max(years)}, over {_TOURNANTS_RECENT} years before the article — "
                             "add the most recent text, a bill under discussion included")
    if step == "lecture":
        for name in _READINGS:
            value = str(fields.get(name, "")).strip()
            if value and not all(_parts(value, 2)):
                hard.append(f"lecture.{name} must read « signature | indicateur »")
            elif value:
                signature, indicator = _parts(value, 2)
                if len(signature) > _SIGNATURE_MAX:
                    hard.append(f"lecture.{name}: the signature is {len(signature)} characters (max {_SIGNATURE_MAX}) — two lines at most")
                if len(indicator) > _INDICATOR_MAX:
                    hard.append(f"lecture.{name}: the indicator is {len(indicator)} characters (max {_INDICATOR_MAX}) — one line")
                known = _stems(_plain(str(fields.get("lead", ""))))
                known_years: set[str] = set()
                for other in ("episodes", "tournants"):
                    for pt in fragments.get(other, {}).get(other, {}).get("reperes", []):
                        known |= _stems(_plain(pt["label"]))
                        known_years |= set(_YEAR.findall(pt["date"]))
                if known and not (_stems(_plain(indicator)) & known or set(_YEAR.findall(indicator)) & known_years):
                    flags.append(f"lecture.{name}: the line refers to nothing of the lead or of the episodes and texts "
                                 "of slides 2–3")
        if fields.get("question", "").strip() and not fields["question"].strip().endswith("?"):
            hard.append("lecture.question must be a question")
    if step == "pieges":
        lecture = fragments.get("lecture", {}).get("lecture", {})
        measure = _stems(_plain(lecture.get("lead", "")))
        for name in _PIEGES:
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            title, question = _parts(value, 2)
            if not title or not question:
                hard.append(f"pieges.{name} must read « titre | question »")
                continue
            if len(title) > _PIEGE_TITLE_MAX:
                hard.append(f"pieges.{name}: the title is {len(title)} characters (max {_PIEGE_TITLE_MAX}) — one line")
            if len(question) > _PIEGE_QUESTION_MAX:
                hard.append(f"pieges.{name}: the question is {len(question)} characters (max {_PIEGE_QUESTION_MAX}) — two lines at most")
            if not question.strip().endswith("?"):
                hard.append(f"pieges.{name}: the question must be a question")
            if measure and not _stems(_plain(value)) & measure:
                flags.append(f"pieges.{name} cites nothing of the measure the deck follows — tie the trap to it")
    if step == "hook" and not fields.get("promise", "").lower().startswith("prendre du recul"):
        flags.append("hook.promise usually reads « Prendre du recul sur … »")
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
    if step.name in _FRISE_STEPS:
        reperes = []
        for name in _REPERES:
            if str(f.get(name, "")).strip():
                date, label, remark = _parts(f[name], 3)
                reperes.append({"date": date, "label": label, "remark": remark})
        return {step.name: {"title": f.get("title", ""), "lead": f.get("lead", ""), "reperes": reperes}}
    if step.name == "lecture":
        readings = []
        for kind in _READINGS:
            if str(f.get(kind, "")).strip():
                signature, indicator = _parts(f[kind], 2)
                readings.append({"kind": kind, "signature": signature, "indicator": indicator})
        return {"lecture": {"title": f.get("title", ""), "lead": f.get("lead", ""), "readings": readings,
                            "question": f.get("question", "")}}
    if step.name == "pieges":
        pieges = []
        for name in _PIEGES:
            if str(f.get(name, "")).strip():
                title, question = _parts(f[name], 2)
                pieges.append({"title": title, "question": question})
        return {"pieges": {"title": f.get("title", ""), "lead": f.get("lead", ""), "pieges": pieges}}
    if step.name == "hook":
        return {"hook": {"title": f.get("title", ""), "promise": f.get("promise", "")}}
    return {"caption": f.get("caption", "")}


def assemble(fragments: dict[str, dict]) -> dict:
    deck: dict = {}
    for step in STEPS:
        if step.name in fragments:
            _merge(deck, copy.deepcopy(fragments[step.name]))
    return deck


# ── Generating a step ───────────────────────────────────────────────────────

def _prompt(step: Step) -> str:
    body = (_PROMPTS / f"{step.n}_{step.name}.md").read_text(encoding="utf-8")
    if step.option_model is None:
        return body
    return (_PROMPTS / "0_options.md").read_text(encoding="utf-8") + "\n" + body


def _message(step: Step, full: ArticleFullAnalysis, fragments: dict, article_text: str | None,
             rejected: list[Option], remarks: list[str]) -> str:
    parts = [_full_analysis_context(full, step.analysis_slice)]
    if article_text:
        parts.append(f"MÉDIA (transcription ou texte) :\n{article_text.strip()}")
    if fragments:
        parts.append(f"CHOIX FIXÉS (ne les réécris pas) :\n{_j(fragments)}")
    parts += [(_PROMPTS / "0_shared.md").read_text(encoding="utf-8"), _prompt(step)]
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
    for s in STEPS[:-1]:
        sf, _ = _load(steps_dir, s)
        if sf is not None and not sf.picked:
            return s.name
    return None


def _run(full, no_api, article_text, steps_dir, stop_after, guided) -> TempsLongPresentation | None:
    base = base_inputs(full, article_text)
    fragments: dict[str, dict] = {}
    for step in STEPS:
        stamp = stamp_for(base, [fragments[s.name] for s in STEPS if s.n < step.n])
        sf, saved = _load(steps_dir, step) if steps_dir is not None else (None, "")
        tag = f"Adaptation temps long — étape {step.n}/{len(STEPS)} ({step.name})"
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
    for s in STEPS:
        if s.n >= step.n:
            break
        sf, _ = _load(steps_dir, s)
        if sf is None or not sf.picked:
            raise ChoiceError(f"{s.name} has no pick: run `produce --guided` to reach step {step.n} ({step.name})")
        fragments[s.name] = sf.fragment
    sf, saved = _load(steps_dir, step)
    stamp = stamp_for(base_inputs(full, article_text), [fragments[s.name] for s in STEPS if s.n < step.n])
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
    fragments = [_load(steps_dir, s)[0].fragment if _load(steps_dir, s)[0] else None for s in STEPS]
    for s in STEPS:
        if s.n > owner.n and _path(steps_dir, s).exists():
            before_frags = fragments[:s.n - 1]
            if None in before_frags:
                break
            _path(steps_dir, s).with_suffix(".sha256").write_text(stamp_for(base, before_frags))
    log_choice(steps_dir.parent, {"step": owner_name, "event": "fix", "field": field,
                                  "before": before, "after": text})
    return owner_name
