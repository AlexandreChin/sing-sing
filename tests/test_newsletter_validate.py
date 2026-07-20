from agent.newsletter_adapt_agent import _validate


def _valid_data():
    return dict(
        subject="Objet", preheader="Aperçu",
        essentiel="L'article avance sa thèse et conclut.",
        selection_headline="Un cas d'école.",
        why_selected="Pourquoi.", payoff="Gain.",
        context="Contexte.",
        reading_posture="Cadrage moral et chiffres-chocs.",
        decryptage=[
            {"kind": "faille", "quote": "Q1", "presentation": "", "reading": "L1.", "prompt": "Repérez.", "lens_ref": "cadrage"},
            {"kind": "faille", "quote": "Q2", "presentation": "", "reading": "M.", "prompt": "Cherchez la source.", "lens_ref": "sources"},
            {"kind": "faille", "quote": "Q3", "presentation": "", "reading": "L2.", "prompt": "Quelle base ?", "lens_ref": "chiffres"},
            {"kind": "faille", "quote": "Q4", "presentation": "", "reading": "M2.", "prompt": "Le mot est-il neutre ?", "lens_ref": "cadrage"},
            {"kind": "faille", "quote": "Q5", "presentation": "", "reading": "L3.", "prompt": "Quelle base ?", "lens_ref": "chiffres"},
        ],
        architecture={"keystone": "Sur quoi tient la thèse ?", "spine": ["A.", "B.", "C."]},
        a_emporter={"key_takeaways": ["T1.", "T2.", "T3.", "T4."],
                    "reflexes_critiques": [
                        {"lens_ref": "chiffres", "rule": "Règle A.", "reusable_on": "santé"},
                        {"lens_ref": "sources", "rule": "Règle B."},
                        {"lens_ref": "causalite", "rule": "Règle C."}]},
        verdict={"enjeux": ["Enjeu 1.", "Enjeu 2."],
                 "objections": ["Objection 1."],
                 "angles_morts": ["Omission 1", "Omission 2"],
                 "nuances": ["Nuance 1", "Nuance 2"],
                 "questions": ["Question ouverte ?"]},
        cui_bono="Cui bono.",
        go_further=[{"title": "R1", "source": "S1", "why": "W.", "type": "étude", "url": "https://ademe.fr"},
                    {"title": "R2", "source": "S2", "why": "W.", "type": "rapport"},
                    {"title": "R3", "source": "S3", "why": "W.", "type": "livre"},
                    {"title": "R4", "source": "S4", "why": "W.", "type": "données"}],
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


def test_missing_prompt_fails():
    # each beat is a quote → prompt → answer; the prompt (instruction) is required.
    d = _valid_data()
    d["decryptage"][1].pop("prompt")
    assert any("decryptage" in e for e in _validate(d))


def test_empty_reading_posture_fails():
    d = _valid_data()
    d["reading_posture"] = "  "
    assert any("reading_posture" in e for e in _validate(d))


def test_beat_bad_lens_ref_fails():
    d = _valid_data()
    d["decryptage"][0]["lens_ref"] = "pas_une_lentille"
    assert any("lens_ref" in e for e in _validate(d))


def test_reflexe_critique_bad_lens_ref_fails():
    d = _valid_data()
    d["a_emporter"]["reflexes_critiques"][0]["lens_ref"] = "bidon"
    assert any("lens_ref" in e for e in _validate(d))


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


def test_verdict_nuances_out_of_range_fails():
    d = _valid_data()
    d["verdict"]["nuances"] = ["one"]
    assert any("nuances" in e for e in _validate(d))


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


def test_reflexe_critique_needs_rule():
    d = _valid_data()
    d["a_emporter"]["reflexes_critiques"][0]["rule"] = "  "
    assert any("reflexes_critiques" in e for e in _validate(d))


def test_go_further_out_of_range_fails():
    d = _valid_data()
    d["go_further"] = d["go_further"][:2]
    assert any("go_further" in e for e in _validate(d))
