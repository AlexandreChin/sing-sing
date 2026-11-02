"""The ANATOMIE D'UN CHIFFRE carousel: the model, the step rules, the cascade (with the
model call faked) and the HTML it renders. The deck in tests/fixtures/anatomie_chiffre_deck.json
is written from samples/articles/bfm_americains."""
import json
from pathlib import Path

import importlib

from extractors.anatomie_chiffre import extract
from extractors.registry import FORMATS
from models.anatomie_chiffre_presentation import AnatomieChiffrePresentation
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/anatomie_chiffre_deck.json").read_text(encoding="utf-8"))


# ── model, extractor, registry ──────────────────────────────────────────────

def test_the_deck_validates():
    pres = AnatomieChiffrePresentation.model_validate(DECK)
    assert [f.value for f in pres.boite_noire.figures][:2] == ["2022-2025", "215.900 $"]
    assert pres.eclairage.ratio.value == "× 15"
    assert len(pres.variable.facts) == 3


def test_a_deck_without_a_variable_still_validates():
    assert AnatomieChiffrePresentation.model_validate({k: v for k, v in DECK.items() if k != "variable"}).variable is None


def test_the_extractor_passes_the_presentation_through():
    pres = AnatomieChiffrePresentation.model_validate(DECK)
    assert extract(full(), pres).presentation == pres


def test_the_format_is_registered():
    names = FORMATS["anatomie_chiffre"]
    assert names[1] == "extractors.anatomie_chiffre"
    assert importlib.import_module(names[1]).extract is extract


# ── flat option fields, cut from the deck ───────────────────────────────────

from agent import anatomie_chiffre_adapt_agent as agent  # noqa: E402
from agent.carousel_steps.steps import Option  # noqa: E402


def _note(n: dict) -> str:
    return f"{'remarque' if n['kind'] == 'remark' else 'source'} | {n['text']}"


def _fig(f: dict) -> str:
    return f"{f['value']} | {f['label']} | {f['compare']}".rstrip(" |")


def option_fields(deck: dict) -> dict[str, dict]:
    v, b, e, p = deck["variable"], deck["boite_noire"], deck["eclairage"], deck["perimetre"]
    pad = lambda items, n: list(items) + [""] * (n - len(items))  # noqa: E731
    part = lambda x: f"{x['value']} | {x['label']}"  # noqa: E731
    return {
        "variable": {k: v[k] for k in ("title", "variable", "pole_a", "pole_b", "proxy", "question", "implication")}
        | dict(zip(("fact1", "fact2", "fact3"), pad(v["facts"], 3)))
        | dict(zip(("look1", "look2"), pad([_note(n) for n in v["looks"]], 2))),
        "boite_noire": dict(zip(("fig1", "fig2", "fig3", "fig4"), pad([_fig(f) for f in b["figures"]], 4)))
        | {"source_card": _fig(b["source_card"]), "claim": b["claim"], "detail": b["detail"]},
        "eclairage": {"claim": e["claim"], "detail": e["detail"], "part1": part(e["part1"]),
                      "part2": part(e["part2"]), "ratio": part(e["ratio"]),
                      "note1": _note(e["note"]) if e["note"] else ""},
        "perimetre": {"title": p["title"],
                      "claim1": p["statistique"]["claim"], "detail1": p["statistique"]["detail"],
                      "note1": _note(p["statistique"]["notes"][0]),
                      "claim2": p["periode"]["claim"], "detail2": p["periode"]["detail"],
                      "note2": _note(p["periode"]["notes"][0])},
        "hook": {"title": deck["hook"]["title"], "promise": deck["hook"]["promise"]},
        "writing": {"caption": deck["caption"]},
    }


FIELDS = option_fields(DECK)
ARTICLE = Path("samples/articles/bfm_americains/bfm_americains.txt")


def _opt(step):
    return Option(id="a", slot="a", reason="", fields=FIELDS[step])


