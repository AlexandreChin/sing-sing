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


# ---- the seven-prism registry -----------------------------------------------------------------------------------

def test_the_catalogue_has_the_seven_prisms_in_the_spec_order():
    from agent.trois_regards_prisms import PRISM_IDS, PRISMS
    assert PRISM_IDS == ("economique", "sociologique", "juridique", "historique", "politique", "ecologique", "technologique")
    assert list(PRISMS) == list(PRISM_IDS)


def test_every_prism_has_a_name_a_definition_and_a_distinct_icon():
    from agent.trois_regards_prisms import PRISMS
    assert all(p.name and p.definition and p.icon_svg for p in PRISMS.values())
    assert len({p.icon_svg for p in PRISMS.values()}) == 7
    assert all("<" in p.icon_svg and "stroke" not in p.icon_svg and "#" not in p.icon_svg for p in PRISMS.values())
    assert PRISMS["economique"].name == "Économique" and PRISMS["ecologique"].name == "Écologique"


def test_the_prism_icons_are_not_in_the_canonical_lenses():
    from agent.lenses import CANONICAL_LENSES
    from agent.trois_regards_prisms import PRISM_IDS
    assert set(CANONICAL_LENSES) == {"sources", "chiffres", "causalite", "cadrage", "opinion_fait", "equilibre",
                                     "sophismes", "angles_morts"}
    assert not set(PRISM_IDS) & set(CANONICAL_LENSES)


def test_the_catalogue_text_names_every_prism():
    from agent.trois_regards_prisms import PRISM_IDS, PRISMS, catalogue_text
    lines = catalogue_text().splitlines()
    assert len(lines) == 7
    for line, pid in zip(lines, PRISM_IDS):
        assert pid in line and PRISMS[pid].name in line and PRISMS[pid].definition in line


# ---- guided steps, option models, fragments --------------------------------------------------------------------

import copy  # noqa: E402

from agent import trois_regards_adapt_agent as agent  # noqa: E402
from agent.carousel_steps.steps import Option  # noqa: E402


def option_fields(deck: dict) -> dict[str, dict]:
    """The flat option fields of every step, cut from a deck."""
    pad = lambda items, n: list(items) + [""] * (n - len(items))  # noqa: E731
    ax, po, pr, mx = deck["axe"], deck["position"], deck["prisms"], deck["matrix"]
    prisms = {}
    for i, s in enumerate(pr, 1):
        prisms[f"p{i}"] = {"question": s["question"],
                           **dict(zip(("line1", "line2", "line3", "line4"), pad(s["lines"], 4))),
                           "sources": " ; ".join(s["sources"]), "media_note": s.get("media_note", "")}
    return {
        "axe": {"question": ax["question"], "article_question": ax["article_question"], "subject": ax["subject"],
                **{f"prism{i}": p for i, p in enumerate(ax["prisms"], 1)},
                "media": ax["media"], "media_grounding": ax["media_grounding"], "closing": ax["closing"]},
        "position": {"kicker": po["kicker"], "title": po["title"], "lead": po["lead"],
                     **dict(zip(("card1", "card2", "card3", "card4"),
                                pad([f"{c['label']} | {c['text']}" for c in po["cards"]], 4)))},
        "prismes": prisms,
        "matrice": {"title": mx["title"],
                    **{f"col{i}": f"{c['variable']} | {c['indicator']}" for i, c in enumerate(mx["columns"], 1)}},
        "hook": {"title": deck["hook"]["title"], "promise": deck["hook"]["promise"]},
        "writing": {"caption": deck["caption"]},
    }


FIELDS = option_fields(DECK)


def _opt(fields: dict, slot: str = "a") -> Option:
    return Option(id=slot, slot=slot, reason="r", fields=fields)


def _fragments(fields: dict = FIELDS) -> dict[str, dict]:
    frags: dict[str, dict] = {}
    for step in agent.STEPS:
        if step.name == "prismes":
            picks = [_opt(fields["prismes"][s], s) for s in step.slots]
        else:
            picks = [_opt(fields[step.name])]
        frags[step.name] = agent.to_fragment(step, picks, frags)
    return frags


def test_the_steps_come_in_order():
    assert agent.STEP_NAMES == ["axe", "position", "prismes", "matrice", "hook"]
    assert agent.STEPS[-1].name == "writing" and agent.STEPS[-1].option_model is None
    assert [s.n for s in agent.STEPS] == [1, 2, 3, 4, 5, 6]


def test_only_prismes_has_three_slots():
    assert {s.name: s.slots for s in agent.STEPS if s.slots != ("a",)} == {"prismes": ("p1", "p2", "p3")}
    assert agent.STEP_BY_NAME["prismes"].offered == (2, 3)


def test_the_fragments_rebuild_the_deck():
    deck = agent.assemble(_fragments())
    assert TroisRegardsPresentation.model_validate(deck).model_dump() == \
        TroisRegardsPresentation.model_validate(DECK).model_dump()
    assert deck == DECK


def test_an_empty_line4_and_an_empty_media_note_are_left_out():
    fields = copy.deepcopy(FIELDS)
    fields["prismes"]["p2"]["line4"] = ""
    frag = agent.to_fragment(agent.STEP_BY_NAME["prismes"], [_opt(fields["prismes"][s], s) for s in ("p1", "p2", "p3")],
                             {"axe": _fragments()["axe"]})
    assert all(len(s["lines"]) == 3 for s in frag["prisms"])
    assert "media_note" in frag["prisms"][0] and "media_note" not in frag["prisms"][1]
    fields["position"]["card4"] = ""
    pos = agent.to_fragment(agent.STEP_BY_NAME["position"], [_opt(fields["position"])], {})
    assert len(pos["position"]["cards"]) == 3


def test_a_prism_fragment_takes_its_prism_id_from_the_axe_order():
    frags = _fragments()
    frags["axe"]["axe"]["prisms"] = ["juridique", "historique", "politique"]
    prismes = agent.to_fragment(agent.STEP_BY_NAME["prismes"],
                                [_opt(FIELDS["prismes"][s], s) for s in ("p1", "p2", "p3")], frags)
    assert [s["prism"] for s in prismes["prisms"]] == ["juridique", "historique", "politique"]
    matrice = agent.to_fragment(agent.STEP_BY_NAME["matrice"], [_opt(FIELDS["matrice"])], frags)
    assert [c["prism"] for c in matrice["matrix"]["columns"]] == ["juridique", "historique", "politique"]
