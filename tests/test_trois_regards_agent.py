"""The TROIS REGARDS adapt agent (revision 4): option models, fragments, hard rules and flags, the cascade with the model
call faked, choose / more / fix, the stale-folder handling of older step files, and the prompts. The deck in
tests/fixtures/trois_regards_deck.json is the validated one; the renderer and the older decks are in test_trois_regards.py."""
import copy
import json
import re
from pathlib import Path

import pytest

from agent import trois_regards_adapt_agent as agent
from agent.carousel_steps.steps import Option
from models.trois_regards_presentation import TroisRegardsPresentation
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/trois_regards_deck.json").read_text(encoding="utf-8"))

# what the article of the sample deck says: the figures and the date the deck's texts may use
ARTICLE = ("Maricarmen Abascal, 87 ans, est expulsée. Il manque environ 750 000 logements ; le logement social ne pèse "
           "que 1,7 % du parc. Législatives le 29 novembre ; le dernier précédent date de 1975 ; 30 jours ; objectif 2028. "
           "« Un manque de logements sociaux » pèse sur les loyers.")


def option_fields(deck: dict) -> dict[str, dict]:
    """The flat option fields of every step, cut from a deck (a clue is « source | find »)."""
    pad = lambda items, n: list(items) + [""] * (n - len(items))  # noqa: E731
    ax, po, t = deck["axe"], deck["position"], deck["tensions"]
    prisms = {f"p{i}": {"title": s["title"], "lead": s["lead"],
                        **{f"head{k}": c["head"] for k, c in enumerate(s["cards"], 1)},
                        **{f"answer{k}": c["answer"] for k, c in enumerate(s["cards"], 1)}}
              for i, s in enumerate(deck["prisms"], 1)}
    return {
        "axe": {"question": ax["question"], "article_question": ax["article_question"], "subject": ax["subject"],
                **{f"prism{i}": p for i, p in enumerate(ax["prisms"], 1)},
                "media": ax["media"], "media_grounding": ax["media_grounding"], "closing": ax["closing"]},
        "position": {"kicker": po["kicker"], "title": po["title"], "lead": po["lead"],
                     **dict(zip(("card1", "card2", "card3", "card4"),
                                pad([f"{c['label']} | {c['text']}" for c in po["cards"]], 4)))},
        "prismes": prisms,
        "tensions": {"title": t["title"], "lead": t["lead"],
                     **{f"topic{k}": c["topic"] for k, c in enumerate(t["cards"], 1)},
                     **{f"view{k}_{p}": v for k, c in enumerate(t["cards"], 1) for p, v in enumerate(c["views"], 1)},
                     **{f"indice{k}": f"{c['source']} | {c['find']}" for k, c in enumerate(t["cards"], 1)}},
        "hook": {"title": deck["hook"]["title"], "promise": deck["hook"]["promise"]},
        "writing": {"caption": deck["caption"]},
    }


FIELDS = option_fields(DECK)


def _opt(fields: dict, slot: str = "a") -> Option:
    return Option(id=slot, slot=slot, reason="r", fields=fields)


def _fragments(fields: dict = FIELDS) -> dict[str, dict]:
    frags: dict[str, dict] = {}
    for step in agent.STEPS:
        picks = [_opt(fields["prismes"][s], s) for s in step.slots] if step.name == "prismes" else [_opt(fields[step.name])]
        frags[step.name] = agent.to_fragment(step, picks, frags)
    return frags


def _validated(deck: dict) -> dict:
    return TroisRegardsPresentation.model_validate(deck).model_dump()


# ---- option models, steps, fragments ------------------------------------------------------------------------------

def test_the_steps_come_in_order():
    assert agent.STEP_NAMES == ["axe", "position", "prismes", "tensions", "hook"]
    assert agent.STEPS[-1].name == "writing" and agent.STEPS[-1].option_model is None
    assert [s.n for s in agent.STEPS] == [1, 2, 3, 4, 5, 6]
    for gone in ("limites", "matrice", "arbitrage"):
        assert gone not in agent.STEP_BY_NAME
    assert not hasattr(agent, "LimitesOption")


def test_the_option_models_have_the_flat_card_fields():
    four, three = (1, 2, 3, 4), (1, 2, 3)
    assert list(agent.PrismesOption.model_fields) == ["title", "lead", *(f"head{k}" for k in four),
                                                       *(f"answer{k}" for k in four)]
    assert list(agent.TensionsOption.model_fields) == [
        "title", "lead", *(f"topic{k}" for k in three), *(f"view{k}_{p}" for k in three for p in three),
        *(f"indice{k}" for k in three)]
    assert list(agent.PositionOption.model_fields) == ["kicker", "title", "lead", "card1", "card2", "card3", "card4"]


def test_only_prismes_has_three_slots():
    assert {s.name: s.slots for s in agent.STEPS if s.slots != ("a",)} == {"prismes": ("p1", "p2", "p3")}
    assert agent.STEP_BY_NAME["prismes"].offered == (2, 3)


def test_the_fragments_rebuild_the_v4_deck():
    deck = agent.assemble(_fragments())
    assert _validated(deck) == _validated(DECK)
    assert set(deck) == {"axe", "position", "prisms", "tensions", "hook", "caption"}
    assert set(deck["prisms"][1]["cards"][0]) == {"head", "answer"}                 # no clue, no claim on a prism card
    assert all(s["lead"] for s in deck["prisms"]) and "media_note" not in deck["prisms"][0]
    card = deck["tensions"]["cards"][2]
    assert set(card) == {"topic", "views", "source", "find"} and len(card["views"]) == 3 and "pair" not in card


def test_a_tension_fragment_holds_its_topic_its_three_views_in_axe_order_and_its_clue():
    card = _fragments()["tensions"]["tensions"]["cards"][1]
    assert card == {"topic": "La location touristique", "views": [FIELDS["tensions"][f"view2_{p}"] for p in (1, 2, 3)],
                    "source": "INE", "find": "les logements touristiques par commune, face aux loyers"}


def test_an_empty_card4_is_left_out_and_the_prism_id_comes_from_the_axe_order():
    fields = copy.deepcopy(FIELDS)
    fields["position"]["card4"] = ""
    assert len(agent.to_fragment(agent.STEP_BY_NAME["position"], [_opt(fields["position"])], {})["position"]["cards"]) == 3
    frags = _fragments()
    frags["axe"]["axe"]["prisms"] = ["sociologique", "historique", "politique"]
    prismes = agent.to_fragment(agent.STEP_BY_NAME["prismes"], [_opt(FIELDS["prismes"][s], s) for s in ("p1", "p2", "p3")], frags)
    assert [s["prism"] for s in prismes["prisms"]] == ["sociologique", "historique", "politique"]


