"""Adapt agent for the CADRAGE & LOGIQUE carousel (7 slides).

A guided cascade in slide order: the facts the speaker leans on (constat), his
thesis and solution (these), the blind spot of that solution (angle_mort), the
levers that answer it (depassement), the arbitrage left to the reader
(boussole), then the hook; `writing` finishes with the caption, without
pausing. Each step proposes options with a reason and a ★, the author picks,
edits or asks for others (`choose`), and a pick feeds the later steps. Steps
are cached in `<format>/adapt_steps/` with a stamp of the inputs and the
earlier picks.

An option's fields are flat strings so that `choose --edit ID.field=TEXT` and
`fix` can rewrite any of them: a figure, a lever, a note are one line each,
their parts separated by « | » (see `to_fragment`).

Same guided semantics as `agent/carousel_steps` (which is bound to the 9-slide
deck), kept as a slim module of its own; the generic pieces are imported.
"""
import copy
import json
import re
import string
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, create_model

from agent._base import _call_with_retry, _j, medium_directive
from agent.carousel_steps.steps import Option
from agent.carousel_steps.store import digest, log_choice, stamp_for
from agent.instagram_carousel_adapt_agent import _full_analysis_context
from models.cadrage_presentation import CadragePresentation
from models.full_analysis import ArticleFullAnalysis

_PROMPTS = Path(__file__).parent / "prompts" / "cadrage_steps"


class ChoiceError(ValueError):
    """A choice, a request for more options or a fix that cannot be applied."""


class AwaitingChoice(Exception):
    def __init__(self, step: str):
        super().__init__(step)
        self.step = step


# ── Option models and the step table ────────────────────────────────────────

class ConstatOption(BaseModel):
    title: str
    fig1: str    # « valeur | libellé | comparaison »
    fig2: str
    fig3: str    # empty when the source gives only two figures
    fig4: str
    claim: str
    detail: str


class TheseOption(BaseModel):
    title: str
    these_claim: str
    these_detail: str
    solution_claim: str
    solution_detail: str
    note1: str   # « source | texte » or « remarque | texte »
    note2: str
    note3: str


class AngleMortOption(BaseModel):
    title: str
    claim: str
    detail: str
    note1: str
    note2: str
    note3: str
    second_claim: str   # the second card: another blind spot
    second_detail: str
    second_note1: str
    second_note2: str


class DepassementOption(BaseModel):
    title: str
    lead: str
    lever1: str  # « titre | détail »
    lever2: str
    lever3: str
    lever1_note: str   # optional « remarque | texte » or « source | texte » under the first lever (empty = none)


class BoussoleOption(BaseModel):
    title: str
    question1: str
    pro1: str
    con1: str
    question2: str
    pro2: str
    con2: str


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
    Step(1, "constat", ConstatOption, "title", 3),
    Step(2, "these", TheseOption, "title", 3),
    Step(3, "angle_mort", AngleMortOption, "title", 3),
    Step(4, "depassement", DepassementOption, "title", 3),
    Step(5, "boussole", BoussoleOption, "title", 3),
    Step(6, "hook", HookOption, "title", 3),
    Step(7, "writing", None, "", 3, (1, 1)),
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


# ── Rules ───────────────────────────────────────────────────────────────────
# Hard: a generated option repairs itself; on the author's own pick they come
# back as warnings. Flags are advisory.

# (step, field) → ("words" | "chars", cap)
_CAPS: dict[tuple[str, str], tuple[str, int]] = {
    ("constat", "title"): ("words", 10), ("constat", "claim"): ("chars", 80), ("constat", "detail"): ("words", 30),
    ("constat", "fig1"): ("words", 14), ("constat", "fig2"): ("words", 14),
    ("constat", "fig3"): ("words", 14), ("constat", "fig4"): ("words", 14),
    ("these", "title"): ("words", 12), ("these", "these_claim"): ("chars", 80), ("these", "these_detail"): ("words", 30),
    ("these", "solution_claim"): ("chars", 80), ("these", "solution_detail"): ("words", 30),
    ("these", "note1"): ("words", 30), ("these", "note2"): ("words", 30), ("these", "note3"): ("words", 30),
    ("angle_mort", "title"): ("words", 10),
    ("angle_mort", "claim"): ("chars", 72), ("angle_mort", "detail"): ("words", 24),
    ("angle_mort", "second_claim"): ("chars", 72), ("angle_mort", "second_detail"): ("words", 24),
    ("angle_mort", "second_note1"): ("words", 30), ("angle_mort", "second_note2"): ("words", 30),
    ("angle_mort", "note1"): ("words", 30), ("angle_mort", "note2"): ("words", 30), ("angle_mort", "note3"): ("words", 30),
    ("depassement", "title"): ("words", 14), ("depassement", "lead"): ("words", 28),
    ("depassement", "lever1"): ("words", 30), ("depassement", "lever2"): ("words", 30), ("depassement", "lever3"): ("words", 30),
    ("boussole", "title"): ("words", 14),
    ("boussole", "question1"): ("words", 22), ("boussole", "question2"): ("words", 22),
    ("boussole", "pro1"): ("words", 16), ("boussole", "con1"): ("words", 16),
    ("boussole", "pro2"): ("words", 16), ("boussole", "con2"): ("words", 16),
    ("hook", "title"): ("chars", 64), ("hook", "promise"): ("chars", 100),
}
_ACCUSING = re.compile(r"\b(biais|manipulation|manipul\w+|mensonges?|trompeu\w+|fallacieu\w+|sophismes?)\b", re.I)
_HASHTAG = re.compile(r"#\w+")
_QUOTED = re.compile(r"«[^»]*»")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_FIG_VALUE_MAX = 9  # a slot holds a figure or a short fact, drawn at 70 px in a half-width column
_REQUIRED = {"constat": ("fig1", "fig2"), "these": ("note1",), "angle_mort": ("note1", "second_claim", "second_detail"),
             "depassement": ("lever1", "lever2", "lever3"), "boussole": ("question1", "question2")}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w']+", " ", s)).strip()


