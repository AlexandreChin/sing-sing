import json
from pathlib import Path

from agent.instagram_carousel_adapt_agent import _clue_errors, _light_errors, _validate
from models.instagram_carousel_presentation import InstagramCarouselPresentation

DECK = Path("tests/fixtures/carousel_axis_adapt.json")   # article_14, full format


def _data():
    data = json.loads(DECK.read_text())
    for b in data["display"]["reading_beats"]:
        b["axis_link"] = "lien"
    return data


def test_vague_clue_is_flagged():
    data = _data()
    beat = next(b for b in data["display"]["reading_beats"] if b["selected"])
    beat["answer"] = "**Comparez** les arrestations d'un lycée à l'autre."
    pres = InstagramCarouselPresentation.model_validate(data)
    errs = _clue_errors(pres, pres.display)
    assert len(errs) == 1 and "names no place to look" in errs[0]


def test_named_sources_pass():
    data = _data()
    beat = next(b for b in data["display"]["reading_beats"] if b["selected"])
    for answer in ("**Des déclarations** : à relire au compte rendu de l'Assemblée.",
                   "**L'Union étudiante** compare Sciences Po et la Seine-Saint-Denis.",
                   "**Plus de moyens** pour l'école : le détail dans les plateformes des syndicats."):
        beat["answer"] = answer
        pres = InstagramCarouselPresentation.model_validate(data)
        assert _clue_errors(pres, pres.display) == [], answer


def test_light_caps_and_counts():
    data = _data()
    d = data["display"]
    full_errs = _validate(data)
    assert not any(e.startswith("light:") for e in full_errs)
    d["reperes_facts"] = d["reperes_facts"][:1]
    data["cta"]["where_to_look"] = data["cta"]["where_to_look"][:1]
    light_errs = _validate(data, light=True)
    assert not any("reperes_facts must have" in e or "where_to_look has" in e for e in light_errs)
    d["essentiel"][0] = "Le gouvernement réduit la révolte lycéenne à une affaire de **casseurs**."
    pres = InstagramCarouselPresentation.model_validate(data)
    assert any("essentiel[0]" in e for e in _light_errors(pres, pres.display))


def test_light_claim_detail_ideas():
    data = _data()
    data["display"]["essentiel"] = ["On montre des **casseurs** : quelques violences pour toute la révolte",
                                    "On tait leurs **demandes** : l'école, l'égalité, être entendus",
                                    "L'État oppose la **force** : arrestations, loi « casseurs-payeurs »"]
    pres = InstagramCarouselPresentation.model_validate(data)
    assert not any("essentiel" in e for e in _light_errors(pres, pres.display))
    data["display"]["essentiel"][0] = "On montre surtout des **casseurs** partout : quelques violences"
    pres = InstagramCarouselPresentation.model_validate(data)
    assert any("essentiel[0]" in e for e in _light_errors(pres, pres.display))
