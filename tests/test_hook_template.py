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
    assert "art-title" in html and "Titre de l" in html  # article_title rendered (apostrophe auto-escaped as &#39;)
    assert "<strong>mot</strong>" in html          # md_bold applied
    assert 'class="cat-pill"' not in html          # old pill element no longer rendered
    assert 'x1="0" y1="0" x2="10" y2="10"' in html  # art_svg injected


def test_hook_drops_category_elements_when_absent():
    html = _render(rubrique=None, glyph="")
    assert '<div class="rubrique-tab">' not in html
    assert '<div class="giant">' not in html
    assert '<div class="artbg">' in html            # art still present
