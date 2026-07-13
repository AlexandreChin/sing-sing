from renderer.newsletter.renderer import (
    _decryptage_ctx, _unwrap_quote, generate_markdown, generate_html, generate_email_html,
)
from models.newsletter_presentation import DecryptageItem
from tests._newsletter_fixtures import sample_doc


def test_quote_stripped_of_surrounding_guillemets():
    # The model often returns the quote already wrapped in « … »; templates wrap it
    # again, so the render layer must unwrap to avoid « « … » ».
    assert _unwrap_quote("« 27,5 % des enfants »") == "27,5 % des enfants"
    assert _unwrap_quote("  «  déjà espacé  »  ") == "déjà espacé"
    assert _unwrap_quote("sans guillemets") == "sans guillemets"


def test_render_does_not_double_wrap_wrapped_quotes():
    doc = sample_doc()
    doc.presentation.decryptage[0] = DecryptageItem(
        kind="fait", quote="« 27,5 % des enfants »",
        presentation="attribué à une source", reading="Lecture.",
    )
    for html in (generate_markdown(doc), generate_html(doc), generate_email_html(doc, "light")):
        assert "« « " not in html and "«&nbsp;«" not in html


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


def test_markdown_structure_and_order():
    md = generate_markdown(sample_doc())
    assert "Le décryptage, pas à pas" in md
    assert "La vue d'ensemble" in md
    assert "Vérification des faits" not in md
    assert "## Les failles" not in md
    assert md.index("Le décryptage") < md.index("La vue d'ensemble") < md.index("Notre verdict")


def test_rich_html_has_badges():
    html = generate_html(sample_doc())
    assert "Le décryptage, pas à pas" in html
    assert "Fait" in html and "Faille" in html
    assert "Vérification des faits" not in html


def test_email_both_themes():
    for theme in ("light", "dark"):
        html = generate_email_html(sample_doc(), theme)
        assert "Le décryptage, pas à pas" in html
        assert "La vue d'ensemble" in html
        assert "Vérification des faits" not in html
        assert "Les failles" not in html
