from agent.newsletter_adapt_agent import _validate


def _valid_data():
    return dict(
        subject="Objet", preheader="Aperçu", intro="Intro.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["R1", "R2"],
        decryptage=[
            {"kind": "faille", "quote": "Q1", "presentation": "", "reading": "L1."},
            {"kind": "faille", "quote": "Q2", "presentation": "", "reading": "M.", "clue": "une source ?"},
            {"kind": "faille", "quote": "Q3", "presentation": "", "reading": "L2."},
            {"kind": "faille", "quote": "Q4", "presentation": "", "reading": "M2.", "clue": "mot neutre ?"},
        ],
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
    d["decryptage"] = d["decryptage"][:3]
    assert any("decryptage" in e for e in _validate(d))


def test_too_many_decryptage_fails():
    d = _valid_data()
    d["decryptage"] = d["decryptage"] + [dict(d["decryptage"][0])] * 3  # 7 items
    assert any("decryptage" in e for e in _validate(d))


def test_empty_quote_fails():
    d = _valid_data()
    d["decryptage"][1]["quote"] = "  "
    assert any("decryptage" in e for e in _validate(d))


def test_empty_reading_fails():
    d = _valid_data()
    d["decryptage"][1]["reading"] = ""
    assert any("decryptage" in e for e in _validate(d))


def test_missing_clue_does_not_fail():
    # clue is no longer required per-item now that the faits/failles quota is gone.
    d = _valid_data()
    d["decryptage"][1].pop("clue")
    assert _validate(d) == []
