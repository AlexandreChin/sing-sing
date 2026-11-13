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


def test_the_sample_deck_breaks_no_hard_rule():
    for step in ("axe", "position", "matrice", "hook", "writing"):
        assert _hard(step, FIELDS[step]) == [], step
    for slot in ("p1", "p2", "p3"):
        assert _hard("prismes", FIELDS["prismes"][slot], slot=slot) == [], slot


def test_a_field_over_its_cap_is_a_hard_error():
    assert any("axe.question" in e and "max 60" in e for e in _hard("axe", _with("axe", question="x" * 59 + "y ?")))
    assert not _hard("axe", _with("axe", question="D'où vient la crise du logement ?"))
    assert any("axe.subject" in e for e in _hard("axe", _with("axe", subject="x" * 37)))
    assert any("axe.closing" in e for e in _hard("axe", _with("axe", closing="x" * 110 + " ?")))
    assert any("axe.media_grounding" in e for e in _hard("axe", _with("axe", media_grounding="x" * 121)))
    for name, cap in (("kicker", 30), ("title", 46), ("lead", 90)):
        assert any(f"position.{name}" in e for e in _hard("position", _with("position", **{name: "x" * (cap + 1)})))
    assert any("prismes.question" in e for e in _hard("prismes", _with("prismes", "p2", question="x" * 65), slot="p2"))
    assert any("prismes.line3" in e for e in _hard("prismes", _with("prismes", "p2", line3="x" * 81), slot="p2"))
    assert any("prismes.media_note" in e for e in _hard("prismes", _with("prismes", "p1", media_note="x" * 91), slot="p1"))
    assert any("matrice.title" in e for e in _hard("matrice", _with("matrice", title="x" * 34 + " ?")))
    assert any("hook.title" in e for e in _hard("hook", _with("hook", title="x" * 70 + " ?")))
    assert any("hook.promise" in e for e in _hard("hook", _with("hook", promise="x" * 101)))


@pytest.mark.parametrize("step,name,part,cap", [
    ("position", "card2", "label", 30), ("position", "card2", "text", 108),
    ("matrice", "col2", "variable", 60), ("matrice", "col2", "indicator", 40)])
def test_a_part_over_its_cap_is_a_hard_error(step, name, part, cap):
    cell = {"label": "ab | cd", "text": "ab | cd", "variable": "ab | cd", "indicator": "ab | cd"}
    over, ok = "x" * (cap + 1), "x" * cap
    other = "ab"
    mk = lambda v: (f"{v} | {other}" if part in ("label", "variable") else f"{other} | {v}")  # noqa: E731
    assert any(f"{step}.{name}" in e and part in e for e in _hard(step, _with(step, **{name: mk(over)})))
    assert not any(f"{step}.{name}" in e for e in _hard(step, _with(step, **{name: mk(ok)})))
    assert cell


def test_a_source_name_over_30_characters_or_a_fourth_source_is_a_hard_error():
    p = lambda s: _hard("prismes", _with("prismes", "p2", sources=s), slot="p2")  # noqa: E731
    assert any("sources" in e for e in p("A ; " + "x" * 31))
    assert any("sources" in e for e in p("A ; B ; C ; D"))
    assert not p("A ; B ; " + "x" * 30)


def test_the_axe_needs_three_distinct_prisms_of_the_catalogue():
    assert any("distinct" in e for e in _hard("axe", _with("axe", prism2="politique")))
    assert any("catalogue" in e for e in _hard("axe", _with("axe", prism3="gastronomique")))
    assert any("distinct" in e or "empty" in e for e in _hard("axe", _with("axe", prism3="")))


def test_the_media_prism_is_one_of_the_three():
    assert any("media" in e for e in _hard("axe", _with("axe", media="juridique")))
    assert not _hard("axe", _with("axe", media="sociologique"))


def test_the_deck_question_the_hook_title_the_closing_line_and_the_matrix_title_end_in_a_question_mark():
    assert any("axe.question" in e and "?" in e for e in _hard("axe", _with("axe", question="D'où vient la crise.")))
    assert any("axe.closing" in e and "?" in e for e in _hard("axe", _with("axe", closing="Quel regard explique la crise.")))
    assert any("matrice.title" in e and "?" in e for e in _hard("matrice", _with("matrice", title="Que mesurer")))
    assert any("hook.title" in e and "?" in e for e in _hard("hook", _with("hook", title="La crise du logement")))


