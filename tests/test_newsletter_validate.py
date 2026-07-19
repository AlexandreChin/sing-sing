from agent.newsletter_adapt_agent import _validate


def _valid_data():
    return dict(
        subject="Objet", preheader="Aperçu", intro="Intro.",
        selection_headline="Un cas d'école.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["R1", "R2", "R3", "R4"],
        decryptage=[
            {"kind": "faille", "quote": "Q1", "presentation": "", "reading": "L1."},
            {"kind": "faille", "quote": "Q2", "presentation": "", "reading": "M.", "clue": "une source ?"},
            {"kind": "faille", "quote": "Q3", "presentation": "", "reading": "L2."},
            {"kind": "faille", "quote": "Q4", "presentation": "", "reading": "M2.", "clue": "mot neutre ?"},
        ],
        architecture={"keystone": "Sur quoi tient la thèse ?", "spine": ["A.", "B.", "C."]},
        a_emporter={"key_takeaways": ["T1.", "T2.", "T3."], "reflexes_critiques": ["RC1.", "RC2.", "RC3."]},
        verdict={"enjeux": ["Enjeu 1.", "Enjeu 2."],
                 "objections": ["Objection 1."],
                 "angles_morts": ["A1", "A2"],
                 "questions": ["Question ouverte ?"]},
        cui_bono="Cui bono.",
        go_further=[{"title": "R1", "source": "S1", "why": "W.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "W.", "type": "rapport"},
                    {"title": "R3", "source": "S3", "why": "W.", "type": "livre"}],
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


def test_reflexes_out_of_range_fails():
    d = _valid_data()
    d["reflexes"] = ["only one"]
    assert any("reflexes" in e for e in _validate(d))


def test_spine_out_of_range_fails():
    d = _valid_data()
    d["architecture"]["spine"] = ["only one"]
    assert any("spine" in e for e in _validate(d))


def test_key_takeaways_out_of_range_fails():
    d = _valid_data()
    d["a_emporter"]["key_takeaways"] = ["one"]
    assert any("key_takeaways" in e for e in _validate(d))


def test_verdict_angles_morts_out_of_range_fails():
    d = _valid_data()
    d["verdict"]["angles_morts"] = ["one"]
    assert any("angles_morts" in e for e in _validate(d))


def test_enjeux_out_of_range_fails():
    d = _valid_data()
    d["verdict"]["enjeux"] = []
    assert any("enjeux" in e for e in _validate(d))


def test_questions_out_of_range_fails():
    d = _valid_data()
    d["verdict"]["questions"] = ["q1", "q2", "q3"]
    assert any("questions" in e for e in _validate(d))


def test_empty_cui_bono_fails():
    d = _valid_data()
    d["cui_bono"] = "  "
    assert any("cui_bono" in e for e in _validate(d))