def _words(s: str) -> int:
    return len(re.sub(r"\*\*", "", s).split())


def _parts(value: str, n: int) -> list[str]:
    """`value` cut at « | » into `n` trimmed parts, the last one keeping any further bar."""
    parts = [p.strip() for p in value.split("|", n - 1)]
    return parts + [""] * (n - len(parts))


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
    for name in _REQUIRED.get(step, ()):
        if not str(fields.get(name, "")).strip():
            hard.append(f"{step}.{name} is empty")
    if step == "constat":
        for name in ("fig1", "fig2", "fig3", "fig4"):
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            if len([p for p in _parts(value, 3)[:2] if p]) < 2:
                hard.append(f"constat.{name} must read « valeur | libellé | comparaison » (the comparison is optional)")
            elif len(_parts(value, 3)[0]) > _FIG_VALUE_MAX:
                hard.append(f"constat.{name}: the value is {len(_parts(value, 3)[0])} characters (max {_FIG_VALUE_MAX}) — it is drawn big")
            elif article and (nums := _NUMBER.findall(_parts(value, 3)[0])) \
                    and not any(n in article for n in nums):
                flags.append(f"constat.{name}: {_parts(value, 3)[0]!r} does not appear as written in the source — check the figure")
    if step in ("these", "angle_mort"):
        for name in ("note1", "note2", "note3", "second_note1", "second_note2"):
            value = str(fields.get(name, "")).strip()
            if value:
                kind, _, text = value.partition("|")
                if kind.strip().lower() not in ("source", "remarque") or not text.strip():
                    hard.append(f"{step}.{name} must read « source | texte » or « remarque | texte »")
    if step == "depassement":
        for name in ("lever1", "lever2", "lever3"):
            value = str(fields.get(name, "")).strip()
            if value and not all(_parts(value, 2)):
                hard.append(f"depassement.{name} must read « titre | détail »")
        value = str(fields.get("lever1_note", "")).strip()
        if value and (value.partition("|")[0].strip().lower() not in ("source", "remarque") or not value.partition("|")[2].strip()):
            hard.append("depassement.lever1_note must read « source | texte » or « remarque | texte »")
    if step == "hook" and not fields.get("promise", "").lower().startswith("décryptage"):
        flags.append("hook.promise usually reads « Décryptage d'une prise de position sur … »")
    if step == "writing":
        tags = _HASHTAG.findall(fields.get("caption", ""))
        if len(tags) != 4:
            hard.append(f"writing.caption has {len(tags)} hashtag(s), must have 4")
        if not 100 <= _words(fields.get("caption", "")) <= 190:
            hard.append(f"writing.caption is {_words(fields.get('caption', ''))} words (aim for about 150)")
    return hard, flags


# ── Fragments and assembly ──────────────────────────────────────────────────

def _notes(f: dict, names: tuple[str, ...] = ("note1", "note2", "note3")) -> list[dict]:
    out = []
    for name in names:
        value = str(f.get(name, "")).strip()
        if value:
            kind, _, text = value.partition("|")
            out.append({"kind": "remark" if kind.strip().lower().startswith("rem") else "source",
                        "text": text.strip() or kind.strip()})
    return out