def test_the_steps_come_in_order():
    assert agent.STEP_NAMES == ["variable", "boite_noire", "eclairage", "perimetre", "hook"]
    assert agent.STEPS[-1].name == "writing"


def test_the_fragments_rebuild_the_deck():
    frags = {s.name: agent.to_fragment(s, _opt(s.name)) for s in agent.STEPS}
    assert AnatomieChiffrePresentation.model_validate(agent.assemble(frags)) == AnatomieChiffrePresentation.model_validate(DECK)


def test_empty_figures_facts_and_notes_are_left_out():
    f = agent.to_fragment(agent.STEP_BY_NAME["boite_noire"],
                          Option(id="a", slot="a", reason="", fields={**FIELDS["boite_noire"], "fig3": "", "fig4": ""}))
    assert len(f["boite_noire"]["figures"]) == 2
    f = agent.to_fragment(agent.STEP_BY_NAME["variable"],
                          Option(id="a", slot="a", reason="", fields={**FIELDS["variable"], "fact3": "", "look2": ""}))
    assert len(f["variable"]["facts"]) == 2 and len(f["variable"]["looks"]) == 1
    f = agent.to_fragment(agent.STEP_BY_NAME["eclairage"],
                          Option(id="a", slot="a", reason="", fields={**FIELDS["eclairage"], "note1": ""}))
    assert f["eclairage"]["note"] is None


# ── rules ───────────────────────────────────────────────────────────────────

def hard(step, **changes):
    return agent.field_errors(step, {**FIELDS[step], **changes}, {}, None)[0]


def flags(step, article=None, fragments=None, **changes):
    return agent.field_errors(step, {**FIELDS[step], **changes}, fragments or {}, article)[1]


def test_the_sample_deck_breaks_no_hard_rule():
    for name, fields in FIELDS.items():
        assert agent.field_errors(name, fields, {}, None)[0] == [], name


def test_a_figure_needs_a_value_and_a_label_and_a_short_value():
    assert any("fig1" in e for e in hard("boite_noire", fig1="2022"))
    assert any("fig1" in e and "characters" in e for e in hard("boite_noire", fig1="1234567890 | période"))
    assert hard("boite_noire", fig3="? | taille de l'échantillon | non précisé") == []


def test_the_source_card_names_a_chain():
    assert any("source_card is empty" in e for e in hard("boite_noire", source_card=""))
    assert any("source_card" in e and "max 24" in e for e in hard("boite_noire", source_card="Fed → WSJ → BFM → Reuters → X | source ?"))


def test_two_figures_are_required():
    assert any("fig2 is empty" in e for e in hard("boite_noire", fig2=""))


def test_the_parts_and_the_ratio_are_typed():
    assert any("part1" in e for e in hard("eclairage", part1="505.000 $"))
    assert any("ratio" in e and "characters" in e for e in hard("eclairage", ratio="un rapport de quinze | x"))


def test_notes_name_their_kind():
    assert any("note1" in e for e in hard("perimetre", note1="Fed : séries"))
    assert any("look1" in e for e in hard("variable", look1="Fed : séries"))
    assert any("note1" in e for e in hard("eclairage", note1="lien | "))
    assert hard("eclairage", note1="") == []


def test_slide_4_adds_no_digit():
    assert any("perimetre.detail1" in e and "digit" in e for e in hard("perimetre", detail1="Une médiane de 2025 ne dit rien."))
    assert any("perimetre.note1" in e for e in hard("perimetre", note1="source | Fed : enquête de 2025"))


def test_slide_5_adds_no_digit_outside_the_source_column():
    assert any("variable.implication" in e and "digit" in e for e in hard("variable", implication="Un écart de 15 fois."))
    assert hard("variable", fact1="Les moins de 35 ans propriétaires : 35,6 % en 2025.") == []
    assert hard("variable", question="De quoi dépend le patrimoine à 35 ans ?") == []   # an age names a group


