"""Adapt agent for the ANATOMIE D'UN CHIFFRE carousel (6 slides).

A guided cascade: first the axe (the fact to explain and three competing readings,
never rendered as such), then in slide order the figures the article gives (chiffres),
the story it builds on them (recit), what those figures cannot decide (angle_mort),
what would decide it (lectures), then the hook; `writing` finishes with the caption,
without pausing. Each step proposes options with a reason and a ★, the author picks,
edits or asks for others (`choose`), and a pick feeds the later steps. Steps are cached
in `<format>/adapt_steps/` with a stamp of the inputs and the earlier picks.

An option's fields are flat strings so that `choose --edit ID.field=TEXT` and `fix`
can rewrite any of them: a figure, a reading, a row are one line each, their parts
separated by « | » (see `to_fragment`).

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

class AxeOption(BaseModel):
    fait: str        # the movement to explain, in neutral words
    article: str     # « nom | formule » — the article's own reading (not drawn on slide 5)
    lecture1: str    # « nom | formule » — four alternatives to the article's reading, each explaining the rise
    lecture2: str
    lecture3: str
    lecture4: str


class ChiffresOption(BaseModel):
    claim: str
    fig1: str        # « valeur | libellé | comparaison » — the key figure, drawn big (« 9 → 15 »): its label is a plain sentence
    fig2: str
    fig3: str
    fig4: str        # optional reference figure (the overall figure), drawn small; empty when none
    note1: str       # « remarque | texte » glossing the statistical term, or « source | texte »


class RecitOption(BaseModel):
    title: str
    # title: specific to the article — names the elements of its story (explanation, framing), never repeats the key figure
    row1: str        # « type | texte | remarque » — type: explication, interpretation, consequence
    row2: str
    row3: str        # optional


class AngleMortOption(BaseModel):
    title: str
    head1: str       # card 1 — the blind spot stated in a short sentence (the card's title)
    claim1: str      # card 1 — the same blind spot as a question ending in « ? » (drawn as the comment under the title)
    verifier1: str   # how to validate or invalidate the assumption it questions (an infinitive sentence)
    ouvre1: str      # the two readings it leaves undecided, e.g. « 1,3 » (not drawn)
    head2: str
    claim2: str      # card 2 — another blind spot, as a question
    verifier2: str
    ouvre2: str
    head3: str
    claim3: str      # card 3 — a third blind spot
    verifier3: str
    ouvre3: str
    head4: str
    claim4: str      # card 4 — a fourth blind spot
    verifier4: str
    ouvre4: str


class LecturesOption(BaseModel):
    title: str
    lead: str        # one line under the title: the frame shared by the three cards (« Trois pistes, chacune avec son indice à chercher. »)
    lecture1: str    # « nom | hypothèse | **mesure** …, au conditionnel » — names equal the axe's
    lecture2: str
    lecture3: str
    lecture4: str


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
    Step(1, "axe", AxeOption, "fait", 3),
    Step(2, "chiffres", ChiffresOption, "claim", 3),
    Step(3, "recit", RecitOption, "title", 3),
    Step(4, "angle_mort", AngleMortOption, "title", 3),
    Step(5, "lectures", LecturesOption, "title", 3),
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

# (step, field) → ("words" | "chars", cap). Characters wherever the text is drawn: the caps
# were measured on the rendered slides (a seeded worst-case render test guards them).
_CAPS: dict[tuple[str, str], tuple[str, int]] = {
    ("axe", "fait"): ("words", 20),
    ("chiffres", "claim"): ("chars", 54), ("chiffres", "note1"): ("chars", 110),
    ("recit", "title"): ("chars", 46),
    ("angle_mort", "title"): ("chars", 40),
    **{("angle_mort", f"head{i}"): ("chars", 36) for i in (1, 2, 3, 4)},
    **{("angle_mort", f"claim{i}"): ("chars", 46) for i in (1, 2, 3, 4)},
    **{("angle_mort", f"verifier{i}"): ("chars", 66) for i in (1, 2, 3, 4)},
    ("lectures", "title"): ("chars", 30), ("lectures", "lead"): ("chars", 64),
    ("hook", "title"): ("chars", 64), ("hook", "promise"): ("chars", 100),
}
# a « a | b | c » field: the name and character cap of each part
_PART_CAPS: dict[tuple[str, str], tuple[tuple[str, int], ...]] = {
    **{("axe", name): (("name", 28), ("formula", 90)) for name in ("article", "lecture1", "lecture2", "lecture3", "lecture4")},
    # fig1 is the key figure, drawn big and alone on its line: a plain sentence, its comparison glosses the term
    ("chiffres", "fig1"): (("value", 9), ("label", 64), ("comparison", 54)),
    **{("chiffres", f"fig{i}"): (("value", 9), ("label", 34), ("comparison", 26)) for i in (2, 3, 4)},
    **{("recit", f"row{i}"): (("type", 16), ("text", 80), ("remark", 90)) for i in (1, 2, 3)},
    **{("lectures", f"lecture{i}"): (("name", 28), ("hypothesis", 56), ("number to follow", 90)) for i in (1, 2, 3, 4)},
}
_ACCUSING = re.compile(r"\b(biais|manipulation|manipul\w+|mensonges?|trompeu\w+|fallacieu\w+|sophismes?)\b", re.I)
_HASHTAG = re.compile(r"#\w+")
_QUOTED = re.compile(r"«[^»]*»")
_DIGIT = re.compile(r"\d")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_KINDS = ("explication", "interpretation", "consequence")
_REQUIRED = {"axe": ("fait", "article", "lecture1", "lecture2", "lecture3", "lecture4"),
             "chiffres": ("claim", "fig1", "fig2", "fig3"),
             "recit": ("title", "row1", "row2"),
             "angle_mort": ("title", *(f"{n}{i}" for i in (1, 2, 3, 4) for n in ("head", "claim", "verifier", "ouvre"))),
             "lectures": ("title", "lead", "lecture1", "lecture2", "lecture3", "lecture4")}
# slides 4 and 5 are outside the article's frame and add no figure (the `ouvre` pair is a reference, not a figure)
_NO_DIGIT = {"angle_mort": {"title", *(f"{n}{i}" for i in (1, 2, 3, 4) for n in ("head", "claim", "verifier"))},
             "lectures": {"title", "lead", "lecture1", "lecture2", "lecture3", "lecture4"}}
# a statistical term the reader may not know: `chiffres.note1` must gloss it in plain words
_JARGON = re.compile(r"\b(médian\w*|écart[- ]type|percentiles?|quantiles?|décile\w*|quartile\w*|corrélation)\b", re.I)


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
    return re.search(rf"(?<![\d.,]){re.escape(number)}(?!\d|[.,]\d)", article) is not None


def _bad_note(value: str) -> bool:
    kind, _, text = value.partition("|")
    return kind.strip().lower() not in ("source", "remarque") or not text.strip()


def _ouvre(value: str) -> list[int] | None:
    """« 1,3 » → [1, 3]; None when it is not two distinct readings numbered 1 to 4."""
    try:
        nums = [int(x) for x in value.split(",")]
    except ValueError:
        return None
    return nums if len(nums) == 2 and len(set(nums)) == 2 and all(1 <= n <= 4 for n in nums) else None


def _axe_names(fragments: dict[str, dict]) -> list[str]:
    axe = fragments.get("axe", {}).get("axe")
    return [r.get("nom", "") for r in axe.get("readings", [])] if axe else []


def field_errors(step: str, fields: dict[str, Any], fragments: dict[str, dict],
                 article: str | None) -> tuple[list[str], list[str]]:
    """(hard, flags) on one step's fields, given the earlier fragments."""
    hard, flags = [], []
    no_digit = _NO_DIGIT.get(step, ())
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
        if name in no_digit and _DIGIT.search(value):
            hard.append(f"{step}.{name} holds a digit — this slide is outside the article's frame and adds no figure")
    for (st, name), caps in _PART_CAPS.items():
        if st == step and str(fields.get(name, "")).strip():
            for (part_name, cap), part in zip(caps, _parts(fields[name], len(caps))):
                if len(re.sub(r"\*\*", "", part)) > cap:
                    hard.append(f"{step}.{name}: the {part_name} is {len(re.sub(r"\*\*", "", part))} characters (max {cap})"
                                + (" — it is drawn big; for a gap write « ? » and put « non précisé » in the comparison"
                                   if part_name == "value" else ""))
            if not all(_parts(fields[name], len(caps))[:2]) and not name.startswith("fig"):
                hard.append(f"{step}.{name} must read « {' | '.join(n for n, _ in caps)} »")
    for name in _REQUIRED.get(step, ()):
        if not str(fields.get(name, "")).strip():
            hard.append(f"{step}.{name} is empty")

    if step == "axe":
        names = [_parts(str(fields.get(n, "")), 2)[0] for n in ("article", "lecture1", "lecture2", "lecture3", "lecture4")]
        if len({_norm(n) for n in names if n}) < len([n for n in names if n]):
            hard.append("axe: two readings share a name — the article's reading and the four alternatives must differ")
    if step == "chiffres":
        for name in ("fig1", "fig2", "fig3", "fig4"):
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            value_, label, compare = _parts(value, 3)
            if not value_ or not label:
                hard.append(f"chiffres.{name} must read « valeur | libellé | comparaison » (the comparison is optional)")
            elif article and (nums := _NUMBER.findall(value_)) and not all(_in_source(n, article) for n in nums) \
                    and "calcul" not in compare.lower():
                flags.append(f"chiffres.{name}: {value_!r} does not appear as written in the source — "
                             "check it; if recomputed, say « calculé » in the comparison")
        value = str(fields.get("note1", "")).strip()
        if value and _bad_note(value):
            hard.append("chiffres.note1 must read « source | texte » or « remarque | texte »")
        if (term := next((m.group(0).lower() for n in ("fig1", "fig2", "fig3", "fig4")
                          if (m := _JARGON.search(str(fields.get(n, "")))) ), None)) \
                and term[:5] not in _parts(str(fields.get("note1", "")), 2)[1].lower():
            flags.append(f"chiffres: « {term} » is a statistical term — gloss it in plain words in note1 (« remarque | … »)")
    if step == "recit":
        kinds = []
        for name in ("row1", "row2", "row3"):
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            kind, text, remark = _parts(value, 3)
            kinds.append(kind)
            if kind not in _KINDS:
                hard.append(f"recit.{name}: the type must be one of {', '.join(_KINDS)}")
            if not remark:
                hard.append(f"recit.{name} needs a remark (third part): the statement's status and what it depends on")
            elif re.search(r"\b(pas|sans)\b", remark, re.I):
                flags.append(f"recit.{name}: the remark names a shortfall (« pas », « sans ») — say the statement's status, not what it lacks")
            if article:
                for q in _QUOTED.findall(text):
                    if _norm(q.strip("«» ")) not in _norm(article):
                        flags.append(f"recit.{name}: {q} does not appear word for word in the source")
        if len(set(kinds)) < len(kinds):
            hard.append("recit: each row has its own type — explication, interpretation, consequence")
        axe = fragments.get("axe", {}).get("axe")
        if axe and axe.get("article", {}).get("nom"):
            third = axe["article"]
            stems = _stems(_plain(third.get("nom", "") + " " + third.get("formule", "")))
            told = [_parts(str(fields.get(n, "")), 3)[1] for n in ("row1", "row2", "row3")
                    if _parts(str(fields.get(n, "")), 3)[0] in ("explication", "interpretation")]
            if told and not any(_stems(_plain(t)) & stems for t in told):
                flags.append("recit: no explanation or interpretation shares a key word with the article's reading "
                             f"(axe article reading, « {third.get('nom', '')} »)")
    if step == "angle_mort":
        for i in (1, 2, 3, 4):
            value = str(fields.get(f"claim{i}", "")).strip()
            if value and not value.endswith("?"):
                hard.append(f"angle_mort.claim{i} must be a question ending in « ? »")
        pairs = []
        for i in (1, 2, 3, 4):
            name = f"ouvre{i}"
            value = str(fields.get(name, "")).strip()
            if not value:
                continue
            pair = _ouvre(value)
            if pair is None:
                hard.append(f"angle_mort.{name} must be two different readings numbered 1 to 4, e.g. « 1,3 »")
            else:
                pairs.append(pair)
        readings = len(_axe_names(fragments)) or 4
        if len(pairs) == 4 and set().union(*map(set, pairs)) != set(range(1, readings + 1)):
            hard.append(f"angle_mort: the four « ouvre » pairs must together cover the {readings} readings")
    if step == "lectures":
        names = _axe_names(fragments)
        for i in (1, 2, 3, 4):
            value = str(fields.get(f"lecture{i}", "")).strip()
            if value and len(names) >= i and _norm(_parts(value, 3)[0]) != _norm(names[i - 1]):
                hard.append(f"lectures.lecture{i} is named « {_parts(value, 3)[0]} » but the axe's reading {i} is « {names[i - 1]} »")
            last = _parts(value, 3)[2] if value else ""
            if value and not re.match(r"\*\*[^*]+\*\*\s*\S", last):
                hard.append(f"lectures.lecture{i}: the last part starts with the measure in bold (**…**), then says what to look for")
        title = str(fields.get("title", "")).strip()
        if title and not title.endswith("?"):
            hard.append("lectures.title must be a question ending in « ? »")
        # advisory: each alternative must follow from the blind spots of slide 4 that leave it open
        cards = fragments.get("angle_mort", {}).get("angle_mort", {}).get("cards", [])
        for i in (1, 2, 3, 4):
            value = str(fields.get(f"lecture{i}", "")).strip()
            blind = " ".join(f"{c.get('claim', '')} {c.get('detail', '')} " + " ".join(n.get("text", "") for n in c.get("notes", []))
                             for c in cards if i in c.get("opens", []))
            if value and blind and not _stems(_plain(value)) & _stems(_plain(blind)):
                flags.append(f"lectures.lecture{i} shares no key word with the slide 4 blind spots that leave it open "
                             "(their `ouvre` pairs): the alternative should follow from them")
    if step == "hook":
        if not fields.get("title", "").strip().startswith("«"):
            flags.append("hook.title is usually the raw figure, in « »")
        if "ce que le chiffre dit" not in fields.get("promise", "").lower():
            flags.append("hook.promise usually reads « <sujet> : ce que le chiffre dit, et ce qu'on en conclut »")
    if step == "writing":
        tags = _HASHTAG.findall(fields.get("caption", ""))
        if len(tags) != 4:
            hard.append(f"writing.caption has {len(tags)} hashtag(s), must have 4")
        if not 100 <= _words(fields.get("caption", "")) <= 190:
            hard.append(f"writing.caption is {_words(fields.get('caption', ''))} words (aim for about 150)")
    return hard, flags


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


