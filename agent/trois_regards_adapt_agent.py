"""Adapt agent for the TROIS REGARDS carousel (8 slides).

A guided cascade: first the axe (the wide question, the narrower one the article answers
and the three prisms that read it, never rendered as such), then in slide order the
article's position, the three prism slides (four cards each: a cause and how it acts), the
tensions (where two regards disagree, one card per pair of prisms, one side each), the
limites (« Les angles morts »: what each regard alone leaves out, one card per prism) and the
hook; `writing` finishes with the caption, without pausing. Each step proposes
options with a reason and a ★, the author picks, edits or asks for others (`choose`),
and a pick feeds the later steps. The `prismes` step is picked slot by slot (one option
per prism). Steps are cached in `<format>/adapt_steps/` with a stamp of the inputs and
the earlier picks.

An option's fields are flat strings so that `choose --edit ID.field=TEXT` and `fix`
can rewrite any of them: a card is one field per part (`headN`, `answerN` or `claimN`, `indiceN`),
a clue « source | find » and a position card « label | text » are one line each, their parts
separated by « | », a tension's pair is two prism numbers « 1,2 » (see `to_fragment`).

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
    title: str               # the prism's thesis on the deck's question
    lead: str                # one line: what this regard examines; empty on the media's prism (its media_note is the lead)
    head1: str               # four cards: the cause this regard points to (headN), one sentence of how it acts and
    head2: str               # what it explains (answerN, never a question), a clue « source | find » (indiceN)
    head3: str
    head4: str
    answer1: str
    answer2: str
    answer3: str
    answer4: str
    indice1: str
    indice2: str
    indice3: str
    indice4: str
    media_note: str          # only on the prism the article takes; empty otherwise


class TensionsOption(BaseModel):
    title: str               # a neutral phrase specific to the subject (a « ? » is allowed, not required)
    lead: str                # one line: the objects of the disagreement
    pair1: str               # two prism numbers « 1,2 »: the three cards take the three pairs
    pair2: str
    pair3: str
    head1: str               # two sides « a ; b »: a for the pair's first prism, b for the second (the tag names them)
    head2: str
    head3: str
    claim1: str              # the question it raises
    claim2: str
    claim3: str
    indice1: str             # « source | find »: what would help settle it
    indice2: str
    indice3: str


class LimitesOption(BaseModel):
    title: str               # a short neutral assertion, never a ranking
    lead: str                # one line: what stays out of sight when the three regards are put together
    head1: str               # card N is the axe's Nth prism: what this regard, taken alone, leaves out
    head2: str
    head3: str
    claim1: str              # the question that follows, discriminating
    claim2: str
    claim3: str
    indice1: str             # « source | find »: what would complete the picture
    indice2: str
    indice3: str


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
    Step(3, "prismes", PrismesOption, "title", 3, (2, 3), ("p1", "p2", "p3")),
    Step(4, "tensions", TensionsOption, "title", 3),
    Step(5, "limites", LimitesOption, "title", 3),
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
    """The step file and its stamp. A file whose options do not carry the step's current fields (the prism slides
    of an older step table: question, lines, sources) reads as unstamped, so it is stale: retired and rerun."""
    path = _path(steps_dir, step)
    if not path.exists():
        return None, ""
    stamp = path.with_suffix(".sha256")
    sf = StepFile.model_validate_json(path.read_text(encoding="utf-8"))
    fields = set(step.option_model.model_fields) if step.option_model is not None else None
    if fields is not None and any(set(o.fields) != fields for o in sf.options):
        return sf, ""
    return sf, stamp.read_text().strip() if stamp.exists() else ""


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


_PAIR = re.compile(r"\s*(\d)\s*,\s*(\d)\s*")


def _pair(value: str) -> list[int]:
    """« 1,2 » (or « 2, 1 ») → [1, 2]; anything else → []."""
    m = _PAIR.fullmatch(str(value))
    return sorted(int(x) for x in m.groups()) if m else []


def _clue(value: str) -> dict[str, str]:
    source, find = _parts(str(value), 2)
    return {"source": source, "find": find}


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
            slide = {"prism": axe_prisms[n - 1] if n <= len(axe_prisms) else "", "title": g.get("title", ""),
                     "lead": g.get("lead", ""),
                     "cards": [{"head": g.get(f"head{k}", ""), "answer": g.get(f"answer{k}", ""),
                                **_clue(g.get(f"indice{k}", ""))} for k in (1, 2, 3, 4)]}
            if str(g.get("media_note", "")).strip():
                slide["media_note"] = str(g["media_note"]).strip()
            slides.append(slide)
        return {"prisms": slides}
    if step.name == "tensions":
        return {"tensions": {"title": f.get("title", ""), "lead": f.get("lead", ""), "cards": [
            {"pair": _pair(f.get(f"pair{k}", "")), "head": f.get(f"head{k}", ""), "claim": f.get(f"claim{k}", ""),
             **_clue(f.get(f"indice{k}", ""))} for k in (1, 2, 3)]}}
    if step.name == "limites":            # card N is the axe's Nth prism: the renderer draws its name
        return {"limites": {"title": f.get("title", ""), "lead": f.get("lead", ""), "cards": [
            {"head": f.get(f"head{k}", ""), "claim": f.get(f"claim{k}", ""), **_clue(f.get(f"indice{k}", ""))}
            for k in (1, 2, 3)]}}
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
    ("position", "kicker"): ("chars", 26), ("position", "title"): ("chars", 32), ("position", "lead"): ("chars", 90),
    ("hook", "title"): ("chars", 70), ("hook", "promise"): ("chars", 100),
    # the four-card prism slides (the media's note is its slide's lead: one line, like every lead)
    ("prismes", "title"): ("chars", 40), ("prismes", "lead"): ("chars", 60), ("prismes", "media_note"): ("chars", 60),
    **{("prismes", f"head{i}"): ("chars", 36) for i in (1, 2, 3, 4)},
    **{("prismes", f"answer{i}"): ("chars", 90) for i in (1, 2, 3, 4)},
    # the tensions (slide 6): a head holds two sides « a ; b »; the title takes two lines up to 44 characters
    ("tensions", "title"): ("chars", 44), ("tensions", "lead"): ("chars", 60),
    **{("tensions", f"head{i}"): ("chars", 76) for i in (1, 2, 3)},
    **{("tensions", f"claim{i}"): ("chars", 46) for i in (1, 2, 3)},
    # « Les angles morts » (slide 7)
    ("limites", "title"): ("chars", 34), ("limites", "lead"): ("chars", 60),
    **{("limites", f"head{i}"): ("chars", 40) for i in (1, 2, 3)},
    **{("limites", f"claim{i}"): ("chars", 46) for i in (1, 2, 3)},
}
# (step, field) -> the parts of a « a | b » field, each with its cap in characters
_PART_CAPS: dict[tuple[str, str], tuple[tuple[str, int], ...]] = {
    **{("position", f"card{i}"): (("label", 30), ("text", 76)) for i in (1, 2, 3, 4)},
    # a clue: « <source nommée> | <ce qu'on y lit> »
    **{(step, f"indice{i}"): (("source", 30), ("find", 60))
       for step, n in (("prismes", 4), ("tensions", 3), ("limites", 3)) for i in range(1, n + 1)},
}
_REQUIRED = {"axe": ("question", "article_question", "subject", "prism1", "prism2", "prism3", "media",
                     "media_grounding", "closing"),
             "position": ("kicker", "title", "lead", "card1", "card2", "card3"),
             # a prism's lead depends on its slot (empty on the media's): checked with the media_note
             "prismes": tuple(f for f in PrismesOption.model_fields if f not in ("media_note", "lead")),
             "tensions": tuple(TensionsOption.model_fields),
             "limites": tuple(LimitesOption.model_fields),
             "hook": ("title", "promise")}
# the card steps: how many cards, and the field that carries a card's second line (a prism card answers, the others ask)
_CARDS = {"prismes": (4, "answer"), "tensions": (3, "claim"), "limites": (3, "claim")}
# a claim that asks whether the subject « explains » the crisis: generic, it discriminates nothing
_GENERIC_CLAIM = re.compile(r"\b(?:explique|expliquent|pèse|pèsent|nourrit|nourrissent|cause|causent|influence|influencent)"
                            r"(?:-t)?-(?:il|elle|ils|elles)\b[^?]*\b(?:crise|situation|problème)\b", re.I)
# a prism answer says how the cause acts: one of these links
_CAUSAL = re.compile(r"\b(?:(?:parce|lors|dès|puis)\s?qu(?:e\b|')|faute d(?:e\b|')|(?:donc|quand|si|s'ils?|car|ce qui)\b"
                     r"|(?:entra[îi]n|provoqu|pouss|condui)\w*)", re.I)
# a discriminating question compares two situations or two periods
_COMPARE = re.compile(r"\b(?:plus|moins|là où|selon|entre|avant|après|par rapport|davantage|que|mieux|pire)\b", re.I)
# what to find in a clue: a measure, a breakdown or a comparison
_PRECISE = re.compile(r"\b(?:par|selon|entre|évolutions?|parts?|taux|prix|nombres?|durées?|écarts?)\b", re.I)
_RANKING = re.compile(r"pèsen?t? le plus|quel regard|meilleur\w*|le mieux", re.I)
_RESTATES = 0.8
# a head's subject group: a determiner, a noun, its « de X » complements; the word after it is the leading verb
_DET = frozenset("le la les l un une des du de d ce cet cette ces son sa ses leur leurs chaque tout toute tous toutes "
                 "aucun aucune".split())
_OF = frozenset("de d du des au aux".split())
_FUNCTION = _DET | _OF | frozenset("à en par pour sur sous dans avec sans et ou qui que qu ne n pas se s y il elle ils "
                                   "elles on plus moins entre vers chez".split())
_ACCUSING = re.compile(r"\b(biais|manipulation|manipul\w+|mensonges?|trompeu\w+|fallacieu\w+|sophismes?)\b", re.I)
_BLAMING = re.compile(r"\b(oublie(?:nt|s)?|ignore(?:nt|s)?|omet(?:s|tent)?|néglige(?:nt|s)?|ne (?:dit|disent) pas)\b", re.I)
_PRESCRIPTIVE = re.compile(r"\b(il faut|faut-il|il faudrait|faudrait|doit|doivent|devrait|devraient)\b", re.I)
_QUOTED = re.compile(r"«[^»]*»")
_HASHTAG = re.compile(r"#\w+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_YEAR = re.compile(r"(?:1[5-9]|20)\d\d")
# on a prism and the axe's question, a date is allowed besides a year: « 15 mai », « 1er », a reference « 12/2023 »
_MONTHS = "janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre"
_DATE = re.compile(rf"\b(?:\d{{1,2}}(?:er)?\s+(?:{_MONTHS})\b|1er\b|\d{{1,2}}/\d{{4}}\b)", re.I)
# a link, or a bare domain (« ine.es »): a name followed by a common top-level domain
_URL = re.compile(r"https?:|www\.|\b[\w-]+\.(?:com|fr|es|org|eu|net|gov|info|int)\b", re.I)
_PROMISE = re.compile(r"Trois regards sur (\S.*?) ; à vous d'en juger\.")
_NO_DOMINANT = re.compile(r"aucun\b.{0,30}\bdomin|pas de prisme dominant|ne domine pas", re.I)
_NEAR_IDENTICAL = 0.6
_STOP = frozenset("""alors après aussi autre autres avant avoir avons cette celle celui comme comment dans donc elle elles
entre être leur leurs mais même moins plus pour quel quelle quelles quels sont sous tout toute toutes tous très vers
vous nous cela ceux dont lors quand quoi sans selon peut peuvent faire fait ainsi encore depuis""".split())


def _typo_plain(s: str) -> str:
    """French typography undone: a no-break space (NBSP, narrow NBSP) is a space, ’ is '."""
    return s.replace("\u00a0", " ").replace("\u202f", " ").replace("’", "'")


