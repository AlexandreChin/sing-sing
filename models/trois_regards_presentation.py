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


class RegardsPrismCard(BaseModel):
    """One card of a prism slide: an assertion, the same point as a question, and a clue — where to look
    (`source`, a named organisation, document or series) and what to find there (`find`)."""
    head: str
    claim: str        # ends in « ? »
    source: str = ""
    find: str = ""


class RegardsPrismSlide(BaseModel):  # slides 3 to 5 — one prism each
    prism: str
    # an older deck carries question / lines / sources; a revision-2 deck carries title / cards
    question: str = ""
    lines: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)   # names to consult, 1 to 3 (2 or 3 asked for)
    media_note: str = ""    # only on the prism the article takes
    title: str = ""         # the prism's thesis on the deck's question
    cards: list[RegardsPrismCard] = Field(default_factory=list)   # 4


class RegardsMatrixColumn(BaseModel):
    prism: str
    variable: str
    indicator: str


class RegardsMatrix(BaseModel):  # slide 6 — what each prism would measure, no digit
    title: str
    columns: list[RegardsMatrixColumn] = Field(default_factory=list)   # 3


class RegardsTensionCard(BaseModel):
    pair: list[int]   # the two prisms that disagree, by their place in the axe (1-based), e.g. [1, 2]
    head: str         # the point of disagreement, stated neutrally
    claim: str        # the question it raises, ends in « ? »
    source: str = ""
    find: str = ""


class RegardsTensions(BaseModel):  # slide 6 — where the regards disagree, one card per pair of prisms
    title: str
    cards: list[RegardsTensionCard] = Field(default_factory=list)   # 3: pairs 1-2, 1-3, 2-3


class RegardsArbitrageCard(BaseModel):
    head: str         # the hypothesis that this prism weighs most
    test: str         # what one would observe if it did, in the conditional
    source: str = ""
    find: str = ""


class RegardsArbitrage(BaseModel):  # slide 7 — one card per prism, in the axe's order
    title: str
    cards: list[RegardsArbitrageCard] = Field(default_factory=list)   # 3


class TroisRegardsPresentation(BaseModel):
    # The post's own copy, not slide content: the Instagram caption.
    caption: str = ""
    axe: RegardsAxe | None = None   # not rendered as such: what every slide is written toward
    hook: RegardsHook
    position: RegardsPosition
    prisms: list[RegardsPrismSlide] = Field(default_factory=list)   # 3
    matrix: RegardsMatrix | None = None          # an older deck's slide 6
    tensions: RegardsTensions | None = None      # slide 6 of a revision-2 deck
    arbitrage: RegardsArbitrage | None = None    # slide 7 of a revision-2 deck


class TroisRegardsDocument(BaseModel):
    """Output of the extractor: the full analysis + the carousel presentation layer."""
    analysis: "ArticleFullAnalysis"  # noqa: F821  (resolved at runtime)
    presentation: TroisRegardsPresentation


from models.full_analysis import ArticleFullAnalysis  # noqa: E402
TroisRegardsDocument.model_rebuild()
