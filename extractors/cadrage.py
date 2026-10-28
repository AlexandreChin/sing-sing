"""Extractor for the CADRAGE & LOGIQUE carousel: the six slides use every field the
adapt agent wrote, so the presentation passes through with the full analysis."""
from __future__ import annotations

from models.cadrage_presentation import CadrageDocument, CadragePresentation
from models.full_analysis import ArticleFullAnalysis


def extract(full: ArticleFullAnalysis, presentation: CadragePresentation, connected: bool = False) -> CadrageDocument:
    return CadrageDocument(analysis=full, presentation=presentation)
