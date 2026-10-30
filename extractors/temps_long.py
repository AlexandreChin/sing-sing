"""Extractor for the TEMPS LONG carousel: the slides use every field the adapt agent
wrote, so the presentation passes through with the full analysis."""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from models.temps_long_presentation import TempsLongDocument, TempsLongPresentation


def extract(full: ArticleFullAnalysis, presentation: TempsLongPresentation, connected: bool = False) -> TempsLongDocument:
    return TempsLongDocument(analysis=full, presentation=presentation)
