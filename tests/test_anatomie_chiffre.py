"""The ANATOMIE D'UN CHIFFRE carousel: the model, the step rules, the cascade (with the
model call faked) and the HTML it renders. The deck in tests/fixtures/anatomie_chiffre_deck.json
is written from samples/articles/bfm_americains."""
import importlib
import json
from pathlib import Path

from extractors.anatomie_chiffre import extract
from extractors.registry import FORMATS
from models.anatomie_chiffre_presentation import AnatomieChiffrePresentation
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/anatomie_chiffre_deck.json").read_text(encoding="utf-8"))


# ── model, extractor, registry ──────────────────────────────────────────────

def test_the_deck_validates():
    pres = AnatomieChiffrePresentation.model_validate(DECK)
    assert [f.value for f in pres.chiffres.figures] == ["505.000 $", "33.000 $", "× 15", "215.900 $"]
    assert pres.recit.rows[0].kind == "donnee"
    assert len(pres.axe.readings) == 3
    assert pres.angle_mort.cards[0].opens == [1, 3]


def test_a_deck_without_an_axe_still_validates():
    assert AnatomieChiffrePresentation.model_validate({k: v for k, v in DECK.items() if k != "axe"}).axe is None


def test_the_extractor_passes_the_presentation_through():
    pres = AnatomieChiffrePresentation.model_validate(DECK)
    assert extract(full(), pres).presentation == pres


def test_the_format_is_registered():
    names = FORMATS["anatomie_chiffre"]
    assert names[1] == "extractors.anatomie_chiffre"
    assert importlib.import_module(names[1]).extract is extract
