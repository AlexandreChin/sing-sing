"""Extractor for the 6-slide short Instagram carousel format.

Keeps the full analysis intact (all six review dimensions, so each slide can
select what it needs — the gauges pick the most decisive, the balanced analysis
picks top/bottom) and trims only go_further. Reuses the enrich agent's
presentation — no extra LLM call.
"""
from __future__ import annotations

from agent.lenses import CANONICAL_LENSES
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselDocument, InstagramCarouselPresentation

CAPS = {"go_further": 1}


def extract(full: ArticleFullAnalysis, presentation: InstagramCarouselPresentation, connected: bool = False) -> InstagramCarouselDocument:
    """Return an InstagramCarouselDocument for the 6-slide short carousel."""
    display = presentation.display
    selected_ids = {lens.id for lens in display.lenses}
    kept_beats = [b for b in display.reading_beats if b.lens_ref in selected_ids]
    normalized_lenses = [
        lens.model_copy(update={
            "name": CANONICAL_LENSES[lens.id]["name"],
            "question": CANONICAL_LENSES[lens.id]["question"],
        })
        for lens in display.lenses if lens.id in CANONICAL_LENSES
    ]
    trimmed_presentation = presentation.model_copy(update={
        "go_further": presentation.go_further[: CAPS["go_further"]],
        "display": display.model_copy(update={"reading_beats": kept_beats, "lenses": normalized_lenses}),
    })
    return InstagramCarouselDocument(analysis=full, presentation=trimmed_presentation)
