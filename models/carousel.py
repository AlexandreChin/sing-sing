from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, HttpUrl


class CarouselInput(BaseModel):
    body: str
    title: str | None = None
    url: HttpUrl | None = None
    source: str | None = None
    published_at: str | None = None


class ArticleMetadata(BaseModel):
    url: HttpUrl | None = None
    title: str | None = None
    source: str | None = None
    published_at: str | None = None
    article_type: Literal["editorial", "news_report", "opinion", "investigation", "interview", "other"] | None = None
    reading_time_minutes: int | None = None
    article_title: str | None = None   # original article title extracted from body
    article_chapo: str | None = None   # lead paragraph extracted from body


# Slide 1
class Hook(BaseModel):
    topic: str
    sub_topic: str
    headline: str
    context_line: str


# Slide 2
class Interest(BaseModel):
    why_read: str
    pull_quote: str | None = None
    next_slide_hook: str


# Slide 3
class TitleAnalysisItem(BaseModel):
    label: str        # short label for the rhetorical device or framing technique (1–2 words)
    observation: str  # analytical observation on the title (post-reading)


class Cadrage(BaseModel):
    title_bullets: list[str] = []              # pre-reading watch-out tips on title rhetoric (slide 3)
    title_analysis: list[TitleAnalysisItem] = []  # post-reading analytical observations on title framing (slide 5)
    chapo_bullets: list[str] = []              # 2–3 bullet observations about how the CHAPO frames the reader


# Slide 4
class TermDefinition(BaseModel):
    term: str
    definition: str


class Context(BaseModel):
    contexts: list[str]
    who_is_speaking: list[str]
    important_facts: list[str]
    key_terms: list[TermDefinition]
    next_slide_hook: str


# Slide 5
class WatchOutItem(BaseModel):
    text: str
    refers_to: Literal["fond", "forme", "faits", "biais"]


class WatchOut(BaseModel):
    items: list[WatchOutItem]
    next_slide_hook: str


# Slide 6
class GlobalAnalysisItem(BaseModel):
    aspect: str
    summary: str
    seeds: str


class AnalysisFond(BaseModel):
    main_claim: str
    implicit_assumptions: list[str]
    blind_spots: list[str]
    observations: list[GlobalAnalysisItem]


# Slide 7
class EmotionalRegister(BaseModel):
    emotion: str
    how: str
    effect: str
    seeds: str


class CuiBono(BaseModel):
    beneficiary: str
    explanation: str
    seeds: str


class AnalyseForme(BaseModel):
    emotional_register: list[EmotionalRegister]
    cui_bono: list[CuiBono]
    next_slide_hook: str


# Slide 8
class ExternalSource(BaseModel):
    name: str
    supports: Literal["validates", "contradicts", "neutral"]
    evidence_type: Literal["official_data", "testimony", "academic", "media", "party_statement"]


class ClaimAndSource(BaseModel):
    quote: str
    presentation: Literal["presented_as_established_fact", "attributed_to_source"]
    proves: str
    explanation: str
    external_sources: list[ExternalSource]
    confidence: int | None = None
    confidence_label: Literal["unverifiable", "false", "likely false", "disputed", "likely true", "true", "consensual"]


class FactsVsOpinions(BaseModel):
    claims_and_sources: list[ClaimAndSource]


# Slide 9
class BiasRhetoric(BaseModel):
    quote: str
    item_type: Literal["bias", "fallacy"]
    label: str
    effect: str
    proves: str


class Focus(BaseModel):
    quote: str
    proves: str
    analysis: str


class BiasesAndFocus(BaseModel):
    biases_and_rhetoric: list[BiasRhetoric]
    focus: Focus
    next_slide_hook: str


# Slide 10
class Synthesis(BaseModel):
    points: list[str]  # exactly 3, sorted most important first
    open_question: str  # analytical question from bias analysis (displayed first on slide 8)
    engagement_question: str  # reader engagement CTA (displayed second on slide 8)


# Slide 11
class GoFurtherItem(BaseModel):
    title: str
    source: str
    media_type: Literal["article", "report", "book", "documentary", "film", "video", "podcast", "academic_paper", "other"]
    category: Literal["deep_dive", "question_answer"]
    url: str | None = None
    duration_minutes: int | None = None
    why_explore: str
    answers_question: str | None = None


class GoFurther(BaseModel):
    items: list[GoFurtherItem]


# Slide 12
class PostReadingQuestion(BaseModel):
    question: str
    type: Literal["article_quality", "topic_substance", "reader_bias", "blind_spot"]


class CTA(BaseModel):
    engagement_sentence: str
    post_reading_questions: list[PostReadingQuestion]  # exactly 2


class CarouselOutput(BaseModel):
    article_metadata: ArticleMetadata
    hook: Hook
    interest: Interest
    cadrage: Cadrage
    context: Context
    watch_out: WatchOut
    analysis_fond: AnalysisFond
    analysis_forme: AnalyseForme
    facts_vs_opinions: FactsVsOpinions
    biases_and_focus: BiasesAndFocus
    synthesis: Synthesis
    go_further: GoFurther
    cta: CTA
