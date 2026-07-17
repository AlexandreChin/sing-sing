from agent.lenses import CANONICAL_LENSES, LENS_IDS


def test_canon_has_seven_lenses_with_unique_ids():
    assert len(CANONICAL_LENSES) == 7
    assert set(CANONICAL_LENSES) == LENS_IDS
    assert "chiffres" in CANONICAL_LENSES
    assert "causalite" in CANONICAL_LENSES
    assert "cadrage" in CANONICAL_LENSES


def test_each_lens_has_nonempty_name_and_question():
    for lid, lens in CANONICAL_LENSES.items():
        assert lid == lid.lower() and " " not in lid
        assert lens["name"].strip()
        assert lens["question"].strip().endswith("?")