# ---- hard rules, flags and caps -------------------------------------------------------------------------------

def _fe(step: str, fields: dict, slot: str = "a", article: str | None = ARTICLE, frags: dict | None = None):
    frags = _fragments() if frags is None else frags
    return agent.field_errors(step, fields, {} if step == "axe" else frags, article, slot)


def _with(step: str, slot: str | None = None, **kw) -> dict:
    return {**(FIELDS[step][slot] if slot else FIELDS[step]), **kw}


def _hard(step, fields, **kw):
    return _fe(step, fields, **kw)[0]


def _flags(step, fields, **kw):
    return _fe(step, fields, **kw)[1]


def _p(slot="p2", **kw):
    """(hard, flags) of one prism slide with `kw` rewritten."""
    return _fe("prismes", _with("prismes", slot, **kw), slot=slot)


def test_the_sample_deck_breaks_no_hard_rule_and_raises_no_flag():
    for step in ("axe", "position", "tensions", "hook", "writing"):
        assert _fe(step, FIELDS[step]) == ([], []), step
    for slot in ("p1", "p3"):
        assert _fe("prismes", FIELDS["prismes"][slot], slot=slot) == ([], []), slot
    # the validated politique slide keeps two answers that name no causal link (« À l'approche du vote, le gouvernement met… »):
    # the flag is advisory, the author kept the wording
    hard, flags = _fe("prismes", FIELDS["prismes"]["p2"], slot="p2")
    assert hard == [] and [f.split(" has")[0] for f in flags] == ["prismes.answer3", "prismes.answer4"], flags
    assert all("has no causal link" in f for f in flags)


def _at(step: str, name: str, n: int) -> str:
    return "x" * n


_CAPPED = [(s, f) for (s, f) in agent._CAPS if s in ("prismes", "tensions", "position")
           and f not in ("kicker", "title", "lead") or (s, f) in (("prismes", "title"), ("prismes", "lead"),
                                                                    ("tensions", "title"), ("tensions", "lead"))]


@pytest.mark.parametrize("step,name", _CAPPED)
def test_each_card_field_at_its_cap_passes_and_one_more_character_fails(step, name):
    cap = agent._CAPS[(step, name)][1]
    slot = "p2" if step == "prismes" else "a"
    base = _with(step, slot if step == "prismes" else None)
    at = agent.field_errors(step, {**base, name: "x" * cap}, _fragments(), None, slot)[0]
    over = agent.field_errors(step, {**base, name: "x" * (cap + 1)}, _fragments(), None, slot)[0]
    assert not any(e.startswith(f"{step}.{name} is") for e in at), (name, at)
    assert any(e.startswith(f"{step}.{name} is {cap + 1} chars (max {cap})") for e in over), (name, over)


def test_the_axe_hook_and_position_caps_still_hold():
    assert any("axe.question" in e and "max 60" in e for e in _hard("axe", _with("axe", question="x" * 59 + "y ?")))
    assert not _hard("axe", _with("axe", question="D'où vient la crise du logement ?"))
    assert any("axe.closing" in e for e in _hard("axe", _with("axe", closing="x" * 110 + " ?")))
    for name, cap in (("kicker", 26), ("title", 32), ("lead", 90)):
        assert any(f"position.{name}" in e for e in _hard("position", _with("position", **{name: "x" * (cap + 1)})))
    assert any("hook.title" in e for e in _hard("hook", _with("hook", title="x" * 70 + " ?")))


def test_the_position_texts_may_be_150_characters_and_follow_the_existing_rules():
    text = ("Fin septembre, " + "x" * 135)[:150]
    assert len(text) == 150
    assert not _hard("position", _with("position", card2=f"Les causes avancées | {text}"))
    assert any("text is 151 characters (max 150)" in e for e in _hard("position", _with("position", card2=f"Les causes avancées | {text}x")))
    assert any("label is 25 characters (max 24)" in e for e in _hard("position", _with("position", card1="x" * 25 + " | Un fait.")))
    assert any("must read" in e for e in _hard("position", _with("position", card3="Sans barre du tout")))
    assert any("does not appear word for word" in f for f in
               _flags("position", _with("position", card3="Les réponses | Le maire dit « une phrase inventée ».")))
    assert not _flags("position", _with("position", card3="Les réponses | Le texte dit « un manque de logements sociaux »."))
    assert any("blames" in e for e in _hard("position", _with("position", card3="Les réponses | L'article oublie les loyers.")))
    for name in ("card1", "card2", "card3"):
        assert any(e == f"position.{name} is empty" for e in _hard("position", _with("position", **{name: ""})))
    assert not _hard("position", _with("position", card4=""))


def test_a_figure_not_in_the_article_is_refused_but_one_in_the_article_passes():
    """Review focus 2: the position, the prism slides and the tensions share the rule; a year or a date always passes."""
    cases = [("position", None, "card1", "Le point de départ | Le déficit atteint 420 000 logements."),
             ("prismes", "p2", "lead", "Les loyers montent de 12 % par an."),
             ("prismes", "p2", "title", "Une offre en retard de 8 ans"),
             ("prismes", "p2", "head1", "Un déficit de 420 000"),
             ("prismes", "p2", "answer2", "Quand l'offre manque de 420 000 unités, les prix montent."),
             ("tensions", None, "topic1", "Les 99 mesures"),
             ("tensions", None, "view1_1", "Il retire 420 000 logements"),
             ("tensions", None, "lead", "Sur 15 sujets, les regards divergent"),
             ("tensions", None, "indice1", "OCDE | 420 000 logements, avant et après")]
    for step, slot, name, bad in cases:
        hard = _hard(step, _with(step, slot, **{name: bad}), slot=slot or "a")
        assert any(f"{step}.{name} holds a figure not in the article" in e for e in hard), (step, name, hard)
        good = bad.replace("420 000", "750 000").replace("12 %", "1,7 %").replace("8 ans", "2028").replace("99", "30").replace("15 sujets", "30 sujets")
        assert not [e for e in _hard(step, _with(step, slot, **{name: good}), slot=slot or "a") if "figure" in e], (name, good)
    for ok in ("Depuis 1975, le pays attend.", "Le 29 novembre, les urnes s'ouvrent.", "Au 1er janvier, la loi entre en vigueur."):
        assert not [e for e in _p(answer1=ok)[0] if "figure" in e], ok
    assert any("prismes.head1 holds a figure" in e for e in _hard("prismes", _with("prismes", "p2", head1="Un déficit de 3"), article=None, slot="p2"))
    assert not [e for e in _hard("prismes", _with("prismes", "p2", head1="Dès 2024"), article=None, slot="p2") if "head1" in e]


