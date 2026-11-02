"""Extractor for the ANATOMIE D'UN CHIFFRE carousel: the six slides use every field the
adapt agent wrote, so the presentation passes through with the full analysis."""
from __future__ import annotations

from models.anatomie_chiffre_presentation import AnatomieChiffreDocument, AnatomieChiffrePresentation
from models.full_analysis import ArticleFullAnalysis


def extract(full: ArticleFullAnalysis, presentation: AnatomieChiffrePresentation, connected: bool = False) -> AnatomieChiffreDocument:
    return AnatomieChiffreDocument(analysis=full, presentation=presentation)
