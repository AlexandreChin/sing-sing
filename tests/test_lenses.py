from agent.lenses import CANONICAL_LENSES, LENS_IDS


def test_canon_has_eight_lenses_with_unique_ids():
    # 8 since « Fait ou opinion » (opinion_fait) joined the canon.
    assert len(CANONICAL_LENSES) == 8
    assert "opinion_fait" in CANONICAL_LENSES
    assert set(CANONICAL_LENSES) == LENS_IDS
    assert "chiffres" in CANONICAL_LENSES
    assert "causalite" in CANONICAL_LENSES
    assert "cadrage" in CANONICAL_LENSES


def test_each_lens_has_nonempty_name_and_question():
    for lid, lens in CANONICAL_LENSES.items():
        assert lid == lid.lower() and " " not in lid
        assert lens["name"].strip()
        assert lens["question"].strip().endswith("?")
