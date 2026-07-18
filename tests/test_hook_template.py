from renderer.categories import CATEGORY_ICONS
from renderer.instagram_carousel._shared import _env

TPL = "article_carousel_optimized_v0/01_hook.html"


def _render(**over):
    ctx = dict(
        slide_n=1, slide_total=10, progress=10, logo="",
        article_title="Titre de l'article", source_meta="LE MONDE · 2026",
        headline="Un **mot** en gras", rubrique="Tech",
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
    assert '<div class="src-card">' in html and "Titre de l" in html  # source card renders article title (apostrophe auto-escaped as &#39;)
    assert "On décrypte" in html                   # brand-voice kicker under the source card
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
