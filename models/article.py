from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, HttpUrl


class Entity(BaseModel):
    name: str
    type: Literal["person", "organization", "location", "other"]


class Claim(BaseModel):
    text: str
    supported: bool | None = None  # None = unverified


class Article(BaseModel):
    url: HttpUrl
    title: str
    body: str
    source: str | None = None
    published_at: str | None = None


class ArticleAnalysis(BaseModel):
    summary: str
    sentiment: Literal["positive", "negative", "neutral", "mixed"]
    entities: list[Entity]
    key_claims: list[Claim]
    topics: list[str]
    tags: list[str]
    language: str  # ISO 639-1 code, e.g. "en", "fr"
    credibility_notes: str | None = None
    region: str | None = None  # geographic focus, e.g. "Middle East", "EU"
    reading_time_minutes: int | None = None
