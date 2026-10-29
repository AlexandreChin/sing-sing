"""The CADRAGE & LOGIQUE carousel: the model, the step rules, the cascade (with the
model call faked) and the HTML it renders. The deck in tests/fixtures/cadrage_deck.json
is the one approved for samples/videos/figaro_orientation_scolaire."""
import copy
import html
import json
from pathlib import Path

import pytest

from agent import cadrage_adapt_agent as agent
from agent.carousel_steps.steps import Option
from extractors.cadrage import extract
from models.cadrage_presentation import CadragePresentation
from renderer.instagram_carousel import cadrage as renderer
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/cadrage_deck.json").read_text(encoding="utf-8"))


def _note(n: dict) -> str:
    return f"{'remarque' if n['kind'] == 'remark' else 'source'} | {n['text']}"


def option_fields(deck: dict) -> dict[str, dict]:
    """Each step's flat option fields, cut from the finished deck."""
    c, t, a, d, b = deck["constat"], deck["these"], deck["angle_mort"], deck["depassement"], deck["boussole"]
    figs = [f"{f['value']} | {f['label']} | {f['compare']}".rstrip(" |") for f in c["figures"]]
    figs += [""] * (4 - len(figs))
    notes = lambda items: dict(zip(("note1", "note2", "note3"), [_note(n) for n in items] + ["", "", ""]))  # noqa: E731
    return {
        "axe": dict(deck["axe"]),
        "constat": {"title": c["title"], **dict(zip(("fig1", "fig2", "fig3", "fig4"), figs)),
                    "claim": c["claim"], "detail": c["detail"]},
        "these": {"title": t["title"], "these_claim": t["these"]["claim"], "these_detail": t["these"]["detail"],
                  "solution_claim": t["solution"]["claim"], "solution_detail": t["solution"]["detail"],
                  **notes(t["notes"])},
        "angle_mort": {k: a[k] for k in ("title", "claim", "detail")} | notes(a["notes"])
        | {"second_claim": a["second"]["claim"], "second_detail": a["second"]["detail"],
           **dict(zip(("second_note1", "second_note2"), [_note(n) for n in a["second_notes"]] + ["", ""]))},
        "depassement": {"title": d["title"], "lead": d["lead"],
                        **{f"lever{i}": f"{lv['title']} | {lv['detail']}" for i, lv in enumerate(d["levers"], 1)},
                        "lever1_note": _note(d["levers"][0]["note"]) if d["levers"][0].get("note") else ""},
        "boussole": {"title": b["title"],
                     **{f"{k}{i}": o[k] for i, o in enumerate(b["options"], 1) for k in ("question", "pro", "con")}},
        "hook": {"title": deck["hook"]["title"], "promise": deck["hook"]["promise"]},
        "writing": {"caption": deck["caption"]},
    }


FIELDS = option_fields(DECK)


# ── model and fragments ─────────────────────────────────────────────────────

AXE = {"title": "Évaluer chaque année ou plus rarement", "variable": "la fréquence de l'évaluation",
       "position1": "évaluer chaque année", "position2": "évaluer plus rarement",
       "thesis": "L'évaluation annuelle protège les élèves."}


def test_a_deck_without_an_axe_still_validates():
    assert CadragePresentation.model_validate({k: v for k, v in DECK.items() if k != "axe"}).axe is None


def test_a_deck_keeps_its_axe():
    pres = CadragePresentation.model_validate(DECK | {"axe": AXE})
    assert pres.axe.position2 == "évaluer plus rarement"


def test_the_axe_step_comes_first():
    assert agent.STEPS[0].name == "axe"
    assert agent.STEP_NAMES == ["axe", "constat", "these", "angle_mort", "depassement", "boussole", "hook"]


def test_every_step_has_its_prompt():
    for s in agent.STEPS:
        assert Path(f"agent/prompts/cadrage_steps/{s.n}_{s.name}.md").exists(), s.name


