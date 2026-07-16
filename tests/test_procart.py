import xml.etree.ElementTree as ET

from renderer.instagram_carousel.procart import (
    STYLES, constellation, contours, orbits, pick_style, cover_art,
)


def _wellformed(markup: str) -> bool:
    # inner markup must be parseable once wrapped in an <svg> root
    ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{markup}</svg>')
    return True


def test_registry_has_the_three_styles():
    assert set(STYLES) == {"constellation", "contours", "orbits"}
    assert all(callable(fn) for fn in STYLES.values())


def test_each_style_returns_wellformed_nonempty_markup():
    for fn in (constellation, contours, orbits):
        m = fn("seed")
        assert m and _wellformed(m)


def test_cover_art_is_deterministic():
    assert cover_art("Réforme des retraites") == cover_art("Réforme des retraites")
    assert pick_style("Réforme des retraites") == pick_style("Réforme des retraites")


def test_different_seeds_produce_different_art():
    assert cover_art("Article A") != cover_art("Article B")


def test_pick_style_covers_all_styles_over_many_seeds():
    seen = {pick_style(f"title-{i}") for i in range(300)}
    assert seen == set(STYLES)


def test_cover_art_matches_picked_style():
    seed = "Un titre quelconque"
    assert cover_art(seed) == STYLES[pick_style(seed)](seed)
