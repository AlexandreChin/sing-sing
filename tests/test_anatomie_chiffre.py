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


# ── flat option fields, cut from the deck ───────────────────────────────────

import copy  # noqa: E402

import pytest  # noqa: E402

from agent import anatomie_chiffre_adapt_agent as agent  # noqa: E402
from agent.carousel_steps.steps import Option  # noqa: E402


def _note(n: dict) -> str:
    return f"{'remarque' if n['kind'] == 'remark' else 'source'} | {n['text']}"


def _fig(f: dict) -> str:
    return f"{f['value']} | {f['label']} | {f['compare']}".rstrip(" |")


def option_fields(deck: dict) -> dict[str, dict]:
    pad = lambda items, n: list(items) + [""] * (n - len(items))  # noqa: E731
    ax, c, r, a, lc = deck["axe"], deck["chiffres"], deck["recit"], deck["angle_mort"], deck["lectures"]
    c1, c2 = a["cards"]
    return {
        "axe": {"fait": ax["fait"], **{f"lecture{i}": f"{x['nom']} | {x['formule']}" for i, x in enumerate(ax["readings"], 1)}},
        "chiffres": {"claim": c["claim"], "detail": c["detail"],
                     **dict(zip(("fig1", "fig2", "fig3", "fig4"), pad([_fig(f) for f in c["figures"]], 4))),
                     "note1": _note(c["note"]) if c["note"] else ""},
        "recit": {"title": r["title"],
                  **dict(zip(("row1", "row2", "row3", "row4"),
                             pad([f"{x['kind']} | {x['text']} | {x['basis']}" for x in r["rows"]], 4)))},
        "angle_mort": {"title": a["title"],
                       "claim1": c1["claim"], "detail1": c1["detail"], "note1": _note(c1["notes"][0]),
                       "ouvre1": ",".join(map(str, c1["opens"])),
                       "claim2": c2["claim"], "detail2": c2["detail"], "note2": _note(c2["notes"][0]),
                       "ouvre2": ",".join(map(str, c2["opens"]))},
        "lectures": {"title": lc["title"], "lead": lc["lead"],
                     **{f"lecture{i}": f"{x['nom']} | {x['voir']} | {x['ou']}" for i, x in enumerate(lc["rows"], 1)}},
        "hook": {"title": deck["hook"]["title"], "promise": deck["hook"]["promise"]},
        "writing": {"caption": deck["caption"]},
    }


FIELDS = option_fields(DECK)
ARTICLE = Path("samples/articles/bfm_americains/bfm_americains.txt")


def _opt(step):
    return Option(id="a", slot="a", reason="", fields=FIELDS[step])


def _frags(*steps):
    return {s: agent.to_fragment(agent.STEP_BY_NAME[s], _opt(s)) for s in steps}


def test_the_steps_come_in_order():
    assert agent.STEP_NAMES == ["axe", "chiffres", "recit", "angle_mort", "lectures", "hook"]
    assert agent.STEPS[-1].name == "writing"


def test_the_fragments_rebuild_the_deck():
    frags = {s.name: agent.to_fragment(s, _opt(s.name)) for s in agent.STEPS}
    assert AnatomieChiffrePresentation.model_validate(agent.assemble(frags)) == AnatomieChiffrePresentation.model_validate(DECK)


def test_empty_figures_rows_and_notes_are_left_out():
    f = agent.to_fragment(agent.STEP_BY_NAME["chiffres"],
                          Option(id="a", slot="a", reason="", fields={**FIELDS["chiffres"], "fig4": "", "note1": ""}))
    assert len(f["chiffres"]["figures"]) == 3 and f["chiffres"]["note"] is None
    f = agent.to_fragment(agent.STEP_BY_NAME["recit"],
                          Option(id="a", slot="a", reason="", fields={**FIELDS["recit"], "row4": ""}))
    assert len(f["recit"]["rows"]) == 3


# ── rules ───────────────────────────────────────────────────────────────────

def hard(step, fragments=None, **changes):
    return agent.field_errors(step, {**FIELDS[step], **changes}, fragments or {}, None)[0]


def flags(step, article=None, fragments=None, **changes):
    return agent.field_errors(step, {**FIELDS[step], **changes}, fragments or {}, article)[1]


def test_the_sample_deck_breaks_no_hard_rule():
    frags = _frags("axe", "chiffres", "recit", "angle_mort", "lectures")
    for name, fields in FIELDS.items():
        assert agent.field_errors(name, fields, frags, None)[0] == [], name


def test_the_axe_needs_three_named_distinct_readings():
    assert any("lecture2 is empty" in e for e in hard("axe", lecture2=""))
    assert any("lecture1" in e and "formula" in e for e in hard("axe", lecture1="Un effet d'âge | "))
    assert any("share a name" in e for e in hard("axe", lecture2=FIELDS["axe"]["lecture1"]))
    assert any("lecture1: the name is 29" in e for e in hard("axe", lecture1="x" * 29 + " | formule"))


def test_a_figure_needs_a_value_and_a_label_and_a_short_value():
    assert any("fig1" in e for e in hard("chiffres", fig1="2022"))
    assert any("fig1" in e and "value is 10" in e for e in hard("chiffres", fig1="1234567890 | période"))
    assert hard("chiffres", fig4="? | taille de l'échantillon | non précisé") == []
    assert any("fig3 is empty" in e for e in hard("chiffres", fig3=""))