def test_the_axe_needs_all_five_fields_and_two_distinct_positions():
    hard = lambda **kw: agent.field_errors("axe", {**FIELDS["axe"], **kw}, {}, None)[0]  # noqa: E731
    assert hard() == []
    assert any("position2" in e for e in hard(position2=FIELDS["axe"]["position1"]))
    assert any("title" in e and "empty" in e for e in hard(title=""))


def test_axe_caps_are_hard():
    hard = lambda **kw: agent.field_errors("axe", {**FIELDS["axe"], **kw}, {}, None)[0]  # noqa: E731
    long = lambda n: " ".join(["mot"] * n)  # noqa: E731
    for name, cap in (("title", 14), ("variable", 16), ("position1", 12), ("position2", 12), ("thesis", 20)):
        assert any(name in e for e in hard(**{name: long(cap + 1)})), name


def test_the_axe_fragment():
    frag = agent.to_fragment(agent.STEP_BY_NAME["axe"], Option(id="a", slot="a", reason="", fields=FIELDS["axe"]))
    assert frag == {"axe": FIELDS["axe"]}


def test_the_deck_validates():
    pres = CadragePresentation.model_validate(DECK)
    assert [f.value for f in pres.constat.figures] == ["95%", "21%", "× 8", "0,5 Md€"]
    assert [n.kind for n in pres.angle_mort.notes] == ["remark", "source"]


def test_fragments_rebuild_the_deck():
    frags = {s.name: agent.to_fragment(s, Option(id="a", slot="a", reason="", fields=FIELDS[s.name]))
             for s in agent.STEPS}
    assert CadragePresentation.model_validate(agent.assemble(frags)) == CadragePresentation.model_validate(DECK)


def test_an_empty_figure_or_note_is_left_out():
    fields = {**FIELDS["constat"], "fig3": "", "fig4": ""}
    frag = agent.to_fragment(agent.STEP_BY_NAME["constat"], Option(id="a", slot="a", reason="", fields=fields))
    assert len(frag["constat"]["figures"]) == 2
    fields = {**FIELDS["these"], "note2": "", "note3": ""}
    frag = agent.to_fragment(agent.STEP_BY_NAME["these"], Option(id="a", slot="a", reason="", fields=fields))
    assert [n["kind"] for n in frag["these"]["notes"]] == ["remark"]


# ── rules ───────────────────────────────────────────────────────────────────

def hard(step, **changes):
    return agent.field_errors(step, {**FIELDS[step], **changes}, {}, None)[0]


def test_the_approved_deck_breaks_no_hard_rule():
    for name, fields in FIELDS.items():
        assert agent.field_errors(name, fields, {}, None)[0] == [], name


def test_a_figure_needs_a_value_and_a_label():
    assert any("fig1" in e for e in hard("constat", fig1="95%"))
    assert hard("constat", fig1="95% | d'admission") == []


def test_two_figures_are_required():
    assert any("fig2 is empty" in e for e in hard("constat", fig2=""))


def test_the_second_card_of_the_angle_mort_is_required_and_checked():
    assert any("second_claim is empty" in e for e in hard("angle_mort", second_claim=""))
    assert any("second_note1" in e for e in hard("angle_mort", second_note1="Boudon : les effets"))
    assert hard("angle_mort", second_note2="") == []


def test_a_note_names_its_kind():
    assert any("note1" in e for e in hard("these", note1="Le Céreq : l'insertion"))
    assert any("note1" in e for e in hard("angle_mort", note1="lien | "))
    assert hard("these", note1="source | **Le Céreq** : l'insertion") == []


def test_a_lever_note_is_optional_but_typed():
    assert hard("depassement", lever1_note="") == []
    assert any("lever1_note" in e for e in hard("depassement", lever1_note="Contestation : un contexte"))


def test_a_lever_needs_a_title_and_a_detail():
    assert any("lever2" in e for e in hard("depassement", lever2="La mixité sociale"))


def test_caps_are_hard():
    assert any("hook.title" in e for e in hard("hook", title="x" * 65))
    assert any("boussole.pro1" in e for e in hard("boussole", pro1="mot " * 17))


