from renderer.categories import CATEGORY_COLORS, CATEGORY_ICONS, pill


def test_pill_returns_theme_colours_and_icon():
    p = pill("Économie", "dark")
    assert p["label"] == "Économie" and p["text"] == "#e3b341" and p["bg"] == "#322914"
    # icon is inline SVG that inherits the pill colour (stroke=currentColor)
    assert p["icon"].startswith("<svg") and "currentColor" in p["icon"]
    light = pill("Économie", "light")
    assert light["text"] == "#8a6410" and light["bg"] == "#f6efd8"


def test_every_category_has_an_icon():
    assert set(CATEGORY_ICONS) == set(CATEGORY_COLORS)
    assert all(CATEGORY_ICONS.values())


def test_pill_none_for_autre_and_missing():
    # "Autre" and absent categories resolve to no pill (templates drop it).
    assert pill("Autre") is None
    assert pill(None) is None
    assert pill("") is None


def test_every_category_defines_all_four_colours():
    for name, v in CATEGORY_COLORS.items():
        assert set(v) == {"dark_text", "dark_bg", "light_text", "light_bg"}, name


def test_taxonomy_matches_model():
    # The colour map keys must be exactly the model's categories minus "Autre".
    from models.full_analysis import ArticleMetadata
    allowed = set(ArticleMetadata.model_fields["category"].annotation.__args__[0].__args__)
    assert set(CATEGORY_COLORS) == allowed - {"Autre"}