def _odd_digits(text: str) -> bool:
    """`text` holds a number that is neither a year (1500–2099) nor part of a date or a law reference."""
    return any(not _YEAR.fullmatch(n) for n in _NUMBER.findall(_DATE.sub(" ", text)))


_DIGIT_RULE = "only a year (1500–2099), a date (« 15 mai », « 1er ») or a reference (« 12/2023 ») is allowed outside the article's frame"


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


def _first_word(s: str) -> str:
    words = _typo_plain(s).split()
    return words[0].strip(",;:.«»").lower() if words else ""


def _leading_verb(head: str) -> str:
    """The word after a head's subject group (a determiner, a noun, its « de X » complements): « Les rapports de force
    font la crise » → « font ». Empty when that word is a function word (« Un gouvernement sans majorité »)."""
    w = re.findall(r"[^\W\d_]+", _typo_plain(head).lower())
    i = 1 if w and w[0] in _DET else 0
    i += 1
    while i + 1 < len(w) and w[i] in _OF:
        i += 2
    verb = w[i] if i < len(w) else ""
    return "" if verb in _FUNCTION else verb


def _card_errors(step: str, fields: dict[str, Any], axe: dict, question) -> tuple[list[str], list[str]]:
    """(hard, flags) of a card step (`prismes`, `tensions`, `limites`): its title and lead, then each card — a prism
    card answers (`answerN`, a sentence with a causal link), a tension or a blind spot asks (`claimN`, a
    discriminating question) — then the cards of the slide against one another."""
    hard, flags = [], []
    count, second = _CARDS[step]
    question_text = str(axe.get("question", ""))
    question_words = _key_words(question_text)
    subject = _norm(str(axe.get("subject", "")))
    title, lead = str(fields.get("title", "")), str(fields.get("lead", ""))
    for name in ("title", "lead"):
        if _odd_digits(str(fields.get(name, ""))):
            hard.append(f"{step}.{name} holds a digit — {_DIGIT_RULE}")
    if lead.strip().endswith("?"):
        hard.append(f"{step}.lead is a line, not a question — say what this slide examines")
    shown = [("title", title), ("lead", lead)] + ([("media_note", str(fields.get("media_note", "")))] if step == "prismes" else [])
    for name, value in shown:
        if value.strip() and question_text.strip() and (
                _norm(value) == _norm(question_text) or len(_key_words(value) & question_words) >= 3):
            flags.append(f"{step}.{name} repeats the deck's question — no slide from 3 to 7 repeats it; "
                         "say what this slide examines")
    if step == "limites" and (m := _RANKING.search(title)):
        flags.append(f"limites.title ranks the regards (« {m.group(0)} ») — the slide says what each regard leaves out, "
                     "never which one weighs most")
    cards, heads, seconds, with_subject = [], [], [], []
    for k in range(1, count + 1):
        head, line, clue = (str(fields.get(f"{n}{k}", "")) for n in ("head", second, "indice"))
        for name, value in ((f"head{k}", head), (f"{second}{k}", line), (f"indice{k}", clue)):
            if _odd_digits(value):
                hard.append(f"{step}.{name} holds a digit — {_DIGIT_RULE}")
        if _URL.search(clue):
            hard.append(f"{step}.indice{k} holds a URL — name the organisation, document or series, never a link")
        if second == "claim":
            question(f"claim{k}", line)
            if _GENERIC_CLAIM.search(_QUOTED.sub("", line)):
                hard.append(f"{step}.claim{k} is a generic question (« … explique-t-il la crise ? ») — ask a "
                            "discriminating one: compare two places or two periods, or name what would differ")
            elif line.strip() and not _COMPARE.search(line):
                flags.append(f"{step}.claim{k} has no comparison marker (plus, moins, là où, avant, après, selon…) — "
                             "a discriminating question compares two situations or two periods")
            find = _parts(clue, 2)[1]
            if find and (len(find.split()) < 5 or not _PRECISE.search(find)):
                flags.append(f"{step}.indice{k}: what to find there is vague — name a precise series or measure "
                             "(par …, selon …, l'évolution de …, le taux de …)")
        elif "?" in line:
            hard.append(f"prismes.answer{k} is a sentence, not a question — the prism answers: how the cause acts")
        elif line.strip():
            if not _CAUSAL.search(_typo_plain(line)):
                flags.append(f"prismes.answer{k} has no causal link (quand, si, donc, parce que, faute de, ce qui…) — "
                             "say how the cause acts and what it explains here")
            said = _key_words(line)
            if said and len(said & _key_words(head)) / len(said) >= _RESTATES:
                flags.append(f"prismes.answer{k} restates its head — say how the cause acts and what it explains here")
        if step == "tensions" and head.strip():
            sides = _typo_plain(head).split(";")
            if len(sides) != 2 or not all(x.strip() for x in sides):
                hard.append(f"tensions.head{k} must hold two sides « … ; … », one per prism of the pair, in the tag's "
                            "order (the tag names the prisms: the head does not)")
        text = f"{head} {line}"
        cards.append(_key_words(text) - question_words)
        heads.append(head)
        seconds.append(line)
        if subject and subject in _norm(text):
            with_subject.append(k)
        if text.strip() and question_words and not _key_words(text) & question_words:
            flags.append(f"{step}.card{k} shares no key word with the axe's question — each card answers that question")
    if len(with_subject) >= 2:
        flags.append(f"{step}: the subject « {axe.get('subject')} » appears in cards {', '.join(map(str, with_subject))} — "
                     "say it once at most, the cards vary their words")
    openings = [("head", heads)] + ([("answer", seconds)] if step == "prismes" else [])
    for i in range(count):
        for j in range(i + 1, count):
            for what, lines in openings:
                w = _first_word(lines[i])
                if w and w == _first_word(lines[j]):
                    flags.append(f"{step}: card{i + 1} and card{j + 1} open their {what} with the same word « {w} » — "
                                 "vary the openings")
            v = _leading_verb(heads[i])
            if v and v == _leading_verb(heads[j]):
                flags.append(f"{step}: the heads of card{i + 1} and card{j + 1} share the leading verb « {v} » — "
                             "vary the verbs")
            a, b = cards[i], cards[j]
            if a and b and len(a & b) / min(len(a), len(b)) >= _NEAR_IDENTICAL:
                flags.append(f"{step}: card{i + 1} and card{j + 1} say nearly the same thing — "
                             "each card should bring its own mechanism")
    return hard, flags


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
        # prescriptive verbs: everywhere on the tensions; on the limites, its title and heads
        if (step == "tensions" or (step == "limites" and (name == "title" or name.startswith("head")))) \
                and (m := _PRESCRIPTIVE.search(outside)):
            hard.append(f"{step}.{name} is prescriptive (« {m.group(0)} ») — the carousel weighs regards, "
                        "it never says what to do")
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
        if _odd_digits(str(fields.get("question", ""))):     # the hook's title
            hard.append(f"axe.question holds a digit — {_DIGIT_RULE}")
        question("closing", str(fields.get("closing", "")))
        closing = str(fields.get("closing", ""))
        if _NO_DOMINANT.search(str(fields.get("media_grounding", ""))):
            flags.append("axe: no prism clearly dominates the article — the media's prism is the closest one; "
                         "the « regard du média » line will say only what the article does with it")
        if re.search(r"\bou\b", closing):
            flags.append("axe.closing contains « ou » — it may read as a binary choice; the question should stay open")
        if (m := _RANKING.search(closing)):
            flags.append(f"axe.closing ranks the regards (« {m.group(0)} ») — ask what is still missing to understand "
                         "the subject, never which regard is best")
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
    if step in _CARDS:
        card_hard, card_flags = _card_errors(step, fields, axe, question)
        hard, flags = hard + card_hard, flags + card_flags
    if step == "tensions":
        pairs = []
        for k in (1, 2, 3):
            raw = str(fields.get(f"pair{k}", "")).strip()
            pair = _pair(raw)
            if raw and (not pair or pair[0] == pair[1] or not set(pair) <= {1, 2, 3}):
                hard.append(f"tensions.pair{k} « {raw} » must be two different prism numbers among 1, 2, 3, as « 1,2 »")
            elif pair:
                pairs.append(tuple(pair))
        if len(pairs) == 3 and sorted(pairs) != [(1, 2), (1, 3), (2, 3)]:
            hard.append("tensions: the three pairs must be the three pairs of prisms (1,2 ; 1,3 ; 2,3), one per card")
    if step == "prismes":
        note = str(fields.get("media_note", "")).strip()
        axe_prisms = _axe_prisms(fragments)
        n = int(slot[1:]) if re.fullmatch(r"p\d", slot) else 0
        lead = str(fields.get("lead", "")).strip()
        if axe.get("media") and 1 <= n <= len(axe_prisms):
            is_media = axe_prisms[n - 1] == axe["media"]
            if is_media and not note:
                hard.append("prismes.media_note is empty — this is the media's prism, it carries the « regard du média » line")
            if not is_media and note:
                hard.append("prismes.media_note must be empty — only the media's prism carries it")
            if is_media and lead:
                hard.append("prismes.lead must be empty on the media's prism — its media_note is the slide's lead")
            if not is_media and not lead:
                hard.append("prismes.lead is empty")
        if article:
            flags += [f"prismes.media_note: {q} does not appear word for word in the source"
                      for q in _QUOTED.findall(note) if _norm(q.strip("« »  ")) not in _norm(article)]
        words = lambda texts: _key_words(" ".join(texts)) - question_words   # noqa: E731
        mine = words([str(fields.get("title", "")), *(str(fields.get(f"{p}{k}", "")) for p in ("head", "answer")
                                                      for k in (1, 2, 3, 4))])
        for k, other in enumerate(fragments.get("prismes", {}).get("prisms", []), 1):
            if k == n:
                continue
            theirs = words([other.get("title", ""), *(c.get(p, "") for c in other.get("cards", []) for p in ("head", "answer"))])
            if mine and theirs and len(mine & theirs) / min(len(mine), len(theirs)) >= _NEAR_IDENTICAL:
                flags.append(f"prismes: this slide and the one of slot p{k} say nearly the same thing — "
                             "each prism should bring its own reading")
    if step == "hook":
        question("title", str(fields.get("title", "")))
        promise = str(fields.get("promise", "")).strip()
        m = _PROMISE.fullmatch(_typo_plain(_bare(promise))) if promise else None
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
    """Every cap a prompt may quote, by name (« {{cap:prismes.head1}} », or « {{cap:prismes.head}} » for every card):
    the prompts never write the numbers, so they cannot drift from the rules the options are checked against."""
    caps = {f"{s}.{f}": n for (s, f), (_, n) in _CAPS.items()}
    caps |= {f"{s}.{re.sub(r'\d+$', '', f)}": n for (s, f), (_, n) in _CAPS.items()}   # « prismes.head »
    for (s, f), parts in _PART_CAPS.items():
        for part, n in parts:
            caps[f"{s}.{f}.{part}"] = n
            caps[f"{s}.{re.sub(r'\d+$', '', f)}.{part}"] = n
    return caps


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


