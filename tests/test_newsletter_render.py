from renderer.newsletter.renderer import _decryptage_ctx
from tests._newsletter_fixtures import sample_doc


def test_decryptage_ctx_preserves_order_and_kinds():
    items = _decryptage_ctx(sample_doc())
    assert [i["kind"] for i in items] == ["fait", "faille", "fait", "faille"]


def test_fait_carries_verdict_faille_carries_clue():
    items = _decryptage_ctx(sample_doc())
    faits = [i for i in items if i["kind"] == "fait"]
    failles = [i for i in items if i["kind"] == "faille"]
    assert faits and all("verdict" in i and "color" in i for i in faits)
    assert failles and all(i.get("clue") for i in failles)
    assert all("verdict" not in i for i in failles)