def to_fragment(step: Step, option: Option) -> dict:
    f = option.fields
    if step.name == "constat":
        figures = []
        for name in ("fig1", "fig2", "fig3", "fig4"):
            if str(f.get(name, "")).strip():
                value, label, compare = _parts(f[name], 3)
                figures.append({"value": value, "label": label, "compare": compare})
        return {"constat": {"title": f.get("title", ""), "figures": figures,
                            "claim": f.get("claim", ""), "detail": f.get("detail", "")}}
    if step.name == "these":
        return {"these": {"title": f.get("title", ""),
                          "these": {"claim": f.get("these_claim", ""), "detail": f.get("these_detail", "")},
                          "solution": {"claim": f.get("solution_claim", ""), "detail": f.get("solution_detail", "")},
                          "notes": _notes(f)}}
    if step.name == "angle_mort":
        return {"angle_mort": {k: f.get(k, "") for k in ("title", "claim", "detail")}
                | {"notes": _notes(f),
                   "second": {"claim": f.get("second_claim", ""), "detail": f.get("second_detail", "")},
                   "second_notes": _notes(f, ("second_note1", "second_note2"))}}
    if step.name == "depassement":
        levers = []
        for name in ("lever1", "lever2", "lever3"):
            if str(f.get(name, "")).strip():
                title, detail = _parts(f[name], 2)
                levers.append({"title": title, "detail": detail})
        if levers and (note := _notes(f, ("lever1_note",))):
            levers[0]["note"] = note[0]
        return {"depassement": {"title": f.get("title", ""), "lead": f.get("lead", ""), "levers": levers}}
    if step.name == "boussole":
        options = [{"question": f.get(f"question{i}", ""), "pro": f.get(f"pro{i}", ""), "con": f.get(f"con{i}", "")}
                   for i in (1, 2) if str(f.get(f"question{i}", "")).strip()]
        return {"boussole": {"title": f.get("title", ""), "options": options}}
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


# ── Generating a step ───────────────────────────────────────────────────────

def _response_model(step: Step):
    if step.option_model is None:
        return WritingCopy
    proposal = create_model(f"{step.name.title()}Proposal", __base__=step.option_model, reason=(str, ...))
    return create_model(f"{step.name.title()}Response", options=(list[proposal], ...), recommended=(list[int], ...))


def _prompt(step: Step) -> str:
    body = (_PROMPTS / f"{step.n}_{step.name}.md").read_text(encoding="utf-8")
    if step.option_model is None:
        return body
    return (_PROMPTS / "0_options.md").read_text(encoding="utf-8") + "\n" + body


def _to_options(proposals: list, rejected: list[Option]) -> list[Option]:
    used = {o.id for o in rejected}
    out = []
    for p in proposals:
        oid = next(c for c in string.ascii_lowercase if c not in used)
        used.add(oid)
        out.append(Option(id=oid, slot="a", reason=p.reason, fields=p.model_dump(mode="json", exclude={"reason"})))
    return out


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


def _failed(step: Step, steps_dir: Path | None, data, errors: list[str]) -> RuntimeError:
    where = ""
    if steps_dir is not None:
        steps_dir.mkdir(parents=True, exist_ok=True)
        path = steps_dir / f"{step.n}_{step.name}.failed.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        where = f" (raw answer saved to {path})"
    return RuntimeError(f"step {step.n} ({step.name}): the model's answer is still invalid after the retries"
                        f"{where}:\n" + "\n".join(f"- {e}" for e in errors))


def generate(step: Step, full: ArticleFullAnalysis, fragments: dict[str, dict], article_text: str | None,
             no_api: bool, rejected: list[Option] = [], remarks: list[str] = [],
             steps_dir: Path | None = None) -> StepFile:
    """One model call for `step`'s options (writing: its copy), checked against the
    rules. Nothing is picked. An answer still breaking a hard rule after the
    retries raises RuntimeError."""
    model = _response_model(step)
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


# ── Showing a step ──────────────────────────────────────────────────────────

def format_options(step: Step, sf: StepFile) -> str:
    lines = [f"[{step.name}]"]
    for o in sf.options:
        name = o.fields.get(step.text_field, "")
        lines.append(f"{o.id} — {name}" + (" ★" if o.id in sf.recommended else ""))
        lines += [f"   · {k} : {v}" for k, v in o.fields.items() if k != step.text_field]
        lines.append(f"   ↳ {o.reason}")
        lines += [f"   ⚠ {flag}" for flag in o.flags]
    return "\n".join(lines)


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


def _run(full, no_api, article_text, steps_dir, stop_after, guided) -> CadragePresentation | None:
    base = base_inputs(full, article_text)
    fragments: dict[str, dict] = {}
    for step in STEPS:
        stamp = stamp_for(base, [fragments[s.name] for s in STEPS if s.n < step.n])
        sf, saved = _load(steps_dir, step) if steps_dir is not None else (None, "")
        tag = f"Adaptation cadrage — étape {step.n}/{len(STEPS)} ({step.name})"
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
    return CadragePresentation.model_validate(assemble(fragments))


def adapt(full: ArticleFullAnalysis, no_api: bool = False, article_text: str | None = None,
          steps_dir: Path | None = None, stop_after: str | None = None,
          guided: bool = False) -> CadragePresentation | None:
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
