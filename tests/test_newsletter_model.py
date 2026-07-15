import pytest
from pydantic import ValidationError
from models.newsletter_presentation import NewsletterPresentation, DecryptageItem


def _base_kwargs(**overrides):
    kwargs = dict(
        subject="Objet", preheader="Aperçu", intro="Intro.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["R1", "R2"],
        decryptage=[
            DecryptageItem(kind="fait", quote="Q1", presentation="fait", reading="L1."),
            DecryptageItem(kind="faille", quote="Q2", presentation="Source unique", reading="M.", clue="une seule source ?"),
            DecryptageItem(kind="fait", quote="Q3", presentation="attribué", reading="L2."),
            DecryptageItem(kind="faille", quote="Q4", presentation="Glissement", reading="M2.", clue="mot neutre ?"),
        ],
        strengths=[{"heading": "Force", "body": "Corps."}],
        angles_morts=["A1", "A2"],
        verdict_line="Verdict.",
        go_further=[{"title": "R1", "source": "S1", "why": "W.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "W.", "type": "rapport"}],
        prolongements=[{"heading": "Prolongement", "body": "Corps."}],
        open_question="Question ouverte ?",
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


def test_decryptage_kind_is_constrained():
    with pytest.raises(ValidationError):
        DecryptageItem(kind="autre", quote="Q", presentation="p", reading="r")
