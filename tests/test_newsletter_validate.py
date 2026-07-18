from agent.newsletter_adapt_agent import _validate


def _valid_data():
    return dict(
        subject="Objet", preheader="Aperçu", intro="Intro.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["R1", "R2"],
        decryptage=[
            {"kind": "fait", "quote": "Q1", "presentation": "fait", "reading": "L1."},
            {"kind": "faille", "quote": "Q2", "presentation": "Source unique", "reading": "M.", "clue": "une source ?"},
            {"kind": "fait", "quote": "Q3", "presentation": "attribué", "reading": "L2."},
            {"kind": "faille", "quote": "Q4", "presentation": "Glissement", "reading": "M2.", "clue": "mot neutre ?"},
        ],
        strengths=[{"heading": "Force", "body": "Corps."}],
        angles_morts=["A1", "A2"],
        wrap_up="Synthèse.",
        go_further=[{"title": "R1", "source": "S1", "why": "W.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "W.", "type": "rapport"}],
        prolongements=[{"heading": "Prolongement 1", "body": "Corps 1."},
                       {"heading": "Prolongement 2", "body": "Corps 2."}],
        open_question="Question ouverte ?",
        signoff="Bye.",
    )


def test_valid_passes():
    assert _validate(_valid_data()) == []


def test_too_few_decryptage_fails():
    d = _valid_data()
    d["decryptage"] = d["decryptage"][:3]  # only 1 faille left → both count + faille-min fail
    assert any("decryptage" in e for e in _validate(d))


def test_faille_without_clue_fails():
    d = _valid_data()
    d["decryptage"][1].pop("clue")
    assert any("clue" in e for e in _validate(d))


def test_needs_at_least_two_of_each_kind():
    d = _valid_data()
    d["decryptage"][3]["kind"] = "fait"  # 3 faits, 1 faille
    assert any("faille" in e for e in _validate(d))