def test_slide_5_never_concludes():
    assert any("concludes" in e for e in hard("variable", implication="Le chiffre prouve que le moment compte."))
    assert any("concludes" in e for e in hard("variable", proxy="L'écart est donc un écart de moment."))


def test_the_question_ends_with_a_question_mark_and_is_not_a_choice():
    assert any("question" in e and "?" in e for e in hard("variable", question="De quoi dépend le patrimoine."))
    assert any("choice" in f for f in flags("variable", question="Est-ce le moment ou le revenu ?"))
    assert not any("choice" in f for f in flags("variable"))


def test_the_poles_must_differ():
    assert any("pole_b" in e for e in hard("variable", pole_b=FIELDS["variable"]["pole_a"]))


def test_accusing_words_are_hard_unless_quoted():
    assert any("accusing" in e for e in hard("perimetre", claim1="Une médiane trompeuse."))
    assert hard("perimetre", claim1="Le patrimoine selon un « biais » cité.") == []


def test_caps_are_hard():
    assert any("hook.title" in e for e in hard("hook", title="x" * 65))
    assert any("variable.proxy" in e for e in hard("variable", proxy="mot " * 33))


def test_a_figure_missing_from_the_source_is_flagged_not_blocked():
    article = ARTICLE.read_text(encoding="utf-8")
    assert flags("boite_noire", article) == [] or not any("215.900" in f for f in flags("boite_noire", article))
    f = flags("boite_noire", article, fig2="999.999 $ | patrimoine médian | la moitié a plus")
    assert any("999.999" in x for x in f)
    assert hard("boite_noire", fig2="999.999 $ | patrimoine médian | la moitié a plus") == []


def test_a_recomputed_ratio_must_say_so():
    article = ARTICLE.read_text(encoding="utf-8")
    assert any("recomputed" in f for f in flags("eclairage", article, ratio="× 8 | écart entre les deux"))
    assert not any("recomputed" in f for f in flags("eclairage", article, ratio="× 8 | écart calculé"))
    assert any("digits" in f for f in flags("eclairage", article, ratio="quinze | rapport"))


def test_a_variable_without_a_fact_is_flagged():
    assert any("no fact" in f for f in flags("variable", fact1="", fact2="", fact3=""))


def test_a_quoted_fact_must_be_in_the_source():
    article = ARTICLE.read_text(encoding="utf-8")
    assert not any("word for word" in f for f in flags("variable", article))
    assert any("word for word" in f for f in flags("variable", article, fact1="Selon la Fed, « le ciel est bleu »."))


def test_an_off_variable_claim_is_flagged_not_blocked():
    frags = {"variable": agent.to_fragment(agent.STEP_BY_NAME["variable"], _opt("variable"))}
    f = agent.field_errors("eclairage", {**FIELDS["eclairage"], "claim": "Les pandas mangent du bambou."}, frags, None)
    assert f[0] == [] and any("shares no key word with the variable" in x for x in f[1])
    assert not [x for x in agent.field_errors("eclairage", FIELDS["eclairage"], frags, None)[1] if "variable" in x]
    assert [x for x in agent.field_errors("eclairage", FIELDS["eclairage"], {}, None)[1] if "variable" in x] == []


def test_the_hook_flags_a_missing_promise_form():
    assert flags("hook") == []
    assert any("promise" in f for f in flags("hook", promise="Un écart entre générations."))
    assert any("raw figure" in f for f in flags("hook", title="Un écart de patrimoine"))


def test_the_caption_needs_four_hashtags():
    assert hard("writing") == []
    assert any("hashtag" in e for e in hard("writing", caption=DECK["caption"].replace("#espritcritique", "")))


# ── prompts ─────────────────────────────────────────────────────────────────

import copy  # noqa: E402

import pytest  # noqa: E402


def test_every_step_has_its_prompt():
    for s in agent.STEPS:
        assert Path(f"agent/prompts/anatomie_chiffre_steps/{s.n}_{s.name}.md").exists(), s.name
    assert Path("agent/prompts/anatomie_chiffre_steps/0_shared.md").exists()


