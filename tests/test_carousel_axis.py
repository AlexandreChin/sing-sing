import json
from pathlib import Path

from agent.instagram_carousel_adapt_agent import _axis_errors
from models.instagram_carousel_presentation import InstagramCarouselPresentation

DECK = Path("tests/fixtures/carousel_axis_adapt.json")   # article_14, hand-tuned around slide 8


def _pres():
    return InstagramCarouselPresentation.model_validate(json.loads(DECK.read_text()))


def test_legacy_deck_without_axis_link_is_not_checked():
    pres = _pres()
    assert _axis_errors(pres, pres.display) == []


def test_selected_beat_needs_axis_link():
    pres = _pres()
    beats = pres.display.reading_beats
    picked = [b for b in beats if b.selected]
    picked[0].axis_link = "Montre d'où vient le récit « casseurs »."
    errs = _axis_errors(pres, pres.display)
    assert sum("axis_link is empty" in e for e in errs) == 2


def test_side_subject_bullet_is_flagged():
    pres = _pres()
    for b in pres.display.reading_beats:
        b.axis_link = "lien"
    assert _axis_errors(pres, pres.display) == []
    pres.display.essentiel[2] = "L'État rend la manifestation plus **coûteuse** devant la loi."
    errs = _axis_errors(pres, pres.display)
    assert len(errs) == 1 and errs[0].startswith("display.essentiel[2]")
