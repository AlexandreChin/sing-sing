"""The TROIS REGARDS carousel: model, extractor, registry. The deck in
tests/fixtures/trois_regards_deck.json (revision 3: four answering cards per prism, a lead per slide, the two-sided
tensions, « Les angles morts ») is written from samples/articles/espagne-comment-la-crise-du-logement-a-t;
tests/fixtures/trois_regards_deck_v1.json is the older deck shape (prism lines and sources, the matrix), kept to prove an
older deck still loads and renders; a revision-2 deck (prism questions, the arbitrage) is built from it in the tests."""
import importlib
import json
import re
from pathlib import Path

from extractors.registry import FORMATS
from extractors.trois_regards import extract
from models.trois_regards_presentation import TroisRegardsPresentation
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/trois_regards_deck.json").read_text(encoding="utf-8"))
DECK_V1 = json.loads(Path("tests/fixtures/trois_regards_deck_v1.json").read_text(encoding="utf-8"))


def test_the_deck_validates():
    pres = TroisRegardsPresentation.model_validate(DECK)
    assert [p.prism for p in pres.prisms] == ["politique", "economique", "juridique"]
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


def test_the_v1_fixture_respects_the_older_caps_and_the_spec():
    p = TroisRegardsPresentation.model_validate(DECK_V1)
    n = lambda s: len(s.replace("**", ""))
    assert n(p.axe.question) <= 60 and n(p.axe.subject) <= 36
    assert n(p.axe.closing) <= 110 and p.axe.closing.endswith("?") and n(p.axe.media_grounding) <= 120
    assert n(p.position.kicker) <= 26 and n(p.position.title) <= 32 and n(p.position.lead) <= 90
    assert all(n(c.text) <= 76 and n(c.label) <= 30 for c in p.position.cards)
    for s in p.prisms:
        assert n(s.question) <= 50 and n(s.media_note) <= 90 and len(s.sources) <= 3
        assert all(n(x) <= 80 and all(re.fullmatch(r"(1[5-9]|20)\d\d", d) for d in re.findall(r"\d+", x)) for x in s.lines)
        assert all(n(x) <= 30 and not re.search(r"\d", x) for x in s.sources)
    assert n(p.matrix.title) <= 34
    assert all(n(c.variable) <= 60 and n(c.indicator) <= 40 for c in p.matrix.columns)
    assert not re.search(r"\d", json.dumps(DECK_V1["matrix"], ensure_ascii=False))
    assert n(p.hook.title) <= 70 and n(p.hook.promise) <= 100
    assert "http" not in json.dumps(DECK_V1, ensure_ascii=False) and p.caption.count("#") == 4
    assert p.matrix.title.endswith("?") and p.hook.title.endswith("?")
    assert p.hook.promise == "Trois regards sur la crise du logement ; à vous d'en juger."
    words = {"politique": "politique", "economique": "économi", "sociologique": "sociolog"}
    assert all(words[k] in p.axe.closing.lower() for k in p.axe.prisms)
    assert [s.prism for s in p.prisms if s.media_note] == [p.axe.media]
    outside = re.sub(r"«[^»]*»", "", json.dumps(DECK_V1, ensure_ascii=False).lower())
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
    """The flat option fields of every step, cut from a deck (a clue is « source | find », a pair « 1,2 »)."""
    pad = lambda items, n: list(items) + [""] * (n - len(items))  # noqa: E731
    clue = lambda c: f"{c['source']} | {c['find']}"  # noqa: E731
    ax, po, t, lim = deck["axe"], deck["position"], deck["tensions"], deck["limites"]
    prisms = {}
    for i, s in enumerate(deck["prisms"], 1):
        cards = s["cards"]
        prisms[f"p{i}"] = {"title": s["title"], "lead": s.get("lead", ""),
                           **{f"head{k}": c["head"] for k, c in enumerate(cards, 1)},
                           **{f"answer{k}": c["answer"] for k, c in enumerate(cards, 1)},
                           **{f"indice{k}": clue(c) for k, c in enumerate(cards, 1)},
                           "media_note": s.get("media_note", "")}
    return {
        "axe": {"question": ax["question"], "article_question": ax["article_question"], "subject": ax["subject"],
                **{f"prism{i}": p for i, p in enumerate(ax["prisms"], 1)},
                "media": ax["media"], "media_grounding": ax["media_grounding"], "closing": ax["closing"]},
        "position": {"kicker": po["kicker"], "title": po["title"], "lead": po["lead"],
                     **dict(zip(("card1", "card2", "card3", "card4"),
                                pad([f"{c['label']} | {c['text']}" for c in po["cards"]], 4)))},
        "prismes": prisms,
        "tensions": {"title": t["title"], "lead": t["lead"],
                     **{f"pair{k}": ",".join(map(str, c["pair"])) for k, c in enumerate(t["cards"], 1)},
                     **{f"head{k}": c["head"] for k, c in enumerate(t["cards"], 1)},
                     **{f"claim{k}": c["claim"] for k, c in enumerate(t["cards"], 1)},
                     **{f"indice{k}": clue(c) for k, c in enumerate(t["cards"], 1)}},
        "limites": {"title": lim["title"], "lead": lim["lead"],
                    **{f"head{k}": c["head"] for k, c in enumerate(lim["cards"], 1)},
                    **{f"claim{k}": c["claim"] for k, c in enumerate(lim["cards"], 1)},
                    **{f"indice{k}": clue(c) for k, c in enumerate(lim["cards"], 1)}},
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
    assert agent.STEP_NAMES == ["axe", "position", "prismes", "tensions", "limites", "hook"]
    assert agent.STEPS[-1].name == "writing" and agent.STEPS[-1].option_model is None
    assert [s.n for s in agent.STEPS] == [1, 2, 3, 4, 5, 6, 7]
    assert "matrice" not in agent.STEP_BY_NAME and not hasattr(agent, "MatriceOption")
    assert "arbitrage" not in agent.STEP_BY_NAME and not hasattr(agent, "ArbitrageOption")


def test_the_option_models_have_the_flat_card_fields():
    four, three = (1, 2, 3, 4), (1, 2, 3)
    assert list(agent.PrismesOption.model_fields) == ["title", "lead", *(f"head{k}" for k in four),
                                                       *(f"answer{k}" for k in four), *(f"indice{k}" for k in four),
                                                       "media_note"]
    assert list(agent.TensionsOption.model_fields) == ["title", "lead", *(f"pair{k}" for k in three),
                                                        *(f"head{k}" for k in three), *(f"claim{k}" for k in three),
                                                        *(f"indice{k}" for k in three)]
    assert list(agent.LimitesOption.model_fields) == ["title", "lead", *(f"head{k}" for k in three),
                                                       *(f"claim{k}" for k in three), *(f"indice{k}" for k in three)]


def test_only_prismes_has_three_slots():
    assert {s.name: s.slots for s in agent.STEPS if s.slots != ("a",)} == {"prismes": ("p1", "p2", "p3")}
    assert agent.STEP_BY_NAME["prismes"].offered == (2, 3)


def test_the_fragments_rebuild_the_v3_deck():
    deck = agent.assemble(_fragments())
    assert TroisRegardsPresentation.model_validate(deck).model_dump() == \
        TroisRegardsPresentation.model_validate(DECK).model_dump()
    assert deck == DECK
    assert "matrix" not in deck and "arbitrage" not in deck and deck["tensions"]["cards"][2]["pair"] == [2, 3]
    assert set(deck["prisms"][1]["cards"][0]) == {"head", "answer", "source", "find"}      # a prism card answers
    assert deck["prisms"][0]["lead"] == "" and deck["prisms"][1]["lead"] and deck["tensions"]["lead"]
    assert set(deck["limites"]) == {"title", "lead", "cards"} and len(deck["limites"]["cards"]) == 3
    assert set(deck["limites"]["cards"][0]) == {"head", "claim", "source", "find"}


def test_an_empty_media_note_is_left_out():
    frag = agent.to_fragment(agent.STEP_BY_NAME["prismes"], [_opt(FIELDS["prismes"][s], s) for s in ("p1", "p2", "p3")],
                             {"axe": _fragments()["axe"]})
    assert all(len(s["cards"]) == 4 for s in frag["prisms"])
    assert "media_note" in frag["prisms"][0] and "media_note" not in frag["prisms"][1]
    fields = copy.deepcopy(FIELDS)
    fields["position"]["card4"] = ""
    pos = agent.to_fragment(agent.STEP_BY_NAME["position"], [_opt(fields["position"])], {})
    assert len(pos["position"]["cards"]) == 3


def test_a_clue_is_cut_into_source_and_find_and_a_pair_into_two_numbers():
    frags = _fragments()
    card = frags["prismes"]["prisms"][1]["cards"][0]
    assert card == {"head": DECK["prisms"][1]["cards"][0]["head"], "answer": DECK["prisms"][1]["cards"][0]["answer"],
                    "source": "Banco de España", "find": "logements achevés et nouveaux ménages, par région"}
    t = agent.to_fragment(agent.STEP_BY_NAME["tensions"], [_opt({**FIELDS["tensions"], "pair1": " 2 , 1 "})], frags)
    assert t["tensions"]["cards"][0]["pair"] == [1, 2]                 # a pair is the same pair either way round
    lim = frags["limites"]["limites"]["cards"][1]
    assert set(lim) == {"head", "claim", "source", "find"} and lim["source"] == "Consejo de la Juventud"


def test_a_prism_fragment_takes_its_prism_id_from_the_axe_order():
    frags = _fragments()
    frags["axe"]["axe"]["prisms"] = ["sociologique", "historique", "politique"]
    prismes = agent.to_fragment(agent.STEP_BY_NAME["prismes"],
                                [_opt(FIELDS["prismes"][s], s) for s in ("p1", "p2", "p3")], frags)
    assert [s["prism"] for s in prismes["prisms"]] == ["sociologique", "historique", "politique"]


# ---- hard rules, flags and caps -------------------------------------------------------------------------------

import pytest  # noqa: E402

ARTICLE = ("Le gouvernement a proposé un plafond. « Un manque de logements sociaux » pèse sur les loyers. "
           "L'article cite aussi l'année 2024 et le Parlement.")


def _fe(step: str, fields: dict, slot: str = "a", article: str | None = None, frags: dict | None = None):
    frags = _fragments() if frags is None else frags
    if step == "axe":
        frags = {}
    return agent.field_errors(step, fields, frags, article, slot)


def _with(step: str, slot: str | None = None, **kw) -> dict:
    base = FIELDS[step][slot] if slot else FIELDS[step]
    return {**base, **kw}


def _hard(step, fields, **kw):
    return _fe(step, fields, **kw)[0]


def _flags(step, fields, **kw):
    return _fe(step, fields, **kw)[1]


def _p2(**kw):
    """The hard errors of the second (non-media) prism slide with `kw` rewritten."""
    return _hard("prismes", _with("prismes", "p2", **kw), slot="p2")


def test_the_sample_deck_breaks_no_hard_rule_and_its_cards_raise_no_flag():
    for step in ("axe", "position", "tensions", "limites", "hook", "writing"):
        assert _hard(step, FIELDS[step]) == [], step
    for step in ("axe", "tensions", "limites"):
        assert _flags(step, FIELDS[step]) == [], step
    for slot in ("p1", "p2", "p3"):
        assert _fe("prismes", FIELDS["prismes"][slot], slot=slot) == ([], []), slot


def test_a_field_over_its_cap_is_a_hard_error():
    assert any("axe.question" in e and "max 60" in e for e in _hard("axe", _with("axe", question="x" * 59 + "y ?")))
    assert not _hard("axe", _with("axe", question="D'où vient la crise du logement ?"))
    assert any("axe.subject" in e for e in _hard("axe", _with("axe", subject="x" * 37)))
    assert any("axe.closing" in e for e in _hard("axe", _with("axe", closing="x" * 110 + " ?")))
    assert any("axe.media_grounding" in e for e in _hard("axe", _with("axe", media_grounding="x" * 121)))
    for name, cap in (("kicker", 26), ("title", 32), ("lead", 90)):
        assert any(f"position.{name}" in e for e in _hard("position", _with("position", **{name: "x" * (cap + 1)})))
    assert any("prismes.media_note" in e for e in _hard("prismes", _with("prismes", "p1", media_note="x" * 61), slot="p1"))
    assert not _hard("prismes", _with("prismes", "p1", media_note="x" * 60), slot="p1")
    assert any("hook.title" in e for e in _hard("hook", _with("hook", title="x" * 70 + " ?")))
    assert any("hook.promise" in e for e in _hard("hook", _with("hook", promise="x" * 101)))


_NEW_CAPS = [(s, f) for (s, f) in agent._CAPS if s in ("prismes", "tensions", "limites") and f != "media_note"]


def _at(step: str, name: str, n: int) -> str:
    """A value of exactly `n` characters that breaks no other rule of `step.name`."""
    if name.startswith("claim"):
        return "x" * (n - 2) + " ?"
    if step == "tensions" and name.startswith("head"):          # two sides « a ; b »
        return "x" * (n // 2 - 1) + " ; " + "y" * (n - n // 2 - 2)
    return "x" * n


@pytest.mark.parametrize("step,name", _NEW_CAPS)
def test_each_card_field_at_its_cap_passes_and_one_more_character_fails(step, name):
    cap = agent._CAPS[(step, name)][1]
    slot = "p2" if step == "prismes" else "a"
    at = _hard(step, _with(step, slot if step == "prismes" else None, **{name: _at(step, name, cap)}), slot=slot)
    over = _hard(step, _with(step, slot if step == "prismes" else None, **{name: _at(step, name, cap + 1)}), slot=slot)
    assert not any(e.startswith(f"{step}.{name} is") for e in at), at
    assert any(e.startswith(f"{step}.{name} is {cap + 1} chars (max {cap})") for e in over), over


def test_the_starting_caps_of_the_spec():
    caps = agent.prompt_caps()
    assert (caps["prismes.title"], caps["prismes.lead"], caps["prismes.head"], caps["prismes.answer"]) == (40, 60, 36, 90)
    assert caps["prismes.media_note"] == 60                        # the media's slide draws it as its lead: one line
    assert (caps["prismes.indice.source"], caps["prismes.indice.find"]) == (30, 60)
    assert (caps["tensions.title"], caps["tensions.lead"], caps["tensions.head"], caps["tensions.claim"]) == (44, 60, 76, 46)
    assert (caps["limites.title"], caps["limites.lead"], caps["limites.head"], caps["limites.claim"]) == (34, 60, 40, 46)
    assert (caps["tensions.indice.source"], caps["limites.indice.find"]) == (30, 60)


@pytest.mark.parametrize("step,name,part,cap", [
    ("position", "card2", "label", 30), ("position", "card2", "text", 76),
    ("prismes", "indice2", "source", 30), ("prismes", "indice4", "find", 60),
    ("tensions", "indice1", "source", 30), ("tensions", "indice3", "find", 60),
    ("limites", "indice2", "source", 30), ("limites", "indice1", "find", 60)])
def test_a_part_over_its_cap_is_a_hard_error(step, name, part, cap):
    over, ok = "x" * (cap + 1), "x" * cap
    mk = lambda v: (f"{v} | ab" if part in ("label", "source") else f"ab | {v}")  # noqa: E731
    slot = "p2" if step == "prismes" else "a"
    h = lambda v: _hard(step, _with(step, slot if step == "prismes" else None, **{name: mk(v)}), slot=slot)  # noqa: E731
    assert any(f"{step}.{name}" in e and part in e for e in h(over))
    assert not any(f"{step}.{name}" in e for e in h(ok))


def test_the_axe_needs_three_distinct_prisms_of_the_catalogue():
    assert any("distinct" in e for e in _hard("axe", _with("axe", prism2="politique")))
    assert any("catalogue" in e for e in _hard("axe", _with("axe", prism3="gastronomique")))
    assert any("distinct" in e or "empty" in e for e in _hard("axe", _with("axe", prism3="")))


def test_the_media_prism_is_one_of_the_three():
    assert any("media" in e for e in _hard("axe", _with("axe", media="sociologique")))
    assert not _hard("axe", _with("axe", media="juridique"))


def test_the_deck_question_the_hook_title_and_the_closing_line_end_in_a_question_mark():
    assert any("axe.question" in e and "?" in e for e in _hard("axe", _with("axe", question="D'où vient la crise.")))
    assert any("axe.closing" in e and "?" in e for e in _hard("axe", _with("axe", closing="Quel regard explique la crise.")))
    assert any("hook.title" in e and "?" in e for e in _hard("hook", _with("hook", title="La crise du logement")))


def test_claims_end_in_a_question_mark_and_titles_need_not():
    for step in ("tensions", "limites"):
        bad = _hard(step, _with(step, claim2="Les loyers montent plus vite là où l'offre manque"))
        assert any(e.startswith(f"{step}.claim2 must be a question") for e in bad), step
        assert not any("must be a question" in e for e in _hard(step, _with(step, title="Trois zones d'ombre"))), step
    assert not any("must be a question" in e for e in _p2(title="Un marché qui ne construit plus"))   # a thesis


def test_the_hook_promise_has_the_fixed_shape():
    ok = "Trois regards sur la crise du logement ; à vous d'en juger."
    assert not _hard("hook", _with("hook", promise=ok))
    for bad in ("Comprendre la crise du logement en trois regards.",
                "Trois regards sur la crise du logement, à vous d'en juger.",
                "Trois regards sur ; à vous d'en juger.",
                "Trois regards sur   ; à vous d'en juger."):
        assert any("hook.promise" in e for e in _hard("hook", _with("hook", promise=bad))), bad


def test_the_hook_promise_accepts_french_typography():
    """A no-break space (NBSP or narrow) before « ; » or a typographic apostrophe is the same promise."""
    for typo in ("Trois regards sur la crise du logement ; à vous d'en juger.",
                 "Trois regards sur la crise du logement ; à vous d'en juger.",
                 "Trois regards sur la crise du logement ; à vous d’en juger.",
                 "Trois regards sur la crise du logement ; à vous d’en juger."):
        hard, flags = _fe("hook", _with("hook", promise=typo))
        assert hard == [] and not [f for f in flags if "subject" in f], typo


def test_a_prism_slide_needs_a_title_and_four_whole_cards():
    for name in ("title", "head1", "head4", "answer2", "indice3"):
        assert any(e == f"prismes.{name} is empty" for e in _p2(**{name: ""})), name
    assert not _p2(media_note="")


def test_the_tensions_and_the_limites_need_three_whole_cards():
    for name in ("title", "lead", "pair2", "head3", "claim1", "indice2"):
        assert any(e == f"tensions.{name} is empty" for e in _hard("tensions", _with("tensions", **{name: ""}))), name
    for name in ("title", "lead", "head3", "claim1", "indice2"):
        assert any(e == f"limites.{name} is empty" for e in _hard("limites", _with("limites", **{name: ""}))), name


def test_only_the_media_prism_slot_carries_a_media_note():
    assert any("media_note" in e for e in _hard("prismes", _with("prismes", "p1", media_note=""), slot="p1"))
    assert any("media_note" in e for e in _hard("prismes", _with("prismes", "p2", media_note="Le regard du média."), slot="p2"))
    assert not _hard("prismes", _with("prismes", "p3"), slot="p3")


def test_accusing_and_blaming_words_are_refused_outside_guillemets_only():
    assert any("oublie" in e for e in _p2(head1="L'article oublie l'offre"))
    assert any("ne dit pas" in e for e in _hard("position", _with("position", lead="L'article ne dit pas pourquoi.")))
    assert any("biais" in e for e in _hard("position", _with("position", card1="Cause | Un biais net.")))
    assert any("manipulation" in e for e in _hard("hook", _with("hook", title="Une manipulation du logement ?")))
    for word in ("ignore", "omet", "néglige", "mensonge", "trompeur"):
        assert any(word in e for e in _p2(answer2=f"Quand il {word} la crise, les prix montent.")), word
        assert any(word in e for e in _p2(lead=f"Ce qu'il {word}")), word
        assert any(word in e for e in _hard("tensions", _with("tensions", head2=f"Il {word} cela ; non"))), word
        assert any(word in e for e in _hard("limites", _with("limites", claim3=f"Il {word} plus cela ?"))), word
        assert any(word in e for e in _hard("limites", _with("limites", lead=f"Ce qu'il {word}"))), word
        assert any(word in e for e in _p2(indice1=f"INE | ce que l'article {word}")), word
    assert not _p2(head1="Le texte dit « l'article oublie »")


def test_prescriptive_verbs_are_refused_on_the_tensions_and_the_limites_title_and_heads():
    """On the tensions every field; on the limites its title and heads (its questions may quote what one « doit »
    know); never on the prism slides."""
    for verb in ("il faut", "doit", "doivent", "devrait", "devraient", "il faudrait", "faut-il"):
        for name in ("title", "lead", "head1", "claim2"):
            value = {"title": f"Ce qu'{verb} bâtir", "lead": f"Ce qu'{verb} bâtir",
                     "head1": f"Ce qu'{verb} bâtir ; non", "claim2": f"Que {verb} bâtir de plus ?"}[name]
            assert any("prescriptive" in e and f"tensions.{name}" in e
                       for e in _hard("tensions", _with("tensions", **{name: value}))), (verb, name)
        assert any("prescriptive" in e for e in _hard("tensions", _with("tensions", indice3=f"INE | ce qu'on {verb} bâtir"))), verb
        assert any("prescriptive" in e and "limites.head2" in e
                   for e in _hard("limites", _with("limites", head2=f"L'État {verb} agir"))), verb
        assert any("prescriptive" in e and "limites.title" in e
                   for e in _hard("limites", _with("limites", title=f"Qui {verb} trancher"))), verb
        assert not any("prescriptive" in e for e in _p2(head2=f"L'État {verb} agir"))
    assert not _hard("tensions", FIELDS["tensions"]) and not _hard("limites", FIELDS["limites"])


def test_a_digit_in_a_card_is_refused_unless_it_is_a_year_a_date_or_a_reference():
    digit = lambda errors: [e for e in errors if "digit" in e]  # noqa: E731
    for ok in ("Le plafond date de 2024", "Le mouvement du 15 mai 2011", "La loi 12/2023", "Le décret du 1er janvier"):
        assert not digit(_p2(head1=ok)), ok
        assert not digit(_p2(answer1=ok + ", donc les prix montent.")), ok
        assert not digit(_hard("tensions", _with("tensions", head1=ok + " ; non"))), ok
        assert not digit(_hard("limites", _with("limites", head2=ok))), ok
    for bad in ("Il manque 600 000 logements", "Les loyers montent de 12 %", "Le 15-M rassemble", "Une loi de 2100"):
        assert any("prismes.head1 holds a digit" in e for e in _p2(head1=bad)), bad
        assert any("prismes.answer1 holds a digit" in e for e in _p2(answer1=bad + ", donc les prix montent.")), bad
        assert any("prismes.lead holds a digit" in e for e in _p2(lead=bad)), bad
        assert any("tensions.claim3 holds a digit" in e for e in _hard("tensions", _with("tensions", claim3=bad + " ?"))), bad
        assert any("tensions.lead holds a digit" in e for e in _hard("tensions", _with("tensions", lead=bad))), bad
        assert any("limites.head1 holds a digit" in e for e in _hard("limites", _with("limites", head1=bad))), bad


def test_an_indice_needs_a_source_and_what_to_find():
    for bad in ("Banque d'Espagne", " | ses estimations", "Banque d'Espagne | ", "|"):
        assert any("prismes.indice2" in e and "source | find" in e for e in _p2(indice2=bad)), bad
        assert any("tensions.indice1" in e and "source | find" in e
                   for e in _hard("tensions", _with("tensions", indice1=bad))), bad
        assert any("limites.indice3" in e and "source | find" in e
                   for e in _hard("limites", _with("limites", indice3=bad))), bad
    assert not _p2(indice2="Banque d'Espagne | ses estimations du déficit")


def test_an_indice_refuses_a_url_a_bare_domain_and_a_figure():
    for clue in ("https://ine.es | les séries", "www.ine.es | les séries", "INE | les séries sur ine.es",
                 "idealista.com | les annonces", "Insee.fr | la série", "who.int | la base", "data.gov | la base"):
        assert any("prismes.indice1" in e and "URL" in e for e in _p2(indice1=clue)), clue
        assert any("URL" in e for e in _hard("tensions", _with("tensions", indice2=clue))), clue
        assert any("URL" in e for e in _hard("limites", _with("limites", indice1=clue))), clue
    for clue in ("INE | les 12 % de logements vides", "INE 2 | les séries", "Eurostat | un écart de 3 points"):
        assert any("prismes.indice1 holds a digit" in e for e in _p2(indice1=clue)), clue
    for clue in ("INE | le recensement de 2021", "Insee | les séries depuis le 1er janvier", "Cour des comptes | son rapport"):
        assert not _p2(indice1=clue), clue


def test_the_tension_pairs_are_the_three_pairs():
    assert not _hard("tensions", FIELDS["tensions"])
    assert not _hard("tensions", _with("tensions", pair1="2,3", pair3="1,2"))        # any order of the cards
    assert not _hard("tensions", _with("tensions", pair1="2, 1"))                    # either way round


def test_a_pair_that_repeats_or_is_missing_is_refused():
    for kw in ({"pair2": "1,2"}, {"pair3": "2,1"}, {"pair1": "1,1"}, {"pair2": "1,4"}, {"pair1": "1"},
               {"pair1": "1 et 2"}, {"pair3": "1,2,3"}):
        assert any("tensions" in e and "pair" in e for e in _hard("tensions", _with("tensions", **kw))), kw
    assert any("tensions.pair3 is empty" == e for e in _hard("tensions", _with("tensions", pair3="")))


def test_position_and_media_note_are_exempt_from_the_digit_rule():
    assert not _hard("position", _with("position", card1="Ce qu'il raconte | 175 000 manifestants."))
    assert not _hard("prismes", _with("prismes", "p1", media_note="L'article chiffre 175 000 personnes."), slot="p1")


def test_the_axe_question_is_digit_checked_like_a_card():
    assert not _hard("axe", _with("axe", question="Pourquoi les loyers ont-ils doublé depuis 2015 ?"))
    assert any("axe.question" in e and "digit" in e for e in _hard("axe", _with("axe", question="Pourquoi 12 % des loyers montent-ils ?")))


def test_an_axe_with_no_dominant_prism_is_a_flag_not_a_hard_error():
    fields = _with("axe", media_grounding="Aucun prisme ne domine : le texte mêle politique et économie.")
    hard, flags = _fe("axe", fields)
    assert hard == [] and any("dominate" in f for f in flags)
    assert not any("dominate" in f for f in _flags("axe", FIELDS["axe"]))


def test_a_card_sharing_no_key_word_with_the_axe_question_is_flagged():
    """The axe asks « D'où vient la crise du logement en Espagne ? »: a card whose head and answer (head and claim on the
    tensions and the limites) never name it drifts."""
    hard, flags = _fe("prismes", _with("prismes", "p2", head2="Les pommes mûrissent tard",
                                       answer2="Quand l'été tarde, les poires suivent."), slot="p2")
    assert hard == [] and any(f.startswith("prismes.card2 shares no key word") for f in flags)
    assert not [f for f in flags if "card1" in f or "card3" in f]
    flags = _flags("tensions", _with("tensions", head3="Les pommes mûrissent ; les poires attendent",
                                     claim3="Lequel mûrit plus tôt ?"))
    assert any(f.startswith("tensions.card3 shares no key word") for f in flags)
    flags = _flags("limites", _with("limites", head1="Les vergers restent hors champ", claim1="Les pommes sont-elles plus chères ?"))
    assert any(f.startswith("limites.card1 shares no key word") for f in flags)
    closing = _with("axe", closing="Politique, économique, juridique : que manque-t-il au tableau ?")
    assert any("axe.closing" in f and "key word" in f for f in _flags("axe", closing))
    assert not any("axe.closing" in f and "key word" in f for f in _flags("axe", FIELDS["axe"]))


def test_two_near_identical_cards_of_one_slide_are_flagged():
    p2 = FIELDS["prismes"]["p2"]
    twin = _with("prismes", "p2", head3=p2["head1"], answer3=p2["answer1"])
    assert any("card1" in f and "card3" in f and "near" in f for f in _flags("prismes", twin, slot="p2"))
    t = FIELDS["tensions"]
    assert any("near" in f for f in _flags("tensions", _with("tensions", head2=t["head1"], claim2=t["claim1"])))
    lim = FIELDS["limites"]
    assert any("near" in f for f in _flags("limites", _with("limites", head3=lim["head2"], claim3=lim["claim2"])))
    assert not [f for f in _flags("prismes", p2, slot="p2") if "near" in f]


def test_two_near_identical_prism_slides_are_flagged():
    frags = _fragments()
    twin = copy.deepcopy(FIELDS["prismes"]["p2"])
    frags["prismes"] = agent.to_fragment(agent.STEP_BY_NAME["prismes"],
                                         [_opt(FIELDS["prismes"]["p1"], "p1"), _opt(twin, "p2")], frags)
    same = _flags("prismes", twin, slot="p3", frags=frags)
    assert any("near" in f and "p2" in f for f in same)
    assert not [f for f in _flags("prismes", FIELDS["prismes"]["p3"], slot="p3") if "near" in f]


def test_a_closing_line_with_ou_is_flagged_not_blocked_and_a_card_title_is_not():
    hard, flags = _fe("axe", _with("axe", closing="Politique, économique ou juridique : que manque-t-il pour comprendre la crise ?"))
    assert hard == [] and any("« ou »" in f for f in flags)
    assert not any("« ou »" in f for f in _flags("axe", FIELDS["axe"]))
    for step in ("tensions", "limites"):
        hard, flags = _fe(step, _with(step, title="Plafonner ou bâtir"))
        assert hard == [] and not any("« ou »" in f for f in flags), step


def test_a_closing_line_that_ranks_the_regards_is_flagged():
    flags = _flags("axe", _with("axe", closing="Entre le politique, l'économique et le juridique, "
                                                "quel regard explique le mieux la crise du logement ?"))
    assert any("axe.closing" in f and "rank" in f for f in flags)
    assert not [f for f in _flags("axe", FIELDS["axe"]) if "rank" in f]


def test_a_quoted_passage_of_the_position_or_the_media_note_must_be_in_the_source():
    fields = _with("position", card2="Ses causes | « Un manque de logements sociaux » pèse.")
    assert not [f for f in _flags("position", fields, article=ARTICLE) if "quote" in f]
    fields = _with("position", card2="Ses causes | « Un excès de touristes » pèse.")
    assert any("position.card2" in f and "word for word" in f for f in _flags("position", fields, article=ARTICLE))
    assert not _hard("position", fields, article=ARTICLE)
    assert not [f for f in _flags("position", fields) if "word for word" in f]
    note = _with("prismes", "p1", media_note="Il parle d'« un plafond inventé ».")
    assert any("media_note" in f and "word for word" in f for f in _flags("prismes", note, slot="p1", article=ARTICLE))


def test_the_closing_line_missing_a_prism_name_is_flagged():
    assert not [f for f in _flags("axe", FIELDS["axe"]) if "name" in f and "closing" in f]
    flags = _flags("axe", _with("axe", closing="Entre le politique et l'économique, que manque-t-il pour comprendre la crise ?"))
    assert any("closing" in f and "juridique" in f.lower() for f in flags)


def test_the_hook_promise_with_another_subject_than_the_axe_is_flagged():
    flags = _flags("hook", _with("hook", promise="Trois regards sur les retraites ; à vous d'en juger."))
    assert any("subject" in f for f in flags)
    assert not [f for f in _flags("hook", FIELDS["hook"]) if "subject" in f]


def test_the_caption_needs_four_hashtags():
    assert any("hashtag" in e for e in _hard("writing", {"caption": "Un texte #un #deux"}))
    assert not [e for e in _hard("writing", FIELDS["writing"]) if "hashtag" in e]


def test_prompt_caps_cover_every_capped_field():
    caps = agent.prompt_caps()
    for (step, name), (_, cap) in agent._CAPS.items():
        assert caps[f"{step}.{name}"] == cap
    for (step, name), parts in agent._PART_CAPS.items():
        for part, cap in parts:
            assert caps[f"{step}.{name}.{part}"] == cap
    assert caps["axe.question"] == 60 and caps["prismes.indice.source"] == 30 and caps["tensions.head"] == 76
    assert agent.fill_caps("max {{cap:axe.question}} signes") == "max 60 signes"
    with pytest.raises(KeyError):
        agent.fill_caps("{{cap:nope.nope}}")


def test_the_removed_fields_have_no_cap_left():
    caps = agent.prompt_caps()
    for gone in ("prismes.question", "prismes.line1", "prismes.line", "prismes.source", "prismes.sources", "matrice.title",
                 "matrice.col.variable", "prismes.claim", "prismes.claim1", "arbitrage.title", "arbitrage.test",
                 "arbitrage.indice.find", "tensions.head_two_sides"):
        assert gone not in caps, gone
    for removed in ("matrice", "arbitrage"):
        assert not any(s == removed for s, _ in agent._CAPS) and not any(s == removed for s, _ in agent._PART_CAPS)
    assert not hasattr(agent, "_SOURCE_MAX") and not hasattr(agent, "_SOURCES_MAX") and not hasattr(agent, "_CONDITIONAL")


# ---- revision 3: leads, answering prism cards, two-sided tensions, discriminating claims, the limites ---------------

def test_a_tension_head_needs_two_sides_separated_by_a_semicolon():
    two = lambda v: [e for e in _hard("tensions", _with("tensions", head2=v)) if "two sides" in e]   # noqa: E731
    for bad in ("Le plafond réduit l'offre et protège le locataire",       # no « ; »
                "Le plafond réduit l'offre ; ",                            # an empty side
                " ; il protège le locataire",
                "Le plafond réduit l'offre ; il protège ; il coûte"):     # three parts
        assert any(e.startswith("tensions.head2") for e in two(bad)), bad
    assert not two("Le plafond réduit l'offre ; il protège le locataire")
    assert not two("Le plafond réduit l'offre ; il protège le locataire")   # French typography
    assert not [e for e in _p2(head2="Un loyer ; un salaire") if "two sides" in e]      # the tensions only


_GENERIC = ["Le marché explique-t-il la crise ?", "Les votes pèsent-ils sur la crise du logement ?",
            "La loi nourrit-elle la crise ?", "Le tourisme cause-t-il le problème ?",
            "Les régions influencent-elles la situation ?", "La rue pèse-t-elle sur la crise du logement ?",
            "Les loyers expliquent-ils la crise ?"]
_DISCRIMINATING = ["Les loyers montent-ils plus vite là où le logement social est rare ?",
                   "Expulse-t-on moins dans les zones tendues ?", "Bâtit-on plus là où la majorité est stable ?",
                   "Le marché explique-t-il plus les loyers que la loi ?"]


def test_the_generic_claim_pattern_is_refused_but_a_discriminating_claim_passes():
    for step in ("tensions", "limites"):
        for claim in _GENERIC:
            assert any(e.startswith(f"{step}.claim1") and "generic" in e
                       for e in _hard(step, _with(step, claim1=claim))), (step, claim)
        for claim in _DISCRIMINATING:
            assert not [e for e in _hard(step, _with(step, claim1=claim)) if "generic" in e], (step, claim)


def test_a_prism_answer_is_a_sentence_not_a_question():
    assert any(e.startswith("prismes.answer3") and "not a question" in e
               for e in _p2(answer3="Le meublé touristique pousse-t-il les prix ?"))
    assert any(e.startswith("prismes.answer3 holds a digit")
               for e in _p2(answer3="Quand un logement sur dix est touristique, 12 % des loyers montent."))
    assert not _p2(answer3="Quand le meublé rapporte plus, des propriétaires retirent leur logement.")


def test_a_prism_answer_without_a_causal_link_is_flagged():
    flag = lambda v: [f for f in _flags("prismes", _with("prismes", "p2", answer2=v), slot="p2")   # noqa: E731
                      if f.startswith("prismes.answer2") and "causal" in f]
    assert flag("Le parc social espagnol est petit et les logements sont rares.")       # a fact, no mechanism
    for ok in ("Faute de logement social, les ménages modestes paient le prix du marché.",
               "Les ménages modestes se reportent sur le marché libre, ce qui pousse les prix.",
               "S'il manque de logements sociaux, les ménages modestes paient plus cher.",
               "Le manque de logement social entraîne un report sur le marché libre."):
        assert not flag(ok), ok


def test_a_prism_answer_that_restates_its_head_is_flagged():
    head = FIELDS["prismes"]["p2"]["head1"]                      # « Moins de logements que de ménages »
    flags = _flags("prismes", _with("prismes", "p2", answer1="Il y a donc moins de logements que de ménages."),
                   slot="p2")
    assert any(f.startswith("prismes.answer1") and "restates" in f for f in flags), (head, flags)
    assert not [f for f in _flags("prismes", FIELDS["prismes"]["p2"], slot="p2") if "restates" in f]


def test_a_claim_without_a_comparison_marker_is_flagged():
    for step in ("tensions", "limites"):
        flags = _flags(step, _with(step, claim2="Le logement social change-t-il la donne ?"))
        assert any(f.startswith(f"{step}.claim2") and "comparison" in f for f in flags), step
        for ok in ("Les loyers montent-ils plus là où l'offre manque ?", "Expulse-t-on moins en zone tendue ?",
                   "Les loyers montaient-ils avant les votes ?", "Les prix varient-ils selon la région ?"):
            assert not [f for f in _flags(step, _with(step, claim2=ok)) if "comparison" in f], (step, ok)


def test_a_vague_find_is_flagged():
    for step in ("tensions", "limites"):
        for vague in ("INE | les loyers", "INE | les études sur le contrôle des loyers"):   # short, or nothing to compare
            assert any(f.startswith(f"{step}.indice1") and "vague" in f
                       for f in _flags(step, _with(step, indice1=vague))), (step, vague)
        for precise in ("INE | l'évolution des loyers avant et après le plafond", "INE | les loyers par ville et par an",
                        "Eurostat | le taux d'effort des locataires en Espagne"):
            assert not [f for f in _flags(step, _with(step, indice1=precise)) if "vague" in f], (step, precise)


def test_two_heads_with_the_same_opening_are_flagged():
    """The « … font la crise » defect: two heads of one slide opening with the same word, or sharing the leading verb."""
    lim = _with("limites", head1="Les votes font la crise du logement", head2="Les prix font la crise du logement",
                head3="Un droit écrit fait peu")
    flags = _flags("limites", lim)
    assert any("card1" in f and "card2" in f and "same word" in f for f in flags)
    same_verb = _with("limites", head1="Les rapports de force font la crise", head2="Le marché font la loi")
    assert any("card1" in f and "card2" in f and "leading verb « font »" in f for f in _flags("limites", same_verb))
    answers = _with("prismes", "p2", answer1="Quand les ménages se multiplient, les prix montent.",
                    answer3="Quand le meublé rapporte plus, l'offre de logements recule.")
    assert any("card1" in f and "card3" in f and "same word" in f for f in _flags("prismes", answers, slot="p2"))
    t = _with("tensions", head1="Le vote décide de tout ; l'offre de logements manque",
              head3="Le plafond réduit l'offre ; il protège le locataire")
    assert any("card1" in f and "card3" in f and "same word" in f for f in _flags("tensions", t))
    for step in ("tensions", "limites"):
        assert not [f for f in _flags(step, FIELDS[step]) if "same word" in f or "leading verb" in f], step


def test_a_lead_is_required_except_on_the_media_slot_and_never_a_question():
    media = lambda **kw: _hard("prismes", _with("prismes", "p1", **kw), slot="p1")   # noqa: E731
    assert any(e.startswith("prismes.lead must be empty") for e in media(lead="Ce que les votes décident"))
    assert not media()
    assert any(e == "prismes.lead is empty" for e in _p2(lead=""))
    for step in ("tensions", "limites"):
        assert any(e == f"{step}.lead is empty" for e in _hard(step, _with(step, lead="")))
        assert any(e.startswith(f"{step}.lead") and "not a question" in e
                   for e in _hard(step, _with(step, lead="Que voit chaque regard ?")))
    assert any(e.startswith("prismes.lead") and "not a question" in e for e in _p2(lead="Qui construit ?"))
    assert any(e.startswith("prismes.lead is 61") for e in _p2(lead="x" * 61))


def test_a_title_or_lead_close_to_the_deck_question_is_flagged():
    question = FIELDS["axe"]["question"]                          # « D'où vient la crise du logement en Espagne ? »
    for step, name in (("tensions", "title"), ("tensions", "lead"), ("limites", "lead"), ("limites", "title")):
        flags = _flags(step, _with(step, **{name: "D'où vient la crise du logement en Espagne"}))
        assert any(f.startswith(f"{step}.{name}") and "deck's question" in f for f in flags), (step, name)
    assert any(f.startswith("tensions.title") and "deck's question" in f
               for f in _flags("tensions", _with("tensions", title=question)))
    flags = _flags("prismes", _with("prismes", "p2", lead="Ce qui vient de la crise du logement en Espagne"), slot="p2")
    assert any(f.startswith("prismes.lead") and "deck's question" in f for f in flags)
    assert not [f for f in _flags("prismes", FIELDS["prismes"]["p2"], slot="p2") if "deck's question" in f]


def test_the_subject_phrase_in_two_cards_of_a_slide_is_flagged():
    subject = FIELDS["axe"]["subject"]                            # « la crise du logement »
    twice = _with("limites", claim1=f"Les loyers montaient-ils avant {subject} ?",
                  claim3=f"Expulse-t-on moins depuis {subject} ?")
    assert any("limites" in f and "subject" in f for f in _flags("limites", twice))
    once = _with("limites", claim1=f"Les loyers montaient-ils avant {subject} ?")
    assert not [f for f in _flags("limites", once) if "subject" in f]
    p2 = _with("prismes", "p2", answer1=f"Quand les ménages se forment vite, {subject} s'aggrave.",
               answer2=f"Sans logement social, {subject} touche les modestes.")
    assert any("prismes" in f and "subject" in f for f in _flags("prismes", p2, slot="p2"))


def test_the_tensions_title_may_be_a_statement():
    for title in ("Plafonner ou bâtir : les regards s'opposent", "Trois désaccords sur le plafond"):
        hard, flags = _fe("tensions", _with("tensions", title=title))
        assert hard == [] and flags == [], (title, hard, flags)
    assert not _hard("tensions", _with("tensions", title="Où les regards divergent-ils ?"))   # a question still passes


def test_the_limites_has_three_cards_and_a_neutral_title():
    assert "head4" not in agent.LimitesOption.model_fields and "claim3" in agent.LimitesOption.model_fields
    assert len(_fragments()["limites"]["limites"]["cards"]) == 3
    for title in ("Quel regard pèse le plus ?", "Le meilleur des trois regards", "Le regard qui pèse le plus"):
        hard, flags = _fe("limites", _with("limites", title=title))
        assert hard == [] and any(f.startswith("limites.title") and "rank" in f for f in flags), title
    assert not [f for f in _flags("limites", FIELDS["limites"]) if "rank" in f]
    assert any("prescriptive" in e and "limites.head1" in e
               for e in _hard("limites", _with("limites", head1="L'État doit bâtir")))
    assert not [e for e in _hard("limites", FIELDS["limites"]) if "prescriptive" in e]


# ---- the cascade, the model call faked ---------------------------------------------------------------------------

def _schema_slots(schema: dict) -> list[str]:
    """The slots the response schema lets the model write (empty when the step has no slot)."""
    for d in schema.get("$defs", {}).values():
        slot = d.get("properties", {}).get("slot")
        if slot:
            return list(slot.get("enum") or [slot["const"]])
    return []


class FakeCalls:
    def __init__(self):
        self.labels, self.errors, self.messages, self.slots, self.no_api = [], {}, [], [], []

    def __call__(self, user_message, schema, validator, no_api=False, label="", system=None):
        self.labels.append(label)
        self.messages.append(user_message)
        self.no_api.append(no_api)
        call = len(self.labels)
        if label == "writing":
            data = copy.deepcopy(FIELDS["writing"])
        elif label == "prismes":
            slots = _schema_slots(schema)
            self.slots.append(slots)
            options = [{**copy.deepcopy(FIELDS["prismes"][s]), "slot": s, "reason": f"r{call}-{k}"}
                       for s in slots for k in range(3)]
            data = {"options": options, "recommended": [3 * i for i in range(len(slots))]}
        else:
            fields = FIELDS[label]
            data = {"options": [{**copy.deepcopy(fields), "reason": f"r{call}-{k}"} for k in range(3)],
                    "recommended": [0]}
        self.errors[label] = validator(data)
        return data


@pytest.fixture
def fake(monkeypatch):
    calls = FakeCalls()
    monkeypatch.setattr(agent, "_call_with_retry", calls)
    return calls


def _step_file(steps, name):
    return agent._load(steps, agent.STEP_BY_NAME[name])[0]


def _log(steps) -> list[dict]:
    return [json.loads(line) for line in (steps.parent / "choices.jsonl").read_text(encoding="utf-8").splitlines()]


def test_unattended_runs_seven_steps_and_rebuilds_the_deck(fake, tmp_path):
    pres = agent.adapt(full(), steps_dir=tmp_path / "adapt_steps")
    assert fake.labels == [s.name for s in agent.STEPS]
    assert all(e == [] for e in fake.errors.values()), fake.errors
    assert fake.slots == [["p1", "p2", "p3"]]
    assert pres.model_dump() == TroisRegardsPresentation.model_validate(DECK).model_dump()
    prismes = _step_file(tmp_path / "adapt_steps", "prismes")
    assert [o.id for o in prismes.options] == ["p1a", "p1b", "p1c", "p2a", "p2b", "p2c", "p3a", "p3b", "p3c"]
    assert prismes.recommended == prismes.picked == ["p1a", "p2a", "p3a"]
    assert [o.id for o in _step_file(tmp_path / "adapt_steps", "axe").options] == ["a", "b", "c"]


def test_guided_pauses_at_the_axe(fake, tmp_path, capsys):
    assert agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", guided=True) is None
    assert fake.labels == ["axe"]
    assert agent.pending_step(tmp_path / "adapt_steps") == "axe"
    assert "[axe]" in capsys.readouterr().out


def test_guided_shows_the_prism_options_one_block_per_slot(fake, tmp_path, capsys):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, stop_after="position")
    capsys.readouterr()
    assert agent.adapt(full(), steps_dir=steps, guided=True) is None
    out = capsys.readouterr().out
    assert agent.pending_step(steps) == "prismes"
    blocks = [out.index(f"[{s}]") for s in ("p1", "p2", "p3")]
    assert blocks == sorted(blocks)
    assert out.count("★") == 3 and "p2a — " in out and "p3c — " in out


def test_stop_after_a_step(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    assert agent.adapt(full(), steps_dir=steps, stop_after="prismes") is None
    assert fake.labels == ["axe", "position", "prismes"]
    assert not (steps / "4_tensions.json").exists() and (steps / "3_prismes.json").exists()


def test_a_later_step_receives_the_earlier_picks(fake, tmp_path):
    agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text="TEXTE-DE-L-ARTICLE", stop_after="prismes")
    first, _, third = fake.messages
    assert "CHOIX FIXÉS" not in first and "CATALOGUE DES PRISMES" in first
    fixed = third.split("CHOIX FIXÉS (ne les réécris pas) :")[1]
    assert FIELDS["axe"]["question"] in fixed and FIELDS["position"]["title"] in fixed
    assert "TEXTE-DE-L-ARTICLE" in third
    assert all(f"{s} = {p}" in third for s, p in zip(("p1", "p2", "p3"), ("politique", "economique", "juridique")))
    for private in ("review", "ethics", "blend", "distill", "guide"):
        assert f'"{private}"' not in third


def test_choose_on_prismes_needs_one_pick_per_slot(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    msg = "prismes: keep exactly one option per prism (p1, p2, p3)"
    with pytest.raises(agent.ChoiceError, match=re.escape(msg)):
        agent.choose(full(), steps, "prismes", ["p1a", "p1b", "p2a"], {})
    with pytest.raises(agent.ChoiceError, match=re.escape(msg)):
        agent.choose(full(), steps, "prismes", ["p1a", "p2a"], {})
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), steps, "prismes", ["p1a", "p2a", "p4a"], {})
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), steps, "axe", ["a", "b"], {})
    assert _step_file(steps, "prismes").picked == ["p1a", "p2a", "p3a"]       # a refused choice changes nothing
    edit = {"p2c.head1": "Les loyers devancent les salaires"}
    assert agent.choose(full(), steps, "prismes", ["p3b", "p1b", "p2c"], edit) == []
    sf = _step_file(steps, "prismes")
    assert sf.picked == ["p1b", "p2c", "p3b"]
    assert sf.fragment["prisms"][1]["cards"][0]["head"] == "Les loyers devancent les salaires"
    assert [s["prism"] for s in sf.fragment["prisms"]] == ["politique", "economique", "juridique"]


