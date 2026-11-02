"""Adapt agent for the ANATOMIE D'UN CHIFFRE carousel (6 slides).

A guided cascade: first the variable (the question behind the figure: the one variable
the figure approaches, two poles, the facts the source states, where to look; slide 5
shows it, and it is the fixed context of the steps before it), then in slide order the
black box (how the figure was measured), the zone of light (what it establishes and how
it decomposes), the excluded perimeter (what the measure cannot capture), then the
hook; `writing` finishes with the caption, without pausing. Each step proposes
options with a reason and a ★, the author picks, edits or asks for others (`choose`),
and a pick feeds the later steps. Steps are cached in `<format>/adapt_steps/` with a
stamp of the inputs and the earlier picks.

An option's fields are flat strings so that `choose --edit ID.field=TEXT` and
`fix` can rewrite any of them: a figure, a part, a note are one line each, their
parts separated by « | » (see `to_fragment`).

Same guided semantics as `agent/cadrage_adapt_agent.py`, kept as a module of its own.
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
from agent.instagram_carousel_adapt_agent import _full_analysis_context, _plain, _stems
from models.anatomie_chiffre_presentation import AnatomieChiffrePresentation
from models.full_analysis import ArticleFullAnalysis

_PROMPTS = Path(__file__).parent / "prompts" / "anatomie_chiffre_steps"


class ChoiceError(ValueError):
    """A choice, a request for more options or a fix that cannot be applied."""


class AwaitingChoice(Exception):
    def __init__(self, step: str):
        super().__init__(step)
        self.step = step


# ── Option models and the step table ────────────────────────────────────────

class VariableOption(BaseModel):
    title: str       # « A ou B », in neutral words of equal weight
    variable: str    # the one variable the figure approaches
    pole_a: str
    pole_b: str
    proxy: str       # why the figure stands for it — our reading, named as such
    question: str    # the open question, neither binary nor normative; the CTA opens it
    fact1: str       # what the source states: slide 5's left column
    fact2: str
    fact3: str
    implication: str  # what a move of the variable would imply, as a consequence to examine
    look1: str       # « source | texte » : where to look at the variable directly
    look2: str


class BoiteNoireOption(BaseModel):
    fig1: str          # « valeur | libellé | comparaison »
    fig2: str
    fig3: str          # empty when the source gives only two
    fig4: str
    source_card: str   # « chaîne | libellé | précision » : the primary source and the chain
    claim: str
    detail: str


class EclairageOption(BaseModel):
    claim: str
    detail: str
    part1: str    # « valeur | libellé » : the first quantity, as the source gives it
    part2: str
    ratio: str    # « valeur | libellé »
    note1: str    # optional « source | texte » or « remarque | texte »


class PerimetreOption(BaseModel):
    title: str
    claim1: str   # card 1 — la statistique
    detail1: str
    note1_1: str  # « source | texte »
    note1_2: str
    claim2: str   # card 2 — la période
    detail2: str
    note2_1: str
    note2_2: str


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
    Step(1, "variable", VariableOption, "title", 3),
    Step(2, "boite_noire", BoiteNoireOption, "claim", 3),
    Step(3, "eclairage", EclairageOption, "claim", 3),
    Step(4, "perimetre", PerimetreOption, "title", 3),
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


# ── Rules ───────────────────────────────────────────────────────────────────
# Hard: a generated option repairs itself; on the author's own pick they come
# back as warnings. Flags are advisory.

# (step, field) → ("words" | "chars", cap). The caps were set on the rendered slides.
_CAPS: dict[tuple[str, str], tuple[str, int]] = {
    ("variable", "title"): ("words", 14), ("variable", "variable"): ("words", 16),
    ("variable", "pole_a"): ("words", 10), ("variable", "pole_b"): ("words", 10),
    ("variable", "proxy"): ("words", 32), ("variable", "question"): ("words", 20),
    ("variable", "fact1"): ("words", 24), ("variable", "fact2"): ("words", 24), ("variable", "fact3"): ("words", 24),
    ("variable", "implication"): ("words", 32), ("variable", "look1"): ("words", 24), ("variable", "look2"): ("words", 24),
    ("boite_noire", "claim"): ("chars", 64), ("boite_noire", "detail"): ("words", 36),
    ("boite_noire", "fig1"): ("words", 14), ("boite_noire", "fig2"): ("words", 14),
    ("boite_noire", "fig3"): ("words", 14), ("boite_noire", "fig4"): ("words", 14),
    ("boite_noire", "source_card"): ("words", 20),
    ("eclairage", "claim"): ("chars", 72), ("eclairage", "detail"): ("words", 30),
    ("eclairage", "part1"): ("words", 8), ("eclairage", "part2"): ("words", 8), ("eclairage", "ratio"): ("words", 8),
    ("eclairage", "note1"): ("words", 24),
    ("perimetre", "title"): ("words", 10),
    ("perimetre", "claim1"): ("chars", 64), ("perimetre", "detail1"): ("words", 28),
    ("perimetre", "claim2"): ("chars", 64), ("perimetre", "detail2"): ("words", 28),
    ("perimetre", "note1_1"): ("words", 24), ("perimetre", "note1_2"): ("words", 24),
    ("perimetre", "note2_1"): ("words", 24), ("perimetre", "note2_2"): ("words", 24),
    ("hook", "title"): ("chars", 64), ("hook", "promise"): ("chars", 100),
}
_ACCUSING = re.compile(r"\b(biais|manipulation|manipul\w+|mensonges?|trompeu\w+|fallacieu\w+|sophismes?)\b", re.I)
# slide 5 offers a reading to examine, never a conclusion
_CONCLUDING = re.compile(r"\b(donc|prouve[nt]?|prouvent|démontre[nt]?|démontrent|par conséquent|en conclusion|c'est la preuve)\b", re.I)
_HASHTAG = re.compile(r"#\w+")
_QUOTED = re.compile(r"«[^»]*»")
_DIGIT = re.compile(r"\d")
_AGE = re.compile(r"\b\d{1,3} ans\b")   # « à 35 ans » names a group, it adds no figure
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_FIG_VALUE_MAX = 9      # a figure card draws its value at 70 px in a half-width column
_CHAIN_MAX = 24         # the source card's chain (« Fed → WSJ → BFM »), on a full-width card
_REQUIRED = {"variable": ("title", "variable", "pole_a", "pole_b", "proxy", "question", "implication", "look1"),
             "boite_noire": ("fig1", "fig2", "source_card", "claim"),
             "eclairage": ("claim", "part1", "part2", "ratio"),
             "perimetre": ("title", "claim1", "claim2", "note1_1", "note2_1")}
# slides 4 and 5 (outside the source's frame) add no figure; slide 5's « source » column (facts) may carry digits
_NO_DIGIT = {"perimetre": None,
             "variable": ("title", "variable", "pole_a", "pole_b", "proxy", "question", "implication", "look1", "look2")}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w']+", " ", s)).strip()


def _words(s: str) -> int:
    return len(re.sub(r"\*\*", "", s).split())


def _parts(value: str, n: int) -> list[str]:
    """`value` cut at « | » into `n` trimmed parts, the last one keeping any further bar."""
    parts = [p.strip() for p in value.split("|", n - 1)]
    return parts + [""] * (n - len(parts))


def _in_source(number: str, article: str) -> bool:
    return re.search(rf"(?<![\d.,]){re.escape(number)}(?![\d])", article) is not None


def _bad_note(value: str) -> bool:
    kind, _, text = value.partition("|")
    return kind.strip().lower() not in ("source", "remarque") or not text.strip()


# the lines of slides 2–4 that must tie back to the variable: (step, field)
_VARIABLE_FIELDS = (("boite_noire", "claim"), ("eclairage", "claim"),
                    ("perimetre", "claim1"), ("perimetre", "claim2"))


def _variable_flags(step: str, fields: dict[str, Any], fragments: dict[str, dict]) -> list[str]:
    """Advisory: a line that shares no key word with the variable is written for something else."""
    var = fragments.get("variable", {}).get("variable")
    if not var:
        return []
    stems = set().union(*(_stems(_plain(var.get(k, ""))) for k in ("title", "variable", "pole_a", "pole_b", "proxy")))
    return [f"{step}.{name} shares no key word with the variable (« {var.get('variable', '')} »)"
            for s, name in _VARIABLE_FIELDS if s == step and str(fields.get(name, "")).strip()
            and not _stems(_plain(fields[name])) & stems]


def field_errors(step: str, fields: dict[str, Any], fragments: dict[str, dict],
                 article: str | None) -> tuple[list[str], list[str]]:
    """(hard, flags) on one step's fields, given the earlier fragments."""
    hard, flags = [], []
    free = _NO_DIGIT.get(step, False)
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
        if free is None or (free and name in free):
            if _DIGIT.search(_AGE.sub("", value) if step == "variable" else value):
                hard.append(f"{step}.{name} holds a digit — this slide is outside the source's frame and adds no figure")
        if step == "variable" and name in ("proxy", "implication", "question", "title") \
                and (m := _CONCLUDING.search(value)):
            hard.append(f"variable.{name} concludes with « {m.group(0)} » — slide 5 offers a reading to examine, never a conclusion")
    for name in _REQUIRED.get(step, ()):
        if not str(fields.get(name, "")).strip():
            hard.append(f"{step}.{name} is empty")
    if step == "variable":
        if fields.get("pole_a") and _norm(fields["pole_a"]) == _norm(fields.get("pole_b", "")):
            hard.append("variable.pole_b repeats pole_a — two identical poles are no variable")
        if fields.get("question") and not fields["question"].strip().endswith("?"):
            hard.append("variable.question must end with « ? »")
        if fields.get("question") and re.search(r"\bou\b", fields["question"]):
            flags.append("variable.question reads as a choice between two answers — keep it open")
        if not str(fields.get("fact1", "")).strip():
            flags.append("variable has no fact from the source to join — the left column of slide 5 would be empty")
        for name in ("look1", "look2"):
            value = str(fields.get(name, "")).strip()
            if value and _bad_note(value):
                hard.append(f"variable.{name} must read « source | texte »")
        if article:
            for name in ("fact1", "fact2", "fact3"):
                for q in _QUOTED.findall(str(fields.get(name, ""))):
                    if _norm(q.strip("«» ")) not in _norm(article):
                        flags.append(f"variable.{name}: {q} does not appear word for word in the source")
    if step == "boite_noire":
        for name in ("fig1", "fig2", "fig3", "fig4"):
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            if len([p for p in _parts(value, 3)[:2] if p]) < 2:
                hard.append(f"boite_noire.{name} must read « valeur | libellé | comparaison » (the comparison is optional)")
            elif len(_parts(value, 3)[0]) > _FIG_VALUE_MAX:
                hard.append(f"boite_noire.{name}: the value is {len(_parts(value, 3)[0])} characters (max {_FIG_VALUE_MAX}) — "
                            "it is drawn big; for a gap write « ? » and put « non précisé » in the comparison")
            elif article and (nums := _NUMBER.findall(_parts(value, 3)[0])) \
                    and not all(_in_source(n, article) for n in nums):
                flags.append(f"boite_noire.{name}: {_parts(value, 3)[0]!r} does not appear as written in the source — check the figure")
        value = str(fields.get("source_card", "")).strip()
        if value:
            chain = _parts(value, 3)
            if not chain[0] or not chain[1]:
                hard.append("boite_noire.source_card must read « chaîne | libellé | précision » (the precision is optional)")
            elif len(chain[0]) > _CHAIN_MAX:
                hard.append(f"boite_noire.source_card: the chain is {len(chain[0])} characters (max {_CHAIN_MAX})")
    if step == "eclairage":
        for name in ("part1", "part2", "ratio"):
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            value_, label = _parts(value, 2)
            if not value_ or not label:
                hard.append(f"eclairage.{name} must read « valeur | libellé »")
            elif len(value_) > _FIG_VALUE_MAX:
                hard.append(f"eclairage.{name}: the value is {len(value_)} characters (max {_FIG_VALUE_MAX})")
            elif article:
                nums = _NUMBER.findall(value_)
                if not nums:
                    flags.append(f"eclairage.{name}: {value_!r} is not written in digits — check it against the source")
                elif not all(_in_source(n, article) for n in nums) and "calcul" not in label.lower():
                    flags.append(f"eclairage.{name}: {value_!r} is not in the source — if recomputed, say so in the label (« calculé »)")
        value = str(fields.get("note1", "")).strip()
        if value and _bad_note(value):
            hard.append("eclairage.note1 must read « source | texte » or « remarque | texte »")
    if step == "perimetre":
        for name in ("note1_1", "note1_2", "note2_1", "note2_2"):
            value = str(fields.get(name, "")).strip()
            if value and _bad_note(value):
                hard.append(f"perimetre.{name} must read « source | texte » or « remarque | texte »")
    if step == "hook":
        if not fields.get("title", "").strip().startswith("«"):
            flags.append("hook.title is usually the raw figure, in « »")
        if "comment il se mesure" not in fields.get("promise", "").lower():
            flags.append("hook.promise usually reads « <sujet> : comment il se mesure, et la question qu'il pose »")
    if step == "writing":
        tags = _HASHTAG.findall(fields.get("caption", ""))
        if len(tags) != 4:
            hard.append(f"writing.caption has {len(tags)} hashtag(s), must have 4")
        if not 100 <= _words(fields.get("caption", "")) <= 190:
            hard.append(f"writing.caption is {_words(fields.get('caption', ''))} words (aim for about 150)")
    return hard, flags + _variable_flags(step, fields, fragments)