def test_a_recit_row_has_a_known_type_and_row1_is_data():
    assert any("row2" in e and "type" in e for e in hard("recit", row2="opinion | texte | base"))
    assert any("row1 must be a « donnee »" in e for e in hard("recit", row1="explication | « x » | y"))
    assert any("row3 is empty" in e for e in hard("recit", row3=""))
    assert hard("recit", row4="") == []


def test_ouvre_must_cover_every_reading():
    assert hard("angle_mort") == []
    assert any("cover the three" in e for e in hard("angle_mort", ouvre1="1,2", ouvre2="1,2"))
    for bad in ("1,1", "1,4", "1", "a,b", "0,1"):
        assert any("ouvre1" in e for e in hard("angle_mort", ouvre1=bad)), bad
    assert any("ouvre2 is empty" in e for e in hard("angle_mort", ouvre2=""))


def test_slides_4_and_5_hold_no_digit():
    assert any("angle_mort.detail1" in e and "digit" in e for e in hard("angle_mort", detail1="Une médiane de 2025 ne dit rien."))
    assert any("angle_mort.note1" in e for e in hard("angle_mort", note1="source | Fed : enquête de 2025"))
    assert any("lectures.lead" in e and "digit" in e for e in hard("lectures", lead="Un écart de 15 fois."))
    assert any("lectures.lecture1" in e and "digit" in e for e in hard("lectures", lecture1="Un effet d'âge | voir en 2025 | Fed"))


def test_lecture_names_must_equal_the_axe_names():
    frags = _frags("axe")
    assert hard("lectures", frags) == []
    bad = "Un effet de cohorte | Chaque génération s'enrichit | Fed"
    assert any("lecture1" in e and "axe's reading 1" in e for e in hard("lectures", frags, lecture1=bad))
    assert hard("lectures", {}, lecture1=bad) == []     # no axe, nothing to compare


def test_notes_name_their_kind():
    assert any("note1" in e for e in hard("angle_mort", note1="Fed : séries"))
    assert any("note1" in e for e in hard("chiffres", note1="lien | "))
    assert hard("chiffres", note1="") == []


def test_accusing_words_are_hard_unless_quoted():
    assert any("accusing" in e for e in hard("angle_mort", claim1="Une médiane trompeuse."))
    assert hard("angle_mort", claim1="Le patrimoine selon un « biais » cité.") == []


def test_caps_are_hard():
    assert any("hook.title" in e for e in hard("hook", title="x" * 65))
    assert any("recit.row2: the text" in e for e in hard("recit", row2="explication | " + "x" * 111 + " | base"))
    assert any("lectures.lead" in e for e in hard("lectures", lead="x" * 91))


def test_a_figure_missing_from_the_source_is_flagged_not_blocked():
    article = ARTICLE.read_text(encoding="utf-8")
    assert not any("505.000" in f for f in flags("chiffres", article))
    f = flags("chiffres", article, fig1="999.999 $ | plus de 75 ans | +37 % depuis 2022")
    assert any("999.999" in x for x in f)
    assert hard("chiffres", fig1="999.999 $ | plus de 75 ans | +37 % depuis 2022") == []


def test_a_derived_figure_must_say_calcule():
    article = ARTICLE.read_text(encoding="utf-8")
    assert any("999.999" in f for f in flags("chiffres", article, fig4="999.999 $ | gain des plus de 75 ans | gain estimé"))
    assert not any("999.999" in f for f in flags("chiffres", article, fig4="999.999 $ | gain des plus de 75 ans | calculé"))


def test_a_quoted_passage_must_be_in_the_source():
    article = ARTICLE.read_text(encoding="utf-8")
    assert not any("word for word" in f for f in flags("recit", article))
    assert any("word for word" in f for f in flags("recit", article, row2="explication | « le ciel est bleu » | un économiste"))


def test_a_recit_with_only_data_is_flagged_not_blocked():
    only = {"row2": "donnee | Le rapport est de × 15. | Fed", "row3": "donnee | Le total est de 215.900 $. | Fed", "row4": ""}
    assert any("only data" in f for f in flags("recit", **only))
    assert hard("recit", **only) == []
    assert not any("only data" in f for f in flags("recit"))


def test_the_article_reading_should_share_a_word_with_the_story():
    frags = _frags("axe")
    assert not any("key word" in f for f in flags("recit", fragments=frags))
    off = {"row2": "explication | « Les pandas mangent du bambou » | un zoologue",
           "row3": "interpretation | Un cadrage sans rapport. | un zoologue", "row4": ""}
    assert any("key word" in f for f in flags("recit", fragments=frags, **off))
    assert not any("key word" in f for f in flags("recit", **off))   # no axe, nothing to compare


def test_the_hook_flags_a_missing_promise_form():
    assert flags("hook") == []
    assert any("promise" in f for f in flags("hook", promise="Un écart entre générations."))
    assert any("raw figure" in f for f in flags("hook", title="Un écart de patrimoine"))


def test_the_caption_needs_four_hashtags():
    assert hard("writing") == []
    assert any("hashtag" in e for e in hard("writing", caption=DECK["caption"].replace("#espritcritique", "")))