def test_every_prism_slot_needs_a_lead_and_an_answer_that_is_not_a_question():
    for slot in ("p1", "p2", "p3"):
        assert any(e == "prismes.lead is empty" for e in _p(slot, lead="")[0]), slot
    for k in (1, 2, 3, 4):
        assert any(e == f"prismes.answer{k} is empty" for e in _p(**{f"answer{k}": ""})[0])
        assert any(e == f"prismes.head{k} is empty" for e in _p(**{f"head{k}": ""})[0])
        assert any(f"prismes.answer{k} is a sentence, not a question" in e for e in _p(**{f"answer{k}": "Le loyer monte-t-il ?"})[0])
    assert any("prismes.lead is a line, not a question" in e for e in _p(lead="Pourquoi les loyers montent-ils ?")[0])
    assert any(e == "prismes.title is empty" for e in _p(title="")[0])


def test_a_prism_head_over_its_cap_is_refused():
    cap = agent._CAPS[("prismes", "head1")][1]
    assert cap == 30 and all(agent._CAPS[("prismes", f"head{k}")][1] == cap for k in (1, 2, 3, 4))
    assert any(f"prismes.head1 is {cap + 1} chars" in e for e in _p(head1="x" * (cap + 1))[0])
    assert not [e for e in _p(head1="x" * cap)[0] if "head1" in e]


def test_the_prism_slide_prompt_fields_are_gone_from_the_rules():
    assert not any(f in agent._CAPS for f in (("prismes", "media_note"), ("prismes", "claim1")))
    assert not any(s in ("limites",) for s, _ in agent._CAPS) and not any(s == "limites" for s, _ in agent._PART_CAPS)
    assert ("prismes", "indice1") not in agent._PART_CAPS and ("tensions", "indice1") in agent._PART_CAPS


def test_accusing_blaming_and_prescriptive_words_are_refused_outside_quotes():
    assert any("accusing" in e for e in _p(answer1="Quand le biais domine, le prix monte.")[0])
    assert any("blames" in e for e in _p(answer1="Quand l'article ignore les loyers, le prix monte.")[0])
    assert not [e for e in _p(answer1="Quand « le biais » domine, le prix monte.")[0] if "accusing" in e]
    for name in ("topic1", "view1_1", "view3_2", "lead", "title"):
        assert any("prescriptive" in e for e in _hard("tensions", _with("tensions", **{name: "Il faut bâtir plus"}))), name
    assert not any("prescriptive" in e for e in _hard("prismes", _with("prismes", "p2", head1="L'État doit agir"), slot="p2"))
    assert any("accusing" in e for e in _hard("tensions", _with("tensions", view2_3="Un sophisme de plus")))


def test_a_tension_view_may_not_name_its_discipline_and_all_nine_views_are_required():
    """Review focus 3."""
    names = {1: "L'économie", 2: "Le politique", 3: "La sociologie"}      # the axe's order here: economique, politique, sociologique
    for p, text in ((1, "L'économie y voit un frein"), (2, "Le politique tranche"), (3, "La sociologie y lit un lien")):
        assert any(f"tensions.view1_{p} names its discipline" in e for e in _hard("tensions", _with("tensions", **{f"view1_{p}": text}))), p
    # another prism's name is not its own discipline's: the rule is per column
    assert not [e for e in _hard("tensions", _with("tensions", view1_1="Il plaît à la sociologie")) if "discipline" in e]
    for k in (1, 2, 3):
        for p in (1, 2, 3):
            name = f"view{k}_{p}"
            assert any(e == f"tensions.{name} is empty" for e in _hard("tensions", _with("tensions", **{name: ""}))), name
        assert any(e == f"tensions.topic{k} is empty" for e in _hard("tensions", _with("tensions", **{f"topic{k}": ""})))
        assert any(e == f"tensions.indice{k} is empty" for e in _hard("tensions", _with("tensions", **{f"indice{k}": ""})))
    assert any(e == "tensions.lead is empty" for e in _hard("tensions", _with("tensions", lead="")))
    assert not [n for n in names if False]


def test_a_tension_indice_needs_a_source_and_what_to_read():
    for bad in ("INE", "INE |", "| les loyers"):
        assert any("tensions.indice1" in e and "source | find" in e for e in _hard("tensions", _with("tensions", indice1=bad))), bad
    assert any("indice1: the source is 31 characters (max 30)" in e for e in
               _hard("tensions", _with("tensions", indice1="x" * 31 + " | les loyers")))
    assert any("indice1: the find is 61 characters (max 60)" in e for e in
               _hard("tensions", _with("tensions", indice1="INE | " + "x" * 61)))
    for clue in ("https://ine.es | les loyers", "ine.es | les loyers", "INE | www.ine.es/loyers"):
        assert any("URL" in e for e in _hard("tensions", _with("tensions", indice1=clue))), clue


def test_two_views_of_a_topic_that_say_nearly_the_same_thing_are_flagged():
    flags = _flags("tensions", _with("tensions", view1_2=FIELDS["tensions"]["view1_1"]))
    assert any("views 1_1 and 1_2 say nearly the same thing" in f for f in flags)
    assert not [f for f in _flags("tensions", FIELDS["tensions"]) if "nearly" in f]


def test_a_title_or_lead_close_to_the_deck_question_is_flagged():
    q = DECK["axe"]["question"]                         # « D'où vient la crise du logement en Espagne ? »
    for step, slot in (("prismes", "p2"), ("tensions", None)):
        for name in ("title", "lead"):
            fields = _with(step, slot, **{name: q})
            assert any(f.startswith(f"{step}.{name} repeats the deck's question") for f in _fe(step, fields, slot=slot or "a")[1]), (step, name)
            near = _with(step, slot, **{name: "La crise du logement, d'où vient-elle en Espagne"})
            assert any("repeats the deck's question" in f for f in _fe(step, near, slot=slot or "a")[1]), (step, name)


