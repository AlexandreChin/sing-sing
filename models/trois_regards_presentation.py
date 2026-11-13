"""Models for the TROIS REGARDS carousel.

The archetype for a question the article answers from one angle: the article's own
position, then three prisms of the catalogue (`agent/trois_regards_prisms.py`, e.g.
politique, économique, sociologique) that each read the same question differently,
and what each would measure. Separate from the format-agnostic ArticleFullAnalysis.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class RegardsAxe(BaseModel):
    """The question and the three prisms, fixed before any slide is written. No slide
    shows it as such."""
    question: str            # the wide question the deck asks, ≤60 characters
    article_question: str    # the narrower question the article actually answers
    subject: str             # « la crise du logement », ≤36 characters
    prisms: list[str] = Field(default_factory=list)   # three slugs
    # media, media_grounding and closing default to "" on purpose: older decks load without them
    media: str = ""          # the prism the article itself takes
    media_grounding: str = ""   # why the article belongs to that prism, ≤120 characters
    closing: str = ""        # the closing question naming the three prisms, ends in « ? », ≤110


class RegardsHook(BaseModel):
    title: str     # slide 1 — the wide question, ≤70 characters
    promise: str   # slide 1 — « Trois regards sur <sujet> ; à vous d'en juger. »


class RegardsCard(BaseModel):
    label: str   # ≤30 characters
    text: str    # ≤76 characters


class RegardsPosition(BaseModel):  # slide 2 — the article's frame
    kicker: str
    title: str
    lead: str    # says which narrower question the article answers
    cards: list[RegardsCard] = Field(default_factory=list)   # 3 or 4 (the fourth is optional)


class RegardsPrismSlide(BaseModel):  # slides 3 to 5 — one prism each
    prism: str
    question: str
    lines: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)   # names to consult, 1 to 3 (2 or 3 asked for)
    media_note: str = ""    # only on the prism the article takes


class RegardsMatrixColumn(BaseModel):
    prism: str
    variable: str
    indicator: str


class RegardsMatrix(BaseModel):  # slide 6 — what each prism would measure, no digit
    title: str
    columns: list[RegardsMatrixColumn] = Field(default_factory=list)   # 3


class TroisRegardsPresentation(BaseModel):
    # The post's own copy, not slide content: the Instagram caption.
    caption: str = ""
    axe: RegardsAxe | None = None   # not rendered as such: what every slide is written toward
    hook: RegardsHook
    position: RegardsPosition
    prisms: list[RegardsPrismSlide] = Field(default_factory=list)   # 3
    matrix: RegardsMatrix


class TroisRegardsDocument(BaseModel):
    """Output of the extractor: the full analysis + the carousel presentation layer."""
    analysis: "ArticleFullAnalysis"  # noqa: F821  (resolved at runtime)
    presentation: TroisRegardsPresentation


from models.full_analysis import ArticleFullAnalysis  # noqa: E402
TroisRegardsDocument.model_rebuild()
