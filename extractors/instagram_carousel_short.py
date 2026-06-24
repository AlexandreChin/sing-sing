"""Extractor for the 6-slide short Instagram carousel format.

Keeps only what the 6 visual slides render: hook + metadata, the evaluation
gauges (reading recommendation, deontology, the 3 most-decisive review
dimensions), and the reading-companion text (pre_reading, watch_out, distill,
blind_spots, balance). Reuses the enrich agent's presentation — no extra LLM call.
"""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselDocument, InstagramCarouselPresentation

CAPS = {"dimensions": 3, "go_further": 1}


def _select_decisive(dims, k: int) -> list[int]:
    """Indices (in declared order) of the k most decisive dimensions: always the
    highest- and lowest-scoring, then by distance from neutral (3). Stable tie-break."""
    n = len(dims)
    if n <= k:
        return list(range(n))
    by_score = sorted(range(n), key=lambda i: (dims[i].score, i))
    chosen = {by_score[0], by_score[-1]}
    for i in sorted(range(n), key=lambda i: (-abs(dims[i].score - 3), i)):
        if len(chosen) >= k:
            break
        chosen.add(i)
    return sorted(chosen)


def extract(full: ArticleFullAnalysis, presentation: InstagramCarouselPresentation, connected: bool = False) -> InstagramCarouselDocument:
    """Return a trimmed InstagramCarouselDocument for the 6-slide short carousel."""
    trimmed_full = full
    if full.review and full.review.dimensions:
        keep = _select_decisive(full.review.dimensions, CAPS["dimensions"])
        sel_dims = [full.review.dimensions[i] for i in keep]
        trimmed_full = full.model_copy(update={
            "review": full.review.model_copy(update={"dimensions": sel_dims}),
        })

    trimmed_presentation = presentation.model_copy(update={
        "go_further": presentation.go_further[: CAPS["go_further"]],
    })

    return InstagramCarouselDocument(analysis=trimmed_full, presentation=trimmed_presentation)
