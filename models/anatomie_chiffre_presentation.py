"""Models for the ANATOMIE D'UN CHIFFRE carousel (6 slides).

The archetype for a statistic, a poll, a ranking: the figures the article gives,
the story it builds on them, what those figures cannot decide, and the readings
that would decide it. Separate from the format-agnostic ArticleFullAnalysis.
"""
from __future__ import annotations
from typing import Literal
from pydantic import AliasChoices, BaseModel, Field


class AnatomieHook(BaseModel):
    title: str    # slide 1 — the raw figure in « », ≤64 characters
    promise: str  # slide 1 — « <sujet> : ce que le chiffre dit, et ce qu'on en conclut » (« En juger soi-même. » is added by the template)


class AnatomieNote(BaseModel):
    """One line under a card: a source to check, or a remark."""
    kind: Literal["source", "remark"] = "source"
    text: str


class AnatomieFigure(BaseModel):
    value: str         # « 505.000 $ », « × 15 »
    label: str
    compare: str = ""  # the term of comparison, when the source gives one


class AnatomieReading(BaseModel):
    nom: str       # the reading's short name, shown on slides 4 and 5
    formule: str   # the reading in one neutral sentence


class AnatomieAxe(BaseModel):
    """The fact to explain and the three competing readings, fixed before any slide is
    written. No slide shows it as such. The third reading is the article's own."""
    fait: str
    readings: list[AnatomieReading] = Field(default_factory=list)   # 3


class AnatomieChiffres(BaseModel):  # slide 2 — the figures the article gives
    claim: str
    detail: str = ""   # no longer produced (older decks load)
    figures: list[AnatomieFigure] = Field(default_factory=list)     # 3 to 4
    note: AnatomieNote | None = None


class AnatomieRecitRow(BaseModel):
    # `donnee` and `prevision` belong to older decks; the story now tells explication → interpretation → consequence
    kind: Literal["donnee", "explication", "interpretation", "consequence", "prevision"]
    text: str
    remark: str = ""   # how much weight this statement can bear (a question or a limit)
    basis: str = ""    # no longer produced (older decks load)


class AnatomieRecit(BaseModel):  # slide 3 — the logical thread, from the measured fact to the story
    title: str   # the measured fact, describing the key figure
    rows: list[AnatomieRecitRow] = Field(default_factory=list)      # 2 to 3: explication, interpretation, consequence


class AnatomieAngleMortCard(BaseModel):
    claim: str         # the blind spot, as a question ending in « ? »
    detail: str = ""   # no longer produced (older decks load)
    notes: list[AnatomieNote] = Field(default_factory=list)   # one: the clue to validate or invalidate the assumption
    opens: list[int] = Field(default_factory=list)   # the two readings (1-based) this blind spot leaves undecided


class AnatomieAngleMort(BaseModel):  # slide 4 — what these figures do not count
    title: str
    cards: list[AnatomieAngleMortCard] = Field(default_factory=list)  # 2


class AnatomieLectureRow(BaseModel):
    nom: str    # equals the axe's reading name
    voir: str   # what we would see if this reading held
    # what it would mean for the figure (« Alors … »); older decks called it `ou`
    sens: str = Field("", validation_alias=AliasChoices("sens", "ou"))


class AnatomieLectures(BaseModel):  # slide 5 — what would separate the readings
    title: str
    lead: str = ""   # no longer produced (older decks load)
    rows: list[AnatomieLectureRow] = Field(default_factory=list)    # 3


class AnatomieChiffrePresentation(BaseModel):
    # The post's own copy, not slide content: the Instagram caption.
    caption: str = ""
    axe: AnatomieAxe | None = None   # not rendered as such: what every slide is written toward
    hook: AnatomieHook
    chiffres: AnatomieChiffres
    recit: AnatomieRecit
    angle_mort: AnatomieAngleMort
    lectures: AnatomieLectures


class AnatomieChiffreDocument(BaseModel):
    """Output of the extractor: the full analysis + the carousel presentation layer."""
    analysis: "ArticleFullAnalysis"  # noqa: F821  (resolved at runtime)
    presentation: AnatomieChiffrePresentation


from models.full_analysis import ArticleFullAnalysis  # noqa: E402
AnatomieChiffreDocument.model_rebuild()
