from renderer.categories import CATEGORY_ICONS
from renderer.instagram_carousel._shared import _env, medium_labels

TPL = "article_carousel_optimized_v0/01_hook.html"


def _render(**over):
    ctx = dict(
        slide_n=1, slide_total=10, progress=10, logo="", L=medium_labels("article"),
        meta_parts=["Le Monde", "2026", "Tribune", "20 min de lecture"],
        sub_topic="Un **mot** en gras", rubrique="Tech",
        glyph=CATEGORY_ICONS["Tech"], art_svg='<line x1="0" y1="0" x2="10" y2="10"/>',
    )
    ctx.update(over)
    return _env().get_template(TPL).render(**ctx)


def test_hook_renders_layers_rubrique_and_headline():
    html = _render()
    assert '<div class="artbg">' in html
    assert '<div class="giant">' in html
    assert '<div class="rubrique-tab">' in html
    assert "Tech" in html
    assert '<div class="meta-line">' in html and "Le Monde" in html  # metadata line, not the source title
    assert "Titre de l" not in html                # the source's own title lives in the capture
    assert "Sélection" in html                     # label above the image, .kicker like On décrypte
    assert "On décrypte" in html                   # brand-voice kicker under the capture
    assert "<strong>mot</strong>" in html          # md_bold applied
    assert 'class="cat-pill"' not in html          # old pill element no longer rendered
    assert 'x1="0" y1="0" x2="10" y2="10"' in html  # art_svg injected


def test_hook_drops_category_elements_when_absent():
    html = _render(rubrique=None, glyph="")
    assert '<div class="rubrique-tab">' not in html
    assert '<div class="giant">' not in html
    assert '<div class="artbg">' in html            # art still present


def test_giant_layer_neutralizes_filled_glyph_shapes():
    # The Culture glyph uses <circle fill="currentColor">; the .giant layer must
    # force fill:none so it renders as a faint gold outline, not solid near-white dots.
    html = _render(rubrique="Culture", glyph=CATEGORY_ICONS["Culture"])
    assert '<div class="giant">' in html
    assert ".giant svg circle { fill: none" in html


def test_capture_slot_renders_only_with_an_image():
    assert '<div class="shot">' not in _render(thumb="")
    html = _render(thumb="data:image/png;base64,AAA")
    assert '<div class="shot">' in html and '<div class="edge">' in html


def test_no_break_space_before_french_question_mark():
    html = _render(sub_topic="Et ce qui ne se chiffre pas ?")
    assert "pas ?" in html


def test_essentiel_prefers_bullets_and_falls_back_to_prose():
    """Slide 2: numbered claims when the deck has them, prose summary otherwise."""
    from renderer.instagram_carousel._shared import _env, medium_labels
    tpl = _env().get_template("article_carousel_optimized_v0/02_essentiel.html")
    ctx = dict(slide_n=2, slide_total=10, progress=20, logo="", L=medium_labels("article"))

    bullets = tpl.render(essentiel=["Premier point", "Deuxième point"],
                         essentiel_summary="Le resume en prose", **ctx)
    assert 'class="pts"' in bullets and "Premier point" in bullets
    assert "01" in bullets and "02" in bullets
    assert "Le resume en prose" not in bullets

    prose = tpl.render(essentiel=[], essentiel_summary="Le resume en prose", **ctx)
    assert 'class="pts"' not in prose and "Le resume en prose" in prose
