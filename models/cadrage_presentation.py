"""Models for the CADRAGE & LOGIQUE carousel (7 slides).

The archetype for an opinion piece: the speaker's case (the facts it leans on,
then its thesis and solution), the blind spot of that solution, the levers that
answer it, and the arbitrage left to the reader. Separate from the
format-agnostic ArticleFullAnalysis.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class CadrageHook(BaseModel):
    title: str    # slide 1 — the hook, ≤64 characters
    promise: str  # slide 1 — « Décryptage d'une prise de position sur … » (« En juger soi-même. » is added by the template)


class CadrageNote(BaseModel):
    """One line under a card: a source to check, or a remark (a citation, a context)."""
    kind: Literal["source", "remark"] = "source"
    text: str


class CadrageStatement(BaseModel):
    claim: str         # the line that carries the point
    detail: str = ""   # its explanation, one size down


class CadrageFigure(BaseModel):
    value: str         # « 95% », « × 8 »
    label: str
    compare: str = ""  # the term of comparison, when the speaker gives one


class CadrageConstat(BaseModel):  # slide 2 — the facts the speaker leans on
    title: str
    figures: list[CadrageFigure] = Field(default_factory=list)  # 2 to 4
    claim: str = ""
    detail: str = ""


class CadrageThese(BaseModel):  # slide 3 — what the speaker concludes and proposes
    title: str
    these: CadrageStatement
    solution: CadrageStatement
    notes: list[CadrageNote] = Field(default_factory=list)      # under the thesis


class CadrageAngleMort(BaseModel):  # slide 4 — what the solution risks, from outside the speaker's frame
    title: str         # the catchy line: a headline, as a press title would put it
    claim: str
    detail: str = ""
    notes: list[CadrageNote] = Field(default_factory=list)
    second: CadrageStatement | None = None      # a second card: a different blind spot, never a restatement of the first
    second_notes: list[CadrageNote] = Field(default_factory=list)


class CadrageLever(BaseModel):
    title: str
    detail: str
    note: CadrageNote | None = None   # an optional remark or source under the lever


class CadrageDepassement(BaseModel):  # slide 5 — the levers that attenuate the risk, at a cost
    title: str
    lead: str
    levers: list[CadrageLever] = Field(default_factory=list)    # 3


class CadrageOption(BaseModel):
    question: str
    pro: str
    con: str


class CadrageBoussole(BaseModel):  # slide 6 — the arbitrage: two questions, each with its pro and con
    title: str
    options: list[CadrageOption] = Field(default_factory=list)  # 2


class CadrageAxe(BaseModel):
    """The arbitrage the deck leads to, fixed before any slide is written. No slide shows it."""
    title: str       # « A ou B », in neutral words of equal weight
    variable: str    # the one variable being set
    position1: str   # the speaker's way
    position2: str   # the opposite setting
    thesis: str      # the speaker's thesis, in his frame


class CadragePresentation(BaseModel):
    # The post's own copy, not slide content: the Instagram caption.
    caption: str = ""
    axe: CadrageAxe | None = None   # not rendered: what every slide is written toward
    hook: CadrageHook
    constat: CadrageConstat
    these: CadrageThese
    angle_mort: CadrageAngleMort
    depassement: CadrageDepassement
    boussole: CadrageBoussole


class CadrageDocument(BaseModel):
    """Output of the extractor: the full analysis + the carousel presentation layer."""
    analysis: "ArticleFullAnalysis"  # noqa: F821  (resolved at runtime)
    presentation: CadragePresentation


from models.full_analysis import ArticleFullAnalysis  # noqa: E402
CadrageDocument.model_rebuild()
