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
        selection_headline="Un cas d'école.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["Réflexe 1", "Réflexe 2"],
        decryptage=[
            DecryptageItem(kind="faille", quote="Q1", presentation="", reading="Lecture 1."),
            DecryptageItem(kind="faille", quote="Q2", presentation="", reading="Mécanisme.", clue="une seule source ?"),
            DecryptageItem(kind="faille", quote="Q3", presentation="", reading="Lecture 2."),
            DecryptageItem(kind="faille", quote="Q4", presentation="", reading="Mécanisme 2.", clue="le mot est-il neutre ?"),
        ],
        architecture={"keystone": "Sur quoi tient la thèse ?",
                      "spine": ["Maillon 1.", "Maillon 2.", "Maillon 3."]},
        a_emporter={"key_takeaways": ["À retenir 1.", "À retenir 2."],
                    "reflexes_critiques": ["Réflexe critique 1.", "Réflexe critique 2."]},
        verdict={"enjeu": "Enjeu.", "objection": "Objection.",
                 "tient_fragile": "Ce qui tient, ce qui reste fragile.",
                 "angles_morts": ["Angle 1", "Angle 2"],
                 "la_question": "Et si la question était mal posée ?"},
        cui_bono="À qui profite ce cadrage.",
        go_further=[{"title": "R1", "source": "S1", "why": "Pourquoi.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "Pourquoi.", "type": "rapport"}],
        signoff="À bientôt.",
    )
    return NewsletterDocument(analysis=full, presentation=pres)
