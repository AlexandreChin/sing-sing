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
    assert n(p.position.kicker) <= 30 and n(p.position.title) <= 36 and n(p.position.lead) <= 90
    assert all(n(c.text) <= 96 and n(c.label) <= 30 for c in p.position.cards)
    for s in p.prisms:
        assert n(s.question) <= 60 and n(s.media_note) <= 90 and len(s.sources) <= 3
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
    for name, cap in (("kicker", 30), ("title", 36), ("lead", 90)):
        assert any(f"position.{name}" in e for e in _hard("position", _with("position", **{name: "x" * (cap + 1)})))
    assert any("prismes.question" in e for e in _hard("prismes", _with("prismes", "p2", question="x" * 61), slot="p2"))
    assert any("prismes.line3" in e for e in _hard("prismes", _with("prismes", "p2", line3="x" * 81), slot="p2"))
    assert any("prismes.media_note" in e for e in _hard("prismes", _with("prismes", "p1", media_note="x" * 91), slot="p1"))
    assert any("matrice.title" in e for e in _hard("matrice", _with("matrice", title="x" * 34 + " ?")))
    assert any("hook.title" in e for e in _hard("hook", _with("hook", title="x" * 70 + " ?")))
    assert any("hook.promise" in e for e in _hard("hook", _with("hook", promise="x" * 101)))


@pytest.mark.parametrize("step,name,part,cap", [
    ("position", "card2", "label", 30), ("position", "card2", "text", 96),
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
    for verb in ("il faut", "doit", "doivent", "devrait", "devraient", "on devrait"):
        col = _with("matrice", col1=f"Ce que {verb} mesurer | Mesures")
        assert any("prescriptive" in e and verb.split()[-1] in e for e in _hard("matrice", col)), verb
        title = _with("matrice", title=f"Que {verb} mesurer ?")
        assert any("prescriptive" in e and "matrice.title" in e for e in _hard("matrice", title)), verb
    assert not _hard("matrice", FIELDS["matrice"])


def test_a_digit_in_a_prism_question_is_refused_unless_it_is_a_year():
    q = lambda text: _hard("prismes", _with("prismes", "p2", question=text), slot="p2")  # noqa: E731
    assert any("prismes.question" in e and "digit" in e for e in q("Que pèse 12 % du budget ?"))
    assert not q("Que change 1975 ?")


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


def test_unattended_runs_six_steps_and_rebuilds_the_deck(fake, tmp_path):
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
    assert not (steps / "4_matrice.json").exists() and (steps / "3_prismes.json").exists()


def test_a_later_step_receives_the_earlier_picks(fake, tmp_path):
    agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text="TEXTE-DE-L-ARTICLE", stop_after="prismes")
    first, _, third = fake.messages
    assert "CHOIX FIXÉS" not in first and "CATALOGUE DES PRISMES" in first
    fixed = third.split("CHOIX FIXÉS (ne les réécris pas) :")[1]
    assert FIELDS["axe"]["question"] in fixed and FIELDS["position"]["title"] in fixed
    assert "TEXTE-DE-L-ARTICLE" in third
    assert all(f"{s} = {p}" in third for s, p in zip(("p1", "p2", "p3"), ("politique", "economique", "sociologique")))
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
    edit = {"p2c.line1": "Les loyers montent plus vite que les salaires."}
    assert agent.choose(full(), steps, "prismes", ["p3b", "p1b", "p2c"], edit) == []
    sf = _step_file(steps, "prismes")
    assert sf.picked == ["p1b", "p2c", "p3b"]
    assert sf.fragment["prisms"][1]["lines"][0] == "Les loyers montent plus vite que les salaires."
    assert [s["prism"] for s in sf.fragment["prisms"]] == ["politique", "economique", "sociologique"]


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
    assert fake.labels[len(agent.STEPS):] == ["position", "prismes", "matrice", "hook", "writing"]
    assert pres.axe.question == "Pourquoi le logement manque-t-il en Espagne ?"
    assert list(steps.glob("stale_*/3_prismes.json"))


def test_fix_rewrites_one_field_without_regenerating(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    assert agent.fix(full(), steps, "axe.question", "Pourquoi le logement manque-t-il en Espagne ?") == ("axe", [])
    assert agent.fix(full(), steps, "position.title", "Une crise devenue enjeu de scrutin") == ("position", [])
    assert agent.fix(full(), steps, "caption", DECK["caption"] + " Merci.")[0] == "writing"
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before                      # the later steps were re-stamped, not rerun
    assert pres.axe.question == "Pourquoi le logement manque-t-il en Espagne ?"
    assert pres.position.title == "Une crise devenue enjeu de scrutin" and pres.caption.endswith("Merci.")
    step, warnings = agent.fix(full(), steps, "hook.title", "x" * 75)
    assert step == "hook" and any("hook.title is 75" in w for w in warnings)
    step, warnings = agent.fix(full(), steps, "matrice.title", "Que mesurer pour en juger ?")
    assert step == "matrice" and not [w for w in warnings if w.startswith("matrice")]
    _, warnings = agent.fix(full(), steps, "prismes.p2.media_note", "Une note.")   # a wording fix still checked
    assert any(w.startswith("p2: prismes.media_note must be empty") for w in warnings)
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before and pres.matrix.title == "Que mesurer pour en juger ?"
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), steps, "invisible.statement", "x")


