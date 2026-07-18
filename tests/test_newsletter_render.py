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
        kind="faille", quote="« 27,5 % des enfants »",
        presentation="", reading="Lecture.",
    )
    for html in (generate_markdown(doc), generate_html(doc), generate_email_html(doc, "light")):
        assert "« « " not in html and "«&nbsp;«" not in html


def test_decryptage_ctx_preserves_order_and_shape():
    items = _decryptage_ctx(sample_doc())
    assert [i["quote"] for i in items] == ["Q1", "Q2", "Q3", "Q4"]
    assert all("kind" not in i and "verdict" not in i and "color" not in i for i in items)


def test_decryptage_ctx_carries_quote_reading_clue():
    items = _decryptage_ctx(sample_doc())
    assert all(i.get("quote") and i.get("reading") for i in items)
    assert [bool(i.get("clue")) for i in items] == [False, True, False, True]


def test_markdown_structure_and_order():
    md = generate_markdown(sample_doc())
    assert "Au fil de la lecture" in md
    assert "La vue d'ensemble" in md
    assert "Vérification des faits" not in md
    assert "## Les failles" not in md
    assert md.index("Au fil de la lecture") < md.index("La vue d'ensemble") < md.index("À vous de juger")


def test_rich_html_has_no_grade_badge():
    html = generate_html(sample_doc())
    assert "Au fil de la lecture" in html
    # the fait/faille grade badge is gone — no more badge markup or verdict pill
    assert "⚖️ Fait" not in html
    assert 'class="badge' not in html
    assert "Vérification des faits" not in html


def test_email_both_themes():
    for theme in ("light", "dark"):
        html = generate_email_html(sample_doc(), theme)
        assert "Au fil de la lecture" in html
        assert "La vue d'ensemble" in html
        assert "Vérification des faits" not in html
        assert "Les failles" not in html


def test_category_pill_renders_with_theme_colours():
    doc = sample_doc()
    doc.analysis.article_metadata.category = "Société"
    # rich newsletter uses the dark palette
    assert "Société" in generate_html(doc) and "#c59cf0" in generate_html(doc)
    # email pill re-resolves per theme
    assert "#7a3fc0" in generate_email_html(doc, "light")   # light text colour
    assert "#c59cf0" in generate_email_html(doc, "dark")    # dark text colour


def test_no_pill_for_autre():
    # "Autre" must render exactly like no category at all — pill-less.
    base = sample_doc()
    base.analysis.article_metadata.category = None
    autre = sample_doc()
    autre.analysis.article_metadata.category = "Autre"
    assert generate_html(autre) == generate_html(base)
    assert generate_email_html(autre, "dark") == generate_email_html(base, "dark")
