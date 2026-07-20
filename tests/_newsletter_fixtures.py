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
        subject="Objet test", preheader="Aperçu test",
        essentiel="L'article avance sa thèse et conclut.",
        selection_headline="Un cas d'école.",
        why_selected="Pourquoi.", payoff="Gain.",
        context="Contexte.",
        reading_posture="L'article convainc par un cadrage moral et des chiffres-chocs.",
        decryptage=[
            DecryptageItem(kind="faille", quote="Q1", presentation="", reading="Lecture 1.", prompt="Repérez le cadrage.", lens_ref="cadrage"),
            DecryptageItem(kind="faille", quote="Q2", presentation="", reading="Mécanisme.", prompt="Cherchez la source.", lens_ref="sources"),
            DecryptageItem(kind="faille", quote="Q3", presentation="", reading="Lecture 2.", prompt="Cherchez la base.", lens_ref="chiffres"),
            DecryptageItem(kind="faille", quote="Q4", presentation="", reading="Mécanisme 2.", prompt="Le mot est-il neutre ?", lens_ref="cadrage"),
            DecryptageItem(kind="faille", quote="Q5", presentation="", reading="Lecture 3.", prompt="Quelle base ?", lens_ref="chiffres"),
        ],
        architecture={"keystone": "Sur quoi tient la thèse ?",
                      "spine": ["Maillon 1.", "Maillon 2.", "Maillon 3."]},
        a_emporter={"key_takeaways": ["À retenir 1.", "À retenir 2.", "À retenir 3.", "À retenir 4."],
                    "reflexes_critiques": [
                        {"lens_ref": "chiffres", "rule": "De combien à combien ?", "reusable_on": "santé, économie"},
                        {"lens_ref": "sources", "rule": "Qui a produit ce chiffre ?", "reusable_on": None},
                        {"lens_ref": "causalite", "rule": "Un tout n'est pas un cas.", "reusable_on": "climat"}]},
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