def test_fix_reaches_a_prism_field_by_slot(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    assert agent.fix(full(), steps, "prismes.p2.line1", "Les loyers montent plus vite que les salaires.") == ("prismes", [])
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before
    assert pres.prisms[1].lines[0] == "Les loyers montent plus vite que les salaires."
    assert pres.prisms[0].lines == DECK["prisms"][0]["lines"] and pres.prisms[2].lines == DECK["prisms"][2]["lines"]
    _, warnings = agent.fix(full(), steps, "prismes.p3.line2", "Plus de 300 collectifs se forment.")
    assert any(w.startswith("p3: prismes.line2 holds a digit") for w in warnings)
    with pytest.raises(agent.ChoiceError, match="prismes.p1.line1"):
        agent.fix(full(), steps, "prismes.line1", "x")
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), steps, "prismes.p4.line1", "x")


def test_the_choice_log_records_picks_edits_and_fixes(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    agent.choose(full(), steps, "prismes", ["p1b", "p2a", "p3a"], {"p1b.question": "Qui décide ?"}, reason="plus court")
    new = agent.more(full(), steps, "prismes", remark="autre angle", slot="p3")
    with pytest.raises(agent.ChoiceError):          # the p3 pick went with its options: nothing to fix yet
        agent.fix(full(), steps, "prismes.p2.line1", "Une ligne refaite.")
    agent.choose(full(), steps, "prismes", ["p1b", "p2a", new.recommended[-1]], {})
    agent.fix(full(), steps, "prismes.p2.line1", "Une ligne refaite.")
    pick, more, _, fix = _log(steps)
    assert pick["event"] == "pick" and pick["step"] == "prismes" and pick["picked"] == ["p1b", "p2a", "p3a"]
    assert pick["edits"] == {"p1b.question": "Qui décide ?"} and pick["reason"] == "plus court"
    assert {"id": "p2b", "slot": "p2", "text": FIELDS["prismes"]["p2"]["question"]} in pick["offered"]
    assert more == {**more, "event": "more", "step": "prismes", "remark": "autre angle", "slot": "p3"}
    assert fix == {**fix, "event": "fix", "step": "prismes", "field": "prismes.p2.line1",
                   "before": FIELDS["prismes"]["p2"]["line1"], "after": "Une ligne refaite."}


def test_no_api_runs_through_the_same_path(fake, tmp_path):
    pres = agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", no_api=True)
    assert fake.labels == [s.name for s in agent.STEPS] and all(fake.no_api)
    assert pres.matrix.title == DECK["matrix"]["title"]


_LATER = ["position", "prismes", "matrice", "hook", "writing"]


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
    owner, warnings = agent.fix(full(), steps, "axe.prism2", "juridique")
    assert owner == "axe" and any("regenerated" in w for w in warnings)
    assert _step_file(steps, "axe").fragment["axe"]["prisms"] == ["politique", "juridique", "sociologique"]
    assert not any(_fresh(steps, s) for s in _LATER)
    # never relabelled: the old p2 text keeps its old prism id until it is regenerated
    assert _step_file(steps, "prismes").fragment["prisms"][1]["prism"] == "economique"
    assert _step_file(steps, "matrice").fragment["matrix"]["columns"][1]["prism"] == "economique"
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels[n:] == _LATER
    assert "p2 = juridique" in fake.messages[n + 1]               # the prism slides were written for the new prism
    assert pres.prisms[1].prism == "juridique" and pres.matrix.columns[1].prism == "juridique"


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
    agent.choose(full(), steps, "axe", ["b"], {"b.prism2": "juridique"})
    agent.fix(full(), steps, "axe.question", "Pourquoi le logement manque-t-il en Espagne ?")
    assert not any(_fresh(steps, s) for s in _LATER)
    assert _step_file(steps, "prismes").fragment["prisms"][1]["prism"] == "economique"   # not rebuilt
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels[n:] == _LATER
    assert pres.axe.question == "Pourquoi le logement manque-t-il en Espagne ?" and pres.prisms[1].prism == "juridique"


def test_a_wording_fix_on_a_later_step_still_restamps_without_a_model_call(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    agent.fix(full(), steps, "position.title", "Une crise devenue enjeu de scrutin")
    assert all(_fresh(steps, s) for s in _LATER)
    agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before


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


def test_the_worked_examples_of_the_prompts_break_no_hard_rule():
    """The examples written in 1_axe / 2_position / 3_prismes / 4_matrice / 5_hook respect the rules."""
    def bullets(name: str) -> dict[str, str]:
        text = _prompt_text(PROMPTS / name).split("Exemple", 1)[1]
        return {m.group(1): m.group(2).strip() for m in re.finditer(r"^- `(\w+)` : « ?(.*?) ?»\s*$", text, re.M)}

    def clean(d: dict[str, str]) -> dict[str, str]:
        return {k: v for k, v in d.items() if k != "reason"}

    axe = clean(bullets("1_axe.md"))
    axe.update(prism1="politique", prism2="economique", prism3="sociologique", media="politique")
    frags = {"axe": agent.to_fragment(agent.STEP_BY_NAME["axe"], [_opt(FIELDS["axe"] | axe)], {})}
    assert agent.field_errors("axe", FIELDS["axe"] | axe, {}, None)[0] == []
    pos = clean(bullets("2_position.md"))
    assert agent.field_errors("position", pos, frags, None)[0] == []
    mat = clean(bullets("4_matrice.md"))
    assert agent.field_errors("matrice", mat, frags, None)[0] == []
    assert agent.field_errors("hook", FIELDS["hook"] | {"title": axe["question"],
                                                         "promise": "Trois regards sur la crise du logement ; à vous d'en juger."},
                              frags, None)[0] == []
    p2 = {"question": "Un marché qui construit trop peu suffit-il à l'expliquer ?", "line1": "Quand l'offre de logements ne suit pas la demande, les prix montent.",
          "line2": "Le logement social, rare, laisse le marché seul face aux besoins.",
          "line3": "Le tourisme met les résidents en concurrence avec les locations courtes.",
          "line4": "", "sources": "Banque d'Espagne ; Eurostat ; INE", "media_note": ""}
    p1 = {"question": "Qui décide, et qui bloque ?", "line1": "Un gouvernement sans majorité doit négocier chaque mesure avec le Congrès.",
          "line2": "Le calendrier électoral pèse sur le moment où les mesures sont proposées.",
          "line3": "Les partis ne s'accordent pas sur le rôle de la loi face au marché locatif.", "line4": "",
          "sources": "Congrès des députés ; Gouvernement d'Espagne",
          "media_note": "Le récit suit les mesures du gouvernement, leur rejet par le Congrès, puis l'élection."}
    assert agent.field_errors("prismes", p2, frags, None, slot="p2")[0] == []
    assert agent.field_errors("prismes", p1, frags, None, slot="p1")[0] == []


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


def test_seven_slides_are_rendered(tmp_path):
    texts = _render(tmp_path)
    assert list(texts) == _SLIDES
    assert "Une crise devenue enjeu d'élection" in texts["02_position"] and "Ce que dit l'article" in texts["02_position"]
    for stem, prism in zip(("03_prisme", "04_prisme", "05_prisme"), DECK["prisms"]):
        assert PRISMS[prism["prism"]].name in texts[stem] and prism["question"] in texts[stem]
        assert PRISMS[prism["prism"]].icon_svg in texts[stem]
        assert all(line in texts[stem] for line in prism["lines"]), stem
        assert " · ".join(prism["sources"]) in texts[stem]
    assert "Que mesurer pour trancher ?" in texts["06_matrice"] and DECK["axe"]["question"] in texts["06_matrice"]


def test_the_position_kicker_defaults_and_the_cards_take_fixed_icons(tmp_path):
    from renderer.instagram_carousel._shared import ICONS
    deck = copy.deepcopy(DECK)
    deck["position"]["kicker"] = ""
    text = _render(tmp_path, deck)["02_position"]
    assert "Ce que dit l'article" in text
    positions = [text.index(ICONS[name]) for name in ("book", "link", "eye", "widen")]
    assert positions == sorted(positions)


def test_the_media_prism_slide_carries_the_badge_and_the_others_do_not(tmp_path):
    texts = _render(tmp_path)
    assert "Le regard du média" in texts["03_prisme"] and DECK["prisms"][0]["media_note"] in texts["03_prisme"]
    assert "Le regard du média" not in texts["04_prisme"] and "Le regard du média" not in texts["05_prisme"]


def test_the_bird_perches_on_each_prism_title(tmp_path):
    texts = _render(tmp_path)
    for stem in ("03_prisme", "04_prisme", "05_prisme"):
        assert texts[stem].count("data-perch") == 1
        assert re.search(r'<h1 class="head[^"]*"[^>]*data-perch', texts[stem]), stem


def test_the_matrix_marks_the_media_column(tmp_path):
    text = _render(tmp_path)["06_matrice"]
    cols = text.split('<div class="col')[1:]
    assert len(cols) == 3
    marked = [c for c in cols if "Le regard du média" in c]
    assert len(marked) == 1 and "Politique" in marked[0] and "data-perch" in marked[0]
    assert text.count("data-perch") == 1
    for col, c in zip(cols, DECK["matrix"]["columns"]):
        assert PRISMS[c["prism"]].name in col and c["variable"] in col and c["indicator"] in col
        assert "Commence par" in col and "À suivre" in col


def test_the_cta_line_is_the_closing_question_lowercased(tmp_path):
    text = _render(tmp_path)["07_cta"]
    assert "— politique, économique ou sociologique : quel regard explique le mieux la crise du logement ?" in text


def test_the_hook_promise_and_title_are_drawn(tmp_path):
    text = _render(tmp_path)["01_hook"]
    assert DECK["hook"]["title"] in text and DECK["hook"]["promise"] in text


# ── the layout: every field at its cap still fits its lines and the slide ───

_POOL = ("le la les de des du un une et à au en par sur pour dans avec plus que qui "
         "logement logements gouvernement Parlement locataires propriétaires intergénérationnelle "
         "constitutionnelle décentralisation institutionnelles municipalités investissements "
         "démographiques recensement observatoire statistiques européennes ménages métropoles "
         "spéculation rénovation copropriétés expulsions coalitions majoritaire").split()


def _chars(rng: random.Random, n: int) -> str:
    """Random French-looking text of at most `n` characters, long words included."""
    out = ""
    while True:
        w = rng.choice(_POOL)
        if len((out + " " + w).strip()) > n:
            return out
        out = (out + " " + w).strip()


def _ask(rng: random.Random, n: int) -> str:
    return _chars(rng, n - 2) + " ?"


def worst_case_fields(seed: int = 0) -> dict:
    """Every step's fields at their caps (four lines and three sources per prism); a « a | b » field
    takes each part at its cap. The three prisms and the media's one are drawn from the catalogue."""
    rng = random.Random(seed)
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    text = lambda step, name: _chars(rng, cap(step, name))   # noqa: E731
    parts = lambda step, name: " | ".join(_chars(rng, c) for _, c in agent._PART_CAPS[(step, name)])   # noqa: E731
    prisms = rng.sample(PRISM_IDS, 3)
    media = rng.choice(prisms)
    axe = {"question": _ask(rng, cap("axe", "question")), "article_question": _ask(rng, 80),
           "subject": text("axe", "subject"), **{f"prism{i}": p for i, p in enumerate(prisms, 1)},
           "media": media, "media_grounding": text("axe", "media_grounding"), "closing": _ask(rng, cap("axe", "closing"))}
    position = {"kicker": text("position", "kicker"), "title": text("position", "title"), "lead": text("position", "lead"),
                **{f"card{i}": parts("position", f"card{i}") for i in (1, 2, 3, 4)}}
    source = lambda: _chars(rng, agent._SOURCE_MAX)   # noqa: E731
    prismes = {f"p{i}": {"question": _ask(rng, cap("prismes", "question")),
                         **{f"line{k}": text("prismes", f"line{k}") for k in (1, 2, 3, 4)},
                         "sources": " ; ".join(source() for _ in range(agent._SOURCES_MAX)),
                         "media_note": text("prismes", "media_note") if p == media else ""}
               for i, p in enumerate(prisms, 1)}
    matrice = {"title": _ask(rng, cap("matrice", "title")), **{f"col{i}": parts("matrice", f"col{i}") for i in (1, 2, 3)}}
    fixed = "Trois regards sur  ; à vous d'en juger."
    hook = {"title": _ask(rng, cap("hook", "title")),
            "promise": f"Trois regards sur {_chars(rng, cap('hook', 'promise') - len(fixed))} ; à vous d'en juger."}
    return {"axe": axe, "position": position, "prismes": prismes, "matrice": matrice, "hook": hook,
            "writing": FIELDS["writing"]}


def worst_case_deck(seed: int = 0) -> dict:
    return agent.assemble(_fragments(worst_case_fields(seed)))


def test_the_worst_case_deck_breaks_no_hard_rule():
    for seed in range(4):
        fields = worst_case_fields(seed)
        frags = _fragments(fields)
        for name in ("axe", "position", "matrice", "hook"):
            assert agent.field_errors(name, fields[name], {} if name == "axe" else frags, None)[0] == [], (seed, name)
        for slot, f in fields["prismes"].items():
            assert agent.field_errors("prismes", f, frags, None, slot)[0] == [], (seed, slot)


_LINES = """() => { const box = (s) => ['paddingTop', 'paddingBottom', 'borderTopWidth', 'borderBottomWidth']
    .reduce((a, k) => a + parseFloat(s[k]), 0);
  const n = (sel) => [...document.querySelectorAll(sel)].map(e => { const s = getComputedStyle(e);
    return Math.round((e.getBoundingClientRect().height - box(s)) / parseFloat(s.lineHeight)); });
  const bottom = Math.max(0, ...[...document.querySelectorAll('.stage *')].map(e => e.getBoundingClientRect().bottom));
  const cut = [...document.querySelectorAll('.col, .col *')]
    .filter(e => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1).map(e => e.className);
  return {head: n('.head'), lines: n('.ln-t'), badge: n('.badge'), title: n('.mh'), bottom, cut,
          page: document.documentElement.scrollWidth}; }"""


@pytest.mark.parametrize("seed", range(4))
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