def to_fragment(step: Step, option: Option) -> dict:
    f = option.fields
    if step.name == "axe":
        readings = []
        for i in (1, 2, 3, 4):
            if i == 4 and not str(f.get("lecture4", "")).strip():
                continue                                   # older decks carry three readings
            nom, formule = _parts(str(f.get(f"lecture{i}", "")), 2)
            readings.append({"nom": nom, "formule": formule})
        nom, formule = _parts(str(f.get("article", "")), 2)
        return {"axe": {"fait": f.get("fait", ""), "article": {"nom": nom, "formule": formule}, "readings": readings}}
    if step.name == "chiffres":
        figures = []
        for n in ("fig1", "fig2", "fig3", "fig4"):
            if str(f.get(n, "")).strip():
                value, label, compare = _parts(f[n], 3)
                figures.append({"value": value, "label": label, "compare": compare})
        note = _notes(f, ("note1",))
        return {"chiffres": {"claim": f.get("claim", ""),
                             "figures": figures, "note": note[0] if note else None}}
    if step.name == "recit":
        rows = []
        for n in ("row1", "row2", "row3"):
            if str(f.get(n, "")).strip():
                kind, text, remark = _parts(f[n], 3)
                rows.append({"kind": kind, "text": text, "remark": remark})
        return {"recit": {"title": f.get("title", ""), "rows": rows}}
    if step.name == "angle_mort":
        cards = []
        for i in (1, 2, 3, 4):
            opens = _ouvre(str(f.get(f"ouvre{i}", ""))) or []
            clue = str(f.get(f"verifier{i}", "")).strip()
            notes = [{"kind": "source", "text": clue}] if clue else []
            # the card's title is the stated blind spot; the question is its comment (`detail`)
            cards.append({"claim": f.get(f"head{i}", ""), "detail": f.get(f"claim{i}", ""), "notes": notes, "opens": opens})
        return {"angle_mort": {"title": f.get("title", ""), "cards": cards}}
    if step.name == "lectures":
        rows = []
        for i in (1, 2, 3, 4):
            if i == 4 and not str(f.get("lecture4", "")).strip():
                continue
            nom, voir, sens = _parts(str(f.get(f"lecture{i}", "")), 3)
            rows.append({"nom": nom, "voir": voir, "sens": sens})
        return {"lectures": {"title": f.get("title", ""), "lead": f.get("lead", ""), "rows": rows}}
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


