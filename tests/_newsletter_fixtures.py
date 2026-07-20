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
        reflexes=["Réflexe 1", "Réflexe 2", "Réflexe 3", "Réflexe 4"],
        decryptage=[
            DecryptageItem(kind="faille", quote="Q1", presentation="", reading="Lecture 1."),
            DecryptageItem(kind="faille", quote="Q2", presentation="", reading="Mécanisme.", clue="une seule source ?"),
            DecryptageItem(kind="faille", quote="Q3", presentation="", reading="Lecture 2."),
            DecryptageItem(kind="faille", quote="Q4", presentation="", reading="Mécanisme 2.", clue="le mot est-il neutre ?"),
            DecryptageItem(kind="faille", quote="Q5", presentation="", reading="Lecture 3.", clue="quelle base ?"),
        ],
        exercices=[{"quote": "un chiffre spectaculaire", "prompt": "Repérez ce qui manque.",
                    "answer": "La base de départ."}],
        architecture={"keystone": "Sur quoi tient la thèse ?",
                      "spine": ["Maillon 1.", "Maillon 2.", "Maillon 3."]},
        a_emporter={"key_takeaways": ["À retenir 1.", "À retenir 2.", "À retenir 3.", "À retenir 4."],
                    "reflexes_critiques": [
                        {"name": "Le réflexe de la base", "rule": "De combien à combien ?", "reusable_on": "santé, économie"},
                        {"name": "Le réflexe de la source", "rule": "Qui a produit ce chiffre ?", "reusable_on": None},
                        {"name": "Le réflexe global → local", "rule": "Un tout n'est pas un cas.", "reusable_on": "climat"}]},
        verdict={"enjeux": ["Enjeu 1.", "Enjeu 2."],
                 "objections": ["Objection 1."],
                 "angles_morts": ["Angle 1", "Angle 2"],
                 "nuances": ["Nuance 1", "Nuance 2"],
                 "questions": ["Et si on posait la question autrement ?"]},
        cui_bono="À qui profite ce cadrage.",
        go_further=[{"title": "R1", "source": "S1", "why": "Pourquoi.", "type": "étude", "url": "https://ademe.fr"},
                    {"title": "R2", "source": "S2", "why": "Pourquoi.", "type": "rapport"},
                    {"title": "R3", "source": "S3", "why": "Pourquoi.", "type": "livre"},
                    {"title": "R4", "source": "S4", "why": "Pourquoi.", "type": "données"}],
        signoff="À bientôt.",
    )
    return NewsletterDocument(analysis=full, presentation=pres)