def test_an_accusing_word_is_hard_unless_quoted():
    assert any("accusing" in e for e in hard("angle_mort", claim="Un discours trompeur sur le mérite."))
    assert hard("angle_mort", claim="L'invité parle d'un « mensonge » collectif.") == []


def test_a_figure_missing_from_the_source_is_flagged_not_blocked():
    errors, flags = agent.field_errors("constat", FIELDS["constat"], {}, "On a 95 % d'admission.")
    assert errors == [] and any("21%" in f for f in flags)
    assert not any("95%" in f for f in flags)


def test_the_caption_needs_four_hashtags():
    assert hard("writing") == []
    assert any("hashtag" in e for e in hard("writing", caption=DECK["caption"].replace("#espritcritique", "")))


# ── the cascade, the model call faked ───────────────────────────────────────

class FakeCalls:
    def __init__(self):
        self.labels, self.errors = [], {}

    def __call__(self, user_message, schema, validator, no_api=False, label="", system=None):
        self.labels.append(label)
        fields = copy.deepcopy(FIELDS[label])
        data = ({"options": [{**fields, "reason": "r"}, {**fields, "reason": "r2"}, {**fields, "reason": "r3"}],
                 "recommended": [0]} if label != "writing" else fields)
        self.errors[label] = validator(data)
        return data


@pytest.fixture
def fake(monkeypatch):
    calls = FakeCalls()
    monkeypatch.setattr(agent, "_call_with_retry", calls)
    return calls


def test_unattended_runs_eight_steps_and_rebuilds_the_deck(fake, tmp_path):
    pres = agent.adapt(full(), steps_dir=tmp_path / "adapt_steps")
    assert fake.labels == [s.name for s in agent.STEPS]
    assert all(e == [] for e in fake.errors.values())
    assert pres.model_dump() == CadragePresentation.model_validate(DECK).model_dump()


def test_guided_pauses_at_the_axe(fake, tmp_path, capsys):
    assert agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", guided=True) is None
    assert fake.labels == ["axe"]
    assert agent.pending_step(tmp_path / "adapt_steps") == "axe"
    assert "[axe]" in capsys.readouterr().out


def test_a_pick_then_a_fix_rewrites_one_field_without_regenerating(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    agent.fix(full(), steps, "constat.fig1", "96% | d'admission à l'université | 40 % en Norvège")
    assert fake.labels == before
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before                      # the later steps were re-stamped, not rerun
    assert pres.constat.figures[0].value == "96%"


def test_fix_reaches_the_axe(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    agent.fix(full(), steps, "axe.position1", "sélectionner très tôt")
    assert fake.labels == before
    assert agent.adapt(full(), steps_dir=steps).axe.position1 == "sélectionner très tôt"
    assert fake.labels == before


def test_choose_refuses_a_step_without_options(fake, tmp_path):
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), tmp_path / "adapt_steps", "writing", ["a"], {})


def test_fix_names_a_known_field(fake, tmp_path):
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), tmp_path / "adapt_steps", "invisible.statement", "x")


# ── the render ──────────────────────────────────────────────────────────────

def test_seven_slides_are_rendered(tmp_path):
    doc = extract(full(), CadragePresentation.model_validate(DECK))
    paths = renderer.generate_html(doc, tmp_path / "html")
    assert [p.stem for p in paths] == ["01_hook", "02_constat", "03_these", "04_angle_mort",
                                       "05_depassement", "06_boussole", "07_cta"]
    texts = {p.stem: html.unescape(p.read_text(encoding="utf-8")) for p in paths}
    assert "Décryptage d'une prise de position" in texts["01_hook"]
    assert "0,5 Md€" in texts["02_constat"]
    assert texts["03_these"].count('class="src"') == 2
    assert "Un <strong>destin social</strong> qui se fige davantage" in texts["04_angle_mort"].replace("⁠", "")
    assert "Raymond Boudon" in texts["04_angle_mort"] and texts["04_angle_mort"].count('class="card"') == 2
    assert "pointer" in texts["06_boussole"] and "data-perch" not in texts["06_boussole"].split("<body>")[1]
    assert "Vous jugez." in texts["07_cta"]
