from models.full_analysis import ArticleMetadata
from renderer.instagram_carousel._shared import _env, cover_layers

TPL = "article_carousel_optimized_v0/01_hook.html"


def test_cover_layers_output_renders_in_hook():
    meta = ArticleMetadata(title="Réforme des retraites", category="Politique")
    layers = cover_layers(meta, "Fallback headline")
    html = _env().get_template(TPL).render(
        slide_n=1, slide_total=10, progress=10, logo="",
        article_title="Réforme des retraites", source_meta="LE MONDE",
        headline="Un **texte** technique", **layers,
    )
    assert "Politique" in html
    assert '<div class="artbg">' in html
    assert '<div class="giant">' in html
    assert 'class="cat-pill"' not in html  # old pill element no longer rendered


def test_renderers_no_longer_pass_cat_pill():
    # guard against a half-done wiring edit
    import renderer.instagram_carousel.optimized as opt
    import renderer.instagram_carousel.optimized_short as short
    import inspect
    for mod in (opt, short):
        src = inspect.getsource(mod.generate_html)
        assert "cat_pill" not in src
        assert "cover_layers(" in src
