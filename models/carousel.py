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
    article_type: Literal[
        "editorial", "news_report", "opinion", "investigation", "interview", "other"
    ] | None = None


class Hook(BaseModel):
    headline: str
    context_line: str
    why_read: str
    pull_quote: str | None = None


class TermDefinition(BaseModel):
    term: str
    definition: str


class BeforeYouRead(BaseModel):
    contexts: list[str]
    who_is_speaking: list[str]
    important_facts: list[str]
    key_terms: list[TermDefinition]
    watch_out: list[str]
    questions: list[str]


class GlobalAnalysisItem(BaseModel):
    aspect: str
    summary: str


class EmotionalRegister(BaseModel):
    emotion: str
    how: str
    effect: str


class CuiBono(BaseModel):
    beneficiary: str
    explanation: str


class ExternalSource(BaseModel):
    name: str
    supports: Literal["validates", "contradicts", "neutral"]
    evidence_type: Literal[
        "official_data", "testimony", "academic", "media", "party_statement"
    ]
    url: HttpUrl | None = None
    reading_time_minutes: int | None = None
    why_read: str | None = None      # 1 sentence: what this source adds


class ClaimOrSourceAnnotation(BaseModel):
    quote: str
    presentation: Literal["presented_as_established_fact", "attributed_to_source"]
    explanation: str
    proves: str                      # aspect label of the global_analysis item this anchors
    external_sources: list[ExternalSource]
    confidence: int | None           # null=unverifiable, 0-20 false, 20-40 opinion as fact,
                                     # 40-60 disputed, 60-80 likely true, 80-90 true, 90+ consensual
    confidence_label: str


class BiasOrRhetoricalAnnotation(BaseModel):
    quote: str
    label: str
    effect: str
    proves: str                      # aspect/emotion/beneficiary of the global item this anchors


class QuoteDeepDive(BaseModel):
    quote: str
    analysis: str
    proves: str                      # aspect of the global item this anchors


class LocalAnnotationsSlide(BaseModel):
    claims_and_sources: list[ClaimOrSourceAnnotation]
    biases_and_rhetoric: list[BiasOrRhetoricalAnnotation]
    quote_deep_dive: QuoteDeepDive


class GoFurtherItem(BaseModel):
    title: str
    source: str
    media_type: Literal[
        "article", "report", "book", "documentary", "film", "video", "podcast", "academic_paper", "other"
    ]
    category: Literal["deep_dive", "question_answer"]
    url: HttpUrl | None = None
    duration_minutes: int | None = None   # reading/watching/listening time
    why_explore: str                      # 1 sentence: what this adds and why it's worth the time
    answers_question: str | None = None   # verbatim question from post_reading_questions it helps answer


class Synthesis(BaseModel):
    points: list[str]                # exactly 3


class PostReadingQuestion(BaseModel):
    question: str
    type: Literal["article_quality", "topic_substance", "reader_bias", "blind_spot"]


class GlobalAnalysis(BaseModel):
    observations: list[GlobalAnalysisItem]
    emotional_register: list[EmotionalRegister]
    cui_bono: list[CuiBono]


class CarouselOutput(BaseModel):
    article_metadata: ArticleMetadata
    hook: Hook
    before_you_read: BeforeYouRead
    global_analysis: GlobalAnalysis
    local_annotations: LocalAnnotationsSlide
    synthesis: Synthesis
    go_further: list[GoFurtherItem]
    post_reading_questions: list[PostReadingQuestion]