def test_choose_keeps_an_edited_pick_and_warns_on_a_broken_rule(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, guided=True)
    long_question = "D'où vient vraiment la crise du logement qui secoue toute l'Espagne ?"
    warnings = agent.choose(full(), steps, "axe", ["b"], {"b.question": long_question}, reason="plus large")
    assert any(w.startswith("axe.question is") for w in warnings)
    sf = _step_file(steps, "axe")
    assert sf.picked == ["b"] and sf.fragment["axe"]["question"] == long_question
    assert next(o for o in sf.options if o.id == "b").edited
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), steps, "axe", ["a"], {"a.nope": "x"})
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), steps, "writing", ["a"], {})


def test_more_with_a_slot_regenerates_only_that_slot(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = _step_file(steps, "prismes")
    stamp = (steps / "3_prismes.sha256").read_text()
    new = agent.more(full(), steps, "prismes", remark="plus concret", slot="p2")
    assert fake.slots[-1] == ["p2"] and "plus concret" in fake.messages[-1]
    keep = lambda sf: [o.model_dump() for o in sf.options if o.slot != "p2"]  # noqa: E731
    assert keep(new) == keep(before)
    p2 = [o for o in new.options if o.slot == "p2"]
    assert len(p2) == 3 and {o.id for o in p2}.isdisjoint({"p2a", "p2b", "p2c"})
    assert {o.id for o in new.rejected} == {"p2a", "p2b", "p2c"}
    assert new.picked == ["p1a", "p3a"] and set(new.recommended) == {"p1a", "p3a", p2[0].id}
    assert _step_file(steps, "prismes").model_dump() == new.model_dump()
    assert (steps / "3_prismes.sha256").read_text() == stamp
    assert agent.pending_step(steps) == "prismes"
    with pytest.raises(agent.ChoiceError):
        agent.more(full(), steps, "prismes", slot="p4")
    whole = agent.more(full(), steps, "prismes")
    assert fake.slots[-1] == ["p1", "p2", "p3"] and whole.picked == []
    assert len(whole.options) == 9 and {o.id for o in whole.options}.isdisjoint({o.id for o in new.options})
    agent.more(full(), steps, "prismes", slot="economique")             # the prism id the axe puts in p2
    assert fake.slots[-1] == ["p2"]


def _half(steps):
    """The prismes step after `choose p1b,p2a,p3c` then `more --prism p2`: p1b and p3c kept, p2 to pick."""
    agent.adapt(full(), steps_dir=steps)
    agent.choose(full(), steps, "prismes", ["p1b", "p2a", "p3c"], {})
    return agent.more(full(), steps, "prismes", slot="p2")


def test_after_more_on_one_prism_the_kept_picks_are_shown(fake, tmp_path, capsys):
    steps = tmp_path / "adapt_steps"
    new = _half(steps)
    out = agent.format_options(agent.STEP_BY_NAME["prismes"], new)
    kept = [line for line in out.splitlines() if "✔ gardée" in line]
    assert [line.split(" — ")[0] for line in kept] == ["p1b", "p3c"]
    assert "--pick" in out and "p2" in out.splitlines()[-1]          # says what is left to pick
    capsys.readouterr()
    agent.adapt(full(), steps_dir=steps, guided=True)               # the guided loop prints the same marks
    assert capsys.readouterr().out.count("✔ gardée") == 2


def test_after_more_on_one_prism_choose_takes_only_the_missing_slot(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    new = _half(steps)
    p2 = [o.id for o in new.options if o.slot == "p2"]
    for bad in ([], [p2[0], p2[1]], ["p9z"], ["p1a"]):              # zero, two for one slot, unknown, p2 still missing
        with pytest.raises(agent.ChoiceError):
            agent.choose(full(), steps, "prismes", bad, {})
    assert agent.choose(full(), steps, "prismes", [p2[1]], {}) == []
    sf = _step_file(steps, "prismes")
    assert sf.picked == ["p1b", p2[1], "p3c"] and all(s["title"] for s in sf.fragment["prisms"])
    assert agent.pending_step(steps) is None


def test_after_more_on_one_prism_naming_a_kept_slot_replaces_its_pick(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    new = _half(steps)
    p2 = next(o.id for o in new.options if o.slot == "p2")
    agent.choose(full(), steps, "prismes", ["p1a", p2], {})
    assert _step_file(steps, "prismes").picked == ["p1a", p2, "p3c"]


def test_a_fix_while_a_prism_awaits_its_pick_says_which_choose_to_run(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    new = _half(steps)
    p2 = [o.id for o in new.options if o.slot == "p2"]
    for field in ("prismes.p1.head1", "tensions.title", "limites.claim1"):
        with pytest.raises(agent.ChoiceError) as e:
            agent.fix(full(), steps, field, "Une ligne refaite.")
        msg = str(e.value)
        assert "choose" in msg and "prismes --pick" in msg and p2[0] in msg and "run `produce`" not in msg, msg


def test_changing_the_axe_makes_every_later_step_stale(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    agent.choose(full(), steps, "axe", ["a"], {})                 # the same pick: nothing changes
    agent.adapt(full(), steps_dir=steps)
    assert fake.labels == [s.name for s in agent.STEPS]
    agent.choose(full(), steps, "axe", ["b"], {"b.question": "Pourquoi le logement manque-t-il en Espagne ?"})
    with pytest.raises(agent.ChoiceError, match="stale"):
        agent.choose(full(), steps, "prismes", ["p1a", "p2a", "p3a"], {})
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels[len(agent.STEPS):] == ["position", "prismes", "tensions", "limites", "hook", "writing"]
    assert pres.axe.question == "Pourquoi le logement manque-t-il en Espagne ?"
    assert list(steps.glob("stale_*/3_prismes.json"))


def test_fix_rewrites_one_field_without_regenerating(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    assert agent.fix(full(), steps, "axe.question", "Pourquoi le logement manque-t-il en Espagne ?") == ("axe", [])
    assert agent.fix(full(), steps, "position.title", "Le logement, enjeu de scrutin") == ("position", [])
    assert agent.fix(full(), steps, "caption", DECK["caption"] + " Merci.")[0] == "writing"
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before                      # the later steps were re-stamped, not rerun
    assert pres.axe.question == "Pourquoi le logement manque-t-il en Espagne ?"
    assert pres.position.title == "Le logement, enjeu de scrutin" and pres.caption.endswith("Merci.")
    step, warnings = agent.fix(full(), steps, "hook.title", "x" * 75)
    assert step == "hook" and any("hook.title is 75" in w for w in warnings)
    step, warnings = agent.fix(full(), steps, "tensions.title", "Sur quoi divergent les regards ?")
    assert step == "tensions" and not [w for w in warnings if w.startswith("tensions")]
    _, warnings = agent.fix(full(), steps, "prismes.p2.media_note", "Une note.")   # a wording fix still checked
    assert any(w.startswith("p2: prismes.media_note must be empty") for w in warnings)
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before and pres.tensions.title == "Sur quoi divergent les regards ?"
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), steps, "invisible.statement", "x")


def test_fix_reaches_a_prism_field_by_slot(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    assert agent.fix(full(), steps, "prismes.p2.indice3", "Insee | les logements vacants, commune par commune") == ("prismes", [])
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before
    card = pres.prisms[1].cards[2]
    assert (card.source, card.find) == ("Insee", "les logements vacants, commune par commune")
    assert card.head == DECK["prisms"][1]["cards"][2]["head"]
    assert [c.model_dump(exclude={"claim"}) for c in pres.prisms[0].cards] == DECK["prisms"][0]["cards"]
    _, warnings = agent.fix(full(), steps, "prismes.p3.head2", "Plus de 300 collectifs")
    assert any(w.startswith("p3: prismes.head2 holds a digit") for w in warnings)
    with pytest.raises(agent.ChoiceError, match="prismes.p1.indice1"):
        agent.fix(full(), steps, "prismes.indice1", "x")
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), steps, "prismes.p4.head1", "x")
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), steps, "prismes.p2.line1", "x")          # a removed field


def test_fix_reaches_a_tensions_field(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    head = "Les partis tranchent au vote ; la loi répartit les compétences"
    assert agent.fix(full(), steps, "tensions.head2", head) == ("tensions", [])
    _, warnings = agent.fix(full(), steps, "tensions.pair3", "1,2")
    assert any("pair" in w for w in warnings)                     # still checked, still kept
    agent.fix(full(), steps, "tensions.pair3", "3,2")
    _, warnings = agent.fix(full(), steps, "tensions.head1", "Les partis contre le marché")
    assert any(w.startswith("tensions.head1") and "two sides" in w for w in warnings)
    agent.fix(full(), steps, "tensions.head1", FIELDS["tensions"]["head1"])
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before
    assert pres.tensions.cards[1].head == head and pres.tensions.cards[2].pair == [2, 3]


def test_fix_reaches_a_limites_field(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    claim = "Les loyers grimpaient-ils avant les votes ?"
    assert agent.fix(full(), steps, "limites.claim1", claim)[0] == "limites"
    _, warnings = agent.fix(full(), steps, "limites.title", "Il faut trancher")
    assert any("limites.title is prescriptive" in w for w in warnings)
    _, warnings = agent.fix(full(), steps, "limites.claim2", "Le marché explique-t-il la crise ?")
    assert any(w.startswith("limites.claim2") and "generic" in w for w in warnings)
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before
    assert pres.limites.cards[0].claim == claim and pres.limites.title == "Il faut trancher"
    assert pres.limites.cards[1].claim == "Le marché explique-t-il la crise ?"


def test_the_choice_log_records_picks_edits_and_fixes(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    agent.choose(full(), steps, "prismes", ["p1b", "p2a", "p3a"], {"p1b.title": "Qui décide ?"}, reason="plus court")
    new = agent.more(full(), steps, "prismes", remark="autre angle", slot="p3")
    with pytest.raises(agent.ChoiceError):          # the p3 pick went with its options: nothing to fix yet
        agent.fix(full(), steps, "prismes.p2.head1", "Une ligne refaite.")
    agent.choose(full(), steps, "prismes", ["p1b", "p2a", new.recommended[-1]], {})
    agent.fix(full(), steps, "prismes.p2.head1", "Une ligne refaite.")
    pick, more, _, fix = _log(steps)
    assert pick["event"] == "pick" and pick["step"] == "prismes" and pick["picked"] == ["p1b", "p2a", "p3a"]
    assert pick["edits"] == {"p1b.title": "Qui décide ?"} and pick["reason"] == "plus court"
    assert {"id": "p2b", "slot": "p2", "text": FIELDS["prismes"]["p2"]["title"]} in pick["offered"]
    assert more == {**more, "event": "more", "step": "prismes", "remark": "autre angle", "slot": "p3"}
    assert fix == {**fix, "event": "fix", "step": "prismes", "field": "prismes.p2.head1",
                   "before": FIELDS["prismes"]["p2"]["head1"], "after": "Une ligne refaite."}


def test_no_api_runs_through_the_same_path(fake, tmp_path):
    pres = agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", no_api=True)
    assert fake.labels == [s.name for s in agent.STEPS] and all(fake.no_api)
    assert pres.tensions.title == DECK["tensions"]["title"] and pres.limites.title == DECK["limites"]["title"]


_LATER = ["position", "prismes", "tensions", "limites", "hook", "writing"]


def _fresh(steps, name) -> bool:
    """The step's saved stamp equals the one its earlier saved fragments give."""
    base = agent.base_inputs(full(), None)
    st = agent.STEP_BY_NAME[name]
    frags = [_step_file(steps, s.name).fragment for s in agent.STEPS if s.n < st.n]
    return (steps / f"{st.n}_{st.name}.sha256").read_text() == agent.stamp_for(base, frags)


def test_a_fix_of_an_axe_prism_leaves_the_later_steps_stale_and_they_rerun(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    n = len(fake.labels)
    owner, warnings = agent.fix(full(), steps, "axe.prism2", "sociologique")
    assert owner == "axe" and any("regenerated" in w for w in warnings)
    assert _step_file(steps, "axe").fragment["axe"]["prisms"] == ["politique", "sociologique", "juridique"]
    assert not any(_fresh(steps, s) for s in _LATER)
    # never relabelled: the old p2 text keeps its old prism id until it is regenerated
    assert _step_file(steps, "prismes").fragment["prisms"][1]["prism"] == "economique"
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels[n:] == _LATER
    assert "p2 = sociologique" in fake.messages[n + 1]            # the prism slides were written for the new prism
    assert pres.prisms[1].prism == "sociologique" and pres.matrix is None


def test_a_fix_of_the_axe_media_leaves_the_later_steps_stale_and_they_rerun(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    n = len(fake.labels)
    _, warnings = agent.fix(full(), steps, "axe.media", "economique")
    assert any("regenerated" in w for w in warnings)
    assert not any(_fresh(steps, s) for s in _LATER)
    assert _step_file(steps, "prismes").fragment["prisms"][0]["media_note"]      # untouched until the rerun
    agent.adapt(full(), steps_dir=steps)
    assert fake.labels[n:] == _LATER
    _, warnings = agent.fix(full(), steps, "axe.prism1", "economique")             # the hard rules still run
    assert any("three prisms must be distinct" in w for w in warnings)


def test_a_wording_fix_on_the_axe_keeps_already_stale_later_steps_stale(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    n = len(fake.labels)
    agent.choose(full(), steps, "axe", ["b"], {"b.prism2": "sociologique"})
    agent.fix(full(), steps, "axe.question", "Pourquoi le logement manque-t-il en Espagne ?")
    assert not any(_fresh(steps, s) for s in _LATER)
    assert _step_file(steps, "prismes").fragment["prisms"][1]["prism"] == "economique"   # not rebuilt
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels[n:] == _LATER
    assert pres.axe.question == "Pourquoi le logement manque-t-il en Espagne ?" and pres.prisms[1].prism == "sociologique"


def test_a_wording_fix_on_a_later_step_still_restamps_without_a_model_call(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    agent.fix(full(), steps, "position.title", "Le logement, enjeu de scrutin")
    assert all(_fresh(steps, s) for s in _LATER)
    agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before


def _write_step(steps, name: str, n: int, fields: dict, stamp: str) -> None:
    """An older step file as the previous step table wrote it: `<n>_<name>.json` and its stamp."""
    sf = agent.StepFile(step=name, options=[Option(id="a", slot="a", reason="r", fields=fields)],
                        recommended=["a"], picked=["a"], fragment={"x": 1})
    (steps / f"{n}_{name}.json").write_text(sf.model_dump_json(indent=2), encoding="utf-8")
    (steps / f"{n}_{name}.sha256").write_text(stamp)


def test_an_old_adapt_steps_folder_with_4_matrice_json_does_not_crash_a_rerun(fake, tmp_path):
    """A folder written by the first step table: 3_prismes (question, lines, sources), 4_matrice, 5_hook, 6_writing.
    The old prism slides keep a stamp that still matches the axe and the position, but their option fields are not the
    current ones: they are retired like a stale step and rerun; the other old files are never read."""
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, stop_after="position")
    stamp = (steps / "2_position.sha256").read_text()
    prism_stamp = agent.stamp_for(agent.base_inputs(full(), None),
                                  [_step_file(steps, s).fragment for s in ("axe", "position")])
    old_prism = {"question": "D'où vient la crise ?", "line1": "a", "line2": "b", "line3": "c", "line4": "",
                 "sources": "INE ; Eurostat", "media_note": ""}
    sf = agent.StepFile(step="prismes", options=[Option(id=f"{s}a", slot=s, reason="r", fields=old_prism)
                                                 for s in ("p1", "p2", "p3")],
                        recommended=["p1a", "p2a", "p3a"], picked=["p1a", "p2a", "p3a"],
                        fragment={"prisms": [{"prism": "politique", "question": "?", "lines": ["a"], "sources": ["INE"]}]})
    (steps / "3_prismes.json").write_text(sf.model_dump_json(indent=2), encoding="utf-8")
    (steps / "3_prismes.sha256").write_text(prism_stamp)
    _write_step(steps, "matrice", 4, {"title": "Que mesurer ?", "col1": "a | b", "col2": "a | b", "col3": "a | b"}, stamp)
    _write_step(steps, "hook", 5, FIELDS["hook"], stamp)
    _write_step(steps, "writing", 6, FIELDS["writing"], stamp)
    assert agent.pending_step(steps) is None                      # the old files do not read as a pending step
    with pytest.raises(agent.ChoiceError, match="stale"):         # nor as a step one can still choose on
        agent.choose(full(), steps, "prismes", ["p1a", "p2a", "p3a"], {})
    n = len(fake.labels)
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels[n:] == ["prismes", "tensions", "limites", "hook", "writing"]
    assert pres.model_dump() == TroisRegardsPresentation.model_validate(DECK).model_dump()
    assert list(steps.glob("stale_*/3_prismes.json"))             # the old prism slides were retired
    assert (steps / "4_tensions.json").exists() and (steps / "6_hook.json").exists() and (steps / "7_writing.json").exists()
    assert agent.adapt(full(), steps_dir=steps).model_dump() == pres.model_dump()   # and the rerun is stable
    assert len(fake.labels) == n + 5


def test_an_old_adapt_steps_folder_with_5_arbitrage_json_does_not_crash_a_rerun(fake, tmp_path):
    """A folder written by the revision-2 step table: 3_prismes (cards with `claimN`, no lead), 4_tensions (no lead),
    5_arbitrage, 6_hook, 7_writing. The old prism slides and tensions keep a stamp that still matches the axe and the
    position, but their option fields are not the current ones: they are retired like a stale step and rerun; the
    arbitrage file is never read (the fifth step is `5_limites.json` now), and nothing crashes."""
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, stop_after="position")
    stamp = agent.stamp_for(agent.base_inputs(full(), None),
                            [_step_file(steps, s).fragment for s in ("axe", "position")])
    old_prism = {"title": "Un marché sous tension", **{f"head{k}": "Le loyer suit la rareté" for k in (1, 2, 3, 4)},
                 **{f"claim{k}": "Le loyer monte-t-il plus vite ?" for k in (1, 2, 3, 4)},
                 **{f"indice{k}": "INE | les loyers par ville" for k in (1, 2, 3, 4)}, "media_note": ""}
    sf = agent.StepFile(step="prismes", options=[Option(id=f"{s}a", slot=s, reason="r", fields=old_prism)
                                                 for s in ("p1", "p2", "p3")],
                        recommended=["p1a", "p2a", "p3a"], picked=["p1a", "p2a", "p3a"],
                        fragment={"prisms": [{"prism": "politique", "title": "t", "cards": []}]})
    (steps / "3_prismes.json").write_text(sf.model_dump_json(indent=2), encoding="utf-8")
    (steps / "3_prismes.sha256").write_text(stamp)
    old_tensions = {k: v for k, v in FIELDS["tensions"].items() if k != "lead"}
    _write_step(steps, "tensions", 4, old_tensions, stamp)
    _write_step(steps, "arbitrage", 5, {"title": "Quel regard pèse le plus ?",
                                        **{f"head{k}": "Les prix font la crise" for k in (1, 2, 3)},
                                        **{f"test{k}": "Les loyers baisseraient" for k in (1, 2, 3)},
                                        **{f"indice{k}": "INE | les loyers" for k in (1, 2, 3)}}, stamp)
    (steps / "5_arbitrage.verification.json").write_text("[]", encoding="utf-8")
    _write_step(steps, "hook", 6, FIELDS["hook"], stamp)
    _write_step(steps, "writing", 7, FIELDS["writing"], stamp)
    assert agent.pending_step(steps) is None                      # the old files do not read as a pending step
    for step, picks in (("prismes", ["p1a", "p2a", "p3a"]), ("tensions", ["a"])):
        with pytest.raises(agent.ChoiceError, match="stale"):     # nor as a step one can still choose on
            agent.choose(full(), steps, step, picks, {})
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), steps, "arbitrage.test1", "x")          # not a deck field any more
    n = len(fake.labels)
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels[n:] == ["prismes", "tensions", "limites", "hook", "writing"]
    assert pres.model_dump() == TroisRegardsPresentation.model_validate(DECK).model_dump()
    assert list(steps.glob("stale_*/3_prismes.json")) and list(steps.glob("stale_*/4_tensions.json"))
    assert (steps / "5_limites.json").exists() and (steps / "5_arbitrage.json").exists()   # left alone, never read
    assert agent.adapt(full(), steps_dir=steps).model_dump() == pres.model_dump()   # and the rerun is stable
    assert len(fake.labels) == n + 5


# ── Prompts ─────────────────────────────────────────────────────────────────

PROMPTS = Path("agent/prompts/trois_regards_steps")


def _prompt_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_every_step_has_its_prompt():
    files = [PROMPTS / "0_options.md", PROMPTS / "0_shared.md",
             *(PROMPTS / f"{s.n}_{s.name}.md" for s in agent.STEPS)]
    for f in files:
        assert f.exists(), f
        assert len(_prompt_text(f)) > 400, f"{f} is still a stub"


def test_the_shared_prompt_states_the_anti_goals():
    text = _prompt_text(PROMPTS / "0_shared.md").lower()
    for guard in ("reproche", "oublie", "inventée", "réelle", "prescri", "il faut", "ligne en trop"):
        assert guard in text, guard


def test_every_cap_placeholder_resolves():
    caps = agent.prompt_caps()
    for f in PROMPTS.glob("*.md"):
        for name in re.findall(r"\{\{cap:([\w.]+)\}\}", _prompt_text(f)):
            assert name in caps, f"{f.name}: {name}"
    for step in agent.STEPS:
        assert "{{" not in agent._prompt(step), step.name
        assert "{{" not in agent.fill_caps(_prompt_text(PROMPTS / "0_shared.md"))


def test_no_prompt_types_a_literal_cap():
    for f in PROMPTS.glob("*.md"):
        text = _prompt_text(f)
        assert not re.search(r"≤\s*\d", text), f.name
        assert not re.search(r"max(?:imum)? \d+ caractères", text), f.name
        assert not re.search(r"\b\d{2,3} (?:caractères|signes)", text), f.name


def test_the_prompts_name_the_exact_option_fields():
    for step in agent.STEPS:
        if step.option_model is None:
            continue
        text = _prompt_text(PROMPTS / f"{step.n}_{step.name}.md")
        for field in step.option_model.model_fields:
            assert f"`{field}`" in text, f"{step.name}: {field}"


def test_the_message_leaves_no_placeholder():
    msg = agent._message(agent.STEP_BY_NAME["prismes"], full(), _fragments(), "Texte.", [], [])
    assert "{{" not in msg and "CATALOGUE DES PRISMES" in msg


_BULLET = re.compile(r"^- `(\w+)` : (?:« (.*) »|`(.*)`)\s*$", re.M)


def _example(text: str) -> dict[str, str]:
    """The `- `field` : « value »` (or `` `value` ``, `` `""` `` for empty) bullets of one worked example."""
    out = {}
    for m in _BULLET.finditer(text):
        value = m.group(2) if m.group(2) is not None else m.group(3)
        out[m.group(1)] = "" if value == '""' else value
    out.pop("reason", None)
    return out


def _examples(name: str) -> list[tuple[str, dict[str, str]]]:
    """Each « Exemple … » section of a prompt: (its heading line, its fields)."""
    parts = re.split(r"^(Exemple.*)$", _prompt_text(PROMPTS / name), flags=re.M)[1:]
    return [(head, _example(body)) for head, body in zip(parts[::2], parts[1::2])]


def _worked() -> tuple[dict, dict]:
    """The worked examples of 1_axe … 6_hook, parsed from the prompt files: (the fragments they build, in step order;
    the example fields by (step, slot), slot « a » for a one-slot step). 3_prismes holds full prism slides (four cards,
    one of them the media's with its `media_note`), 4_tensions three cards (one per pair), 5_limites three cards."""
    def only(name):
        examples = _examples(name)
        assert len(examples) == 1, (name, [h for h, _ in examples])
        return examples[0][1]

    base: dict[tuple[str, str], dict] = {}
    axe = base[("axe", "a")] = only("1_axe.md")
    frags = {"axe": agent.to_fragment(agent.STEP_BY_NAME["axe"], [_opt(axe)], {})}
    pos = base[("position", "a")] = only("2_position.md")
    frags["position"] = agent.to_fragment(agent.STEP_BY_NAME["position"], [_opt(pos)], frags)
    prisms = []
    for head, fields in _examples("3_prismes.md"):
        slot, pid = re.search(r"emplacement (p\d) = `(\w+)`", head).groups()
        assert axe[f"prism{slot[1]}"] == pid, head
        assert set(fields) == set(agent.PrismesOption.model_fields), (head, set(fields) ^ set(agent.PrismesOption.model_fields))
        prisms.append(_opt(fields, slot))
        base[("prismes", slot)] = fields
    assert len(prisms) >= 2 and len({o.slot for o in prisms}) == len(prisms)
    assert [o.slot for o in prisms if o.fields["media_note"]] == [f"p{[axe[f'prism{i}'] for i in (1, 2, 3)].index(axe['media']) + 1}"]
    prisms.sort(key=lambda o: o.slot)                     # a prismes fragment is in slot order
    frags["prismes"] = agent.to_fragment(agent.STEP_BY_NAME["prismes"], prisms, frags)
    for name, step in (("4_tensions.md", "tensions"), ("5_limites.md", "limites")):
        fields = base[(step, "a")] = only(name)
        model = agent.STEP_BY_NAME[step].option_model
        assert set(fields) == set(model.model_fields), (step, set(fields) ^ set(model.model_fields))
        frags[step] = agent.to_fragment(agent.STEP_BY_NAME[step], [_opt(fields)], frags)
    base[("hook", "a")] = only("6_hook.md")
    return frags, base


def test_the_worked_examples_break_no_hard_rule_and_raise_no_flag():
    """The examples are what the model imitates: they keep every hard rule AND every advisory flag."""
    frags, base = _worked()
    for (step, slot), fields in base.items():
        earlier = {k: v for k, v in frags.items() if k != step} if step != "axe" else {}
        hard, flags = agent.field_errors(step, fields, earlier if step != "prismes" else frags, None, slot)
        assert hard == [] and flags == [], (step, slot, hard, flags)
    assert len(frags["tensions"]["tensions"]["cards"]) == 3 and len(frags["limites"]["limites"]["cards"]) == 3
    assert base[("hook", "a")]["title"] == base[("axe", "a")]["question"]
    assert all(c["head"].count(";") == 1 for c in frags["tensions"]["tensions"]["cards"])


# a good/bad pair line: « - BON `step[.slot].field` : « value » » or « - MAUVAIS (defect) `step[.slot].field` : « value » »
_PAIR_LINE = re.compile(r"^- (BON|MAUVAIS)(?: \(([^)]+)\))? `([\w.]+)` : « (.*) »\s*$", re.M)
# the defect a bad example names → the words of the rule message that catches it
_DEFECTS = {"fait au lieu de mécanisme": "causal link", "question générique": "generic", "indice vague": "vague",
            "répétition d'amorce": "same word", "une question": "not a question", "reprise de la tête": "restates",
            "un chiffre": "holds a digit", "sans comparaison": "comparison", "un seul côté": "two sides",
            "classement": "rank", "question du carrousel répétée": "deck's question", "reproche à l'article": "blames"}


def _pairs() -> list[tuple[str, str, str | None, str, str]]:
    """(file, kind, defect, field path, value) of every good/bad line of the prompt files."""
    return [(f.name, m.group(1), m.group(2), m.group(3), m.group(4))
            for f in sorted(PROMPTS.glob("*.md")) for m in _PAIR_LINE.finditer(_prompt_text(f))]


def test_the_worked_examples_good_ones_raise_nothing_and_bad_ones_the_expected_defect():
    """Each BON/MAUVAIS line rewrites one field of the step's worked example: the good one keeps it free of any hard
    error and any flag, the bad one raises the defect it names."""
    frags, base = _worked()
    pairs = _pairs()
    for fname, kind, defect, path, value in pairs:
        step, *rest = path.split(".")
        slot, field = (rest[0], rest[1]) if len(rest) == 2 else ("a", rest[0])
        fields = {**base[(step, slot)], field: value}
        assert field in base[(step, slot)], (fname, path)
        hard, flags = agent.field_errors(step, fields, frags, None, slot)
        if kind == "BON":
            assert defect is None and hard == [] and flags == [], (fname, path, value, hard, flags)
        else:
            assert defect in _DEFECTS, (fname, defect)
            assert any(_DEFECTS[defect] in m for m in hard + flags), (fname, path, defect, hard, flags)
    by_file = lambda name: {d for f, k, d, _, _ in pairs if f == name and k == "MAUVAIS"}   # noqa: E731
    assert {"fait au lieu de mécanisme", "question générique", "indice vague", "répétition d'amorce"} <= by_file("0_shared.md")
    assert {"une question", "reprise de la tête", "un chiffre"} <= by_file("3_prismes.md")
    assert "un seul côté" in by_file("4_tensions.md") and "classement" in by_file("5_limites.md")
    for fname, kind, _, path, _ in pairs:                 # every bad line has its good twin in the same file
        if kind == "MAUVAIS":
            assert (fname, "BON", path) in {(f, k, p) for f, k, _, p, _ in pairs}, (fname, path)


def test_the_examples_are_on_another_subject_than_the_spanish_article():
    """The sample deck's article is not the examples' subject: the model must not copy their wording into that deck."""
    every = " ".join(_prompt_text(f) for f in PROMPTS.glob("*.md"))
    for word in ("Espagne", "espagnol", "logement", "Radio-Canada", "Congrès", "loyer"):
        assert word.lower() not in every.lower(), word


def test_no_prompt_mentions_the_removed_fields():
    for f in PROMPTS.glob("*.md"):
        text = _prompt_text(f)
        low = text.lower()
        for gone in ("matrice", "line1", "line4", "`lines`", "sources à consulter", "column", "colonne", "variable | indicateur",
                     "`sources`", "`col1`", "prismes.question", "prismes.source}}", "arbitrage", "`test1`", "`test`",
                     "{{cap:arbitrage", "affiche d'elle-même la question"):
            assert gone not in low, (f.name, gone)
        if f.name != "2_position.md":                     # the position's last card may stay « au conditionnel »
            assert "conditionnel" not in low, f.name
    prismes = _prompt_text(PROMPTS / "3_prismes.md")
    assert "`question`" not in prismes                    # the prism slide has a thesis title now
    assert not re.search(r"`claim\d?`", prismes)          # the prism cards answer, they do not ask


def test_the_card_prompts_define_the_card_the_clue_and_the_two_sides():
    shared = _prompt_text(PROMPTS / "0_shared.md")
    for word in ("`head`", "`answer`", "`claim`", "`indice`", "`lead`", "source nommée | ce qu'on y lit", "URL",
                 "quatre mécanismes", "BON", "MAUVAIS"):
        assert word in shared, word
    tensions = _prompt_text(PROMPTS / "4_tensions.md")
    assert all(p in tensions for p in ("`1,2`", "`1,3`", "`2,3`", "« ; »"))
    limites = _prompt_text(PROMPTS / "5_limites.md").lower()
    assert "angles morts" in limites and "classement" in limites and "reproche" in limites
    assert "manque" in _prompt_text(PROMPTS / "1_axe.md")          # the closing line asks what is still missing


# ── the render ──────────────────────────────────────────────────────────────

import html  # noqa: E402
import random  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

from agent.trois_regards_prisms import PRISM_IDS, PRISMS  # noqa: E402
from renderer.instagram_carousel import trois_regards as renderer  # noqa: E402

_SLIDES = ["01_hook", "02_position", "03_prisme", "04_prisme", "05_prisme", "06_matrice", "07_cta"]


def _texts(paths) -> dict[str, str]:
    clean = lambda s: html.unescape(s).replace(" ", " ").replace(" ", " ").replace("⁠", "")   # noqa: E731
    # the body only: the shared stylesheets name `data-perch` too
    return {p.stem: clean(p.read_text(encoding="utf-8")).split("<body>", 1)[1] for p in paths}


def _render(tmp_path, deck: dict = DECK) -> dict[str, str]:
    doc = extract(full(), TroisRegardsPresentation.model_validate(deck))
    return _texts(renderer.generate_html(doc, tmp_path / "html"))


def test_an_older_deck_renders_seven_slides(tmp_path):
    texts = _render(tmp_path, DECK_V1)
    assert list(texts) == _SLIDES
    assert "Le logement, enjeu d'élection" in texts["02_position"] and "Ce que dit l'article" in texts["02_position"]
    for stem, prism in zip(("03_prisme", "04_prisme", "05_prisme"), DECK_V1["prisms"]):
        assert PRISMS[prism["prism"]].name in texts[stem] and prism["question"] in texts[stem]
        assert PRISMS[prism["prism"]].icon_svg in texts[stem]
        assert all(line in texts[stem] for line in prism["lines"]), stem
        assert " · ".join(prism["sources"]) in texts[stem]
    assert "Que mesurer pour trancher ?" in texts["06_matrice"] and DECK_V1["axe"]["question"] in texts["06_matrice"]


def test_the_position_kicker_defaults_and_the_cards_take_fixed_icons(tmp_path):
    from renderer.instagram_carousel._shared import ICONS
    deck = copy.deepcopy(DECK)
    deck["position"]["kicker"] = ""
    text = _render(tmp_path, deck)["02_position"]
    assert "Ce que dit l'article" in text
    positions = [text.index(ICONS[name]) for name in ("book", "link", "eye", "widen")]
    assert positions == sorted(positions)


def test_the_media_prism_slide_of_an_older_deck_carries_the_badge_and_the_others_do_not(tmp_path):
    texts = _render(tmp_path, DECK_V1)
    assert "Le regard du média" in texts["03_prisme"] and DECK_V1["prisms"][0]["media_note"] in texts["03_prisme"]
    assert "Le regard du média" not in texts["04_prisme"] and "Le regard du média" not in texts["05_prisme"]


def test_the_bird_perches_on_each_prism_title(tmp_path):
    texts = _render(tmp_path, DECK_V1)
    for stem in ("03_prisme", "04_prisme", "05_prisme"):
        assert texts[stem].count("data-perch") == 1
        assert re.search(r'<h1 class="head[^"]*"[^>]*data-perch', texts[stem]), stem


def test_the_matrix_of_an_older_deck_marks_the_media_column(tmp_path):
    text = _render(tmp_path, DECK_V1)["06_matrice"]
    cols = text.split('<div class="col')[1:]
    assert len(cols) == 3
    marked = [c for c in cols if "Le regard du média" in c]
    assert len(marked) == 1 and "Politique" in marked[0] and "data-perch" in marked[0]
    assert text.count("data-perch") == 1
    for col, c in zip(cols, DECK_V1["matrix"]["columns"]):
        assert PRISMS[c["prism"]].name in col and c["variable"] in col and c["indicator"] in col
        assert "Commence par" in col and "À suivre" in col


def test_the_cta_line_is_the_closing_question_lowercased(tmp_path):
    text = _render(tmp_path)["08_cta"]
    assert "— entre le politique, l'économique et le juridique, que manque-t-il pour comprendre la crise du logement ?" in text


def test_the_hook_promise_and_title_are_drawn(tmp_path):
    text = _render(tmp_path)["01_hook"]
    assert DECK["hook"]["title"] in text and DECK["hook"]["promise"] in text


def test_the_hook_promise_keeps_its_semicolon_on_the_line_and_the_title_its_hyphens(tmp_path):
    """The renderer puts a no-break space before « ; » (and « ? ») and word joiners around in-word hyphens."""
    deck = copy.deepcopy(DECK)
    deck["hook"]["title"] = "Le logement a-t-il mené aux urnes ?"
    doc = extract(full(), TroisRegardsPresentation.model_validate(deck))
    raw = (renderer.generate_html(doc, tmp_path / "html")[0]).read_text(encoding="utf-8")
    assert "logement\u00a0; à vous" in raw and "logement ; à vous" not in raw
    assert "a\u2060-\u2060t\u2060-\u2060il" in raw and "urnes\u00a0?" in raw


# ── the layout: every field at its cap still fits its lines and the slide ───

_POOL = ("le la les de des du un une et à au en par sur pour dans avec plus que qui "
         "logement logements gouvernement Parlement locataires propriétaires intergénérationnelle "
         "constitutionnelle décentralisation institutionnelles municipalités investissements "
         "démographiques recensement observatoire statistiques européennes ménages métropoles "
         "spéculation rénovation copropriétés expulsions coalitions majoritaire").split()
_SHORT = [w for w in _POOL if len(w) <= 6]       # ordinary words of a narrow grid cell (an average French word has about 5 letters)


def _chars(rng: random.Random, n: int, pool=None) -> str:
    """Random French-looking text of EXACTLY `n` characters, long words included: words while they fit,
    then a long word cut to the room left (or the last word stretched by a letter), so no field undershoots its cap.
    `pool` narrows the words."""
    pool = pool or _POOL
    out = ""
    while True:
        w = rng.choice(pool)
        if len((out + " " + w).strip()) > n:
            break
        out = (out + " " + w).strip()
    room = n - len(out) - (1 if out else 0)
    if room >= 1:
        out = (out + " " + rng.choice([w for w in pool if len(w) >= max(room, 10)] or ["x" * 12])[:room]).strip()
    elif len(out) < n:
        out += "s"
    assert len(out) == n, (out, n)
    return out


def _ask(rng: random.Random, n: int) -> str:
    return _chars(rng, n - 2) + " ?"


# the older deck shape (prism question, lines and sources, the matrix) is no longer written by the agent: its caps,
# kept here as they were, and a builder of its deck keep the older-deck layout test alive
_OLD_PRISM_CAPS = {("prismes", "question"): ("chars", 50), **{("prismes", f"line{i}"): ("chars", 80) for i in (1, 2, 3, 4)},
                   ("prismes", "media_note"): ("chars", 90)}
_OLD_CAPS = {**{k: v for k, v in agent._CAPS.items() if k[0] in ("axe", "position", "hook") and not k[1].startswith("v4_")},
             **_OLD_PRISM_CAPS, ("matrice", "title"): ("chars", 34)}
_OLD_PART_CAPS = {**{k: v for k, v in agent._PART_CAPS.items() if k[0] == "position"},
                  **{("matrice", f"col{i}"): (("variable", 60), ("indicator", 40)) for i in (1, 2, 3)}}
_OLD_SOURCE_MAX, _OLD_SOURCES_MAX = 30, 3


def worst_case_fields(seed: int = 0) -> dict:
    """Every older-shape field at its cap (four lines and three sources per prism); a « a | b » field
    takes each part at its cap. The three prisms and the media's one are drawn from the catalogue."""
    rng = random.Random(seed)
    cap = lambda step, name: _OLD_CAPS[(step, name)][1]   # noqa: E731
    text = lambda step, name: _chars(rng, cap(step, name))   # noqa: E731
    parts = lambda step, name: " | ".join(_chars(rng, c) for _, c in _OLD_PART_CAPS[(step, name)])   # noqa: E731
    prisms = rng.sample(PRISM_IDS, 3)
    media = rng.choice(prisms)
    axe = {"question": _ask(rng, cap("axe", "question")), "article_question": _ask(rng, 80),
           "subject": text("axe", "subject"), **{f"prism{i}": p for i, p in enumerate(prisms, 1)},
           "media": media, "media_grounding": text("axe", "media_grounding"), "closing": _ask(rng, cap("axe", "closing"))}
    position = {"kicker": text("position", "kicker"), "title": text("position", "title"), "lead": text("position", "lead"),
                **{f"card{i}": parts("position", f"card{i}") for i in (1, 2, 3, 4)}}
    source = lambda: _chars(rng, _OLD_SOURCE_MAX)   # noqa: E731
    prismes = {f"p{i}": {"question": _ask(rng, cap("prismes", "question")),
                         **{f"line{k}": text("prismes", f"line{k}") for k in (1, 2, 3, 4)},
                         "sources": " ; ".join(source() for _ in range(_OLD_SOURCES_MAX)),
                         "media_note": text("prismes", "media_note") if p == media else ""}
               for i, p in enumerate(prisms, 1)}
    matrice = {"title": _ask(rng, cap("matrice", "title")), **{f"col{i}": parts("matrice", f"col{i}") for i in (1, 2, 3)}}
    fixed = "Trois regards sur  ; à vous d'en juger."
    hook = {"title": _ask(rng, cap("hook", "title")),
            "promise": f"Trois regards sur {_chars(rng, cap('hook', 'promise') - len(fixed))} ; à vous d'en juger."}
    return {"axe": axe, "position": position, "prismes": prismes, "matrice": matrice, "hook": hook,
            "writing": FIELDS["writing"]}


def worst_case_deck(seed: int = 0) -> dict:
    """The older deck shape at its caps: axe, position, hook and caption through the agent, the prism lines and
    sources and the matrix built here."""
    fields = worst_case_fields(seed)
    frags: dict[str, dict] = {}
    for name in ("axe", "position", "hook", "writing"):
        frags[name] = agent.to_fragment(agent.STEP_BY_NAME[name], [_opt(fields[name])], frags)
    deck = agent.assemble(frags)
    ids = deck["axe"]["prisms"]
    deck["prisms"] = [{"prism": ids[i - 1], "question": f["question"],
                       "lines": [f[f"line{k}"] for k in (1, 2, 3, 4) if f[f"line{k}"]],
                       "sources": [x.strip() for x in f["sources"].split(";")],
                       **({"media_note": f["media_note"]} if f["media_note"] else {})}
                      for i, f in ((int(s[1]), f) for s, f in fields["prismes"].items())]
    m = fields["matrice"]
    deck["matrix"] = {"title": m["title"], "columns": [
        {"prism": ids[i - 1], **dict(zip(("variable", "indicator"), agent._parts(m[f"col{i}"], 2)))} for i in (1, 2, 3)]}
    return deck


def test_the_worst_case_fields_sit_exactly_at_their_caps():
    """The generator must not undershoot: every capped field, part and source name is at its cap exactly."""
    for seed in range(12):
        fields = worst_case_fields(seed)
        steps = [(st, f) for st in ("axe", "position", "matrice", "hook") for f in [fields[st]]]
        steps += [("prismes", f) for f in fields["prismes"].values()]
        for st, f in steps:
            for (cst, name), (_, cap) in _OLD_CAPS.items():
                if cst == st and (name != "media_note" or f.get(name)):
                    assert len(f[name]) == cap, (seed, st, name, len(f[name]), cap)
            for (cst, name), caps in _OLD_PART_CAPS.items():
                if cst == st:
                    assert [len(x) for x in agent._parts(f[name], len(caps))] == [c for _, c in caps], (seed, st, name)
            if st == "prismes":
                names = [x.strip() for x in f["sources"].split(";")]
                assert len(names) == _OLD_SOURCES_MAX and all(len(x) == _OLD_SOURCE_MAX for x in names)
        assert sum(bool(f["media_note"]) for f in fields["prismes"].values()) == 1
        TroisRegardsPresentation.model_validate(worst_case_deck(seed))


def test_the_worst_case_deck_breaks_no_hard_rule():
    """The steps the agent still writes (axe, position, hook) at their caps; the card steps below."""
    for seed in range(12):
        fields = worst_case_fields(seed)
        frags = {"axe": agent.to_fragment(agent.STEP_BY_NAME["axe"], [_opt(fields["axe"])], {})}
        for name in ("axe", "position", "hook"):
            assert agent.field_errors(name, fields[name], {} if name == "axe" else frags, None)[0] == [], (seed, name)


_LINES = """() => { const box = (s) => ['paddingTop', 'paddingBottom', 'borderTopWidth', 'borderBottomWidth']
    .reduce((a, k) => a + parseFloat(s[k]), 0);
  const n = (sel) => [...document.querySelectorAll(sel)].map(e => { const s = getComputedStyle(e);
    return Math.round((e.getBoundingClientRect().height - box(s)) / parseFloat(s.lineHeight)); });
  const bottom = Math.max(0, ...[...document.querySelectorAll('.stage *')].map(e => e.getBoundingClientRect().bottom));
  const cut = [...document.querySelectorAll('.col, .col *')]
    .filter(e => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1).map(e => e.className);
  return {head: n('.head'), lines: n('.ln-t'), badge: n('.badge'), title: n('.mh'), bottom, cut,
          page: document.documentElement.scrollWidth}; }"""


@pytest.mark.parametrize("seed", range(12))
def test_every_field_at_its_cap_fits_on_the_slide(tmp_path, seed):
    doc = extract(full(), TroisRegardsPresentation.model_validate(worst_case_deck(seed)))
    renderer.generate_html(doc, tmp_path)
    measured = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for f in sorted(tmp_path.glob("*.html")):
            page.set_content(f.read_text(encoding="utf-8"), wait_until="load")
            page.evaluate("document.fonts.ready")          # the web fonts change the line breaks
            measured[f.stem] = page.evaluate(_LINES)
        browser.close()
    assert list(measured) == _SLIDES
    for slide, m in measured.items():
        assert m["page"] <= 1080, (slide, "horizontal overflow", m["page"])
        assert m["bottom"] <= 1255, (slide, m["bottom"])
    assert all(n <= 2 for n in measured["02_position"]["title"]), ("position title", measured["02_position"]["title"])
    for slide in ("03_prisme", "04_prisme", "05_prisme"):
        m = measured[slide]
        assert len(m["head"]) == 1 and m["head"][0] <= 2, (slide, "the question takes more than two lines", m["head"])
        assert len(m["lines"]) == 4 and all(n <= 2 for n in m["lines"]), (slide, "a line takes more than two lines", m["lines"])
        assert all(n == 1 for n in m["badge"]), (slide, "the badge wraps", m["badge"])
    assert sum(len(measured[s]["badge"]) for s in ("03_prisme", "04_prisme", "05_prisme")) == 1
    assert measured["06_matrice"]["cut"] == [], ("a matrix cell is clipped", measured["06_matrice"]["cut"])
    assert len(measured["06_matrice"]["head"]) == 1 and measured["06_matrice"]["head"][0] <= 2


# ── four-card prism slides and the tensions (older decks keep their seven slides) ──

_PAIRS = [[1, 2], [1, 3], [2, 3]]


def test_the_new_caps_are_exposed_to_the_prompts():
    caps = agent.prompt_caps()
    assert caps["prismes.title"] == agent._CAPS[("prismes", "title")][1]
    for step, n in (("prismes", 4), ("tensions", 3), ("limites", 3)):
        for k in range(1, n + 1):
            assert f"{step}.head{k}" in caps and f"{step}.indice{k}.source" in caps and f"{step}.indice{k}.find" in caps
        assert f"{step}.lead" in caps
    assert "tensions.claim1" in caps and "limites.claim3" in caps and "limites.title" in caps and "prismes.answer4" in caps


def test_an_older_deck_still_loads_and_renders(tmp_path):
    pres = TroisRegardsPresentation.model_validate(DECK_V1)
    assert pres.tensions is None and pres.limites is None and pres.matrix is not None
    assert all(not s.cards and not s.title for s in pres.prisms)
    texts = _render(tmp_path, DECK_V1)
    assert list(texts) == _SLIDES
    assert all('class="card ln"' in texts[s] for s in ("03_prisme", "04_prisme", "05_prisme"))


def test_a_prism_slide_shows_its_title_and_four_cards_and_not_the_deck_question(tmp_path):
    texts = _render(tmp_path, DECK)
    for stem, s in zip(("03_prisme", "04_prisme", "05_prisme"), DECK["prisms"]):
        t = texts[stem]
        assert PRISMS[s["prism"]].name in t and PRISMS[s["prism"]].icon_svg in t
        assert not re.search(r'<h1[^>]*data-perch', t) and t.count("data-perch") == 1, stem
        assert t.split('class="card pc"')[1].lstrip('"').lstrip().startswith("data-perch"), stem
        title = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s["title"])
        assert title in t and DECK["axe"]["question"] not in t
        assert t.count('class="card pc"') == 4, stem
        heads = [t.index(c["head"]) for c in s["cards"]]
        assert heads == sorted(heads) and all(c["answer"] in t for c in s["cards"])
        assert 'class="card ln"' not in t


def test_the_media_prism_slide_keeps_the_badge_and_the_note_only_there(tmp_path):
    texts = _render(tmp_path, DECK)
    media = [s for s in DECK["prisms"] if s.get("media_note")]
    assert len(media) == 1
    for stem, s in zip(("03_prisme", "04_prisme", "05_prisme"), DECK["prisms"]):
        has = "Le regard du média" in texts[stem]
        assert has == (s is media[0]), stem
        if has:
            assert s["media_note"] in texts[stem]
    assert all("Le regard du média" not in texts[k] for k in ("06_tensions", "07_limites"))


def test_a_tension_card_is_tagged_with_its_two_prism_names(tmp_path):
    text = _render(tmp_path, DECK)["06_tensions"]
    names = [PRISMS[p].name for p in DECK["axe"]["prisms"]]
    cards = text.split('class="card pc"')[1:]
    assert len(cards) == 3
    assert DECK["tensions"]["title"] in text and DECK["axe"]["question"] not in text
    for card, c in zip(cards, DECK["tensions"]["cards"]):
        a, b = c["pair"]
        assert re.search(rf'<span class="tagk">{names[a - 1]} × {names[b - 1]}</span>', card), card[:300]
        assert c["head"] in card and c["claim"] in card
    assert "Économique × Juridique" in cards[2]   # drawn upper-case by .tagk
    assert text.count("data-perch") == 1


def test_the_clue_shows_the_source_in_bold_then_what_to_find(tmp_path):
    texts = _render(tmp_path, DECK)
    c = DECK["prisms"][1]["cards"][0]
    assert f"<strong>{c['source']}</strong> : {c['find']}" in texts["04_prisme"]
    t = DECK["tensions"]["cards"][2]
    assert f"<strong>{t['source']}</strong> : {t['find']}" in texts["06_tensions"]
    lim = DECK["limites"]["cards"][0]
    assert f"<strong>{lim['source']}</strong> : {lim['find']}" in texts["07_limites"]


# ── revision 3: slide 7 « Les angles morts » (`limites`), answering prism cards, a lead per slide, the bird on the
# first card, the first card at the same height on sibling slides ──

_SLIDES_V3 = ["01_hook", "02_position", "03_prisme", "04_prisme", "05_prisme", "06_tensions", "07_limites", "08_cta"]
_LATE = ("03_prisme", "04_prisme", "05_prisme", "06_tensions", "07_limites")
# the caps of the revision-3 slides
_V3_CAPS = {("prismes", "lead"), *(("prismes", f"answer{i}") for i in (1, 2, 3, 4)),
            ("tensions", "lead"), *(("tensions", f"head{i}") for i in (1, 2, 3)),
            ("limites", "title"), ("limites", "lead"),
            *(("limites", f"{k}{i}") for k in ("head", "claim") for i in (1, 2, 3))}


def _first_card(text: str) -> str:
    """The opening tag's attributes and the body of a slide's first card."""
    return text.split('class="card pc"')[1]


def test_a_v3_deck_validates():
    pres = TroisRegardsPresentation.model_validate(DECK)
    assert [p.prism for p in pres.prisms] == pres.axe.prisms == ["politique", "economique", "juridique"]
    assert all(p.title and len(p.cards) == 4 for p in pres.prisms)
    assert all(c.head and c.answer and c.source and c.find and not c.claim for p in pres.prisms for c in p.cards)
    assert [bool(p.lead) for p in pres.prisms] == [p.prism != pres.axe.media for p in pres.prisms]
    assert [p.prism for p in pres.prisms if p.media_note] == [pres.axe.media]
    assert pres.tensions.lead and [c.pair for c in pres.tensions.cards] == _PAIRS
    assert all(len([x for x in c.head.split(";") if x.strip()]) == 2 for c in pres.tensions.cards)
    assert pres.limites.title and pres.limites.lead and len(pres.limites.cards) == 3
    assert all(c.head and c.claim and c.source and c.find for c in pres.limites.cards)
    assert pres.matrix is None and "arbitrage" not in TroisRegardsPresentation.model_fields


def test_the_revision_3_caps_replace_the_revision_2_ones():
    for key in _V3_CAPS:
        assert key in agent._CAPS, key
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    assert cap("prismes", "lead") <= 60 and cap("tensions", "lead") <= 60 and cap("limites", "lead") <= 60
    assert all(cap("prismes", f"answer{i}") <= 90 for i in (1, 2, 3, 4))
    assert all(cap("tensions", f"head{i}") <= 76 for i in (1, 2, 3)) and cap("limites", "title") <= 34
    assert cap("prismes", "media_note") <= cap("prismes", "lead")         # the media's lead: one line too
    assert all(cap("limites", f"head{i}") <= 40 and cap("limites", f"claim{i}") <= 46 for i in (1, 2, 3))
    for i in (1, 2, 3):
        (s, src), (f, find) = agent._PART_CAPS[("limites", f"indice{i}")]
        assert (s, f) == ("source", "find") and src <= 30 and find <= 60
    # the revision-2 keys are gone: the prism cards answer, the arbitrage became the limites
    assert ("prismes", "claim1") not in agent._CAPS and ("arbitrage", "test1") not in agent._CAPS
    assert ("tensions", "head_two_sides") not in agent._CAPS


def test_the_v3_fixture_respects_the_caps_and_the_spec():
    p = TroisRegardsPresentation.model_validate(DECK)
    n = lambda s: len(s.replace("**", ""))   # noqa: E731
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    parts = lambda step, k: [c for _, c in agent._PART_CAPS[(step, f"indice{k}")]]   # noqa: E731
    question, subject = p.axe.question, p.axe.subject
    words = agent._key_words(question)
    no_digit = lambda s: all(re.fullmatch(r"(1[5-9]|20)\d\d", d) for d in re.findall(r"\d+", s))   # noqa: E731
    clue = lambda c, step, k: (n(c.source) <= parts(step, k)[0] and n(c.find) <= parts(step, k)[1] and c.source  # noqa: E731
                               and c.find and no_digit(c.source) and "http" not in c.source + c.find
                               and "www" not in c.source + c.find and not re.search(r"\.\w{2,3}\b", c.source))
    title_ok = lambda s: s != question and len(agent._key_words(s) & words) < 3 and no_digit(s)   # noqa: E731
    lead_ok = lambda s: title_ok(s) and not s.endswith("?")   # noqa: E731
    distinct_openings = lambda heads: len({h.split()[0].lower() for h in heads}) == len(heads)   # noqa: E731
    for s in p.prisms:
        assert n(s.title) <= cap("prismes", "title") and title_ok(s.title)
        if s.prism == p.axe.media:
            # the media's lead is its media_note: one line, at the lead's cap
            assert s.lead == "" and 0 < n(s.media_note) <= cap("prismes", "media_note") and lead_ok(s.media_note)
        else:
            assert 0 < n(s.lead) <= cap("prismes", "lead") and lead_ok(s.lead) and not s.media_note
        for k, c in enumerate(s.cards, 1):
            assert n(c.head) <= cap("prismes", f"head{k}") and n(c.answer) <= cap("prismes", f"answer{k}"), c
            assert "?" not in c.answer and clue(c, "prismes", k) and no_digit(c.head + c.answer + c.find), c
        assert distinct_openings([c.head for c in s.cards]) and distinct_openings([c.answer for c in s.cards]), s.prism
        assert sum(subject in (c.head + " " + c.answer).lower() for c in s.cards) <= 1, s.prism
    t = p.tensions
    assert n(t.title) <= cap("tensions", "title") and title_ok(t.title)
    assert 0 < n(t.lead) <= cap("tensions", "lead") and lead_ok(t.lead)
    for k, c in enumerate(t.cards, 1):
        sides = [x.strip() for x in c.head.split(";")]
        assert n(c.head) <= cap("tensions", f"head{k}") and len(sides) == 2 and all(sides), c
        assert not any(w in c.head.lower() for w in ("politique", "économique", "juridique")), c   # the tag names them
        assert n(c.claim) <= cap("tensions", f"claim{k}") and c.claim.endswith("?"), c
        assert clue(c, "tensions", k) and no_digit(c.head + c.claim + c.find), c
    lim = p.limites
    assert n(lim.title) <= cap("limites", "title") and lead_ok(lim.title)
    assert 0 < n(lim.lead) <= cap("limites", "lead") and lead_ok(lim.lead)
    for k, c in enumerate(lim.cards, 1):
        assert n(c.head) <= cap("limites", f"head{k}") and n(c.claim) <= cap("limites", f"claim{k}"), c
        assert c.claim.endswith("?") and clue(c, "limites", k) and no_digit(c.head + c.claim + c.find), c
    assert distinct_openings([c.head for c in lim.cards]) and distinct_openings([c.head for c in t.cards])
    # the prism answers vary their openings across the three slides too
    assert distinct_openings([c.answer for s in p.prisms for c in s.cards])
    for cards in (t.cards, lim.cards):
        assert distinct_openings([c.claim for c in cards])
        assert sum(subject in (c.head + " " + c.claim).lower() for c in cards) <= 1
        assert not any(re.search(r"(explique|pèse|nourrit|cause|influence)(nt)?(-t)?-(il|elle)s?\b", c.claim)
                       for c in cards)
    outside = re.sub(r"«[^»]*»", "", json.dumps(DECK, ensure_ascii=False).lower())
    for w in ("biais", "manipulation", "mensonge", "trompeur", "oublie", "ignore", "omet", "néglige", "ne dit pas",
              "ne disent pas", "il faut", "devrait", "doit", "font la crise", "pèse le plus", "quel regard"):
        assert not re.search(rf"\b{w}\b", outside), w


def test_a_v3_deck_renders_eight_slides(tmp_path):
    texts = _render(tmp_path, DECK)
    assert list(texts) == _SLIDES_V3
    assert "8 / 8" in texts["08_cta"] and "7 / 8" in texts["07_limites"]


def _revision_2_deck() -> dict:
    """A revision-2 deck as the sample was regenerated: prism cards that ask (`claim`, no `answer`), no lead, the
    arbitrage as slide 7 (`arbitrage`, no `limites`)."""
    deck = copy.deepcopy({k: v for k, v in DECK.items() if k != "limites"})
    for s in deck["prisms"]:
        s.pop("lead", None)
        s["cards"] = [{"head": c["head"], "claim": f"{c['head']} ?", "source": c["source"], "find": c["find"]}
                      for c in s["cards"]]
    deck["tensions"].pop("lead")
    deck["arbitrage"] = {"title": "Quel regard pèse le plus ?", "cards": [
        {"head": "Les prix font la crise", "test": "Les loyers baisseraient là où l'on bâtit", "source": "INE",
         "find": "les loyers par ville"} for _ in range(3)]}
    return deck


def test_a_revision_2_deck_with_arbitrage_loads_and_renders_seven_slides(tmp_path):
    """The `arbitrage` key is no longer read: the deck loads (the key is ignored), its prism cards draw their
    questions, and it renders seven slides — hook, position, three prisms, tensions, sign-off."""
    deck = _revision_2_deck()
    pres = TroisRegardsPresentation.model_validate(deck)
    assert pres.limites is None and not hasattr(pres, "arbitrage")
    assert all(c.claim and not c.answer for s in pres.prisms for c in s.cards)
    texts = _render(tmp_path, deck)
    assert list(texts) == ["01_hook", "02_position", "03_prisme", "04_prisme", "05_prisme", "06_tensions", "07_cta"]
    assert "7 / 7" in texts["07_cta"]
    assert all(c["claim"] in texts["03_prisme"] for c in deck["prisms"][0]["cards"])
    assert not any("Quel regard pèse le plus" in t or "Les loyers baisseraient" in t for t in texts.values())


def test_a_prism_card_draws_its_answer_and_falls_back_to_its_claim(tmp_path):
    deck = copy.deepcopy(DECK)
    deck["prisms"][1]["cards"][0]["claim"] = "Une question restée là ?"
    texts = _render(tmp_path, deck)
    for stem, s in zip(("03_prisme", "04_prisme", "05_prisme"), DECK["prisms"]):
        for c in s["cards"]:
            card = texts[stem]
            assert card.index(c["head"]) < card.index(c["answer"]) < card.index(c["source"]), c
    assert "Une question restée là ?" not in texts["04_prisme"]
    v2 = _revision_2_deck()                            # a revision-2 card has no answer: its claim is drawn
    texts = _render(tmp_path / "v2", v2)
    assert all(c["claim"] in texts["03_prisme"] for c in v2["prisms"][0]["cards"])


def test_the_limites_cards_are_tagged_with_the_axe_prism_names_in_order(tmp_path):
    from renderer.instagram_carousel._shared import ICONS
    text = _render(tmp_path, DECK)["07_limites"]
    assert "Les angles morts" in text and ICONS["eye_off"] in text
    assert DECK["limites"]["title"] in text and DECK["limites"]["lead"] in text
    cards = text.split('class="card pc"')[1:]
    assert len(cards) == 3
    for card, pid, c in zip(cards, DECK["axe"]["prisms"], DECK["limites"]["cards"]):
        assert f'<span class="tagk">{PRISMS[pid].name}</span>' in card
        assert card.index(c["head"]) < card.index(c["claim"]) < card.index(c["source"]), c
        assert f"<strong>{c['source']}</strong> : {c['find']}" in card


def test_the_prism_icons_are_drawn_untouched_on_the_limites(tmp_path):
    doc = extract(full(), TroisRegardsPresentation.model_validate(DECK))
    raw = [p for p in renderer.generate_html(doc, tmp_path / "html") if p.stem == "07_limites"][0].read_text(encoding="utf-8")
    drawn = re.sub(r"></(?:line|path|circle|rect)>", "/>", raw)
    for pid in DECK["axe"]["prisms"]:
        assert PRISMS[pid].icon_svg in drawn, pid


def test_no_slide_from_3_to_7_draws_the_deck_question(tmp_path):
    for k, deck in enumerate((DECK, DECK)):
        texts = _render(tmp_path / str(k), deck)
        for stem in texts:
            if stem[:2] in ("03", "04", "05", "06", "07"):
                assert deck["axe"]["question"] not in texts[stem], stem
        assert deck["axe"]["question"] in texts["01_hook"]


def test_each_slide_draws_its_own_lead_and_the_media_slide_draws_the_media_note(tmp_path):
    texts = _render(tmp_path, DECK)
    lead = lambda t: re.findall(r'<p class="ld">(.*?)</p>', t, re.S)   # noqa: E731
    for stem, s in zip(("03_prisme", "04_prisme", "05_prisme"), DECK["prisms"]):
        drawn = lead(texts[stem])
        assert len(drawn) == 1, stem
        if s["prism"] == DECK["axe"]["media"]:
            assert s["media_note"] in drawn[0] and "Le regard du média" in texts[stem]
        else:
            assert s["lead"] in drawn[0] and "Le regard du média" not in texts[stem]
    assert DECK["tensions"]["lead"] in lead(texts["06_tensions"])[0]
    assert DECK["limites"]["lead"] in lead(texts["07_limites"])[0]
    # the title sits above the lead, the lead above the first card
    t = texts["06_tensions"]
    assert t.index(DECK["tensions"]["title"]) < t.index(DECK["tensions"]["lead"]) < t.index('class="card pc"')
    # an empty lead draws no line
    deck = copy.deepcopy(DECK)
    deck["tensions"]["lead"] = deck["limites"]["lead"] = deck["prisms"][1]["lead"] = ""
    texts = _render(tmp_path / "empty", deck)
    assert not lead(texts["06_tensions"]) and not lead(texts["07_limites"]) and not lead(texts["04_prisme"])


def test_the_bird_perches_on_the_first_card_not_on_the_title(tmp_path):
    texts = _render(tmp_path, DECK)
    for stem in _LATE:
        t = texts[stem]
        assert t.count("data-perch") == 1 and not re.search(r"<h1[^>]*data-perch", t), stem
        first = _first_card(t)
        opening = first.split(">", 1)[0]
        assert "data-perch" in opening, stem
        # the first card takes no share of the room left (data-gap): it stays where the title block ends
        assert "data-gap" not in opening, stem
        assert first.split(">", 1)[1].lstrip().startswith('<img class="perch"'), stem


# the seeded worst case of the revision-3 fields

def _two_sides(rng: random.Random, n: int) -> str:
    """« a ; b » of EXACTLY `n` characters."""
    a = (n - 3) // 2
    return f"{_chars(rng, a)} ; {_chars(rng, n - 3 - a)}"


def worst_case_fields_v3(seed: int = 0) -> dict:
    """The revision-3 flat fields at their caps: per prism slot `title`, `lead` (empty on the media's slot, which carries
    a `media_note`), `head1…4`, `answer1…4`, `indice1…4` (each part at its cap); the tensions `title`, `lead`, `pair1…3`,
    `head1…3` (two sides « a ; b » at the head's cap), `claim1…3`, `indice1…3`; the limites `title`, `lead`, `head1…3`,
    `claim1…3`, `indice1…3`. The axe, the position and the hook are the older worst case's. The media's slide draws
    its `media_note` as its lead, one line at its cap."""
    rng = random.Random(2000 + seed)
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    text = lambda step, name: _chars(rng, cap(step, name))   # noqa: E731
    ask = lambda step, name: _ask(rng, cap(step, name))   # noqa: E731
    parts = lambda step, name: " | ".join(_chars(rng, c) for _, c in agent._PART_CAPS[(step, name)])   # noqa: E731
    base = worst_case_fields(seed)
    media = base["axe"]["media"]
    prismes = {}
    for i in (1, 2, 3):
        mine = base["axe"][f"prism{i}"] == media
        prismes[f"p{i}"] = {"title": text("prismes", "title"), "lead": "" if mine else text("prismes", "lead"),
                            **{f"head{k}": text("prismes", f"head{k}") for k in (1, 2, 3, 4)},
                            **{f"answer{k}": text("prismes", f"answer{k}") for k in (1, 2, 3, 4)},
                            **{f"indice{k}": parts("prismes", f"indice{k}") for k in (1, 2, 3, 4)},
                            # the media's slide draws its media_note as its lead: one line, at the lead's cap
                            "media_note": text("prismes", "media_note") if mine else ""}
    tensions = {"title": text("tensions", "title"), "lead": text("tensions", "lead"),
                **{f"pair{k}": ",".join(map(str, pair)) for k, pair in enumerate(_PAIRS, 1)},
                **{f"head{k}": _two_sides(rng, cap("tensions", f"head{k}")) for k in (1, 2, 3)},
                **{f"claim{k}": ask("tensions", f"claim{k}") for k in (1, 2, 3)},
                **{f"indice{k}": parts("tensions", f"indice{k}") for k in (1, 2, 3)}}
    limites = {"title": text("limites", "title"), "lead": text("limites", "lead"),
               **{f"head{k}": text("limites", f"head{k}") for k in (1, 2, 3)},
               **{f"claim{k}": ask("limites", f"claim{k}") for k in (1, 2, 3)},
               **{f"indice{k}": parts("limites", f"indice{k}") for k in (1, 2, 3)}}
    return {**base, "prismes": prismes, "tensions": tensions, "limites": limites}


def worst_case_deck_v3(seed: int = 0) -> dict:
    """The revision-3 deck at its caps, assembled by the agent from the flat fields."""
    return agent.assemble(_fragments(worst_case_fields_v3(seed)))


def test_the_v3_worst_case_fields_break_no_hard_rule():
    for seed in range(12):
        fields = worst_case_fields_v3(seed)
        frags = _fragments(fields)
        for slot, f in fields["prismes"].items():
            assert agent.field_errors("prismes", f, frags, None, slot)[0] == [], (seed, slot)
        for name in ("tensions", "limites"):
            assert agent.field_errors(name, fields[name], frags, None)[0] == [], (seed, name)


def test_the_v3_worst_case_fields_sit_exactly_at_their_caps():
    """Every field the revision-3 slides draw is at its cap exactly, each part of a clue too."""
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    for seed in range(12):
        f = worst_case_fields_v3(seed)
        for slot, p in f["prismes"].items():
            media = bool(p["media_note"])
            assert len(p["title"]) == cap("prismes", "title"), (seed, slot)
            assert len(p["lead"]) == (0 if media else cap("prismes", "lead")), (seed, slot)
            assert not media or len(p["media_note"]) == cap("prismes", "media_note")
            for k in (1, 2, 3, 4):
                assert len(p[f"head{k}"]) == cap("prismes", f"head{k}") and len(p[f"answer{k}"]) == cap("prismes", f"answer{k}")
                caps = agent._PART_CAPS[("prismes", f"indice{k}")]
                assert [len(x.strip()) for x in p[f"indice{k}"].split("|")] == [c for _, c in caps], (seed, slot, k)
        assert sum(bool(p["media_note"]) for p in f["prismes"].values()) == 1
        for step in ("tensions", "limites"):
            g = f[step]
            assert len(g["title"]) == cap(step, "title") and len(g["lead"]) == cap(step, "lead"), (seed, step)
            for k in (1, 2, 3):
                head_cap = cap(step, f"head{k}")
                assert len(g[f"head{k}"]) == head_cap and len(g[f"claim{k}"]) == cap(step, f"claim{k}"), (seed, step, k)
                caps = agent._PART_CAPS[(step, f"indice{k}")]
                assert [len(x.strip()) for x in g[f"indice{k}"].split("|")] == [c for _, c in caps], (seed, step, k)
            if step == "tensions":
                assert all(len([x for x in g[f"head{k}"].split(";") if x.strip()]) == 2 for k in (1, 2, 3))
        TroisRegardsPresentation.model_validate(worst_case_deck_v3(seed))


_LINES_V3 = """() => { const box = (s) => ['paddingTop', 'paddingBottom', 'borderTopWidth', 'borderBottomWidth']
    .reduce((a, k) => a + parseFloat(s[k]), 0);
  const n = (sel) => [...document.querySelectorAll(sel)].map(e => { const s = getComputedStyle(e);
    return Math.round((e.getBoundingClientRect().height - box(s)) / parseFloat(s.lineHeight)); });
  const bottom = Math.max(0, ...[...document.querySelectorAll('.stage *')].map(e => e.getBoundingClientRect().bottom));
  const cut = [...document.querySelectorAll('.card, .card *, .ld, .ld *')]
    .filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.className);
  const first = document.querySelector('.card.pc'), head = document.querySelector('.head');
  return {head: n('.head'), nm: n('.card .nm'), see: n('.card .see'), foot: n('.card .foot > span'), tag: n('.tagk'),
          badge: n('.badge'), lead: n('.ld > span'), cards: document.querySelectorAll('.card.pc').length,
          first: first ? first.getBoundingClientRect().top : null, title: head ? head.getBoundingClientRect().bottom : null,
          perch: !!(first && first.hasAttribute('data-perch')), perches: document.querySelectorAll('[data-perch]').length,
          text: (document.querySelector('.stage') || document.body).innerText, bottom, cut,
          page: document.documentElement.scrollWidth}; }"""


def _measure(tmp_path, deck: dict) -> dict[str, dict]:
    """Every slide of `deck` measured as `renderer.shoot` shoots it: web fonts loaded, the room left shared out."""
    from renderer.shoot import _FIT, FIT_CAP, FIT_MARGIN
    doc = extract(full(), TroisRegardsPresentation.model_validate(deck))
    renderer.generate_html(doc, tmp_path)
    measured = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for f in sorted(tmp_path.glob("*.html")):
            page.set_content(f.read_text(encoding="utf-8"), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.evaluate(_FIT, [FIT_MARGIN, FIT_CAP])
            measured[f.stem] = page.evaluate(_LINES_V3)
        browser.close()
    return measured


@pytest.fixture(scope="module")
def v3_worst(tmp_path_factory):
    return _measure(tmp_path_factory.mktemp("v3_worst"), worst_case_deck_v3(0))


def test_the_first_card_starts_at_the_same_height_on_the_three_prism_slides(v3_worst):
    tops = [v3_worst[s]["first"] for s in ("03_prisme", "04_prisme", "05_prisme")]
    assert max(tops) - min(tops) <= 2, tops
    assert sum(len(v3_worst[s]["badge"]) for s in ("03_prisme", "04_prisme", "05_prisme")) == 1   # the media slide is in


def test_the_tensions_and_limites_first_cards_start_at_the_same_height(v3_worst):
    tops = [v3_worst[s]["first"] for s in ("06_tensions", "07_limites")]
    assert max(tops) - min(tops) <= 2, tops


@pytest.mark.parametrize("seed", range(12))
def test_every_v3_field_at_its_cap_fits_on_the_slide(tmp_path, seed):
    deck = worst_case_deck_v3(seed)
    measured = _measure(tmp_path, deck)
    assert list(measured) == _SLIDES_V3
    for slide, m in measured.items():
        assert m["page"] <= 1080, (slide, "horizontal overflow", m["page"])
        assert m["bottom"] <= 1255, (slide, m["bottom"])
        assert m["cut"] == [], (slide, "a card or a lead overflows sideways", m["cut"])
    for slide, cards in (("03_prisme", 4), ("04_prisme", 4), ("05_prisme", 4), ("06_tensions", 3), ("07_limites", 3)):
        m = measured[slide]
        assert m["cards"] == cards, (slide, m["cards"])
        assert len(m["head"]) == 1 and m["head"][0] <= 2, (slide, "the title takes more than two lines", m["head"])
        assert m["title"] < m["first"], (slide, "the title must sit above the first card")
        assert len(m["nm"]) == cards and all(x <= 2 for x in m["nm"]), (slide, "a card head", m["nm"])
        assert len(m["see"]) == cards and all(x <= 2 for x in m["see"]), (slide, "a card answer or claim", m["see"])
        assert len(m["foot"]) == cards and all(x <= 2 for x in m["foot"]), (slide, "a clue", m["foot"])
        assert m["lead"] == [1], (slide, "the lead takes one line", m["lead"])
        assert all(x == 1 for x in m["badge"]), (slide, "the badge wraps", m["badge"])
        assert m["perch"] and m["perches"] == 1, (slide, "the bird perches on the first card")
        assert deck["axe"]["question"] not in m["text"], (slide, "the deck question is repeated")
    for slide in ("06_tensions", "07_limites"):
        assert len(measured[slide]["tag"]) == 3 and all(x == 1 for x in measured[slide]["tag"]), (slide, measured[slide]["tag"])
    tops = [measured[s]["first"] for s in ("03_prisme", "04_prisme", "05_prisme")]
    assert max(tops) - min(tops) <= 2, ("the prism slides' first cards", tops)
    tops = [measured[s]["first"] for s in ("06_tensions", "07_limites")]
    assert max(tops) - min(tops) <= 2, ("the tensions' and limites' first cards", tops)


# ── revision 4: the seven-slide deck the author validated on rendered images ──
# position (precise facts) · three « Le prisme … » slides (four role cards, a lead, no clue) · « Les tensions » as a grid · CTA

DECK_V4 = json.loads(Path("tests/fixtures/trois_regards_deck_v4.json").read_text(encoding="utf-8"))
_SLIDES_V4 = ["01_hook", "02_position", "03_prisme", "04_prisme", "05_prisme", "06_tensions", "07_cta"]
_ROLES_V4 = ["Origine", "Mécanisme", "Amplificateur", "Ce qu'on en voit"]
_PRISM_SLIDES = ("03_prisme", "04_prisme", "05_prisme")


def test_a_v4_deck_validates():
    pres = TroisRegardsPresentation.model_validate(DECK_V4)
    assert [p.prism for p in pres.prisms] == pres.axe.prisms
    assert all(p.title and p.lead and len(p.cards) == 4 for p in pres.prisms)
    # the prism cards answer and carry no clue and no media note: the sources were removed to relieve the density
    assert all(c.head and c.answer and not c.source and not c.find and not c.claim for p in pres.prisms for c in p.cards)
    assert not any(p.media_note for p in pres.prisms)
    t = pres.tensions
    assert t.title and t.lead and len(t.cards) == 3
    assert all(c.topic and len(c.views) == 3 and all(c.views) and c.source and c.find for c in t.cards)
    assert pres.limites is None and pres.matrix is None and len(pres.position.cards) == 4


def test_a_v4_deck_renders_seven_slides(tmp_path):
    texts = _render(tmp_path, DECK_V4)
    assert list(texts) == _SLIDES_V4
    assert "2 / 7" in texts["02_position"] and "7 / 7" in texts["07_cta"]


def test_the_v4_position_draws_its_labelled_cards(tmp_path):
    t = _render(tmp_path, DECK_V4)["02_position"]
    pos = DECK_V4["position"]
    assert pos["kicker"] in t and pos["lead"] in t
    for c in pos["cards"]:
        assert c["label"] in t and c["text"] in t, c
    assert [t.index(c["label"]) for c in pos["cards"]] == sorted(t.index(c["label"]) for c in pos["cards"])


def test_each_v4_prism_slide_reads_le_prisme_its_title_its_lead_and_the_four_role_tags_in_order(tmp_path):
    texts = _render(tmp_path, DECK_V4)
    for stem, p in zip(_PRISM_SLIDES, DECK_V4["prisms"]):
        t = texts[stem]
        assert f"Le prisme {PRISMS[p['prism']].name.lower()}" in t, stem
        assert p["lead"] in t and p["title"].replace("**", "") in t.replace("<strong>", "").replace("</strong>", ""), stem
        assert PRISMS[p["prism"]].icon_svg in t, stem
        assert all(c["head"] in t and c["answer"] in t for c in p["cards"]), stem
        at = [t.index(r) for r in _ROLES_V4]
        assert at == sorted(at), (stem, "the role tags come in this order")
        assert renderer.MEDIA_BADGE not in t, stem           # no « Le regard du média » pill any more
        assert 'class="foot' not in t, stem                   # no clue line on a prism card


def test_a_v4_role_tag_sits_on_the_head_line(tmp_path):
    t = _render(tmp_path, DECK_V4)["03_prisme"]
    for role, c in zip(_ROLES_V4, DECK_V4["prisms"][0]["cards"]):
        assert re.search(rf'<div class="nm"><span class="rl">{re.escape(role)}</span><span class="sep">·</span>', t), role


def test_the_v4_tensions_grid_names_the_regards_once_in_a_header_and_draws_the_views_without_names(tmp_path):
    t = _render(tmp_path, DECK_V4)["06_tensions"]
    names = [PRISMS[x].name for x in DECK_V4["axe"]["prisms"]]
    assert [t.count(f"</svg>{n}</div>") for n in names] == [1, 1, 1], "each regard is named once, in the header row"
    assert [t.index(f"</svg>{n}</div>") for n in names] == sorted(t.index(f"</svg>{n}</div>") for n in names)
    for c in DECK_V4["tensions"]["cards"]:
        assert c["topic"] in t
        assert [t.index(v) for v in c["views"]] == sorted(t.index(v) for v in c["views"]), c["topic"]
        assert f"<strong>{c['source']}</strong> : {c['find']}" in t, c["topic"]
        assert not any(n.lower() in v.lower() for n in names for v in c["views"]), c["topic"]
    assert t.count("tclue") == 3 + 1 or t.count('class="tclue"') == 3          # one clue line per row
    assert 'class="card pc"' not in t, "a grid, not three cards"


def test_the_v4_title_block_is_slide_2s_on_slides_3_to_6_and_the_deck_question_is_not_repeated(tmp_path):
    texts = _render(tmp_path, DECK_V4)
    for stem in (*_PRISM_SLIDES, "06_tensions"):
        assert 'class="top ctr"' in texts[stem], stem              # the title and the lead centred, as slide 2's
    q = DECK_V4["axe"]["question"]
    for stem in ("02_position", *_PRISM_SLIDES, "06_tensions"):
        assert q not in texts[stem], stem
    for p in DECK_V4["prisms"]:
        assert p["lead"].endswith(".") and not p["lead"].endswith("?")
    assert DECK_V4["tensions"]["lead"] in texts["06_tensions"]


# the seeded worst case of the revision-4 fields, built here (the agent's steps follow in the next task)

def worst_case_deck_v4(seed: int = 0) -> dict:
    """Every revision-4 field at its cap exactly. The caps are the validated deck's own longest texts, so the words are
    ordinary French (at most six letters, an average word has five): a pathological unbreakable word is not what a model
    writes in a 70 px title or a 25 px fact. The axe, the hook and the caption are the older worst case's."""
    rng = random.Random(4000 + seed)
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    plain = lambda step, name: _chars(rng, cap(step, name), _SHORT)   # noqa: E731
    deck = {k: v for k, v in worst_case_deck(seed).items() if k != "matrix"}
    deck["position"] = {"kicker": plain("position", "kicker"), "title": plain("position", "title"),
                        "lead": plain("position", "lead"),
                        "cards": [{"label": plain("position", f"v4_label{i}"), "text": plain("position", f"v4_text{i}")}
                                  for i in (1, 2, 3, 4)]}
    deck["prisms"] = [{"prism": p, "title": plain("prismes", "v4_title"), "lead": plain("prismes", "v4_lead"),
                       "cards": [{"head": plain("prismes", f"v4_head{k}"), "answer": plain("prismes", f"answer_role{k}")}
                                 for k in (1, 2, 3, 4)]} for p in deck["axe"]["prisms"]]
    deck["tensions"] = {"title": plain("tensions", "v4_title"), "lead": plain("tensions", "v4_lead"),
                        "cards": [{"topic": plain("tensions", f"topic{k}"),
                                   "views": [plain("tensions", f"view{j}") for j in (1, 2, 3)],
                                   "source": _chars(rng, 30, _SHORT), "find": plain("tensions", "v4_find")}
                                  for k in (1, 2, 3)]}
    return deck


def test_the_v4_worst_case_sits_exactly_at_its_caps():
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    for seed in range(12):
        d = worst_case_deck_v4(seed)
        TroisRegardsPresentation.model_validate(d)
        assert [len(c["text"]) for c in d["position"]["cards"]] == [cap("position", f"v4_text{i}") for i in (1, 2, 3, 4)]
        assert [len(c["label"]) for c in d["position"]["cards"]] == [cap("position", f"v4_label{i}") for i in (1, 2, 3, 4)]
        for p in d["prisms"]:
            assert len(p["title"]) == cap("prismes", "v4_title") and len(p["lead"]) == cap("prismes", "v4_lead"), seed
            for k, c in enumerate(p["cards"], 1):
                assert len(c["head"]) == cap("prismes", f"v4_head{k}") and len(c["answer"]) == cap("prismes", f"answer_role{k}")
        t = d["tensions"]
        assert len(t["title"]) == cap("tensions", "v4_title") and len(t["lead"]) == cap("tensions", "v4_lead"), seed
        for k, c in enumerate(t["cards"], 1):
            assert len(c["topic"]) == cap("tensions", f"topic{k}")
            assert [len(v) for v in c["views"]] == [cap("tensions", f"view{j}") for j in (1, 2, 3)], seed


_LINES_V4 = """() => { const box = (s) => ['paddingTop', 'paddingBottom', 'borderTopWidth', 'borderBottomWidth']
    .reduce((a, k) => a + parseFloat(s[k]), 0);
  const n = (sel) => [...document.querySelectorAll(sel)].map(e => { const s = getComputedStyle(e);
    return Math.round((e.getBoundingClientRect().height - box(s)) / parseFloat(s.lineHeight)); });
  const bottom = Math.max(0, ...[...document.querySelectorAll('.stage *')].map(e => e.getBoundingClientRect().bottom));
  const cut = [...document.querySelectorAll('.card, .card *, .ld, .ld *, .tgrid > div, .row, .row *')]
    .filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.className);
  const first = document.querySelector('.card.pc') || document.querySelector('.tbl');
  const h = document.querySelector('.head') || document.querySelector('.mh'), hs = h ? getComputedStyle(h) : null;
  return {head: n('.head, .mh'), lead: n('.ld > span, .ml'), nm: n('.card .nm'), see: n('.card .see'), say: n('.row .say'),
          label: n('.row .h span'), view: n('.tview'), topic: n('.ttopic'), clue: n('.tclue .foot > span'),
          cards: document.querySelectorAll('.card.pc').length, first: first ? first.getBoundingClientRect().top : null,
          titleBottom: h ? h.getBoundingClientRect().bottom : null, size: hs ? parseFloat(hs.fontSize) : null,
          align: hs ? hs.textAlign : null, perches: document.querySelectorAll('[data-perch]').length,
          onFirst: !!(first && first.hasAttribute('data-perch')), onRow: !!document.querySelector('.row[data-perch]'),
          text: (document.querySelector('.stage') || document.body).innerText, bottom, cut,
          page: document.documentElement.scrollWidth}; }"""


def _measure_v4(tmp_path, deck: dict) -> dict[str, dict]:
    from renderer.shoot import _FIT, FIT_CAP, FIT_MARGIN
    doc = extract(full(), TroisRegardsPresentation.model_validate(deck))
    renderer.generate_html(doc, tmp_path)
    measured = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for f in sorted(tmp_path.glob("*.html")):
            page.set_content(f.read_text(encoding="utf-8"), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.evaluate(_FIT, [FIT_MARGIN, FIT_CAP])
            measured[f.stem] = page.evaluate(_LINES_V4)
        browser.close()
    return measured


@pytest.fixture(scope="module")
def v4_fixture_measured(tmp_path_factory):
    return _measure_v4(tmp_path_factory.mktemp("v4_fixture"), DECK_V4)


def test_the_v4_fixture_deck_fits_and_slides_2_to_6_share_the_title_block(v4_fixture_measured):
    m = v4_fixture_measured
    assert list(m) == _SLIDES_V4
    for stem, s in m.items():
        assert s["page"] <= 1080 and s["bottom"] <= 1255 and s["cut"] == [], (stem, s["bottom"], s["cut"])
    for stem in ("02_position", *_PRISM_SLIDES, "06_tensions"):
        assert m[stem]["size"] == 70 and m[stem]["align"] == "center", (stem, m[stem]["size"], m[stem]["align"])
        assert all(x <= 2 for x in m[stem]["head"]) and all(x <= 2 for x in m[stem]["lead"]), stem
        assert m[stem]["lead"], (stem, "a lead is drawn")


def test_the_bird_perches_on_the_first_card_row_or_grid_edge_of_slides_2_to_6(v4_fixture_measured):
    m = v4_fixture_measured
    assert m["02_position"]["onRow"] and m["02_position"]["perches"] == 1
    for stem in (*_PRISM_SLIDES, "06_tensions"):
        assert m[stem]["onFirst"] and m[stem]["perches"] == 1, stem
        assert m[stem]["titleBottom"] < m[stem]["first"], (stem, "the title sits above the wire")


def test_the_first_prism_card_starts_at_the_same_height_on_the_three_prism_slides(v4_fixture_measured):
    tops = [v4_fixture_measured[s]["first"] for s in _PRISM_SLIDES]
    assert max(tops) - min(tops) <= 2, tops


@pytest.mark.parametrize("seed", range(12))
def test_every_v4_field_at_its_cap_fits_on_the_slide(tmp_path, seed):
    deck = worst_case_deck_v4(seed)
    m = _measure_v4(tmp_path, deck)
    assert list(m) == _SLIDES_V4
    for stem, s in m.items():
        assert s["page"] <= 1080, (stem, "horizontal overflow", s["page"])
        assert s["bottom"] <= 1255, (stem, "passes the page number", s["bottom"])
        assert s["cut"] == [], (stem, "a card, a lead or a cell overflows sideways", s["cut"])
    p = m["02_position"]
    assert all(x <= 2 for x in p["head"]) and all(x <= 2 for x in p["lead"]), p
    assert all(x <= 3 for x in p["say"]) and all(x <= 2 for x in p["label"]), (p["say"], p["label"])
    for stem in _PRISM_SLIDES:
        s = m[stem]
        assert s["cards"] == 4 and all(x <= 2 for x in s["head"]) and all(x <= 2 for x in s["lead"]), (stem, s["head"], s["lead"])
        assert all(x == 1 for x in s["nm"]), (stem, "the role tag and the head share one line", s["nm"])
        assert all(x <= 2 for x in s["see"]), (stem, "an answer takes more than two lines", s["see"])
    t = m["06_tensions"]
    assert all(x <= 2 for x in t["head"]) and all(x <= 2 for x in t["lead"]), t
    assert len(t["view"]) == 9 and all(x <= 4 for x in t["view"]), (t["view"])
    assert len(t["topic"]) == 3 and all(x <= 4 for x in t["topic"]), t["topic"]
    tops = [m[s]["first"] for s in _PRISM_SLIDES]
    assert max(tops) - min(tops) <= 2, ("the prism slides' first cards", tops)


def test_the_v4_fixture_respects_the_v4_caps():
    """The validated deck is inside the caps the worst-case test renders at."""
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    n = lambda s: len(s.replace("**", ""))   # noqa: E731
    pos = DECK_V4["position"]
    assert n(pos["kicker"]) <= cap("position", "kicker") and n(pos["title"]) <= cap("position", "title")
    assert n(pos["lead"]) <= cap("position", "lead")
    for i, c in enumerate(pos["cards"], 1):
        assert n(c["label"]) <= cap("position", f"v4_label{i}") and n(c["text"]) <= cap("position", f"v4_text{i}"), c
    for s in DECK_V4["prisms"]:
        assert n(s["title"]) <= cap("prismes", "v4_title") and n(s["lead"]) <= cap("prismes", "v4_lead"), s["prism"]
        for i, c in enumerate(s["cards"], 1):
            assert n(c["head"]) <= cap("prismes", f"v4_head{i}") and n(c["answer"]) <= cap("prismes", f"answer_role{i}"), c
    t = DECK_V4["tensions"]
    assert n(t["title"]) <= cap("tensions", "v4_title") and n(t["lead"]) <= cap("tensions", "v4_lead")
    for i, c in enumerate(t["cards"], 1):
        assert n(c["topic"]) <= cap("tensions", f"topic{i}") and n(c["find"]) <= cap("tensions", "v4_find"), c
        assert all(n(v) <= cap("tensions", f"view{j}") for j, v in enumerate(c["views"], 1)) and n(c["source"]) <= 30, c