# ── Fragments and assembly ──────────────────────────────────────────────────

def _notes(f: dict, names: tuple[str, ...]) -> list[dict]:
    out = []
    for name in names:
        value = str(f.get(name, "")).strip()
        if value:
            kind, _, text = value.partition("|")
            out.append({"kind": "remark" if kind.strip().lower().startswith("rem") else "source",
                        "text": text.strip() or kind.strip()})
    return out


def _figure(value: str) -> dict:
    v, label, compare = _parts(value, 3)
    return {"value": v, "label": label, "compare": compare}


def _part(value: str) -> dict | None:
    if not str(value).strip():
        return None
    v, label = _parts(value, 2)
    return {"value": v, "label": label}


def to_fragment(step: Step, option: Option) -> dict:
    f = option.fields
    if step.name == "variable":
        keys = ("title", "variable", "pole_a", "pole_b", "proxy", "question", "implication")
        return {"variable": {k: f.get(k, "") for k in keys}
                | {"facts": [f[n].strip() for n in ("fact1", "fact2", "fact3") if str(f.get(n, "")).strip()],
                   "looks": _notes(f, ("look1", "look2"))}}
    if step.name == "boite_noire":
        figures = [_figure(f[n]) for n in ("fig1", "fig2", "fig3", "fig4") if str(f.get(n, "")).strip()]
        card = _figure(f["source_card"]) if str(f.get("source_card", "")).strip() else None
        return {"boite_noire": {"figures": figures, "source_card": card,
                                "claim": f.get("claim", ""), "detail": f.get("detail", "")}}
    if step.name == "eclairage":
        note = _notes(f, ("note1",))
        return {"eclairage": {"claim": f.get("claim", ""), "detail": f.get("detail", ""),
                              "part1": _part(f.get("part1", "")), "part2": _part(f.get("part2", "")),
                              "ratio": _part(f.get("ratio", "")), "note": note[0] if note else None}}
    if step.name == "perimetre":
        return {"perimetre": {"title": f.get("title", ""),
                              "statistique": {"claim": f.get("claim1", ""), "detail": f.get("detail1", ""),
                                              "notes": _notes(f, ("note1_1", "note1_2"))},
                              "periode": {"claim": f.get("claim2", ""), "detail": f.get("detail2", ""),
                                          "notes": _notes(f, ("note2_1", "note2_2"))}}}
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


def _run(full, no_api, article_text, steps_dir, stop_after, guided) -> AnatomieChiffrePresentation | None:
    base = base_inputs(full, article_text)
    fragments: dict[str, dict] = {}
    for step in STEPS:
        stamp = stamp_for(base, [fragments[s.name] for s in STEPS if s.n < step.n])
        sf, saved = _load(steps_dir, step) if steps_dir is not None else (None, "")
        tag = f"Adaptation anatomie_chiffre — étape {step.n}/{len(STEPS)} ({step.name})"
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
    return AnatomieChiffrePresentation.model_validate(assemble(fragments))


def adapt(full: ArticleFullAnalysis, no_api: bool = False, article_text: str | None = None,
          steps_dir: Path | None = None, stop_after: str | None = None,
          guided: bool = False) -> AnatomieChiffrePresentation | None:
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