def test_the_hook_promise_has_the_fixed_shape():
    ok = "Trois regards sur la crise du logement ; à vous d'en juger."
    assert not _hard("hook", _with("hook", promise=ok))
    for bad in ("Comprendre la crise du logement en trois regards.",
                "Trois regards sur la crise du logement, à vous d'en juger.",
                "Trois regards sur ; à vous d'en juger.",
                "Trois regards sur   ; à vous d'en juger."):
        assert any("hook.promise" in e for e in _hard("hook", _with("hook", promise=bad))), bad


def test_a_prism_slide_needs_three_lines_and_a_source():
    assert any("line3" in e for e in _hard("prismes", _with("prismes", "p2", line3=""), slot="p2"))
    assert any("line1" in e for e in _hard("prismes", _with("prismes", "p2", line1=""), slot="p2"))
    assert any("sources" in e for e in _hard("prismes", _with("prismes", "p2", sources=" ; "), slot="p2"))
    assert any("question" in e for e in _hard("prismes", _with("prismes", "p2", question=""), slot="p2"))
    assert not _hard("prismes", _with("prismes", "p2", line4=""), slot="p2")


def test_only_the_media_prism_slot_carries_a_media_note():
    assert any("media_note" in e for e in _hard("prismes", _with("prismes", "p1", media_note=""), slot="p1"))
    assert any("media_note" in e for e in _hard("prismes", _with("prismes", "p2", media_note="Le regard du média."), slot="p2"))
    assert not _hard("prismes", _with("prismes", "p3"), slot="p3")


def test_accusing_and_blaming_words_are_refused_outside_guillemets_only():
    assert any("oublie" in e for e in _hard("prismes", _with("prismes", "p2", line1="L'article oublie l'économie."), slot="p2"))
    assert any("ne dit pas" in e for e in _hard("position", _with("position", lead="L'article ne dit pas pourquoi.")))
    assert any("biais" in e for e in _hard("position", _with("position", card1="Cause | Un biais net.")))
    assert any("manipulation" in e for e in _hard("hook", _with("hook", title="Une manipulation du logement ?")))
    for word in ("ignore", "omet", "néglige", "mensonge", "trompeur"):
        assert any(word in e for e in _hard("prismes", _with("prismes", "p2", line2=f"Il {word} cela."), slot="p2")), word
    assert not _hard("prismes", _with("prismes", "p2", line1="Le texte cite « l'article oublie » tel quel."), slot="p2")


def test_the_matrix_refuses_prescriptive_verbs():
    for text in ("Il faut plafonner les loyers", "Le Parlement doit voter", "Ils devraient agir", "On devrait construire"):
        assert any("prescriptive" in e for e in _hard("matrice", _with("matrice", col1=f"{text} | Mesures")))
    assert any("prescriptive" in e for e in _hard("matrice", _with("matrice", title="Que faut-il faire ? Il faut mesurer ?")))
    assert not _hard("matrice", FIELDS["matrice"])


def test_no_url_in_sources():
    for s in ("https://ine.es", "www.ine.es", "ine.com/data", "ine.fr/data"):
        assert any("URL" in e for e in _hard("prismes", _with("prismes", "p2", sources=f"A ; {s}"), slot="p2")), s


def test_no_digit_on_the_matrix_or_in_sources():
    assert any("digit" in e for e in _hard("prismes", _with("prismes", "p2", sources="INE 2024"), slot="p2"))
    assert any("digit" in e for e in _hard("matrice", _with("matrice", col2="Écart | 3 millions")))
    assert any("digit" in e for e in _hard("matrice", _with("matrice", title="Que mesurer en 2024 ?")))


def test_a_year_is_allowed_on_a_prism_line_but_not_another_number():
    p = lambda line: _hard("prismes", _with("prismes", "p2", line1=line), slot="p2")  # noqa: E731
    assert not p("Le plafond date de 2024.")
    assert not p("La loi de 1985 reste en vigueur.")
    assert any("digit" in e for e in p("Il manque 600 000 logements."))
    assert any("digit" in e for e in p("Les loyers montent de 12 %."))
    assert any("digit" in e for e in p("Une loi de 1200."))
    assert any("digit" in e for e in p("Une loi de 2100."))


