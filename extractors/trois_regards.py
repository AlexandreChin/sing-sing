"""Extractor for the TROIS REGARDS carousel: every slide uses the fields the adapt agent
wrote, so the presentation passes through with the full analysis."""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from models.trois_regards_presentation import TroisRegardsDocument, TroisRegardsPresentation


def extract(full: ArticleFullAnalysis, presentation: TroisRegardsPresentation, connected: bool = False) -> TroisRegardsDocument:
    return TroisRegardsDocument(analysis=full, presentation=presentation)
