"""Extractor for the Instagram carousel format.

Keeps the full analysis intact and passes the adapt presentation through
(trimming only go_further). Reuses the adapt agent's presentation — no extra
LLM call. The candidate pool of reading beats / takeaways is preserved for
manual cherry-picking; the renderer selects and derives from it.
"""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselDocument, InstagramCarouselPresentation

CAPS = {"go_further": 1}


def extract(full: ArticleFullAnalysis, presentation: InstagramCarouselPresentation, connected: bool = False) -> InstagramCarouselDocument:
    """Return an InstagramCarouselDocument for the carousel formats.

    The full candidate pool of `reading_beats` is passed through untouched so it
    can be cherry-picked manually in extract.json; the renderer shows the
    `selected` beats and derives the réflexe lenses from them (via the canonical
    vocabulary). Only go_further is capped.
    """
    trimmed_presentation = presentation.model_copy(update={
        "go_further": presentation.go_further[: CAPS["go_further"]],
    })
    return InstagramCarouselDocument(analysis=full, presentation=trimmed_presentation)