def test_the_subject_phrase_in_two_cards_of_a_slide_is_flagged():
    subject = DECK["axe"]["subject"]
    twice = _p(head1=f"Trop peu pour {subject}", answer3=f"Quand {subject} dure, le parc social recule.")[1]
    assert any("subject" in f and "cards 1, 3" in f for f in twice)
    once = _p(head1=f"Trop peu pour {subject}")[1]
    assert not [f for f in once if "subject" in f]


def test_two_heads_of_a_slide_opening_with_the_same_word_are_flagged():
    flags = _p(head2="Trop de ménages", head1="Trop peu de logements")[1]
    assert any("card1 and card2 open their head with the same word « trop »" in f for f in flags)


def test_a_prism_answer_with_no_causal_link_or_restating_its_head_is_flagged():
    assert any("answer1 has no causal link" in f for f in _p(answer1="Le pays construit moins de logements neufs.")[1])
    assert any("answer2 restates its head" in f for f in _p(head2="La rareté fait monter les prix", answer2="Donc la rareté fait monter les prix.")[1])


def test_a_slide_with_no_key_word_of_the_article_is_flagged_and_a_slide_that_names_the_case_is_not():
    off = {**_with("prismes", "p2"), "title": "Un marché sans visage", "lead": "Le jeu des acteurs économiques sur la durée.",
           **{f"head{k}": f"Un mécanisme abstrait {k}" for k in (1, 2, 3, 4)},
           **{f"answer{k}": "Quand le marché bouge, les agents réagissent donc ailleurs." for k in (1, 2, 3, 4)}}
    assert any("no word of the slide appears in the article" in f for f in _fe("prismes", off, slot="p2", article="Des loyers à Madrid.")[1])
    assert not [f for f in _fe("prismes", FIELDS["prismes"]["p2"], slot="p2")[1] if "no word of the slide" in f]


def test_two_prism_slides_that_say_nearly_the_same_thing_are_flagged():
    frags = _fragments()
    frags["prismes"]["prisms"][0] = copy.deepcopy(frags["prismes"]["prisms"][1])
    assert any("nearly the same thing" in f for f in agent.field_errors("prismes", FIELDS["prismes"]["p2"], frags, ARTICLE, "p2")[1])


def test_the_hook_and_the_caption_keep_their_rules():
    assert any("hook.promise must read" in e for e in _hard("hook", _with("hook", promise="Trois regards ; à vous.")))
    assert any("hashtag" in e for e in _hard("writing", {"caption": "Un texte #un #deux"}))
    assert any(f.startswith("hook.promise names") for f in _flags("hook", _with("hook", promise="Trois regards sur les loyers ; à vous d'en juger.")))
    assert any("not a question" in e or "must be a question" in e for e in _hard("hook", _with("hook", title="Une affirmation")))


# ---- the cascade, the model call faked -----------------------------------------------------------------------------

def _schema_slots(schema: dict) -> list[str]:
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
            options = [{**copy.deepcopy(FIELDS["prismes"][s]), "slot": s, "reason": f"r{call}-{k}"} for s in slots for k in range(3)]
            data = {"options": options, "recommended": [3 * i for i in range(len(slots))]}
        else:
            data = {"options": [{**copy.deepcopy(FIELDS[label]), "reason": f"r{call}-{k}"} for k in range(3)], "recommended": [0]}
        self.errors[label] = validator(data)
        return data


@pytest.fixture
def fake(monkeypatch):
    calls = FakeCalls()
    monkeypatch.setattr(agent, "_call_with_retry", calls)
    return calls


def _adapt(steps, **kw):
    return agent.adapt(full(), steps_dir=steps, article_text=ARTICLE, **kw)


def _choose(steps, step, picks, edits=None, **kw):
    return agent.choose(full(), steps, step, picks, edits or {}, article_text=ARTICLE, **kw)


def _more(steps, step, **kw):
    return agent.more(full(), steps, step, article_text=ARTICLE, **kw)


def _fix(steps, field, text):
    return agent.fix(full(), steps, field, text, article_text=ARTICLE)


def _step_file(steps, name):
    return agent._load(steps, agent.STEP_BY_NAME[name])[0]


def _log(steps) -> list[dict]:
    return [json.loads(line) for line in (steps.parent / "choices.jsonl").read_text(encoding="utf-8").splitlines()]


def test_unattended_runs_six_steps_and_rebuilds_the_v4_deck(fake, tmp_path):
    pres = _adapt(tmp_path / "adapt_steps")
    assert fake.labels == ["axe", "position", "prismes", "tensions", "hook", "writing"]
    assert all(e == [] for e in fake.errors.values()), fake.errors
    assert fake.slots == [["p1", "p2", "p3"]]
    assert pres.model_dump() == _validated(DECK)
    prismes = _step_file(tmp_path / "adapt_steps", "prismes")
    assert [o.id for o in prismes.options] == ["p1a", "p1b", "p1c", "p2a", "p2b", "p2c", "p3a", "p3b", "p3c"]
    assert prismes.recommended == prismes.picked == ["p1a", "p2a", "p3a"]
    assert sorted(p.name for p in (tmp_path / "adapt_steps").glob("*.json")) == [
        "1_axe.json", "2_position.json", "3_prismes.json", "4_tensions.json", "5_hook.json", "6_writing.json"]


def test_guided_pauses_at_the_axe_and_shows_the_prism_options_one_block_per_slot(fake, tmp_path, capsys):
    steps = tmp_path / "adapt_steps"
    assert _adapt(steps, guided=True) is None and fake.labels == ["axe"] and agent.pending_step(steps) == "axe"
    assert "[axe]" in capsys.readouterr().out
    _adapt(steps, stop_after="position")
    capsys.readouterr()
    assert _adapt(steps, guided=True) is None
    out = capsys.readouterr().out
    assert agent.pending_step(steps) == "prismes"
    blocks = [out.index(f"[{s}]") for s in ("p1", "p2", "p3")]
    assert blocks == sorted(blocks) and out.count("★") == 3 and "p3c — " in out


def test_stop_after_tensions_stops_before_the_hook(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    assert _adapt(steps, stop_after="tensions") is None
    assert fake.labels == ["axe", "position", "prismes", "tensions"]
    assert (steps / "4_tensions.json").exists() and not (steps / "5_hook.json").exists()


def test_a_later_step_receives_the_earlier_picks_and_the_article(fake, tmp_path):
    agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text="TEXTE-DE-L-ARTICLE", stop_after="prismes")
    first, _, third = fake.messages
    assert "CHOIX FIXÉS" not in first and "CATALOGUE DES PRISMES" in first and "TEXTE-DE-L-ARTICLE" in third
    fixed = third.split("CHOIX FIXÉS (ne les réécris pas) :")[1]
    assert FIELDS["axe"]["question"] in fixed and FIELDS["position"]["title"] in fixed
    assert all(f"{s} = {p}" in third for s, p in zip(("p1", "p2", "p3"), ("economique", "politique", "sociologique")))
    for private in ("review", "ethics", "blend", "distill", "guide"):
        assert f'"{private}"' not in third


