"""Intermediate Pydantic models for the multi-step carousel pipeline."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel
from models.carousel import (
    AnalysisFond, AnalyseForme, AuthorityAnchor, BiasesAndFocus, Cadrage,
    Context, CTA, FactsVsOpinions, GoFurther, Hook, Interest, Synthesis, WatchOut, WatchOutItem,
)


class ExtractedClaim(BaseModel):
    quote: str
    source: str | None = None
    type: Literal["factual", "attributed", "statistical", "legal", "testimonial"]


class ExtractedActor(BaseModel):
    name: str
    role: str


class ExtractionResult(BaseModel):
    article_type: Literal["editorial", "news_report", "opinion", "investigation", "interview", "other"]
    key_claims: list[ExtractedClaim]
    key_quotes: list[str]
    key_actors: list[ExtractedActor]
    authority_anchors: list[AuthorityAnchor]  # entities cited to confer credibility on specific claims
    notable_omissions: list[str]
    rhetorical_patterns: list[str]


class Step2Output(BaseModel):
    cadrage: Cadrage
    context: Context
    watch_out: WatchOut


class Step5Output(BaseModel):
    facts_vs_opinions: FactsVsOpinions
    biases_and_focus: BiasesAndFocus


class Step6Output(BaseModel):
    hook: Hook
    interest: Interest
    synthesis: Synthesis
    go_further: GoFurther
    cta: CTA
