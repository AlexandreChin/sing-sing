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
    promise: str  # slide 1 — the question the deck tests, ≤100 characters, in plain words (« La force en manifestation est-elle nouvelle ? »); the template adds the second paragraph
    tagline: str = ""  # slide 1 — the second paragraph, one line, key words in gold `**…**`; empty = the archetype's default


class TempsLongRepere(BaseModel):
    """One dated reference point of a timeline: an episode people remember, or a turning point of the rules."""
    date: str          # « 2018–2019 », « 1986 »
    label: str
    remark: str = ""   # what the point lets the reader check in the slide's lead — one line
    tags: list[str] = Field(default_factory=list)   # the tests of the lecture slide this point illustrates (« cible », « proportion », « effet »): drawn as chips under the remark


class TempsLongFrise(BaseModel):  # slides 2 and 3 — a timeline of dated reference points
    title: str
    lead: str
    reperes: list[TempsLongRepere] = Field(default_factory=list)   # 3 to 5, oldest first
    layout: Literal["liste", "annees", "axe"] = "liste"   # liste: dates on the left; annees: large years; axe: centred spine, texts alternating, gaps written on it
    key: str = ""   # one or two lines under the rows: what the pills mean (every pill is gold, whichever camp's criterion it is); empty = none


class TempsLongReading(BaseModel):
    """One card of the lecture slide. An older deck names it by `kind` (rupture / continuite / cycle); a newer one
    writes its own `label` (≤10 characters: « Cible », « Proportion », « 2016→2019 »…) and may pick its `icon`."""
    kind: str = ""   # rupture / continuite / cycle, or any older key: the label and the icon of the old three readings
    label: str = ""  # the card's name, before its question; empty = the label of `kind`
    icon: str = ""   # the pictogram's key; empty = the one of `kind`
    signature: str   # the question the card asks (≤40 characters, ends with « ? »)
    indicator: str   # the card's text, with one **bold** passage (beside an aside: the left outcome of its row)
    other: str = ""  # beside an aside: the right outcome of the row
    where: str = ""       # where to find the series: an organisation, never a URL


class TempsLongAsideCard(BaseModel):
    """One of the second voice's signs: a short name (also the pill that tags the timelines), its icon and, beside it, the
    explicit phrase."""
    label: str         # the short name, ≤10 characters (« Presse »)
    text: str = ""     # the explicit phrase, as the media words it (« attaquer la presse »)
    icon: str = ""     # the pictogram's key; empty = the generic one


class TempsLongLecture(BaseModel):  # slide 4 — rupture, continuité or cycle?
    title: str
    lead: str         # the procedure and the measure: « Pour trancher : comparer … d'un épisode à l'autre »
    readings: list[TempsLongReading] = Field(default_factory=list)   # 3, in this order
    question: str     # the neutral closing question: not drawn on the slide, taken up by the sign-off and the caption
    where: str = ""   # one line under the lead: where to find the series the three readings are tested on (an organisation, never a URL); empty = each card carries its own
    where_label: str = ""   # the bold label of that line; empty = « Où regarder »
    kicker: str = ""        # the label above the title; empty = « La lecture du temps »
    # The move `seuil`: the cards are the rows of a decision table whose two columns are named in `heads` (the title's two words),
    # and a second voice's own signs follow under `aside_heading` as small cards (`aside_cards`, up to 7). Empty `aside_cards` =
    # the cards alone, full width.
    heads: list[str] = Field(default_factory=list)
    aside_heading: str = ""
    aside_cards: list["TempsLongAsideCard"] = Field(default_factory=list)
    author: str = ""  # one line under the cards: which of the readings the author's own thesis combines — attributed, never judged


class TempsLongPiege(BaseModel):
    title: str
    question: str     # the question a reader can ask


class TempsLongPieges(BaseModel):  # slide 5 — the traps a time series sets
    title: str        # the headline: « Quatre points à vérifier avant de choisir »
    lead: str = ""    # an older deck's sub-line — no longer drawn
    pieges: list[TempsLongPiege] = Field(default_factory=list)   # 3


class TempsLongPosition(BaseModel):  # slide 2 — what the author says, in the article's own frame
    title: str    # the claim, up to two lines at 70 px, a key passage in gold (**…**)
    lead: str     # the sentence under it, naming the author (two lines at 34 px)
    ecarte: str   # card 1 — what the author sets aside (the explanation he rejects)
    diagnostic: str   # card 2 — his own reading
    mecanisme: str = ""   # card 3 — why it lasted and why it breaks (an older deck has three cards)
    issue: str    # card 4 — his conclusion
    kicker: str = ""   # the label above the title, specific to the article; empty = « Ce que dit l'auteur »
    # each card's own heading, specific to the article; empty = the default heading of the renderer
    ecarte_label: str = ""
    diagnostic_label: str = ""
    mecanisme_label: str = ""
    issue_label: str = ""


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
    # The slides between the hook and the sign-off, in reading order (« position », « lecture », « episodes », « tournants »,
    # « pieges »); empty = the archetype's own order: position, episodes, tournants, lecture, pieges.
    order: list[str] = Field(default_factory=list)
    move: str = ""   # the axe's move (forme, seuil, séquence, nouveauté, délai, mémoire): the default pictogram of the lecture cards; empty = forme


class TempsLongDocument(BaseModel):
    """Output of the extractor: the full analysis + the carousel presentation layer."""
    analysis: "ArticleFullAnalysis"  # noqa: F821  (resolved at runtime)
    presentation: TempsLongPresentation


from models.full_analysis import ArticleFullAnalysis  # noqa: E402
TempsLongDocument.model_rebuild()