def test_the_shared_prompt_lists_every_step():
    shared = Path("agent/prompts/anatomie_chiffre_steps/0_shared.md").read_text(encoding="utf-8")
    for name in ("La variable", "La boîte noire", "La zone d'éclairage", "Le périmètre exclu", "L'accroche", "La rédaction"):
        assert name in shared, name
    assert "Six étapes" in shared


# ── the cascade, the model call faked ───────────────────────────────────────

class FakeCalls:
    def __init__(self):
        self.labels, self.errors, self.messages = [], {}, []

    def __call__(self, user_message, schema, validator, no_api=False, label="", system=None):
        self.labels.append(label)
        self.messages.append(user_message)
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


def test_unattended_runs_six_steps_and_rebuilds_the_deck(fake, tmp_path):
    pres = agent.adapt(full(), steps_dir=tmp_path / "adapt_steps")
    assert fake.labels == [s.name for s in agent.STEPS]
    assert all(e == [] for e in fake.errors.values())
    assert pres.model_dump() == AnatomieChiffrePresentation.model_validate(DECK).model_dump()


def test_guided_pauses_at_the_variable(fake, tmp_path, capsys):
    assert agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", guided=True) is None
    assert fake.labels == ["variable"]
    assert agent.pending_step(tmp_path / "adapt_steps") == "variable"
    assert "[variable]" in capsys.readouterr().out


def test_choose_picks_and_the_run_goes_on(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, guided=True)
    assert agent.choose(full(), steps, "variable", ["b"], {"b.question": "Qu'est-ce qui fait le patrimoine à 35 ans ?"}) == []
    agent.adapt(full(), steps_dir=steps, guided=True, stop_after="variable")
    assert agent.adapt(full(), steps_dir=steps, guided=True) is None
    assert fake.labels == ["variable", "boite_noire"] and agent.pending_step(steps) == "boite_noire"


def test_choose_returns_hard_failures_as_warnings(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, guided=True)
    warnings = agent.choose(full(), steps, "variable", ["a"], {"a.question": "De quoi dépend le patrimoine."})
    assert any("question" in w for w in warnings)


def test_choose_refuses_unknown_options_fields_and_steps(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, guided=True)
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), steps, "writing", ["a"], {})
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), steps, "variable", ["a"], {"a.nope": "x"})
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), steps, "variable", ["z"], {})


def test_more_sets_the_options_aside(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, guided=True)
    new = agent.more(full(), steps, "variable", remark="une autre variable")
    assert len(new.rejected) == 3 and {o.id for o in new.options}.isdisjoint({o.id for o in new.rejected})
    assert "une autre variable" in fake.messages[-1] and "DÉJÀ PROPOSÉES ET ÉCARTÉES" in fake.messages[-1]


def test_a_fix_rewrites_one_field_without_regenerating(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    before = list(fake.labels)
    agent.fix(full(), steps, "boite_noire.fig2", "216.000 $ | patrimoine net médian, 2025 | la moitié des ménages a plus")
    pres = agent.adapt(full(), steps_dir=steps)
    assert fake.labels == before                      # the later steps were re-stamped, not rerun
    assert pres.boite_noire.figures[1].value == "216.000 $"


def test_fix_reaches_the_variable_and_the_caption(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    agent.fix(full(), steps, "variable.pole_a", "Le moment de l'entrée")
    agent.fix(full(), steps, "caption", DECK["caption"] + " Merci.")
    pres = agent.adapt(full(), steps_dir=steps)
    assert pres.variable.pole_a == "Le moment de l'entrée" and pres.caption.endswith("Merci.")


def test_fix_names_a_known_field(fake, tmp_path):
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), tmp_path / "adapt_steps", "invisible.statement", "x")


