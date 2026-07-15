import json
from pathlib import Path

from models.full_analysis import ArticleFullAnalysis
from models.newsletter_presentation import (
    NewsletterPresentation, NewsletterDocument, DecryptageItem,
)

_ANALYSIS = Path(__file__).resolve().parent.parent / "samples/outputs/article_1/analysis.json"


def sample_doc() -> NewsletterDocument:
    """A NewsletterDocument built from a real sample analysis + a hand-authored
    presentation on the new schema (no API)."""
    full = ArticleFullAnalysis.model_validate(json.loads(_ANALYSIS.read_text(encoding="utf-8")))
    pres = NewsletterPresentation(
        subject="Objet test", preheader="Aperçu test", intro="Intro.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["Réflexe 1", "Réflexe 2"],
        decryptage=[
            DecryptageItem(kind="fait", quote="Q1", presentation="présenté comme un fait", reading="Lecture 1."),
            DecryptageItem(kind="faille", quote="Q2", presentation="Source unique", reading="Mécanisme.", clue="une seule source ?"),
            DecryptageItem(kind="fait", quote="Q3", presentation="attribué à une source", reading="Lecture 2."),
            DecryptageItem(kind="faille", quote="Q4", presentation="Glissement sémantique", reading="Mécanisme 2.", clue="le mot est-il neutre ?"),
        ],
        strengths=[{"heading": "Une force", "body": "Corps."}],
        angles_morts=["Angle 1", "Angle 2"],
        verdict_line="Verdict.",
        go_further=[{"title": "R1", "source": "S1", "why": "Pourquoi.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "Pourquoi.", "type": "rapport"}],
        prolongements=[{"heading": "Prolongement", "body": "Corps."}],
        open_question="Et si la question était mal posée ?",
        signoff="À bientôt.",
    )
    return NewsletterDocument(analysis=full, presentation=pres)
