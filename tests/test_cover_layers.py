from models.full_analysis import ArticleMetadata
from renderer.categories import CATEGORY_ICONS
from renderer.instagram_carousel._shared import cover_layers
from renderer.instagram_carousel.procart import cover_art


def test_known_category_yields_tab_and_glyph_and_art():
    meta = ArticleMetadata(title="Titre", category="Tech")
    out = cover_layers(meta, "fallback")
    assert out["rubrique"] == "Tech"
    assert out["glyph"] == CATEGORY_ICONS["Tech"]
    assert out["art_svg"]


def test_autre_and_missing_drop_rubrique_and_glyph():
    for cat in ("Autre", None):
        out = cover_layers(ArticleMetadata(title="T", category=cat), "fallback")
        assert out["rubrique"] is None
        assert out["glyph"] == ""
        assert out["art_svg"]  # art still present


def test_seed_uses_title_then_falls_back_to_headline():
    with_title = cover_layers(ArticleMetadata(title="Le vrai titre", category="Tech"), "HL")
    assert with_title["art_svg"] == cover_art("Le vrai titre")
    no_title = cover_layers(ArticleMetadata(title=None, category="Tech"), "La retombée")
    assert no_title["art_svg"] == cover_art("La retombée")
