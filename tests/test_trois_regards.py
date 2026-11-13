"""The TROIS REGARDS carousel: model, extractor, registry. The deck in
tests/fixtures/trois_regards_deck.json is written from
samples/articles/espagne-comment-la-crise-du-logement-a-t."""
import importlib
import json
import re
from pathlib import Path

from extractors.registry import FORMATS
from extractors.trois_regards import extract
from models.trois_regards_presentation import TroisRegardsPresentation
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/trois_regards_deck.json").read_text(encoding="utf-8"))


def test_the_deck_validates():
    pres = TroisRegardsPresentation.model_validate(DECK)
    assert [p.prism for p in pres.prisms] == ["politique", "economique", "sociologique"]
    assert len(pres.position.cards) == 4
    assert [p.prism for p in pres.prisms if p.media_note] == ["politique"] == [pres.axe.media]


def test_a_deck_without_an_axe_still_validates():
    assert TroisRegardsPresentation.model_validate({k: v for k, v in DECK.items() if k != "axe"}).axe is None


def test_the_extractor_passes_the_presentation_through():
    pres = TroisRegardsPresentation.model_validate(DECK)
    assert extract(full(), pres).presentation == pres


def test_the_format_is_registered():
    names = FORMATS["trois_regards"]
    assert names[1] == "extractors.trois_regards"
    assert importlib.import_module(names[1]).extract is extract


def test_the_fixture_respects_the_caps_and_the_spec():
    p = TroisRegardsPresentation.model_validate(DECK)
    n = lambda s: len(s.replace("**", ""))
    assert n(p.axe.question) <= 60 and n(p.axe.subject) <= 36
    assert n(p.axe.closing) <= 110 and p.axe.closing.endswith("?") and n(p.axe.media_grounding) <= 120
    assert n(p.position.kicker) <= 30 and n(p.position.title) <= 46 and n(p.position.lead) <= 90
    assert all(n(c.text) <= 108 and n(c.label) <= 30 for c in p.position.cards)
    for s in p.prisms:
        assert n(s.question) <= 64 and n(s.media_note) <= 90 and len(s.sources) <= 3
        assert all(n(x) <= 80 and all(re.fullmatch(r"(1[5-9]|20)\d\d", d) for d in re.findall(r"\d+", x)) for x in s.lines)
        assert all(n(x) <= 30 and not re.search(r"\d", x) for x in s.sources)
    assert n(p.matrix.title) <= 34
    assert all(n(c.variable) <= 60 and n(c.indicator) <= 40 for c in p.matrix.columns)
    assert not re.search(r"\d", json.dumps(DECK["matrix"], ensure_ascii=False))
    assert n(p.hook.title) <= 70 and n(p.hook.promise) <= 100
    assert "http" not in json.dumps(DECK, ensure_ascii=False) and p.caption.count("#") == 4
    assert p.matrix.title.endswith("?") and p.hook.title.endswith("?")
    assert p.hook.promise == "Trois regards sur la crise du logement ; à vous d'en juger."
    words = {"politique": "politique", "economique": "économi", "sociologique": "sociolog"}
    assert all(words[k] in p.axe.closing.lower() for k in p.axe.prisms)
    assert [s.prism for s in p.prisms if s.media_note] == [p.axe.media]
    outside = re.sub(r"«[^»]*»", "", json.dumps(DECK, ensure_ascii=False).lower())
    for w in ("biais", "manipulation", "mensonge", "trompeur", "oublie", "ignore", "omet", "néglige", "ne dit pas"):
        assert w not in outside, w
