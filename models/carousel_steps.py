"""Intermediate Pydantic models for the multi-step carousel pipeline.

These are internal — they never appear in CarouselOutput.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from models.carousel import GoFurtherItem, Hook, PostReadingQuestion, Synthesis


class ExtractedClaim(BaseModel):
    quote: str
    source: str | None = None
    type: Literal["factual", "attributed", "statistical", "legal", "testimonial"]


class ExtractedActor(BaseModel):
    name: str
    role: str


class ExtractionResult(BaseModel):
    article_type: Literal[
        "editorial", "news_report", "opinion", "investigation", "interview", "other"
    ]
    key_claims: list[ExtractedClaim]
    key_quotes: list[str]
    key_actors: list[ExtractedActor]
    notable_omissions: list[str]
    rhetorical_patterns: list[str]


class HookSynthesisFinale(BaseModel):
    hook: Hook
    synthesis: Synthesis
    post_reading_questions: list[PostReadingQuestion]
    go_further: list[GoFurtherItem]
