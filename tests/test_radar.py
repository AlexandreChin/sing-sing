from types import SimpleNamespace

from renderer.radar import radar_svg, DIM_SHORT
from renderer.instagram_carousel._shared import _env


def _dim(dimension, score):
    return SimpleNamespace(dimension=dimension, score=score, label=dimension)


def test_radar_empty_returns_blank():
    assert radar_svg([]) == ""


def test_radar_renders_every_dimension_and_score():
    dims = [_dim(k, 3) for k in DIM_SHORT]
    svg = radar_svg(dims)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    for label in DIM_SHORT.values():
        assert label in svg                       # every axis labelled
    assert svg.count("<polygon") == 6             # 5 rings + 1 data shape
    assert svg.count("<tspan") == len(dims)       # a score per axis


def test_verdict_slide_is_two_block_wrapup_without_tracker():
    # Wrap-up slide: "À retenir" + "Les réflexes critiques", no tracker (like the CTA), no radar.
    html = _env().get_template("article_carousel_optimized_v0/09_bilan.html").render(
        slide_n=9, slide_total=10, progress=90, logo="",
        takeaways=["Premier point", "Deuxième point"],
        critical=["Premier réflexe", "Deuxième réflexe"],
    )
    assert "À retenir" in html and "Les réflexes critiques" in html
    assert "Premier point" in html and "Deuxième réflexe" in html
    assert 'class="tracker"' not in html       # no tracker on the wrap-up
    assert "<polygon" not in html              # no radar
