from types import SimpleNamespace

from renderer.radar import radar_svg, DIM_SHORT


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
