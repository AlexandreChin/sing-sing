"""Intermediate Pydantic models for the multi-step full analysis pipeline."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel
from models.full_analysis import (
    AnalysisFond, AnalyseForme, AuthorityAnchor, BiasesAndFocus,
    Blend, Context, Deontology, Distill, FactsVsOpinions,
    ReadingGuide, Review,
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
    authority_anchors: list[AuthorityAnchor]
    notable_omissions: list[str]
    rhetorical_patterns: list[str]
    context: Context  # extracted in step 1, seeds later steps


class ProbeOutput(BaseModel):
    facts_vs_opinions: FactsVsOpinions
    biases_and_focus: BiasesAndFocus


class EthicsOutput(BaseModel):
    deontology: Deontology


class ReviewOutput(BaseModel):
    review: Review


class BlendOutput(BaseModel):
    blend: Blend


class DistillOutput(BaseModel):
    distill: Distill


class GuideOutput(BaseModel):
    guide: ReadingGuide
