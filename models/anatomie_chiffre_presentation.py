"""Models for the ANATOMIE D'UN CHIFFRE carousel (6 slides).

The archetype for a statistic, a poll, a ranking: how the figure was measured
(the black box, what it establishes and how it decomposes), what that measure
leaves out, and the question the figure is a symptom of. Separate from the
format-agnostic ArticleFullAnalysis.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class AnatomieHook(BaseModel):
    title: str    # slide 1 — the raw figure in « », ≤64 characters
    promise: str  # slide 1 — « <subject> : comment il se mesure, et la question qu'il pose » (« En juger soi-même. » is added by the template)


class AnatomieNote(BaseModel):
    """One line under a card: a source to check, or a remark."""
    kind: Literal["source", "remark"] = "source"
    text: str


class AnatomieFigure(BaseModel):
    value: str         # « 15 fois », « non précisé »
    label: str
    compare: str = ""  # the term of comparison, when the source gives one


class AnatomieBoiteNoire(BaseModel):  # slide 2 — how the figure was measured
    figures: list[AnatomieFigure] = Field(default_factory=list)  # 2 to 4
    source_card: AnatomieFigure | None = None   # the primary source and the chain (« Fed → WSJ → BFM »)
    claim: str = ""
    detail: str = ""


class AnatomiePart(BaseModel):
    value: str
    label: str


class AnatomieEclairage(BaseModel):  # slide 3 — what the figure establishes, and how it decomposes
    claim: str
    detail: str = ""
    part1: AnatomiePart | None = None   # the first quantity (numerator, starting point), as the source gives it
    part2: AnatomiePart | None = None   # the second one (denominator, end point)
    ratio: AnatomiePart | None = None   # the ratio between them
    note: AnatomieNote | None = None


class AnatomieLimite(BaseModel):
    claim: str
    detail: str = ""
    notes: list[AnatomieNote] = Field(default_factory=list)  # series or organisations to consult


class AnatomiePerimetre(BaseModel):  # slide 4 — what the measure cannot capture; no figure added
    title: str
    statistique: AnatomieLimite   # what a mean or a median hides
    periode: AnatomieLimite       # the dates, the starting point, a date against a generation followed


class AnatomieVariable(BaseModel):
    """The question behind the figure, fixed before any slide is written. Slide 5 shows it
    (facts left, question right, the variable as a two-pole bar); slides 2–4 are written toward it."""
    title: str            # « A ou B », in neutral words of equal weight
    variable: str         # the one variable the figure approaches
    pole_a: str
    pole_b: str
    proxy: str            # why the figure stands for the variable — our reading, named as such
    question: str         # the open question, neither binary nor normative — the CTA opens it
    facts: list[str] = Field(default_factory=list)   # what the source states (2–3), to join
    implication: str = ""  # what a move of the variable would imply, as a consequence to examine
    looks: list[AnatomieNote] = Field(default_factory=list)  # where to look at the variable directly


class AnatomieChiffrePresentation(BaseModel):
    # The post's own copy, not slide content: the Instagram caption.
    caption: str = ""
    variable: AnatomieVariable | None = None   # slide 5; fixed context of the earlier steps
    hook: AnatomieHook
    boite_noire: AnatomieBoiteNoire
    eclairage: AnatomieEclairage
    perimetre: AnatomiePerimetre


class AnatomieChiffreDocument(BaseModel):
    """Output of the extractor: the full analysis + the carousel presentation layer."""
    analysis: "ArticleFullAnalysis"  # noqa: F821  (resolved at runtime)
    presentation: AnatomieChiffrePresentation


from models.full_analysis import ArticleFullAnalysis  # noqa: E402
AnatomieChiffreDocument.model_rebuild()
