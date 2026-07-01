"""Extractor for the 6-slide short Instagram carousel format.

Keeps the full analysis intact (all six review dimensions, so each slide can
select what it needs — the gauges pick the most decisive, the balanced analysis
picks top/bottom) and trims only go_further. Reuses the enrich agent's
presentation — no extra LLM call.
"""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselDocument, InstagramCarouselPresentation

CAPS = {"go_further": 1}


def extract(full: ArticleFullAnalysis, presentation: InstagramCarouselPresentation, connected: bool = False) -> InstagramCarouselDocument:
    """Return an InstagramCarouselDocument for the 6-slide short carousel."""
    trimmed_presentation = presentation.model_copy(update={
        "go_further": presentation.go_further[: CAPS["go_further"]],
    })
    return InstagramCarouselDocument(analysis=full, presentation=trimmed_presentation)
