import pytest
from pydantic import ValidationError
from models.newsletter_presentation import NewsletterPresentation, DecryptageItem, AVousDeJuger


def _base_kwargs(**overrides):
    kwargs = dict(
        subject="Objet", preheader="Aperçu", intro="Intro.",
        selection_headline="Un cas d'école.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["R1", "R2", "R3", "R4"],
        decryptage=[
            DecryptageItem(kind="fait", quote="Q1", presentation="fait", reading="L1."),
            DecryptageItem(kind="faille", quote="Q2", presentation="Source unique", reading="M.", clue="une seule source ?"),
            DecryptageItem(kind="fait", quote="Q3", presentation="attribué", reading="L2."),
            DecryptageItem(kind="faille", quote="Q4", presentation="Glissement", reading="M2.", clue="mot neutre ?"),
        ],
        exercices=[{"quote": "un chiffre", "prompt": "Repérez.", "answer": "La base."}],
        architecture={"keystone": "Sur quoi tient la thèse ?", "spine": ["A.", "B.", "C."]},
        a_emporter={"key_takeaways": ["T1.", "T2.", "T3.", "T4."],
                    "reflexes_critiques": [
                        {"name": "Le réflexe A", "rule": "Règle A.", "reusable_on": "santé"},
                        {"name": "Le réflexe B", "rule": "Règle B."},
                        {"name": "Le réflexe C", "rule": "Règle C."}]},
        verdict={"enjeux": ["Enjeu 1.", "Enjeu 2."],
                 "objections": ["Objection 1."],
                 "angles_morts": ["A1", "A2"],
                 "questions": ["Question ouverte ?"]},
        cui_bono="Cui bono.",
        go_further=[{"title": "R1", "source": "S1", "why": "W.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "W.", "type": "rapport"},
                    {"title": "R3", "source": "S3", "why": "W.", "type": "livre"},
                    {"title": "R4", "source": "S4", "why": "W.", "type": "données"}],
        share_line="Transférez.",
        reply_prompt="Répondez.",
        signoff="Bye.",
    )
    kwargs.update(overrides)
    return kwargs


def test_presentation_accepts_decryptage_list():
    pres = NewsletterPresentation(**_base_kwargs())
    assert [d.kind for d in pres.decryptage] == ["fait", "faille", "fait", "faille"]
    assert pres.decryptage[1].clue == "une seule source ?"


def test_fact_check_and_failles_fields_removed():
    assert "fact_check" not in NewsletterPresentation.model_fields
    assert "failles" not in NewsletterPresentation.model_fields
    assert "decryptage" in NewsletterPresentation.model_fields


def test_strengths_field_removed():
    # "Ce qui tient" was derived from the quality-eval `review.dimensions` — the
    # newsletter no longer grades the article, so the field is gone.
    assert "strengths" not in NewsletterPresentation.model_fields


def test_arc_fields_present_and_leftovers_removed():
    fields = NewsletterPresentation.model_fields
    # new arc blocks
    for f in ("selection_headline", "architecture", "a_emporter", "verdict", "cui_bono"):
        assert f in fields
    # leftover fields that no longer map to a section are gone
    for f in ("wrap_up", "prolongements", "open_question", "angles_morts"):
        assert f not in fields


def test_decryptage_kind_is_constrained():
    with pytest.raises(ValidationError):
        DecryptageItem(kind="autre", quote="Q", presentation="p", reading="r")


def test_verdict_uses_lists_and_drops_tient_fragile():
    fields = AVousDeJuger.model_fields
    assert set(("enjeux", "objections", "angles_morts", "questions")) <= set(fields)
    for gone in ("enjeu", "objection", "tient_fragile", "la_question"):
        assert gone not in fields