def test_a_later_step_receives_the_variable_the_article_and_only_its_slice(fake, tmp_path):
    agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text="TEXTE-DE-L-ARTICLE", stop_after="boite_noire")
    first, second = fake.messages
    assert "CHOIX FIXÉS" not in first
    fixed = second.split("CHOIX FIXÉS (ne les réécris pas) :")[1]
    assert FIELDS["variable"]["pole_b"] in fixed
    assert "TEXTE-DE-L-ARTICLE" in first and "TEXTE-DE-L-ARTICLE" in second
    assert "ÉTAPE 2 — LA BOÎTE NOIRE" in second and "ÉTAPE 1 — LA VARIABLE" not in second
    for private in ("review", "ethics", "blend", "distill", "guide"):
        assert f'"{private}"' not in second


# ── CLI wiring ──────────────────────────────────────────────────────────────

def test_the_cli_knows_the_format_and_its_steps():
    import main
    assert main.GUIDED_AGENTS["anatomie_chiffre"] == "agent.anatomie_chiffre_adapt_agent"
    assert len(main._STEP_CHOICES) == len(set(main._STEP_CHOICES))
    assert set(agent.STEP_NAMES) <= set(main._STEP_CHOICES)


# ── the layout: every field at its cap still fits its lines and the slide ───

import random  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

from renderer.instagram_carousel import anatomie_chiffre as renderer  # noqa: E402

_POOL = ("le la les de des du un une et ou à au en par sur pour dans avec sans plus que qui ne pas "
         "l'État patrimoine médiane médian ménages générations générationnelle l'échantillon représentatif "
         "indépendamment propriétaires immobilier portefeuille financiers distribution liquidité remboursements "
         "enquête classes d'âge Réserve fédérale statistiques consommation comparaison variable décomposition").split()


def _chars(rng: random.Random, n: int) -> str:
    """Random French-looking text of at most `n` characters, long words included."""
    out = ""
    while True:
        w = rng.choice(_POOL)
        if len((out + " " + w).strip()) > n:
            return out
        out = (out + " " + w).strip()


def _wordn(rng: random.Random, n: int) -> str:
    """Exactly `n` words, drawn from the pool."""
    return " ".join(rng.choice(_POOL) for _ in range(n))


def _fit(rng, step: str, field: str) -> str:
    kind, cap = agent._CAPS[(step, field)]
    return _chars(rng, cap) if kind == "chars" else _wordn(rng, cap)


def worst_case_fields(seed: int = 0) -> dict[str, dict]:
    """Every step's fields at their caps."""
    rng = random.Random(seed)
    f = lambda step, name: _fit(rng, step, name)   # noqa: E731
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    parts = lambda step, name, value: " | ".join([value] + [_chars(rng, c) for c in agent._PART_CAPS[(step, name)][1:]])  # noqa: E731
    note = lambda step, name: "source | **Fed** : " + _chars(rng, cap(step, name) - 19)   # noqa: E731
    v = {k: f("variable", k) for k in ("title", "variable", "pole_a", "pole_b", "proxy", "implication",
                                       "fact1", "fact2", "fact3")}
    v["question"] = _chars(rng, cap("variable", "question") - 2) + " ?"
    v["look1"], v["look2"] = note("variable", "look1"), note("variable", "look2")
    b = {f"fig{i}": parts("boite_noire", f"fig{i}", "WWWWWWWWW") for i in range(1, 5)}
    b |= {"source_card": parts("boite_noire", "source_card", "WWWWWWWWWWWWWWWWWWWWWWWW"),
          "claim": f("boite_noire", "claim"), "detail": f("boite_noire", "detail")}
    e = {"claim": f("eclairage", "claim"), "detail": f("eclairage", "detail"),
         "part1": parts("eclairage", "part1", "WWWWWWWWW"), "part2": parts("eclairage", "part2", "WWWWWWWWW"),
         "ratio": parts("eclairage", "ratio", "× 15"), "note1": note("eclairage", "note1")}
    p = {k: f("perimetre", k) for k in ("title", "claim1", "detail1", "claim2", "detail2")}
    p |= {k: note("perimetre", k) for k in ("note1", "note2")}
    return {"variable": v, "boite_noire": b, "eclairage": e, "perimetre": p,
            "hook": {"title": f("hook", "title"), "promise": f("hook", "promise")}, "writing": FIELDS["writing"]}