def test_position_and_media_note_are_exempt_from_the_digit_rule():
    assert not _hard("position", _with("position", card1="Ce qu'il raconte | 175 000 manifestants."))
    assert not _hard("prismes", _with("prismes", "p1", media_note="L'article chiffre 175 000 personnes."), slot="p1")


def test_an_axe_with_no_dominant_prism_is_a_flag_not_a_hard_error():
    fields = _with("axe", media_grounding="Aucun prisme ne domine : le texte mêle politique et économie.")
    hard, flags = _fe("axe", fields)
    assert hard == [] and any("dominate" in f for f in flags)
    assert not any("dominate" in f for f in _flags("axe", FIELDS["axe"]))


def test_a_prism_question_a_matrix_cell_or_the_closing_line_sharing_no_key_word_with_the_axe_question_is_flagged():
    assert not [f for f in _flags("prismes", FIELDS["prismes"]["p2"], slot="p2") if "question" in f]
    bad = _flags("prismes", _with("prismes", "p2", question="Combien de pommes, à quel prix ?"), slot="p2")
    assert any("prismes.question" in f and "key word" in f for f in bad)
    assert not _flags("prismes", _with("prismes", "p2", question="Combien de logements, à quel prix ?"), slot="p2")
    cell = _flags("matrice", _with("matrice", col1="Les pommes | Récolte"))
    assert any("matrice.col1" in f for f in cell)
    assert not any("matrice.col2" in f for f in cell)
    closing = _with("axe", closing="Politique, économique ou sociologique : quel regard est le meilleur ?")
    assert any("axe.closing" in f and "key word" in f for f in _flags("axe", closing))
    assert not any("axe.closing" in f and "key word" in f for f in _flags("axe", FIELDS["axe"]))


def test_a_closing_line_with_ou_is_flagged_not_blocked():
    hard, flags = _fe("axe", FIELDS["axe"])
    assert hard == [] and any("« ou »" in f for f in flags)
    hard, flags = _fe("axe", _with("axe", closing="Politique, économique, sociologique : quel regard explique la crise du logement ?"))
    assert hard == [] and not any("« ou »" in f for f in flags)
    assert any("« ou »" in f for f in _flags("matrice", _with("matrice", title="Prix ou loyers ?")))


def test_a_quoted_passage_of_the_position_or_the_media_note_must_be_in_the_source():
    fields = _with("position", card2="Ses causes | « Un manque de logements sociaux » pèse.")
    assert not [f for f in _flags("position", fields, article=ARTICLE) if "quote" in f]
    fields = _with("position", card2="Ses causes | « Un excès de touristes » pèse.")
    assert any("position.card2" in f and "word for word" in f for f in _flags("position", fields, article=ARTICLE))
    assert not _hard("position", fields, article=ARTICLE)
    assert not [f for f in _flags("position", fields) if "word for word" in f]
    note = _with("prismes", "p1", media_note="Il parle d'« un plafond inventé ».")
    assert any("media_note" in f and "word for word" in f for f in _flags("prismes", note, slot="p1", article=ARTICLE))


def test_two_near_identical_prism_slides_are_flagged():
    frags = _fragments()
    twin = copy.deepcopy(FIELDS["prismes"]["p2"])
    frags["prismes"] = agent.to_fragment(agent.STEP_BY_NAME["prismes"],
                                         [_opt(FIELDS["prismes"]["p1"], "p1"), _opt(twin, "p2")], frags)
    same = _flags("prismes", twin, slot="p3", frags=frags)
    assert any("near" in f for f in same)
    assert not [f for f in _flags("prismes", FIELDS["prismes"]["p3"], slot="p3") if "near" in f]


def test_the_closing_line_missing_a_prism_name_is_flagged():
    assert not [f for f in _flags("axe", FIELDS["axe"]) if "name" in f and "closing" in f]
    flags = _flags("axe", _with("axe", closing="Politique ou économique : quel regard explique la crise du logement ?"))
    assert any("closing" in f and "sociolog" in f.lower() for f in flags)


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
    assert caps["axe.question"] == 60 and caps["prismes.source"] == 30 and caps["prismes.sources"] == 3
    assert agent.fill_caps("max {{cap:axe.question}} signes") == "max 60 signes"
    with pytest.raises(KeyError):
        agent.fill_caps("{{cap:nope.nope}}")