def _with_kept(step: Step, sf: StepFile, picks: list[str]) -> list[str]:
    """While a prism awaits its pick (after `more --prism`), the picks kept on the other slots complete
    `picks`: the author names only the missing slot(s), and naming a kept slot replaces its pick. Once
    every slot has a pick, `picks` must name one per slot again."""
    if not _multi(step) or not picks or _complete(step, sf):
        return list(picks)
    slot_of = {o.id: o.slot for o in sf.options}
    named = {slot_of.get(p) for p in picks}
    return list(picks) + [p for p in sf.picked if slot_of.get(p) not in named]


def _missing_slots(step: Step, sf: StepFile) -> list[str]:
    slot_of = {o.id: o.slot for o in sf.options}
    taken = {slot_of.get(p) for p in sf.picked}
    return [s for s in step.slots if s not in taken]


def _no_pick(steps_dir: Path, step: Step, sf: StepFile | None) -> str:
    """Why `step` cannot be fixed yet, and what to run."""
    if sf is not None and _multi(step) and sf.picked:
        missing = _missing_slots(step, sf)
        ids = [o.id for o in sf.options if o.slot in missing]
        return (f"{step.name} awaits a pick for {', '.join(missing)} (the other prisms are kept): run "
                f"`python main.py choose {steps_dir.parent} {step.name} --pick <one of {', '.join(ids)}>` first")
    return f"{step.name} has no pick: run `produce` first"


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
    if step.option_model is not None:
        body = (_PROMPTS / "0_options.md").read_text(encoding="utf-8") + "\n" + body
    return fill_caps(body)


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
    parts += [fill_caps((_PROMPTS / "0_shared.md").read_text(encoding="utf-8")), _prompt(step)]
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
    alone) and one recommended per slot. A hard-rule failure is sent back to the model
    for repair (`_call_with_retry`); an option still breaking one after the retries is
    kept as it is (the retry loop prints the failures, and they come back as ⚠ on the
    author's pick). RuntimeError only when the answer cannot be read: it does not fit the
    schema, its recommended indices are wrong, or a slot has no option."""
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
    kept = set(sf.picked) if _multi(step) else set()
    for slot in step.slots:
        opts = [o for o in sf.options if o.slot == slot]
        if not opts:
            continue
        if _multi(step):
            lines.append(f"[{slot}]")
        for o in opts:
            name = o.fields.get(step.text_field, "")
            lines.append(f"{o.id} — {name}" + (" ★" if o.id in sf.recommended else "")
                         + (" ✔ gardée" if o.id in kept else ""))
            lines += [f"   · {k} : {v}" for k, v in o.fields.items() if k != step.text_field]
            lines.append(f"   ↳ {o.reason}")
            lines += [f"   ⚠ {flag}" for flag in o.flags]
        if _multi(step):
            lines.append("")
    if kept and not _complete(step, sf):
        missing = _missing_slots(step, sf)
        lines.append(f"Kept picks (✔): {', '.join(sorted(kept))}. Still to pick: {', '.join(missing)} — "
                     f"`choose <fmt_dir> {step.name} --pick <one option of {', '.join(missing)}>`; the kept picks complete the set.")
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
    picks = _with_kept(st, sf, picks)
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


VERIFIED_STEPS = ("prismes", "tensions", "limites")
_VERIFY_SLOT = {"tensions": "t", "limites": "l"}     # a prism slide keeps its own slot (p1–p3)


async def verify_pick(steps_dir: Path, step: str, search=None) -> list[str]:
    """Check the sources named in the clues (`indiceN`, the part before « | ») of the picked option(s) against the
    web (see `trois_regards_verify`): the ⚠ lines for the author, the results kept beside the step and in the
    choice log. Advisory, never blocking."""
    from agent import trois_regards_verify as tv
    st = STEP_BY_NAME[step]
    sf, _ = _load(steps_dir, st)
    if step not in VERIFIED_STEPS or sf is None or not _complete(st, sf):
        return []
    axe_sf, _ = _load(steps_dir, STEP_BY_NAME["axe"])
    axe = (axe_sf.fragment if axe_sf else {}).get("axe", {})
    chosen = _chosen(st, sf)
    pts = tv.points({_VERIFY_SLOT.get(step, o.slot): o.fields for o in chosen}, list(axe.get("prisms", [])))
    results = await tv.verify_sources(pts, str(axe.get("subject", "")), search)
    tv.save(steps_dir, st.n, step, results)
    log_choice(steps_dir.parent, {"step": step, "event": "verify",
                                  "results": [{k: r[k] for k in ("slot", "field", "source", "status", "source_ref")}
                                              for r in results]})
    return tv.warnings(step, results)


# deck field → (owning step, slot or None, option field): « <step>.<field> », « prismes.<slot>.<field> », the caption
_FIELD_OWNER: dict[str, tuple[str, str | None, str]] = {
    (f"{st.name}.{slot}.{name}" if _multi(st) else f"{st.name}.{name}"): (st.name, slot if _multi(st) else None, name)
    for st in STEPS if st.option_model is not None for slot in st.slots for name in st.option_model.model_fields}
_FIELD_OWNER["caption"] = ("writing", None, "caption")


# axe fields that carry a prism id or decide the media's prism: the later steps were written for them
_PRISM_FIELDS = ("axe.prism1", "axe.prism2", "axe.prism3", "axe.media")
# the warning `fix` returns when the later steps were left stale (main.cmd_fix then says so instead of « keep your version »)
LATER_STALE = "are stale and will be regenerated on the next `adapt`"


def fix(full, steps_dir: Path, field: str, text: str, article_text: str | None = None) -> tuple[str, list[str]]:
    """Overwrite one field of the picked option of the step that owns it (« <step>.<field> »,
    « prismes.<slot>.<field> », or `caption`) and rebuild its fragment. Nothing is regenerated:
    a later step that was fresh is rebuilt from its picks and re-stamped; one that was already
    stale stays stale. A fix of a prism field of the axe (`_PRISM_FIELDS`) re-stamps nothing:
    the later steps were written for the old prisms, so they go stale and the next `adapt`
    reruns them. Returns the owner step and the hard-rule failures of the rewritten field and
    of every re-stamped later step, as warnings: like `choose`, `fix` leaves the last word to
    the author."""
    if field not in _FIELD_OWNER:
        raise ChoiceError(f"{field!r} is not a deck field — fields: {', '.join(_FIELD_OWNER)}")
    owner_name, slot, option_field = _FIELD_OWNER[field]
    owner = STEP_BY_NAME[owner_name]
    sf, _ = _load(steps_dir, owner)
    if sf is None or not sf.fragment or not _complete(owner, sf):
        raise ChoiceError(_no_pick(steps_dir, owner, sf))
    picked = next(o for o in _chosen(owner, sf) if slot is None or o.slot == slot)
    before, picked.fields[option_field] = picked.fields.get(option_field, ""), text
    picked.edited = True
    reprism = field in _PRISM_FIELDS and text.strip() != str(before).strip()
    base = base_inputs(full, article_text)
    old: dict[str, dict] = {}       # the fragments as saved before the fix
    new: dict[str, dict] = {}       # the fragments after it
    warnings: list[str] = []
    for s in STEPS:
        current, saved = _load(steps_dir, s)
        if s.n == owner.n:
            current = sf
        if current is None or not _complete(s, current):
            if s.n <= owner.n:
                raise ChoiceError(_no_pick(steps_dir, s, current))
            break                                  # nothing later can be re-stamped
        fresh = saved == stamp_for(base, [old[t.name] for t in STEPS if t.n < s.n])
        old[s.name] = current.fragment
        if s.n < owner.n:
            new[s.name] = current.fragment
            continue
        if s.n > owner.n:
            if reprism or not fresh:
                break                              # stale: the next `adapt` reruns it and every later step
            saved = stamp_for(base, [new[t.name] for t in STEPS if t.n < s.n])
        current.fragment = to_fragment(s, _chosen(s, current), new)
        new[s.name] = current.fragment
        warnings += _pick_rules(s, current, new, article_text)[0]
        _save(steps_dir, current, saved)
        if s.n == owner.n and not fresh:
            break                                  # a stale owner: its later steps stay stale too
    if reprism:
        later = ", ".join(t.name for t in STEPS if t.n > owner.n)
        warnings.append(f"{field} changes the prisms: the later steps ({later}) {LATER_STALE}")
    log_choice(steps_dir.parent, {"step": owner_name, "event": "fix", "field": field,
                                  "before": before, "after": text})
    return owner_name, warnings