def worst_case_deck(seed: int = 0) -> dict:
    fields = worst_case_fields(seed)
    frags = {s.name: agent.to_fragment(s, Option(id="a", slot="a", reason="", fields=fields[s.name])) for s in agent.STEPS}
    return agent.assemble(frags)


def test_the_worst_case_deck_breaks_no_hard_rule():
    for name, fields in worst_case_fields().items():
        if name != "writing":
            hard_ = [e for e in agent.field_errors(name, fields, {}, None)[0] if "digit" not in e]
            assert hard_ == [], (name, hard_)


_LINES = """() => { const n = (sel) => [...document.querySelectorAll(sel)].map(e =>
    Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)));
  const bottom = Math.max(0, ...[...document.querySelectorAll('.stage *')].map(e => e.getBoundingClientRect().bottom));
  const cut = [...document.querySelectorAll('.fig .n, .chain .n, .bar .row, .ratio, .poles')]
    .filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.className);
  return {subtitle: n('.subtitle'), head: n('.head'), bottom, cut, page: document.documentElement.scrollWidth}; }"""


@pytest.mark.parametrize("seed", range(4))
def test_every_field_at_its_cap_fits_on_the_slide(tmp_path, seed):
    doc = extract(full(), AnatomieChiffrePresentation.model_validate(worst_case_deck(seed)))
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
    # the promise takes three lines at its 100-character cap, then « En juger soi-même. »
    assert all(n <= 4 for n in measured["01_hook"]["subtitle"]), measured["01_hook"]["subtitle"]
    for slide in ("02_boite_noire", "03_eclairage", "04_perimetre", "05_variable"):
        m = measured[slide]
        assert m["page"] <= 1080, (slide, "horizontal overflow", m["page"])
        assert m["cut"] == [], (slide, "a nowrap value is cut", m["cut"])
        assert m["bottom"] <= 1255, (slide, m["bottom"])


# ── the render ──────────────────────────────────────────────────────────────

def test_six_slides_are_rendered(tmp_path):
    import html
    doc = extract(full(), AnatomieChiffrePresentation.model_validate(DECK))
    paths = renderer.generate_html(doc, tmp_path / "html")
    assert [p.stem for p in paths] == ["01_hook", "02_boite_noire", "03_eclairage", "04_perimetre", "05_variable", "06_cta"]
    texts = {p.stem: html.unescape(p.read_text(encoding="utf-8")) for p in paths}
    assert "comment il se mesure" in texts["01_hook"]
    assert "215.900 $" in texts["02_boite_noire"] and "Fed → WSJ → BFM" in texts["02_boite_noire"]
    assert 'style="width: 7%;"' in texts["03_eclairage"] and "× 15" in texts["03_eclairage"]
    assert texts["04_perimetre"].count('class="card"') == 2
    assert "pointer" in texts["05_variable"] and "data-perch" not in texts["05_variable"].split("<body>")[1]
    assert "Ce que la source énonce" in texts["05_variable"] and "Ce que nous en tirons" in texts["05_variable"]
    assert "de quoi dépend, selon vous, le patrimoine qu'on a à 35 ans ?" in texts["06_cta"]


def test_the_bars_follow_the_ratio_or_stay_unfilled():
    assert renderer.bar_widths("× 15") == (100, 7)
    assert renderer.bar_widths("× 0,5") == (50, 100)
    assert renderer.bar_widths("+37%") is None and renderer.bar_widths("") is None


def test_a_deck_without_a_variable_cannot_be_drawn(tmp_path):
    doc = extract(full(), AnatomieChiffrePresentation.model_validate({k: v for k, v in DECK.items() if k != "variable"}))
    with pytest.raises(ValueError):
        renderer.generate_html(doc, tmp_path)
