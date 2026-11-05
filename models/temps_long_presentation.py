"""Models for the TEMPS LONG carousel (7 slides: 6, and one more once the author's position is written).

The archetype for a hot-news piece: the episodes people remember from the last
ten years (episodes) and the turning points that changed the rules over fifty
years (tournants), the three temporal readings — rupture, continuité, cycle — a
reader can test them against, and the traps a time series sets. Separate from
the format-agnostic ArticleFullAnalysis.
"""
from __future__ import annotations
from typing import Literal
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TempsLongHook(BaseModel):
    title: str    # slide 1 — the raw fact, dated, ≤64 characters
    promise: str  # slide 1 — « Prendre du recul sur … » (« En juger soi-même. » is added by the template)


class TempsLongRepere(BaseModel):
    """One dated reference point of a timeline: an episode people remember, or a turning point of the rules."""
    date: str          # « 2018–2019 », « 1986 »
    label: str
    remark: str = ""   # what the point lets the reader check in the slide's lead — one line


class TempsLongFrise(BaseModel):  # slides 2 and 3 — a timeline of dated reference points
    title: str
    lead: str
    reperes: list[TempsLongRepere] = Field(default_factory=list)   # 3 to 5, oldest first


class TempsLongReading(BaseModel):
    kind: Literal["rupture", "continuite", "cycle"]
    signature: str   # the hypothesis, as a question: what this reading says in this case
    indicator: str   # the test: the bold measure, and what one would see if the reading held
    where: str = ""       # where to find the series: an organisation, never a URL


class TempsLongLecture(BaseModel):  # slide 4 — rupture, continuité or cycle?
    title: str
    lead: str         # the procedure and the measure: « Pour trancher : comparer … d'un épisode à l'autre »
    readings: list[TempsLongReading] = Field(default_factory=list)   # 3, in this order
    question: str     # the neutral closing question: not drawn on the slide, taken up by the sign-off and the caption
    author: str = ""  # one line under the cards: which of the readings the author's own thesis combines — attributed, never judged


class TempsLongPiege(BaseModel):
    title: str
    question: str     # the question a reader can ask


class TempsLongPieges(BaseModel):  # slide 5 — the traps a time series sets
    title: str
    lead: str
    pieges: list[TempsLongPiege] = Field(default_factory=list)   # 3


class TempsLongPosition(BaseModel):  # slide 2 — what the author says, in the article's own frame
    title: str    # the claim in a few plain words, all white (the lead names the author)
    lead: str     # the summary: the author's position in one or two sentences
    ecarte: str   # card 1 — what the author sets aside (the explanation he rejects)
    diagnostic: str   # card 2 — his own reading
    mecanisme: str = ""   # card 3 — why it lasted and why it breaks (an older deck has three cards)
    issue: str    # card 4 — his conclusion


class TempsLongPresentation(BaseModel):
    # An older deck wrote `palier` and `vague_de_fond`: both keys are still read.
    model_config = ConfigDict(populate_by_name=True)

    # The post's own copy, not slide content: the Instagram caption.
    caption: str = ""
    hook: TempsLongHook
    tournants: TempsLongFrise = Field(validation_alias=AliasChoices("tournants", "vague_de_fond"))   # slide 3, written first
    episodes: TempsLongFrise = Field(validation_alias=AliasChoices("episodes", "palier"))            # slide 2
    position: TempsLongPosition | None = None   # slide 2 when written — an older deck has none and keeps its 6 slides
    lecture: TempsLongLecture       # slide 4
    pieges: TempsLongPieges         # slide 5


class TempsLongDocument(BaseModel):
    """Output of the extractor: the full analysis + the carousel presentation layer."""
    analysis: "ArticleFullAnalysis"  # noqa: F821  (resolved at runtime)
    presentation: TempsLongPresentation


from models.full_analysis import ArticleFullAnalysis  # noqa: E402
TempsLongDocument.model_rebuild()