def fix(full, steps_dir: Path, field: str, text: str, article_text: str | None = None) -> tuple[str, list[str]]:
    """Overwrite one field of the picked option of the step that owns it (« <step>.<field> »,
    or `caption`), and rebuild that step's fragment. Nothing is regenerated: the later
    steps are re-stamped. Returns the owner step and the hard-rule failures of the rewritten
    field and of every later step (a renamed reading, a figure over its cap…), as warnings:
    like `choose`, `fix` leaves the last word to the author."""
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
    fragments: dict[str, dict] = {}
    warnings: list[str] = []
    for s in STEPS:
        current, saved = _load(steps_dir, s)
        if current is None or not current.picked:
            break                                  # nothing later can be re-stamped
        if s.n > owner.n:
            saved = stamp_for(base, [fragments[t.name] for t in STEPS if t.n < s.n])
        fragments[s.name] = current.fragment
        if s.n >= owner.n:
            chosen = next(o for o in current.options if o.id == current.picked[0])
            hard, chosen.flags = field_errors(s.name, chosen.fields, {k: v for k, v in fragments.items() if k != s.name},
                                              article_text)
            warnings += hard
            _save(steps_dir, current, saved)
    log_choice(steps_dir.parent, {"step": owner_name, "event": "fix", "field": field,
                                  "before": before, "after": text})
    return owner_name, warnings