def test_choose_on_prismes_needs_one_pick_per_slot_and_keeps_an_edit(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    msg = "prismes: keep exactly one option per prism (p1, p2, p3)"
    for bad in (["p1a", "p1b", "p2a"], ["p1a", "p2a"]):
        with pytest.raises(agent.ChoiceError, match=re.escape(msg)):
            _choose(steps, "prismes", bad)
    with pytest.raises(agent.ChoiceError):
        _choose(steps, "prismes", ["p1a", "p2a", "p4a"])
    assert _step_file(steps, "prismes").picked == ["p1a", "p2a", "p3a"]
    assert _choose(steps, "prismes", ["p3b", "p1b", "p2c"], {"p2c.head1": "Les loyers devancent"}) == []
    sf = _step_file(steps, "prismes")
    assert sf.picked == ["p1b", "p2c", "p3b"] and sf.fragment["prisms"][1]["cards"][0]["head"] == "Les loyers devancent"
    with pytest.raises(agent.ChoiceError):
        _choose(steps, "prismes", ["p1a", "p2a", "p3a"], {"p1a.indice1": "x"})       # a removed field
    with pytest.raises(agent.ChoiceError):
        _choose(steps, "limites", ["a"])


def test_choose_keeps_an_edited_pick_and_warns_on_a_broken_rule(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps, guided=True)
    long_question = "D'où vient vraiment la crise du logement qui secoue toute l'Espagne ?"
    warnings = _choose(steps, "axe", ["b"], {"b.question": long_question}, reason="plus large")
    assert any(w.startswith("axe.question is") for w in warnings)
    sf = _step_file(steps, "axe")
    assert sf.picked == ["b"] and sf.fragment["axe"]["question"] == long_question and next(o for o in sf.options if o.id == "b").edited


def test_more_with_a_slot_regenerates_only_that_slot(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    before = _step_file(steps, "prismes")
    stamp = (steps / "3_prismes.sha256").read_text()
    new = _more(steps, "prismes", remark="plus concret", slot="p2")
    assert fake.slots[-1] == ["p2"] and "plus concret" in fake.messages[-1]
    keep = lambda sf: [o.model_dump() for o in sf.options if o.slot != "p2"]  # noqa: E731
    assert keep(new) == keep(before) and new.picked == ["p1a", "p3a"]
    assert (steps / "3_prismes.sha256").read_text() == stamp and agent.pending_step(steps) == "prismes"
    with pytest.raises(agent.ChoiceError):
        _more(steps, "prismes", slot="p4")
    _more(steps, "prismes", slot="politique")                      # the prism id the axe puts in p2
    assert fake.slots[-1] == ["p2"]


def test_after_more_on_one_prism_the_kept_picks_complete_the_choice(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    _choose(steps, "prismes", ["p1b", "p2a", "p3c"])
    new = _more(steps, "prismes", slot="p2")
    p2 = [o.id for o in new.options if o.slot == "p2"]
    out = agent.format_options(agent.STEP_BY_NAME["prismes"], new)
    assert [line.split(" — ")[0] for line in out.splitlines() if "✔ gardée" in line] == ["p1b", "p3c"]
    for bad in ([], [p2[0], p2[1]], ["p9z"], ["p1a"]):
        with pytest.raises(agent.ChoiceError):
            _choose(steps, "prismes", bad)
    for field in ("prismes.p1.head1", "tensions.title"):
        with pytest.raises(agent.ChoiceError) as e:
            _fix(steps, field, "Une ligne refaite.")
        assert "prismes --pick" in str(e.value) and p2[0] in str(e.value)
    assert _choose(steps, "prismes", [p2[1]]) == [] and _step_file(steps, "prismes").picked == ["p1b", p2[1], "p3c"]


def test_changing_the_axe_makes_every_later_step_stale(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    _choose(steps, "axe", ["a"])                                                # the same pick: nothing changes
    _adapt(steps)
    assert fake.labels == [s.name for s in agent.STEPS]
    _choose(steps, "axe", ["b"], {"b.question": "Pourquoi le logement manque-t-il en Espagne ?"})
    with pytest.raises(agent.ChoiceError, match="stale"):
        _choose(steps, "prismes", ["p1a", "p2a", "p3a"])
    pres = _adapt(steps)
    assert fake.labels[len(agent.STEPS):] == ["position", "prismes", "tensions", "hook", "writing"]
    assert pres.axe.question == "Pourquoi le logement manque-t-il en Espagne ?" and list(steps.glob("stale_*/3_prismes.json"))


def test_fix_rewrites_one_field_without_regenerating(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    before = list(fake.labels)
    assert _fix(steps, "axe.question", "Pourquoi le logement manque-t-il en Espagne ?") == ("axe", [])
    assert _fix(steps, "position.title", "Le logement, enjeu de scrutin") == ("position", [])
    assert _fix(steps, "caption", DECK["caption"] + " Merci.")[0] == "writing"
    step, warnings = _fix(steps, "hook.title", "x" * 75)
    assert step == "hook" and any("hook.title is 75" in w for w in warnings)
    pres = _adapt(steps)
    assert fake.labels == before and pres.position.title == "Le logement, enjeu de scrutin" and pres.caption.endswith("Merci.")
    with pytest.raises(agent.ChoiceError):
        _fix(steps, "invisible.statement", "x")
    for gone in ("limites.claim1", "arbitrage.test1", "prismes.p2.indice1", "prismes.p2.media_note", "tensions.pair1", "tensions.claim1"):
        with pytest.raises(agent.ChoiceError):
            _fix(steps, gone, "x")


def test_fix_reaches_a_position_card(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    before = list(fake.labels)
    text = "Les réponses des acteurs | Le gouvernement adopte un plafond des loyers."
    assert _fix(steps, "position.card3", text) == ("position", [])
    _, warnings = _fix(steps, "position.card2", "Les causes avancées | Un déficit de 999 logements.")
    assert any(w.startswith("position.card2 holds a figure not in the article") for w in warnings)
    _, warnings = _fix(steps, "position.card1", "x" * 25 + " | Un fait.")
    assert any("label is 25 characters (max 24)" in w for w in warnings)
    pres = _adapt(steps)
    assert fake.labels == before and pres.position.cards[2].label == "Les réponses des acteurs"
    assert pres.position.cards[1].text == "Un déficit de 999 logements."          # kept: the author has the last word


def test_fix_reaches_a_prism_field_by_slot(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    before = list(fake.labels)
    answer = "Quand le loyer dépasse le revenu, les ménages partent."
    assert _fix(steps, "prismes.p2.answer3", answer) == ("prismes", [])
    _, warnings = _fix(steps, "prismes.p3.answer2", "Le loyer monte-t-il ?")
    assert any(w.startswith("p3: prismes.answer2 is a sentence, not a question") for w in warnings)
    _, warnings = _fix(steps, "prismes.p1.lead", "")
    assert any(w == "p1: prismes.lead is empty" for w in warnings)
    pres = _adapt(steps)
    assert fake.labels == before and pres.prisms[1].cards[2].answer == answer
    assert pres.prisms[1].cards[2].head == DECK["prisms"][1]["cards"][2]["head"]
    with pytest.raises(agent.ChoiceError, match="prismes.p1.head1"):
        _fix(steps, "prismes.head1", "x")
    with pytest.raises(agent.ChoiceError):
        _fix(steps, "prismes.p4.head1", "x")


def test_fix_reaches_a_tensions_view_a_topic_and_a_clue(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    before = list(fake.labels)
    assert _fix(steps, "tensions.view2_3", "Elle chasse les familles du quartier") == ("tensions", [])
    assert _fix(steps, "tensions.topic1", "Le gel des expulsions")[0] == "tensions"
    _, warnings = _fix(steps, "tensions.view1_1", "L'économie y voit un frein")
    assert any("tensions.view1_1 names its discipline" in w for w in warnings)
    _, warnings = _fix(steps, "tensions.indice3", "ine.es | les dates")
    assert any("URL" in w for w in warnings)
    _fix(steps, "tensions.view1_1", FIELDS["tensions"]["view1_1"])
    _fix(steps, "tensions.indice3", FIELDS["tensions"]["indice3"])
    pres = _adapt(steps)
    assert fake.labels == before
    assert pres.tensions.cards[1].views[2] == "Elle chasse les familles du quartier" and pres.tensions.cards[0].topic == "Le gel des expulsions"


def test_the_choice_log_records_picks_edits_and_fixes(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    _choose(steps, "prismes", ["p1b", "p2a", "p3a"], {"p1b.title": "Qui décide ?"}, reason="plus court")
    new = _more(steps, "prismes", remark="autre angle", slot="p3")
    with pytest.raises(agent.ChoiceError):          # the p3 pick went with its options: nothing to fix yet
        _fix(steps, "prismes.p2.head1", "Une ligne refaite.")
    _choose(steps, "prismes", ["p1b", "p2a", new.recommended[-1]])
    _fix(steps, "prismes.p2.head1", "Une ligne refaite.")
    pick, more, _, fix = _log(steps)
    assert pick["event"] == "pick" and pick["picked"] == ["p1b", "p2a", "p3a"] and pick["reason"] == "plus court"
    assert pick["edits"] == {"p1b.title": "Qui décide ?"}
    assert more == {**more, "event": "more", "step": "prismes", "remark": "autre angle", "slot": "p3"}
    assert fix == {**fix, "event": "fix", "field": "prismes.p2.head1", "before": FIELDS["prismes"]["p2"]["head1"], "after": "Une ligne refaite."}


def test_no_api_runs_through_the_same_path(fake, tmp_path):
    pres = _adapt(tmp_path / "adapt_steps", no_api=True)
    assert fake.labels == [s.name for s in agent.STEPS] and all(fake.no_api)
    assert pres.tensions.title == DECK["tensions"]["title"]


_LATER = ["position", "prismes", "tensions", "hook", "writing"]


def _fresh(steps, name) -> bool:
    base = agent.base_inputs(full(), ARTICLE)
    st = agent.STEP_BY_NAME[name]
    frags = [_step_file(steps, s.name).fragment for s in agent.STEPS if s.n < st.n]
    return (steps / f"{st.n}_{st.name}.sha256").read_text() == agent.stamp_for(base, frags)


def test_a_fix_of_an_axe_prism_leaves_the_later_steps_stale_and_they_rerun(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    n = len(fake.labels)
    owner, warnings = _fix(steps, "axe.prism2", "juridique")
    assert owner == "axe" and any("regenerated" in w for w in warnings)
    assert not any(_fresh(steps, s) for s in _LATER)
    assert _step_file(steps, "prismes").fragment["prisms"][1]["prism"] == "politique"       # relabelled only on the rerun
    pres = _adapt(steps)
    assert fake.labels[n:] == _LATER and "p2 = juridique" in fake.messages[n + 1] and pres.prisms[1].prism == "juridique"


def test_a_wording_fix_on_a_later_step_still_restamps_without_a_model_call(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    _adapt(steps)
    before = list(fake.labels)
    _fix(steps, "position.title", "Le logement, enjeu de scrutin")
    assert all(_fresh(steps, s) for s in _LATER)
    _adapt(steps)
    assert fake.labels == before


def _write_step(steps, name: str, n: int, fields: dict, stamp: str) -> None:
    """An older step file as an earlier step table wrote it: `<n>_<name>.json` and its stamp."""
    sf = agent.StepFile(step=name, options=[Option(id="a", slot="a", reason="r", fields=fields)],
                        recommended=["a"], picked=["a"], fragment={"x": 1})
    (steps / f"{n}_{name}.json").write_text(sf.model_dump_json(indent=2), encoding="utf-8")
    (steps / f"{n}_{name}.sha256").write_text(stamp)


def test_an_old_adapt_steps_folder_with_5_limites_json_does_not_crash_a_rerun(fake, tmp_path):
    """Review focus 5. A folder written by the revision-3 step table: 3_prismes (claims, clues, media note), 4_tensions
    (pairs, heads, claims), 5_limites, 6_hook, 7_writing. The old prism slides and tensions keep a stamp that matches the
    axe and the position, but their fields are not the current ones: they are retired like a stale step and rerun; the
    limites file is never read (the fifth step is `5_hook.json` now) and nothing crashes."""
    steps = tmp_path / "adapt_steps"
    _adapt(steps, stop_after="position")
    stamp = agent.stamp_for(agent.base_inputs(full(), ARTICLE), [_step_file(steps, s).fragment for s in ("axe", "position")])
    old_prism = {"title": "Un marché sous tension", "lead": "", **{f"head{k}": "Le loyer suit la rareté" for k in (1, 2, 3, 4)},
                 **{f"answer{k}": "Quand l'offre manque, le prix monte." for k in (1, 2, 3, 4)},
                 **{f"indice{k}": "INE | les loyers par ville" for k in (1, 2, 3, 4)}, "media_note": ""}
    sf = agent.StepFile(step="prismes", options=[Option(id=f"{s}a", slot=s, reason="r", fields=old_prism) for s in ("p1", "p2", "p3")],
                        recommended=["p1a", "p2a", "p3a"], picked=["p1a", "p2a", "p3a"],
                        fragment={"prisms": [{"prism": "politique", "title": "t", "cards": []}]})
    (steps / "3_prismes.json").write_text(sf.model_dump_json(indent=2), encoding="utf-8")
    (steps / "3_prismes.sha256").write_text(stamp)
    _write_step(steps, "tensions", 4, {"title": "Quel regard ?", "lead": "x", **{f"pair{k}": "1,2" for k in (1, 2, 3)},
                                        **{f"head{k}": "a ; b" for k in (1, 2, 3)}, **{f"claim{k}": "Plus ?" for k in (1, 2, 3)},
                                        **{f"indice{k}": "INE | les loyers" for k in (1, 2, 3)}}, stamp)
    _write_step(steps, "limites", 5, {"title": "Ce qui reste hors champ", "lead": "x"}, stamp)
    (steps / "5_limites.verification.json").write_text("[]", encoding="utf-8")
    _write_step(steps, "hook", 6, FIELDS["hook"], stamp)
    _write_step(steps, "writing", 7, FIELDS["writing"], stamp)
    assert agent.pending_step(steps) is None                         # the old files do not read as a pending step
    for step, picks in (("prismes", ["p1a", "p2a", "p3a"]), ("tensions", ["a"])):
        with pytest.raises(agent.ChoiceError, match="stale"):         # nor as a step one can still choose on
            _choose(steps, step, picks)
    with pytest.raises(agent.ChoiceError):
        _fix(steps, "limites.claim1", "x")                            # not a deck field any more
    n = len(fake.labels)
    pres = _adapt(steps)
    assert fake.labels[n:] == ["prismes", "tensions", "hook", "writing"]
    assert pres.model_dump() == _validated(DECK) and pres.limites is None
    assert list(steps.glob("stale_*/3_prismes.json")) and list(steps.glob("stale_*/4_tensions.json"))
    assert (steps / "5_limites.json").exists() and (steps / "5_hook.json").exists() and (steps / "6_writing.json").exists()
    assert _adapt(steps).model_dump() == pres.model_dump() and len(fake.labels) == n + 4         # the rerun is stable


def test_a_first_version_steps_folder_with_4_matrice_json_does_not_crash_a_rerun(fake, tmp_path):
    """The first step table: 3_prismes (question, lines, sources), 4_matrice, 5_hook, 6_writing."""
    steps = tmp_path / "adapt_steps"
    _adapt(steps, stop_after="position")
    stamp = agent.stamp_for(agent.base_inputs(full(), ARTICLE), [_step_file(steps, s).fragment for s in ("axe", "position")])
    old_prism = {"question": "D'où vient la crise ?", "line1": "a", "line2": "b", "line3": "c", "line4": "",
                 "sources": "INE ; Eurostat", "media_note": ""}
    sf = agent.StepFile(step="prismes", options=[Option(id=f"{s}a", slot=s, reason="r", fields=old_prism) for s in ("p1", "p2", "p3")],
                        recommended=["p1a", "p2a", "p3a"], picked=["p1a", "p2a", "p3a"], fragment={"prisms": []})
    (steps / "3_prismes.json").write_text(sf.model_dump_json(indent=2), encoding="utf-8")
    (steps / "3_prismes.sha256").write_text(stamp)
    _write_step(steps, "matrice", 4, {"title": "Que mesurer ?", "col1": "a | b", "col2": "a | b", "col3": "a | b"}, stamp)
    _write_step(steps, "hook", 5, FIELDS["hook"], stamp)
    _write_step(steps, "writing", 6, FIELDS["writing"], stamp)
    n = len(fake.labels)
    pres = _adapt(steps)
    assert fake.labels[n:] == ["prismes", "tensions", "hook", "writing"] and pres.model_dump() == _validated(DECK)
    assert list(steps.glob("stale_*/3_prismes.json")) and list(steps.glob("stale_*/5_hook.json"))


# ---- the web check of the tensions' clues ---------------------------------------------------------------------------

def test_only_the_tensions_are_verified():
    assert agent.VERIFIED_STEPS == ("tensions",)


# ── Prompts ─────────────────────────────────────────────────────────────────

PROMPTS = Path("agent/prompts/trois_regards_steps")


def _prompt_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_every_step_has_its_prompt_and_no_prompt_is_left_for_a_removed_step():
    files = [PROMPTS / "0_options.md", PROMPTS / "0_shared.md", *(PROMPTS / f"{s.n}_{s.name}.md" for s in agent.STEPS)]
    for f in files:
        assert f.exists() and len(_prompt_text(f)) > 400, f
    assert sorted(p.name for p in PROMPTS.glob("*.md")) == sorted(f.name for f in files)
    assert not (PROMPTS / "5_limites.md").exists()


def test_the_shared_prompt_states_the_anti_goals_and_the_fixed_roles():
    text = _prompt_text(PROMPTS / "0_shared.md").lower()
    for guard in ("reproche", "oublie", "inventée", "réelle", "prescri", "il faut", "ligne en trop", "origine", "mécanisme",
                  "amplificateur", "ce qu'on en voit", "complète", "dans l'article", "n'a rien lu", "discipline"):
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


def test_no_prompt_mentions_the_removed_fields():
    for f in PROMPTS.glob("*.md"):
        low = _prompt_text(f).lower()
        for gone in ("limites", "arbitrage", "media_note", "`claim", "matrice", "line1", "`lines`", "`pair", "prismes.indice",
                     "prismes.claim", "angles morts", "regard du média", "{{cap:limites", "{{cap:arbitrage"):
            assert gone not in low, (f.name, gone)
    prismes = _prompt_text(PROMPTS / "3_prismes.md")
    assert not re.search(r"`(?:indice\d?|claim\d?|media_note)`", prismes)


_BULLET = re.compile(r"^- `(\w+)` : (?:« (.*) »|`(.*)`)\s*$", re.M)


def _example(text: str) -> dict[str, str]:
    out = {}
    for m in _BULLET.finditer(text):
        value = m.group(2) if m.group(2) is not None else m.group(3)
        out[m.group(1)] = "" if value == '""' else value
    out.pop("reason", None)
    return out


def _examples(name: str) -> list[tuple[str, dict[str, str]]]:
    parts = re.split(r"^(Exemple.*)$", _prompt_text(PROMPTS / name), flags=re.M)[1:]
    return [(head, _example(body)) for head, body in zip(parts[::2], parts[1::2])]


def _worked() -> tuple[dict, dict]:
    """The worked examples of 1_axe … 5_hook, parsed from the prompt files: (the fragments they build, in step order; the
    example fields by (step, slot), slot « a » for a one-slot step)."""
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
    prisms.sort(key=lambda o: o.slot)
    frags["prismes"] = agent.to_fragment(agent.STEP_BY_NAME["prismes"], prisms, frags)
    fields = base[("tensions", "a")] = only("4_tensions.md")
    assert set(fields) == set(agent.TensionsOption.model_fields), set(fields) ^ set(agent.TensionsOption.model_fields)
    frags["tensions"] = agent.to_fragment(agent.STEP_BY_NAME["tensions"], [_opt(fields)], frags)
    base[("hook", "a")] = only("5_hook.md")
    return frags, base


def test_the_worked_examples_break_no_hard_rule_and_raise_no_flag():
    """The examples are what the model imitates: they keep every hard rule AND every advisory flag."""
    frags, base = _worked()
    for (step, slot), fields in base.items():
        hard, flags = agent.field_errors(step, fields, {} if step == "axe" else frags, None, slot)
        assert hard == [] and flags == [], (step, slot, hard, flags)
    assert len(frags["tensions"]["tensions"]["cards"]) == 3 and all(len(c["views"]) == 3 for c in frags["tensions"]["tensions"]["cards"])
    assert base[("hook", "a")]["title"] == base[("axe", "a")]["question"]
    assert all(len(p["cards"]) == 4 and p["lead"] for p in frags["prismes"]["prisms"])


# a good/bad pair line: « - BON `step[.slot].field` : « value » » or « - MAUVAIS (defect) `step[.slot].field` : « value » »
_PAIR_LINE = re.compile(r"^- (BON|MAUVAIS)(?: \(([^)]+)\))? `([\w.]+)` : « (.*) »\s*$", re.M)
# the defect a bad example names → the words of the rule message that catches it
_DEFECTS = {"fait au lieu de mécanisme": "causal link", "une question": "not a question", "reprise de la tête": "restates",
            "un chiffre hors de l'article": "not in the article", "répétition d'amorce": "same word",
            "une vue qui nomme sa discipline": "names its discipline", "deux vues presque identiques": "nearly the same",
            "question du carrousel répétée": "deck's question", "un lien": "URL",
            "un nom propre dans le titre": "prismes.title names", "un sigle non expliqué": "is not spelled out"}


def _pairs() -> list[tuple[str, str, str | None, str, str]]:
    return [(f.name, m.group(1), m.group(2), m.group(3), m.group(4))
            for f in sorted(PROMPTS.glob("*.md")) for m in _PAIR_LINE.finditer(_prompt_text(f))]


def test_the_worked_examples_good_ones_raise_nothing_and_bad_ones_the_expected_defect():
    """Each BON/MAUVAIS line rewrites one field of the step's worked example: the good one keeps it free of any hard error
    and any flag, the bad one raises the defect it names."""
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
    bad = {d for f, k, d, _, _ in pairs if k == "MAUVAIS"}
    assert set(_DEFECTS) <= bad                                       # every rule the prompts teach has its bad example
    for fname, kind, _, path, _ in pairs:                             # every bad line has its good twin in the same file
        if kind == "MAUVAIS":
            assert (fname, "BON", path) in {(f, k, p) for f, k, _, p, _ in pairs}, (fname, path)


def test_the_examples_are_on_another_subject_than_the_spanish_article():
    every = " ".join(_prompt_text(f) for f in PROMPTS.glob("*.md"))
    for word in ("Espagne", "espagnol", "logement", "Radio-Canada", "Congrès", "loyer"):
        assert word.lower() not in every.lower(), word


def test_the_card_prompts_define_the_roles_the_grid_and_the_closing_line():
    shared = _prompt_text(PROMPTS / "0_shared.md")
    for word in ("`head`", "`answer`", "`indice`", "`lead`", "source nommée | ce qu'on y lit", "URL", "BON", "MAUVAIS"):
        assert word in shared, word
    tensions = _prompt_text(PROMPTS / "4_tensions.md")
    assert all(f"`view{k}_{p}`" in tensions for k in (1, 2, 3) for p in (1, 2, 3)) and "grille" in tensions
    position = _prompt_text(PROMPTS / "2_position.md")
    assert all(label in position for label in ("Le déclencheur", "Les causes avancées", "Les réponses des acteurs", "Les conséquences"))
    assert "quel regard manquait" in _prompt_text(PROMPTS / "1_axe.md")


def test_a_prism_title_naming_a_person_or_an_acronym_never_spelled_out_is_flagged():
    flags = _p(title="Un calendrier que Sánchez choisit")[1]
    assert any(f.startswith("prismes.title names « Sánchez »") for f in flags)
    assert not [f for f in _p(title="Élections **avancées** faute de majorité")[1] if "names" in f]
    assert any("« PSOE » is not spelled out" in f for f in _p(answer1="Faute de majorité, le PSOE dépend d'autres voix.")[1])
    assert not [f for f in _p(answer1="Faute de majorité, le Parti socialiste (PSOE) dépend d'autres voix.")[1] if "spelled" in f]
    assert not [f for f in _p(answer1="Faute de majorité, l'UE dépend d'autres voix.")[1] if "spelled" in f]
    flags = _flags("position", _with("position", card4="Les conséquences | Le PSOE espère la majorité."))
    assert any("« PSOE » is not spelled out" in f for f in flags)
    assert not [f for f in _flags("position", _with("position", card4="Les conséquences | Le Parti socialiste (PSOE) espère la majorité.")) if "spelled" in f]
