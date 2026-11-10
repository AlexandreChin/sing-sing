"""The TEMPS LONG carousel: the model, the step rules, the cascade (with the model
call faked) and the HTML it renders. The deck in tests/fixtures/temps_long_deck.json
is hand-written for a news dispatch on UN experts and student protests; its dates
are test data, not checked facts."""
import copy
import html
import json
import random
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from agent import temps_long_adapt_agent as agent
from agent.carousel_steps.steps import Option
from extractors.registry import FORMATS
from extractors.temps_long import extract
from models.temps_long_presentation import TempsLongDocument, TempsLongPresentation
from renderer.instagram_carousel import temps_long as renderer
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/temps_long_deck.json").read_text(encoding="utf-8"))
ARTICLE = ("Le Figaro, 29 Oct 2026. Amnesty évoque sept points d'alerte sur un «glissement vers des pratiques "
           "autoritaires». «la France n'est plus à l'abri de cette tendance mondiale.» L'ampleur des "
           "interpellations «apparaît disproportionnée», et une «surenchère sécuritaire» dans la législation. Des experts "
           "de l'ONU «consternés» par la «répression» des manifestations.")


def _frise(f: dict) -> dict:
    reps = [f"{r['date']} | {r['label']} | {r['remark']}" for r in f["reperes"]]
    return {"title": f["title"], "lead": f["lead"], **dict(zip(("rep1", "rep2", "rep3", "rep4", "rep5"), reps + [""] * 5))}


AXE = {"fait": "Des experts de l'ONU « consternés » par la « répression »",
       "title": "La « répression » est-elle nouvelle ?", "move": "forme", "mot": "glissement",
       "reponse": "Trois lectures du changement et ce que chacune ferait voir", "criteres": "Rupture, Continuité, Cycle"}


def option_fields(deck: dict) -> dict[str, dict]:
    """Each step's flat option fields, cut from the finished deck."""
    le, pi = deck["lecture"], deck["pieges"]
    traps = [f"{x['title']} | {x['question']}" for x in pi["pieges"]]
    cards = {f"card{i}": f"{r.get('label') or agent._OLD_LABELS[r['kind']]} | {r['signature']} | {r['indicator']}"
             for i, r in enumerate(le["readings"], 1)}
    return {
        "axe": {**AXE, "fait": deck["hook"]["title"]},
        "tournants": _frise(deck["tournants"]),
        "episodes": _frise(deck["episodes"]),
        "lecture": {"title": le["title"], "lead": le["lead"], **cards, "question": le["question"],
                    "where": le.get("where", "")},
        "pieges": {"title": pi["title"], "lead": pi["lead"], **dict(zip(("piege1", "piege2", "piege3", "piege4"), traps))},
        "hook": {"promise": deck["hook"]["promise"], "tagline": deck["hook"].get("tagline", "")},
        "position": dict(deck["position"]),
        "writing": {"caption": deck["caption"]},
    }


FIELDS = option_fields(DECK)


def hard(step, **changes):
    return agent.field_errors(step, {**FIELDS[step], **changes}, {}, ARTICLE)[0]


def flags(step, fragments=None, **changes):
    return agent.field_errors(step, {**FIELDS[step], **changes}, fragments or {}, ARTICLE)[1]


def _fragment(step: str) -> dict:
    return {step: agent.to_fragment(agent.STEP_BY_NAME[step], Option(id="a", slot="a", reason="", fields=FIELDS[step]))}


# ── model, steps and fragments ──────────────────────────────────────────────

def test_the_deck_validates():
    pres = TempsLongPresentation.model_validate(DECK)
    assert [r.kind for r in pres.lecture.readings] == ["rupture", "continuite", "cycle"] and pres.move == "forme"
    assert pres.episodes.reperes[1].date == "2018–2019" and pres.episodes.reperes[1].remark
    assert len(pres.episodes.reperes) == 5 and len(pres.tournants.reperes) == 4 and len(pres.pieges.pieges) == 4
    assert "mineurs" not in pres.lecture.lead and pres.lecture.lead.startswith("Pour trancher")
    assert pres.tournants.reperes[-1].date == "oct. 2026"
    assert pres.position.title.startswith("Amnesty") and pres.position.issue


def test_an_older_deck_has_no_position_and_keeps_six_slides(tmp_path):
    old = {k: v for k, v in copy.deepcopy(DECK).items() if k != "position"}
    pres = TempsLongPresentation.model_validate(old)
    assert pres.position is None
    paths = renderer.generate_html(extract(full(), pres), tmp_path / "html")
    assert [p.stem for p in paths] == ["01_hook", "02_episodes", "03_tournants", "04_lecture", "05_pieges", "06_cta"]


def test_the_slides_between_hook_and_signoff_follow_the_deck_order(tmp_path):
    default = renderer.generate_html(extract(full(), TempsLongPresentation.model_validate(DECK)), tmp_path / "default")
    assert [p.stem for p in default] == ["01_hook", "02_position", "03_episodes", "04_tournants", "05_lecture", "06_pieges", "07_cta"]
    deck = copy.deepcopy(DECK)
    deck["order"] = ["position", "lecture", "episodes", "tournants", "pieges"]
    paths = renderer.generate_html(extract(full(), TempsLongPresentation.model_validate(deck)), tmp_path / "ordered")
    assert [p.stem for p in paths] == ["01_hook", "02_position", "03_lecture", "04_episodes", "05_tournants", "06_pieges", "07_cta"]


def test_a_reference_point_draws_its_test_tags_as_pills(tmp_path):
    deck = copy.deepcopy(DECK)
    deck["episodes"]["reperes"][0]["tags"] = ["cible", "effet"]
    paths = renderer.generate_html(extract(full(), TempsLongPresentation.model_validate(deck)), tmp_path / "html")
    html_text = next(p for p in paths if p.stem.endswith("episodes")).read_text(encoding="utf-8")
    assert '<span class="tg"><i class="pl">cible</i><i class="pl">effet</i></span>' in html_text      # no reading of that name: no icon
    assert html_text.count('class="tg"') == 1


def _seuil_deck() -> dict:
    deck = copy.deepcopy(DECK)
    deck["move"] = "seuil"
    deck["lecture"] |= {
        "readings": [{"kind": "cible", "label": "Cible", "signature": "Qui est visé ?", "indicator": "les auteurs", "other": "des pacifiques"},
                     {"kind": "proportion", "label": "Proportion", "signature": "Quelle ampleur ?", "indicator": "à la mesure", "other": "disproportionnée"},
                     {"kind": "effet", "label": "Effet", "signature": "Quel effet ?", "indicator": "aucun", "other": "dissuade"}],
        "heads": ["Maintien de l'ordre", "« Répression »"], "aside_heading": "Amnesty juge autrement : un « glissement »",
        "aside_cards": [{"label": "Presse", "text": "attaquer la presse", "icon": "book"}, {"label": "Peur", "text": "gouverner par la peur", "icon": "flame"}],
        "where": "", "author": ""}
    return deck


def test_a_pill_shows_whose_criterion_it_is_and_its_icon(tmp_path):
    deck = _seuil_deck()
    deck["episodes"]["reperes"][0]["tags"] = ["cible", "presse"]
    paths = renderer.generate_html(extract(full(), TempsLongPresentation.model_validate(deck)), tmp_path / "html")
    texts = {p.stem[3:]: p.read_text(encoding="utf-8") for p in paths}
    episodes = texts["episodes"]
    assert '<i class="pl"><svg viewBox="0 0 24 24"><circle' in episodes and 'Cible'.lower() in episodes.lower()
    assert '<i class="pl am"' not in episodes and "presse</i>" in episodes       # the second voice's pill looks like the others
    lecture = texts["lecture"]
    assert 'class="tb-h"' in lecture and "Maintien de l&#39;ordre" in lecture and lecture.count('class="card read tr"') == 3
    assert lecture.count('class="card read am-c"') == 2 and "attaquer la <strong>presse</strong>" in lecture


def test_an_older_deck_with_the_old_keys_still_loads():
    old = {k: v for k, v in copy.deepcopy(DECK).items() if k not in ("tournants", "episodes")}
    old["vague_de_fond"], old["palier"] = DECK["tournants"], DECK["episodes"]
    old["palier"]["reperes"][0]["where"] = "Légifrance"
    old["lecture"]["words_line"] = "« Glissement » suppose la continuité."
    old["mots"] = {"title": "x", "lead": "y", "words": []}
    pres = TempsLongPresentation.model_validate(old)
    assert pres.episodes.reperes[0].remark and pres.tournants.title == DECK["tournants"]["title"]


def test_the_steps_run_noyau_first_and_every_step_has_its_prompt():
    assert agent.STEP_NAMES == ["axe", "position", "tournants", "episodes", "lecture", "pieges", "hook"]
    for s in agent.STEPS:
        assert Path(f"agent/prompts/temps_long_steps/{s.n}_{s.name}.md").exists(), s.name


def test_the_shared_prompt_lists_every_step():
    shared = Path("agent/prompts/temps_long_steps/0_shared.md").read_text(encoding="utf-8")
    for name in ("**axe**", "**position**", "**lecture**", "**episodes**", "**tournants**", "**pieges**", "**hook**", "**writing**"):
        assert name in shared, name
    assert "Huit étapes" in shared


def _with_layouts(deck: dict) -> dict:
    """The fixture deck as the pipeline builds it: the episodes as large years, the texts on a spine."""
    deck = copy.deepcopy(deck)
    deck["episodes"]["layout"], deck["tournants"]["layout"] = "annees", "axe"
    return deck


def test_fragments_rebuild_the_deck():
    frags = {s.name: agent.to_fragment(s, Option(id="a", slot="a", reason="", fields=FIELDS[s.name]))
             for s in agent.STEPS}
    assert TempsLongPresentation.model_validate(agent.assemble(frags)) == TempsLongPresentation.model_validate(_with_layouts(DECK))


def test_an_empty_reference_point_is_left_out():
    frag = agent.to_fragment(agent.STEP_BY_NAME["episodes"], Option(id="a", slot="a", reason="", fields=FIELDS["episodes"]))
    assert len(frag["episodes"]["reperes"]) == 5
    assert frag["episodes"]["reperes"][0] == {"date": "2016", "label": "Mobilisations contre la loi Travail",
                                              "remark": "Lycéens et étudiants dans la rue", "tags": []}


# ── rules ───────────────────────────────────────────────────────────────────

def test_the_approved_deck_breaks_no_hard_rule_and_no_flag():
    frags = {}
    for name, fields in FIELDS.items():
        hard_, flags_ = agent.field_errors(name, fields, frags, ARTICLE)
        assert hard_ == [] and flags_ == [], (name, hard_, flags_)
        if name != "writing":
            frags[name] = _fragment(name)[name]


def test_a_reference_point_needs_a_year_and_a_label():
    assert any("rep1" in e for e in hard("episodes", rep1="Les mobilisations | Un cortège"))
    assert any("rep1" in e for e in hard("episodes", rep1="2016 |"))
    assert hard("episodes", rep1="2016 | Mobilisations contre la loi Travail") == []


def test_three_reference_points_are_required():
    assert any("rep3 is empty" in e for e in hard("episodes", rep3=""))
    assert any("rep3 is empty" in e for e in hard("tournants", rep3=""))


def test_the_episodes_need_four_points_but_the_tournants_only_three():
    assert any("rep4 is empty" in e for e in hard("episodes", rep4=""))
    assert not [e for e in hard("tournants", rep4="", rep5="") if "rep4" in e]


def test_the_tournants_take_three_or_four_points_never_five():
    assert any("rep5" in e and "3 or 4" in e for e in hard("tournants", rep5="2021 | Un texte | Une remarque"))
    assert hard("tournants") == []


def test_a_turning_point_remark_takes_two_lines_but_an_episode_remark_one():
    eighty = "Partisans : faire payer. Opposants : un frein au droit."
    assert hard("tournants", rep1=f"1986 | Un texte | {eighty}") == []
    assert any("rep1" in e and "remark" in e and "two lines" in e
               for e in hard("tournants", rep1="1986 | Un texte | " + "mot " * 30))
    assert any("rep1" in e and "remark" in e and "one line" in e for e in hard("episodes", rep1=f"2016 | Un épisode | {eighty}"))


def test_a_tournants_slide_without_a_recent_text_is_flagged_not_blocked():
    old = {"rep3": "2019 | Un texte plus ancien | Une autre remarque",
           "rep4": "2020 | Schéma national du maintien de l'ordre | Une doctrine de la force, publiée"}
    assert hard("tournants", **old) == []
    assert any("ends in 2020" in f and "most recent text" in f for f in flags("tournants", **old))
    assert not [f for f in flags("tournants") if "ends in" in f]


def test_a_date_is_short():
    assert any("rep1" in e and "characters" in e for e in hard("episodes", rep1="entre 2016 et 2019 | Mobilisations"))


def test_a_remark_is_one_line():
    assert any("rep1" in e and "remark" in e for e in hard("episodes", rep1="2016 | Mobilisations | " + "mot " * 20))


def test_a_label_is_two_lines_at_most():
    assert any("rep1" in e and "label" in e for e in hard("episodes", rep1="2016 | " + "mot " * 20 + "| Un cortège"))


def test_a_trend_figure_is_hard_but_a_date_is_not():
    assert any("figure" in e for e in hard("episodes", rep2="2018 | Les interpellations ont augmenté de 40 % | Un cortège"))
    assert any("figure" in e for e in hard("lecture", card1="Rupture | Un bond ? | Un bond de **3 millions** d'interpellations"))
    assert hard("episodes", rep2="28 oct. 2026 | Le fait | Un cortège") == []


def test_a_reference_point_with_no_remark_is_flagged_not_blocked():
    assert hard("episodes", rep1="2016 | Mobilisations contre la loi Travail") == []
    assert any("rep1 has no remark" in f for f in flags("episodes", rep1="2016 | Mobilisations contre la loi Travail"))


def test_a_remark_that_only_echoes_the_lead_word_is_flagged_not_blocked():
    echo = "2016 | Mobilisations contre la loi Travail | « Disproportionnée » : un cortège"
    assert hard("episodes", rep1=echo) == []
    assert any(f.startswith("episodes.rep1: the remark only echoes the lead's quoted word")
               for f in flags("episodes", rep1=echo))
    assert not [f for f in flags("episodes") if "echoes" in f]


def test_a_remark_that_repeats_another_is_flagged_not_blocked():
    twin = "2018–2019 | Gilets jaunes ; usage du lanceur de balles de défense (LBD) | Des mutilés graves, un débat sur le LBD"
    twin_fields = {"rep2": twin, "rep3": "mars 2023 | Sainte-Soline : heurts autour d'une retenue d'eau | Des mutilés graves, un débat sur la force"}
    assert hard("episodes", **twin_fields) == []
    assert any(f.startswith("episodes.rep3: the remark repeats rep2's") for f in flags("episodes", **twin_fields))
    assert not [f for f in flags("episodes") if "repeats rep" in f]


def test_one_shared_word_between_remarks_is_not_a_repeat():
    fields = {"rep3": "mars 2023 | Sainte-Soline : heurts autour d'une retenue d'eau | Des mutilés, des blessés des deux côtés"}
    assert not [f for f in flags("episodes", **fields) if "repeats rep" in f]     # « mutil » alone is shared with rep2


def test_a_remark_that_repeats_its_own_label_is_flagged_not_blocked():
    echo = "2018–2019 | Gilets jaunes ; débat sur le lanceur de balles de défense (LBD) | Des blessés graves, débat sur le LBD"
    assert hard("episodes", rep2=echo) == []
    assert any(f.startswith("episodes.rep2: the remark repeats the label") for f in flags("episodes", rep2=echo))
    assert not [f for f in flags("episodes") if "repeats the label" in f]
    assert not [f for f in flags("tournants") if "repeats the label" in f]


def test_a_timeline_lead_must_quote_a_word_of_the_media():
    assert any("must quote" in e for e in hard("episodes", lead="Dix ans d'épisodes à comparer."))
    assert any("quotes « inédit »" in e for e in hard("episodes", lead="Un mot comme « inédit » : dix ans d'épisodes."))
    assert hard("tournants", lead="Un « glissement » : cinquante ans de textes.") == []


def test_an_episodes_slide_that_reaches_too_far_back_is_flagged():
    assert any("tournants" in f for f in flags("episodes", rep1="2008 | Un épisode | « Disproportionnée » : un point"))
    assert not [f for f in flags("episodes") if "reaches back" in f]


def test_a_tournants_slide_that_stays_close_is_flagged():
    close = {"rep1": "2012 | Un repère | Un texte", "rep2": "2015 | Un repère | Un autre", "rep3": "2017 | Un repère | Encore un",
             "rep4": ""}
    assert any("reach further back" in f for f in flags("tournants", **close))
    assert not [f for f in flags("tournants") if "reach further back" in f]


def test_a_seuil_tournants_slide_only_needs_ten_years_of_reach():
    close = {"rep1": "2012 | Un repère | Un texte", "rep2": "2015 | Un repère | Un autre", "rep3": "2017 | Un repère | Encore un",
             "rep4": ""}
    seuil = {"axe": {"axe": {**AXE, "move": "seuil", "criteres": "Cible, Proportion, Effet"}}}
    assert not [f for f in agent.field_errors("tournants", {**FIELDS["tournants"], **close}, seuil, ARTICLE)[1] if "reach further back" in f]


def test_the_same_event_on_both_slides_is_flagged_not_blocked():
    twin = "2020 | Schéma national du maintien de l'ordre publié | « Disproportionnée » : la force"
    fields = {**FIELDS["episodes"], "rep3": twin}
    hard_, flags_ = agent.field_errors("episodes", fields, _fragment("tournants"), ARTICLE)
    assert hard_ == [] and [f for f in flags_ if f.startswith("episodes.rep3 looks like the point")]


def test_a_shared_year_alone_is_not_a_duplicate():
    # an episode and the law it prompted may share a year: only the same event is flagged
    fields = {**FIELDS["episodes"], "rep2": "2019 | Gilets jaunes ; débat sur le LBD | « Disproportionnée » : la force"}
    assert not [f for f in agent.field_errors("episodes", fields, _fragment("tournants"), ARTICLE)[1]
                if "looks like" in f]


def test_the_duplicate_flag_only_concerns_the_episodes():
    assert not [f for f in flags("tournants", _fragment("tournants")) if "looks like" in f]


def test_a_card_needs_its_three_parts():
    ok = "Cycle | Y a-t-il un retour ? | Le **retour** : elle reviendrait"
    assert hard("lecture", card3=ok) == []
    assert any("lecture.card3" in e and "must read" in e for e in hard("lecture", card3="Cycle | Des pics à chaque mobilisation ?"))
    assert any("lecture.card3" in e and "must read" in e for e in hard("lecture", card3="Cycle | Un retour ? | "))
    assert any("needs three cards" in e for e in hard("lecture", card1="", card2="", card3=""))
    assert any("the text" in e and "characters" in e for e in hard("lecture", card3="Cycle | Un retour ? | Le **retour** : " + "mot " * 30))
    assert any("bold" in e for e in hard("lecture", card3="Cycle | Un retour ? | Le retour arriverait"))
    assert any("end with" in e for e in hard("lecture", card3="Cycle | Un retour | Le **retour** : x"))
    assert any("the question is" in e for e in hard("lecture", card3="Cycle | " + "Un retour " * 5 + "? | Le **retour** : x"))
    assert any("the name is" in e for e in hard("lecture", card3="Un très long nom | Un retour ? | Le **retour** : x"))


def _duo(**changes):
    return {"title": "Maintien de l'ordre ou « **répression** » ?", "lead": "Pour les experts, trois critères les séparent.",
            "card1": "Rupture | Qui est visé ? | les auteurs de violences | des manifestants pacifiques",
            "card2": "Continuité | Par rapport aux violences ? | à la mesure | disproportionnée",
            "card3": "Cycle | Sur le droit de manifester ? | aucun effet | dissuade", "question": "Où placez-vous la ligne ?",
            "where": "", "author": "", "head1": "Maintien de l'ordre", "head2": "« Répression »",
            "aside_heading": "Pour Amnesty, sept signes d'un « glissement ».",
            "aside1": "Presse | attaquer la presse | book", "aside2": "Dissidence | écraser la dissidence", **changes}


def test_a_table_row_has_two_outcomes_and_the_signs_each_a_name_and_a_phrase():
    def duo_hard(**c):
        return agent.field_errors("lecture", _duo(**c), {}, ARTICLE)[0]
    assert duo_hard() == []
    # a row of the decision table: « critère | question | issue 1 | issue 2 »
    assert any("must read" in e for e in duo_hard(card1="Rupture | Qui est visé ? | les auteurs"))
    assert any("must read" in e for e in duo_hard(card1="Rupture | | les auteurs | des pacifiques"))
    assert any("the question is" in e and "max 28" in e for e in duo_hard(card1="Rupture | Qui est donc visé, au juste, ici ? | a | b"))
    assert any("first outcome" in e and "max 30" in e for e in duo_hard(card1="Rupture | Qui ? | " + "mot " * 12 + "| b"))
    assert any("second outcome" in e and "max 30" in e for e in duo_hard(card1="Rupture | Qui ? | a | " + "mot " * 12))
    assert any("the name is" in e for e in duo_hard(card1="Un très long nom | Qui ? | a | b"))
    assert not any("question must end" in e or "bold" in e for e in duo_hard())                     # no « ? » or bold asked here
    # the names of the columns and the line above the signs
    for field in ("head1", "head2", "aside_heading"):
        assert any(f"{field} is empty" in e for e in duo_hard(**{field: ""})), field
    assert any("head1" in e and "max 20" in e for e in duo_hard(head1="Maintien de l'ordre public"))
    assert any("aside_heading" in e and "max 60" in e for e in duo_hard(aside_heading="Pour Amnesty, " + "tout autrement " * 6))
    # the signs: « nom | phrase | icône », a name that is a pill
    assert any("2 to 7" in e for e in duo_hard(aside2=""))
    assert any("must read" in e and "aside1" in e for e in duo_hard(aside1="Presse | "))
    assert any("aside1" in e and "name" in e and "max 10" in e for e in duo_hard(aside1="Une presse attaquée | attaquer la presse"))
    assert any("aside1" in e and "phrase" in e and "max 34" in e for e in duo_hard(aside1="Presse | " + "mot " * 10))
    assert duo_hard(**{f"aside{i}": f"Signe {i} | une phrase" for i in range(1, 8)}) == []             # seven signs are allowed
    assert any("lecture.where must stay empty" in e for e in duo_hard(where="ministère de l'Intérieur"))
    assert any("lecture.author must stay empty" in e for e in duo_hard(author="Une ligne."))
    frag = agent.to_fragment(agent.STEP_BY_NAME["lecture"], Option(id="a", slot="a", reason="", fields=_duo()))["lecture"]
    assert frag["aside_cards"] == [{"label": "Presse", "text": "attaquer la presse", "icon": "book"}, {"label": "Dissidence", "text": "écraser la dissidence", "icon": ""}]
    assert (frag["readings"][0]["signature"], frag["readings"][0]["indicator"], frag["readings"][0]["other"]) == \
        ("Qui est visé ?", "les auteurs de violences", "des manifestants pacifiques")
    assert frag["heads"] == ["Maintien de l'ordre", "« Répression »"] and frag["aside_heading"].startswith("Pour Amnesty")
    plain = agent.to_fragment(agent.STEP_BY_NAME["lecture"], Option(id="a", slot="a", reason="", fields=FIELDS["lecture"]))["lecture"]
    assert plain["aside_cards"] == [] and plain["heads"] == [] and plain["readings"][0]["other"] == ""


def test_the_second_voice_names_must_match_the_axe_and_tags_may_use_both_voices():
    axe = {"axe": {"axe": {**AXE, "move": "seuil", "criteres": "Rupture, Continuité, Cycle", "criteres2": "Presse, Dissidence"}}}
    assert agent.field_errors("lecture", _duo(), axe, ARTICLE)[0] == []
    assert any("signes" in e or "must be named Presse, Dissidence" in e
               for e in agent.field_errors("lecture", _duo(aside1="Peur | gouverner par la peur"), axe, ARTICLE)[0])
    one = {**FIELDS["episodes"], "rep1": FIELDS["episodes"]["rep1"] + " | rupture, presse"}
    assert not [e for e in agent.field_errors("episodes", one, axe, ARTICLE)[0] if "tag" in e]
    three = {**FIELDS["episodes"], "rep1": FIELDS["episodes"]["rep1"] + " | rupture, presse, cycle"}
    assert any("3 tags" in e and "2 at most" in e for e in agent.field_errors("episodes", three, axe, ARTICLE)[0])
    def axe_hard(**c):
        return agent.field_errors("axe", {**AXE, "move": "seuil", "criteres": "Cible, Proportion, Effet", **c}, {}, ARTICLE)[0]
    assert axe_hard(criteres2="Presse, Dissidence, Techno") == []
    assert any("only for the move seuil" in e for e in agent.field_errors("axe", {**AXE, "criteres2": "Presse, Dissidence"}, {}, ARTICLE)[0])
    assert any("signs" in e for e in axe_hard(criteres2="Presse"))
    assert any("at most" in e for e in axe_hard(criteres2="Presse, Une presse attaquée"))


def test_the_cards_take_the_axe_criteria_in_order():
    frags = _fragment("axe")
    assert agent.field_errors("lecture", FIELDS["lecture"], frags, ARTICLE)[0] == []
    swapped = {**FIELDS["lecture"], "card1": FIELDS["lecture"]["card2"], "card2": FIELDS["lecture"]["card1"]}
    assert any("must be named Rupture, Continuité, Cycle" in e for e in agent.field_errors("lecture", swapped, frags, ARTICLE)[0])
    seuil = {"axe": {"axe": {**AXE, "move": "seuil", "criteres": "Cible, Proportion, Effet"}}}
    own = {**FIELDS["lecture"], "card1": "Cible | Qui est visé ? | Les **auteurs**, pas la foule",
           "card2": "Proportion | À la mesure ? | L'**ampleur** est jugée disproportionnée",
           "card3": "Effet | Quel effet ? | L'ampleur **dissuade** de manifester"}
    assert agent.field_errors("lecture", own, seuil, ARTICLE)[0] == []
    assert any("must be named" in e for e in agent.field_errors("lecture", FIELDS["lecture"], seuil, ARTICLE)[0])


def test_an_older_lecture_keeps_its_three_readings_without_an_axe():
    old = {"title": "Rupture, continuité ou **cycle** ?", "lead": FIELDS["lecture"]["lead"], "question": FIELDS["lecture"]["question"],
           "rupture": "Un saut ? | Le **saut** : il sortirait de la série | INSEE",
           "continuite": "Octobre prolonge-t-il la tendance ? | Le **prolongement** : sans saut | INSEE",
           "cycle": "Y a-t-il un retour ? | Le **retour** : il reviendrait | INSEE"}
    assert agent.field_errors("lecture", old, {}, ARTICLE)[0] == []
    frag = agent.to_fragment(agent.STEP_BY_NAME["lecture"], Option(id="a", slot="a", reason="", fields=old))
    assert [(r["kind"], r["label"], r["where"]) for r in frag["lecture"]["readings"]] == [
        ("rupture", "Rupture", "INSEE"), ("continuite", "Continuité", "INSEE"), ("cycle", "Cycle", "INSEE")]
    assert any("où regarder" in e for e in agent.field_errors("lecture", {**old, "rupture": "Un saut ? | Le **saut** : x"}, {}, ARTICLE)[0])


def test_a_line_that_refers_to_nothing_of_the_lead_or_slides_2_and_3_is_flagged_not_blocked():
    off = "Cycle | Des pics à chaque mobilisation ? | Les **mêmes données**, ordonnées dans le temps"
    frags = {**_fragment("tournants"), **_fragment("episodes")}
    assert hard("lecture", card3=off) == []
    assert any(f.startswith("lecture.card3: the text refers to nothing") for f in flags("lecture", frags, card3=off))
    assert not [f for f in flags("lecture", frags) if "refers to nothing" in f]


def test_a_line_can_point_at_an_episode_a_text_or_a_year():
    frags = {**_fragment("tournants"), **_fragment("episodes")}
    for line in ("Le dernier épisode contre les gilets jaunes", "Les textes de 1970 à 2026, dans l'ordre",
                 "Les mois calmes de 2023 à 2025"):
        assert not [f for f in flags("lecture", frags, card1=f"Rupture | Un saut net ? | **{line}**") if "refers to nothing" in f], line


def test_the_closing_line_is_a_question():
    assert any("must be a question" in e for e in hard("lecture", question="Dites-nous votre lecture."))


def test_a_trap_needs_a_title_and_a_question():
    assert any("piege1 must read" in e for e in hard("pieges", piege1="Le point de départ"))
    assert hard("pieges", piege1="Le point de départ | Changer de date.") == []        # a watch-out is as good as a question
    assert any("piege4 is empty" in e for e in hard("pieges", piege4=""))


def test_the_slide_5_lead_need_not_name_the_measure():
    plain = "Trois points à vérifier avant de dire que la réponse a changé."
    assert hard("pieges", lead=plain) == []
    assert not [f for f in flags("pieges", _fragment("lecture"), lead=plain) if "pieges.lead" in f]


def test_a_trap_that_cites_nothing_of_the_measure_is_flagged_not_blocked():
    off = {**FIELDS["pieges"], "piege1": "Le point de départ | Le résultat change-t-il si l'on commence plus tard ?"}
    hard_, flags_ = agent.field_errors("pieges", off, _fragment("lecture"), ARTICLE)
    assert hard_ == [] and any(f.startswith("pieges.piege1 cites nothing") for f in flags_)


def test_caps_and_accusing_words_are_hard_unless_quoted():
    assert any("axe.fait" in e for e in agent.field_errors("axe", {**AXE, "fait": "x" * 65}, {}, ARTICLE)[0])
    assert any("accusing" in e for e in hard("pieges", lead="Une lecture trompeuse du temps."))
    assert hard("lecture", lead="L'ONG parle de « manipulation » de l'opinion.") == []


def test_the_hook_promise_is_flagged_not_blocked():
    assert hard("hook", promise="Un regard sur la séquence.") == []
    assert any("Prendre du recul" in f for f in flags("hook", promise="Un regard sur la séquence."))


def test_the_hook_promise_continues_the_title_and_the_axe():
    frags = _fragment("axe")
    assert agent.field_errors("hook", FIELDS["hook"], frags, ARTICLE) == ([], [])
    off = "Un regard sur la séquence ?"
    assert any("axe's question" in f for f in agent.field_errors("hook", {**FIELDS["hook"], "promise": off}, frags, ARTICLE)[1])
    assert any("quoted passages" in f for f in agent.field_errors("hook", {**FIELDS["hook"], "promise": "Un phénomène récent, ou ancien ?"},
                                                                  {"axe": {"axe": {**AXE, "title": "Un phénomène récent, ou ancien ?"}}}, ARTICLE)[1])


def test_the_hook_tagline_is_one_line_with_key_words_in_gold():
    frags = _fragment("axe")
    assert any("tagline is empty" in e for e in agent.field_errors("hook", {**FIELDS["hook"], "tagline": ""}, frags, ARTICLE)[0])
    assert any("no key words in gold" in e for e in agent.field_errors("hook", {**FIELDS["hook"], "tagline": "Trois lectures pour en juger."}, frags, ARTICLE)[0])
    assert any("hook.tagline" in e and "max 110" in e for e in agent.field_errors("hook", {**FIELDS["hook"], "tagline": "mot " * 40 + "**x**"}, frags, ARTICLE)[0])
    assert hard("hook", tagline="") == []                                            # an older deck has no axe, so no tagline to ask for


def test_the_axe_names_a_move_a_question_and_a_word_of_the_media():
    def axe_hard(**c):
        return agent.field_errors("axe", {**AXE, **c}, {}, ARTICLE)[0]
    assert axe_hard() == []
    assert any("one of" in e for e in axe_hard(move="tendance"))
    assert any("must be a question" in e for e in axe_hard(title="La force est-elle nouvelle."))
    assert any("not in the source" in e for e in axe_hard(mot="dérive autoritaire du pouvoir"))
    assert any("criteres" in e for e in axe_hard(move="seuil", criteres="Cible, Effet"))
    assert any("Rupture, Continuité, Cycle" in e for e in axe_hard(criteres="Rupture, Cycle, Continuité"))
    assert any("at most" in e for e in axe_hard(move="seuil", criteres="Cible, Proportion, Une durée longue"))
    assert axe_hard(move="sequence", criteres="") == []
    assert any("is empty" in e for e in axe_hard(reponse=""))
    assert any("axe.fait" in e and "source does not say it" in e for e in axe_hard(fait="Des experts « scandalisés » par la loi"))
    assert any("is empty" in e for e in axe_hard(fait=""))


def test_the_fact_of_the_axe_is_the_hook_title_and_fix_reaches_it(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    assert agent.adapt(full(), steps_dir=steps, article_text=ARTICLE).hook.title == AXE["fait"]
    before = list(fake.labels)
    agent.fix(full(), steps, "axe.fait", "Des experts de l'ONU « consternés » par la « répression » en France", ARTICLE)
    assert fake.labels == before
    pres = agent.adapt(full(), steps_dir=steps, article_text=ARTICLE)
    assert pres.hook.title.endswith("en France") and pres.hook.promise == DECK["hook"]["promise"]


def test_a_key_under_the_rows_is_optional_and_drawn_when_given(tmp_path):
    tagged = {**FIELDS["episodes"], "rep1": FIELDS["episodes"]["rep1"] + " | rupture"}
    seuil = {"axe": {"axe": {**AXE, "criteres": "Rupture, Continuité, Cycle"}}}
    assert not [e for e in agent.field_errors("episodes", tagged, seuil, ARTICLE)[0] if "key" in e]   # the key is optional, pills or not
    keyed = {**tagged, "key": "Pastilles : les critères des experts et les signes d'Amnesty."}
    assert not [e for e in agent.field_errors("episodes", keyed, seuil, ARTICLE)[0] if "key" in e]
    assert not [e for e in agent.field_errors("episodes", FIELDS["episodes"], seuil, ARTICLE)[0] if "key" in e]   # no pills, no key
    assert any("key is" in e and "max 100" in e for e in agent.field_errors("episodes", {**keyed, "key": "mot " * 30}, seuil, ARTICLE)[0])
    frag = agent.to_fragment(agent.STEP_BY_NAME["episodes"], Option(id="a", slot="a", reason="", fields=keyed))
    assert frag["episodes"]["key"].startswith("Pastilles")
    deck = copy.deepcopy(DECK)
    deck["episodes"]["key"] = "Pastilles : en or, les critères des experts."
    deck["episodes"]["reperes"][0]["tags"] = ["rupture"]
    paths = renderer.generate_html(extract(full(), TempsLongPresentation.model_validate(deck)), tmp_path / "html")
    html_text = next(p for p in paths if p.stem.endswith("episodes")).read_text(encoding="utf-8")
    assert '<div class="fkey">' in html_text and "Pastilles : en or, les critères des experts." in html_text
    plain = renderer.generate_html(extract(full(), TempsLongPresentation.model_validate(DECK)), tmp_path / "plain")
    assert 'class="fkey"' not in next(p for p in plain if p.stem.endswith("episodes")).read_text(encoding="utf-8")


def test_a_tag_must_be_one_of_the_axe_criteria():
    seuil = {"axe": {"axe": {**AXE, "move": "seuil", "criteres": "Cible, Proportion, Effet"}}}
    ok = {**FIELDS["episodes"], "rep1": FIELDS["episodes"]["rep1"] + " | cible, effet"}
    assert not [e for e in agent.field_errors("episodes", ok, seuil, ARTICLE)[0] if "tag" in e]
    assert any("tag « durée »" in e for e in agent.field_errors("episodes", {**ok, "rep1": FIELDS["episodes"]["rep1"] + " | durée"}, seuil, ARTICLE)[0])
    assert any("the axe has none" in e or "Rupture" in e for e in agent.field_errors("episodes", ok, {}, ARTICLE)[0])
    frag = agent.to_fragment(agent.STEP_BY_NAME["episodes"], Option(id="a", slot="a", reason="", fields=ok))
    assert frag["episodes"]["reperes"][0]["tags"] == ["cible", "effet"] and frag["episodes"]["reperes"][1]["tags"] == []


def test_the_move_sets_the_order_of_the_slides():
    frags = {s.name: agent.to_fragment(s, Option(id="a", slot="a", reason="", fields=FIELDS[s.name])) for s in agent.STEPS}
    assert agent.assemble(frags)["order"] == [] and agent.assemble(frags)["move"] == "forme"
    frags["axe"] = {"axe": {**AXE, "move": "seuil"}}
    assert agent.assemble(frags)["order"] == ["position", "lecture", "episodes", "tournants", "pieges"]


def test_the_caption_needs_four_hashtags():
    assert hard("writing") == []
    assert any("hashtag" in e for e in hard("writing", caption=DECK["caption"].replace("#espritcritique", "")))


def test_an_older_reading_needs_no_where_once_the_series_is_named_under_the_lead():
    old = {**{k: v for k, v in FIELDS["lecture"].items() if not k.startswith("card")}, "where": "",
           "rupture": "Interpelle-t-on soudain bien plus ? | Le nombre d'octobre sortirait de la **trajectoire** des épisodes précédents",
           "continuite": "Octobre prolonge-t-il la tendance ? | Octobre **prolongerait** la tendance",
           "cycle": "Y a-t-il un retour ? | Le **retour** : elle reviendrait"}
    assert any("où regarder" in e for e in agent.field_errors("lecture", old, {}, ARTICLE)[0])            # three parts without a shared line
    assert agent.field_errors("lecture", {**old, "where": "ministère de l'Intérieur"}, {}, ARTICLE)[0] == []   # two are enough with it
    assert any("URL" in e for e in hard("lecture", where="https://www.interieur.gouv.fr"))
    assert any("max 48" in e for e in hard("lecture", where="x" * 49))


def test_the_position_breaks_no_rule_and_every_card_is_required_and_capped():
    assert hard("position") == [] and flags("position") == []
    assert any("ecarte is empty" in e for e in hard("position", ecarte=""))
    assert any("mecanisme is empty" in e for e in hard("position", mecanisme=""))
    assert any("title" in e and "max 46" in e for e in hard("position", title="**x** " + "x" * 46))
    assert any("issue" in e and "max 108" in e for e in hard("position", issue="x" * 109))
    assert any("kicker" in e and "max 30" in e for e in hard("position", kicker="x" * 31))
    assert any("issue_label" in e and "max 30" in e for e in hard("position", issue_label="x" * 31))
    assert hard("position", issue_label="") == []   # a label is optional


def test_a_quoted_passage_of_the_position_must_be_in_the_source():
    assert any("quotes" in e for e in hard("position", issue="Elle y lit une « dérive inventée »."))
    assert hard("position", issue="Elle y lit un « glissement ».") == []


def test_the_position_may_give_a_figure_only_if_the_source_has_it():
    assert hard("position", diagnostic="Sept points d'alerte, soit 12 % des cas.") == []     # no trend-figure ban here
    assert any("12 %" in f for f in flags("position", diagnostic="Sept points d'alerte, soit 12 % des cas."))
    assert flags("position", diagnostic="Sept points d'alerte relevés.") == []


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


def _seuil_fields() -> dict:
    """The step fields of a `seuil` deck: a decision table and signs, written before the timelines."""
    fields = copy.deepcopy(FIELDS)
    fields["axe"] = {**AXE, "move": "seuil", "criteres": "Cible, Proportion, Effet", "criteres2": "Presse, Dissidence"}
    fields["lecture"] = _duo(card1="Cible | Qui est visé ? | les auteurs de violences | des milliers de mineurs",
                             card2="Proportion | Par rapport aux violences ? | à la mesure | disproportionnée",
                             card3="Effet | Sur le droit de manifester ? | aucun effet | dissuade")
    return fields


def test_a_seuil_deck_writes_the_lecture_before_the_timelines(monkeypatch, tmp_path):
    fields = _seuil_fields()
    labels, messages = [], {}

    def call(user_message, schema, validator, no_api=False, label="", system=None):
        labels.append(label)
        messages[label] = user_message
        one = copy.deepcopy(fields[label])
        data = ({"options": [{**one, "reason": "r"}, {**one, "reason": "r2"}, {**one, "reason": "r3"}], "recommended": [0]}
                if label != "writing" else one)
        assert validator(data) == [], (label, validator(data))
        return data

    monkeypatch.setattr(agent, "_call_with_retry", call)
    pres = agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE)
    assert labels == ["axe", "position", "lecture", "episodes", "tournants", "pieges", "hook", "writing"]
    assert pres.order == ["position", "lecture", "episodes", "tournants", "pieges"]
    assert "ORDRE D'ÉCRITURE (mouvement" not in messages["axe"]
    assert "à venir = episodes, tournants, pieges, hook, writing" in messages["lecture"]
    assert "déjà écrit = axe, position, lecture" in messages["episodes"]
    assert pres.episodes.layout == "annees" and pres.tournants.layout == "axe"
    labels.clear()
    agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE)       # a second run reuses every step
    assert labels == []


def test_a_guided_seuil_run_asks_for_the_lecture_before_the_timelines(monkeypatch, tmp_path):
    fields = _seuil_fields()

    def call(user_message, schema, validator, no_api=False, label="", system=None):
        one = copy.deepcopy(fields[label])
        return ({"options": [{**one, "reason": "r"}, {**one, "reason": "r2"}, {**one, "reason": "r3"}], "recommended": [0]}
                if label != "writing" else one)

    monkeypatch.setattr(agent, "_call_with_retry", call)
    steps = tmp_path / "adapt_steps"
    asked = []
    for _ in range(8):
        agent.adapt(full(), steps_dir=steps, article_text=ARTICLE, guided=True)
        pending = agent.pending_step(steps)
        if pending is None:
            break
        asked.append(pending)
        agent.choose(full(), steps, pending, ["a"], {}, article_text=ARTICLE)
    assert asked == ["axe", "position", "lecture", "episodes", "tournants", "pieges", "hook"]
    deck = agent.adapt(full(), steps_dir=steps, article_text=ARTICLE, guided=True)
    assert deck is not None and deck.move == "seuil"
    agent.fix(full(), steps, "lecture.lead", "Pour les rapporteurs, trois critères jugent la réponse.", ARTICLE)
    assert agent.pending_step(steps) is None                                                # the later steps are re-stamped, not stale


def test_the_other_moves_keep_the_default_order():
    assert [s.name for s in agent.steps_in_order("forme")] == [s.name for s in agent.STEPS]
    assert [s.name for s in agent.steps_in_order(None)] == [s.name for s in agent.STEPS]
    assert [s.name for s in agent.steps_in_order("seuil")][:4] == ["axe", "position", "lecture", "episodes"]


def test_unattended_runs_eight_steps_and_rebuilds_the_deck(fake, tmp_path):
    pres = agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE)
    assert fake.labels == [s.name for s in agent.STEPS] and len(fake.labels) == 8
    assert all(e == [] for e in fake.errors.values())
    assert pres.model_dump() == TempsLongPresentation.model_validate(_with_layouts(DECK)).model_dump()


def test_guided_pauses_at_the_first_step(fake, tmp_path, capsys):
    assert agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE, guided=True) is None
    assert fake.labels == ["axe"]
    assert agent.pending_step(tmp_path / "adapt_steps") == "axe"
    assert "[axe]" in capsys.readouterr().out


def test_stop_after_a_step(fake, tmp_path):
    assert agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE, stop_after="episodes") is None
    assert fake.labels == ["axe", "position", "tournants", "episodes"]


def test_a_later_step_receives_the_earlier_picks(fake, tmp_path, monkeypatch):
    messages = []
    monkeypatch.setattr(agent, "_call_with_retry",
                        lambda msg, *a, **kw: messages.append(msg) or fake(msg, *a, **kw))
    agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE, stop_after="pieges")
    fixed = messages[5].split("CHOIX FIXÉS (ne les réécris pas) :")[1]
    assert "casseurs-payeurs" in fixed and "loi Travail" in fixed and "recours à la force" in fixed and "répression" in fixed


def test_a_pick_then_a_fix_rewrites_one_field_without_regenerating(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, article_text=ARTICLE)
    before = list(fake.labels)
    agent.fix(full(), steps, "episodes.rep1", "2016 | Mobilisations contre la loi El Khomri | « Disproportionnée » : un cortège", ARTICLE)
    assert fake.labels == before
    pres = agent.adapt(full(), steps_dir=steps, article_text=ARTICLE)
    assert fake.labels == before                      # the later steps were re-stamped, not rerun
    assert pres.episodes.reperes[0].label == "Mobilisations contre la loi El Khomri"


def test_fix_reaches_the_traps(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, article_text=ARTICLE)
    agent.fix(full(), steps, "pieges.piege1", "Le départ | Change-t-on de lecture en changeant de date ?", ARTICLE)
    assert agent.adapt(full(), steps_dir=steps, article_text=ARTICLE).pieges.pieges[0].title == "Le départ"


def test_choose_keeps_an_edited_pick_and_warns_on_a_broken_rule(fake, tmp_path):
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, article_text=ARTICLE, guided=True)
    agent.choose(full(), steps, "axe", ["a"], {}, article_text=ARTICLE)
    agent.adapt(full(), steps_dir=steps, article_text=ARTICLE, guided=True)
    agent.choose(full(), steps, "position", ["a"], {}, article_text=ARTICLE)
    agent.adapt(full(), steps_dir=steps, article_text=ARTICLE, guided=True)
    warnings = agent.choose(full(), steps, "tournants", ["a"],
                            {"a.rep2": "2011 | Une hausse de 12 % | « Glissement » : un texte"}, article_text=ARTICLE)
    assert any("figure" in w for w in warnings)
    assert agent.pending_step(steps) is None


def test_choose_refuses_a_step_without_options(fake, tmp_path):
    with pytest.raises(agent.ChoiceError):
        agent.choose(full(), tmp_path / "adapt_steps", "writing", ["a"], {})


def test_fix_names_a_known_field(fake, tmp_path):
    with pytest.raises(agent.ChoiceError):
        agent.fix(full(), tmp_path / "adapt_steps", "invisible.field", "x")


# ── wiring and the render ───────────────────────────────────────────────────

def test_the_format_is_registered():
    assert FORMATS["temps_long"] == ("agent.temps_long_adapt_agent", "extractors.temps_long",
                                     "renderer.instagram_carousel.temps_long")


def test_the_cli_finds_the_guided_module_of_a_format_folder():
    import main
    assert main._guided_module("samples/outputs/x/temps_long") is agent
    assert main._guided_module("samples/outputs/x/cadrage_logique").__name__ == "agent.cadrage_adapt_agent"


def test_every_step_can_be_a_stop_after_choice():
    import main
    for name in agent.STEP_NAMES:
        assert name in main._STEP_CHOICES, name


def test_seven_slides_are_rendered(tmp_path):
    doc = extract(full(), TempsLongPresentation.model_validate(DECK))
    paths = renderer.generate_html(doc, tmp_path / "html")
    assert [p.stem for p in paths] == ["01_hook", "02_position", "03_episodes", "04_tournants", "05_lecture", "06_pieges", "07_cta"]
    texts = {p.stem: html.unescape(p.read_text(encoding="utf-8")).replace("⁠", "").replace(" ", " ")
             for p in paths}
    assert "est-elle nouvelle" in texts["01_hook"]
    position = texts["02_position"]
    assert "Ce que dit l'auteur" in position and "glissement" in position and "Amnesty relève" in position   # the title, then the sentence under it
    assert all(label in position for label in ("Ce qu'il écarte", "Son diagnostic", "Pourquoi ça a duré", "Sa conclusion"))
    custom = copy.deepcopy(DECK)
    custom["position"] |= {"kicker": "Ce que disent l'ONU et Amnesty", "ecarte_label": "Ce qu'ils reconnaissent", "issue_label": "Ce qu'Amnesty y voit"}
    cpaths = renderer.generate_html(extract(full(), TempsLongPresentation.model_validate(custom)), tmp_path / "custom")
    ctext = html.unescape(next(p for p in cpaths if p.stem == "02_position").read_text(encoding="utf-8"))
    assert "Ce que disent l'ONU et Amnesty" in ctext and "Ce que dit l'auteur" not in ctext and "Ce que dit l'auteur" in position
    assert "Ce qu'ils reconnaissent" in ctext and "Ce qu'Amnesty y voit" in ctext
    assert "Ce qu'il écarte" not in ctext and "Sa conclusion" not in ctext and "Son diagnostic" in ctext   # empty = default
    assert position.count('class="row"') == 4 and position.split("<body>")[1].count("data-perch") == 1
    assert "« surenchère sécuritaire »" in position and "7 / 7" in texts["07_cta"] and "2 / 7" in position
    assert "Les épisodes récents" in texts["03_episodes"] and "2018–2019" in texts["03_episodes"]
    assert "Des mutilés, un débat sur la force" in texts["03_episodes"]
    assert texts["03_episodes"].count('class="rep"') == 5 and "Légifrance" not in texts["03_episodes"]
    for slide in ("03_episodes", "04_tournants"):          # the bird perches above the first row
        first = texts[slide].index('class="rep"')
        assert texts[slide][first:].startswith('class="rep" data-perch'), slide
        assert texts[slide].split("<body>")[1].count("data-perch") == 1
    assert "Les textes de loi" in texts["04_tournants"] and "casseurs-payeurs" in texts["04_tournants"]
    assert "Payer les dégâts du groupe, même sans en être l'auteur" in texts["04_tournants"]
    assert "Une sanction pénale, au-delà des auteurs identifiés" in texts["04_tournants"]
    assert "vidéosurveillance algorithmique" in texts["04_tournants"]
    assert texts["04_tournants"].count('class="rep"') == 4
    lecture = texts["05_lecture"]
    assert all(label in lecture for label in ("Rupture", "Continuité", "Cycle")) and lecture.count('class="card read"') == 3
    assert "Pour trancher" in lecture and "Mesure suivie" not in lecture
    assert 'class="ask"' not in lecture and "soutiennent-elles" not in lecture and "mineurs" not in lecture
    assert "Le point de départ" in texts["06_pieges"] and texts["06_pieges"].count('class="card piege"') == 4
    assert "Vous jugez." in texts["07_cta"]
    assert "votre intuition avant de regarder : rupture, continuité ou cycle ?</span>" in texts["07_cta"]


# ── the picture: one photo opens and closes the deck ────────────────────────

def _render_with(tmp_path, *image_names):
    from PIL import Image
    base = tmp_path / "article"
    base.mkdir()
    for name in image_names:
        Image.new("RGB", (40, 24), "#445566").save(base / name)
    doc = extract(full(), TempsLongPresentation.model_validate(DECK))
    paths = renderer.generate_html(doc, base / "temps_long" / "html")
    return {p.stem: p.read_text(encoding="utf-8") for p in paths}, base


def test_a_lone_image_is_the_full_bleed_photo_of_the_hook_and_the_sign_off(tmp_path):
    from renderer.instagram_carousel._shared import background_image
    texts, base = _render_with(tmp_path, "image.png")
    photo = background_image(base, or_cover=True)
    assert photo.startswith("data:image/png;base64,")
    assert '<div class="photo-zone"' in texts["01_hook"] and 'class="shot"' not in texts["01_hook"]
    assert '<div class="book"' in texts["07_cta"]
    assert photo in texts["01_hook"] and photo in texts["07_cta"]          # the same picture, twice


def test_a_background_file_still_wins_over_the_image(tmp_path):
    from renderer.instagram_carousel._shared import background_image
    from PIL import Image
    base = tmp_path / "article"
    base.mkdir()
    Image.new("RGB", (40, 24), "#112233").save(base / "image.png")
    Image.new("RGB", (40, 24), "#aa5500").save(base / "background.png")
    assert background_image(base, or_cover=True) == background_image(base)


def test_no_image_means_no_photo(tmp_path):
    texts, _ = _render_with(tmp_path)
    assert '<div class="photo-zone"' not in texts["01_hook"] and '<div class="book"' not in texts["07_cta"]


def test_other_formats_keep_ignoring_an_image_as_background(tmp_path):
    from renderer.instagram_carousel._shared import background_image
    from PIL import Image
    base = tmp_path / "article"
    base.mkdir()
    Image.new("RGB", (40, 24), "#112233").save(base / "image.png")
    assert background_image(base) == ""


# ── the layout: every field at its cap still fits its lines and the slide ───

_POOL = ("le la les de des du un une et ou à au en par sur pour dans avec sans plus que qui ne pas "
         "l'État l'ordre l'encadrement manifestations manifestation lycéennes étudiantes mobilisation mobilisations "
         "interpellations interpellé vidéosurveillance algorithmique administrative réforme retraites libertés "
         "constitutionnel Conseil d'État Défenseur droits Ministère l'Intérieur bilans décisions rapports annuels "
         "gilets jaunes schéma national justice mineurs rupture continuité cycle séries mesure épisodes comparer").split()
_QUOTED_PHRASES = ("depuis quand", "glissement", "dérive", "tendance mondiale", "répression")


def _sample(rng: random.Random, n: int) -> str:
    """Random French-looking text of at most `n` characters, long words and « … » groups
    (tied by non-breaking spaces, as the typography filter does) included."""
    out = ""
    while True:
        w = rng.choice(_POOL) if rng.random() > 0.08 else "« " + rng.choice(_QUOTED_PHRASES) + " »"
        if len((out + " " + w).strip()) > n:
            return out
        out = (out + " " + w).strip()


def _cap(step: str, field: str) -> int:
    return agent._CAPS[(step, field)][1]


def worst_case_deck(seed: int = 0) -> dict:
    """The fixture deck with every text field at its cap and five reference points per timeline."""
    rng = random.Random(seed)
    quote = " « glissement »"                         # a timeline lead must quote the media
    frise = lambda step: {"title": _sample(rng, _cap(step, "title")),  # noqa: E731
                          "lead": _sample(rng, _cap(step, "lead") - len(quote)) + quote,
                          "reperes": [{"date": "2018–2019", "label": _sample(rng, agent._TOURNANTS_LABEL_MAX if step == "tournants" else agent._LABEL_MAX),
                                       "remark": _sample(rng, agent._TOURNANTS_REMARK_MAX if step == "tournants"
                                                         else agent._REMARK_MAX)}
                                      for _ in range(4 if step == "tournants" else 5)]}
    return DECK | {
        "hook": {"title": _sample(rng, _cap("axe", "fait")), "promise": _sample(rng, _cap("hook", "promise"))},
        "position": {"title": "**" + _sample(rng, 12) + "** " + _sample(rng, _cap("position", "title") - 14), "lead": _sample(rng, _cap("position", "lead")),
                     **{c: _sample(rng, _cap("position", c)) for c in agent._POSITION_CARDS},
                     "kicker": _sample(rng, _cap("position", "kicker")),
                     **{f"{c}_label": _sample(rng, _cap("position", f"{c}_label")) for c in agent._POSITION_CARDS}},
        "tournants": frise("tournants"), "episodes": frise("episodes"),
        "lecture": {"title": _sample(rng, _cap("lecture", "title")), "lead": _sample(rng, _cap("lecture", "lead")),
                    "readings": [{"kind": k, "signature": _sample(rng, agent._SIGNATURE_MAX - 2) + " ?",
                                  "indicator": "Le **déficit** : " + _sample(rng, agent._INDICATOR_MAX - 15),
                                  "where": _sample(rng, agent._WHERE_MAX)}
                                 for k in ("rupture", "continuite", "cycle")],
                    "question": _sample(rng, _cap("lecture", "question") - 2) + " ?",
                    "where": _sample(rng, _cap("lecture", "where"))},
        "pieges": {"title": _sample(rng, _cap("pieges", "title")), "lead": "",
                   "pieges": [{"title": _sample(rng, agent._PIEGE_TITLE_MAX),
                               "question": _sample(rng, agent._PIEGE_QUESTION_MAX - 2) + " ?"} for _ in range(4)]},
    }


_LINES = """() => { const n = (sel) => [...document.querySelectorAll(sel)].map(e =>
    Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)));
  const bottom = Math.max(0, ...[...document.querySelectorAll('.stage *')].map(e => e.getBoundingClientRect().bottom));
  const trapTitle = [...document.querySelectorAll('.piege .t')].map(t => Math.round(
    (t.getBoundingClientRect().height - t.querySelector('small').getBoundingClientRect().height - 10) /
    (parseFloat(getComputedStyle(t).fontSize) * 1.1)));
  return {subtitle: n('.subtitle'), lead: n('.lead, .ml'), label: n('.rep .l'), head: n('.head, .mh'),
          hl: n('.msg .mt').filter(x => Number.isFinite(x)),
          rowh: n('.row .h span'),
          remark: n('.rep .w span'), one: [...document.querySelectorAll('.read .s, .read .w span, .shared-w span, .own span')].filter(e => !e.closest('.duo-b')).map(e => Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight))), two: [...document.querySelectorAll('.read .t, .piege .t small')].filter(e => !e.closest('.duo-b')).map(e => Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight))),
          duot: n('.tr .c span'), duoq: n('.tr .rq'), aside: n('.am-c .at'), asidek: n('.am-c .ak'), amh: n('.am-lead'),
          fkey: n('.fkey span'),
          hdr: [...document.querySelectorAll('.tb-h span')].map(e => Math.round(e.getBoundingClientRect().height / (parseFloat(getComputedStyle(e).fontSize) * 1.3))),
          qlabel: [...document.querySelectorAll('.q-label')].map(e => Math.round(e.getBoundingClientRect().height / (parseFloat(getComputedStyle(e).fontSize) * 1.1))),
          kick: [...document.querySelectorAll('.kick')].map(e => Math.round(e.getBoundingClientRect().height / (parseFloat(getComputedStyle(e).fontSize) * 1.3))),
          trap: trapTitle, say: n('.row .say'), bottom,
          dateOverflow: [...document.querySelectorAll('.rep .d, .rep .cy, .rep .dd')].map(e => e.scrollWidth - e.clientWidth)}; }"""


def _worst_case_doc(deck: dict):
    return extract(full(), TempsLongPresentation.model_validate(deck))


def test_the_worst_case_deck_breaks_no_hard_rule():
    fields = option_fields(worst_case_deck())
    for name, f in fields.items():
        if name != "writing":
            hard_ = agent.field_errors(name, f, {}, None)[0]
            assert hard_ == [], (name, hard_)


@pytest.mark.parametrize("seed", range(4))
def test_every_field_at_its_cap_fits_in_its_lines_and_on_the_slide(tmp_path, seed):
    renderer.generate_html(_worst_case_doc(worst_case_deck(seed)), tmp_path)
    measured = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for f in sorted(tmp_path.glob("*.html")):
            page.set_content(f.read_text(encoding="utf-8"), wait_until="load")
            measured[f.stem] = page.evaluate(_LINES)
        browser.close()
    _assert_every_slide_fits(measured, ("02_position", "03_episodes", "04_tournants", "05_lecture", "06_pieges"), "05_lecture")


def _assert_every_slide_fits(measured: dict, slides: tuple, lecture_slide: str, frise_two_lines: str = "04_tournants") -> None:
    assert all(n <= 3 for n in measured["01_hook"]["subtitle"]), "the promise is three lines at most"
    for slide in slides:
        m = measured[slide]
        assert all(n <= 3 for n in m["say"]), (slide, "position card", m["say"])
        assert all(n <= (3 if slide == lecture_slide else 2) for n in m["lead"]), (slide, "lead", m["lead"])
        assert all(n <= 5 for n in m["hl"]), (slide, "the position's headline", m["hl"])
        assert all(n <= 2 for n in m["rowh"]), (slide, "a detail row's heading", m["rowh"])
        assert all(n <= 2 for n in m["head"]), (slide, "title", m["head"])
        assert all(n <= 2 for n in m["label"]), (slide, "label", m["label"])
        assert all(n <= (2 if slide == frise_two_lines else 1) for n in m["remark"]), (slide, "remark", m["remark"])
        assert all(n <= 1 for n in m["one"]), (slide, "one-line fields", m["one"])
        assert all(n <= 1 for n in m["kick"]), (slide, "kicker", m["kick"])
        assert all(n <= 1 for n in m["qlabel"]), (slide, "card heading", m["qlabel"])
        assert all(n <= 2 for n in m["two"]), (slide, "two-line fields", m["two"])
        assert all(n <= 1 for n in m["trap"]), (slide, "trap title", m["trap"])
        assert all(n <= 2 for n in m["duot"]), (slide, "an outcome of the table", m["duot"])
        assert all(n <= 2 for n in m["duoq"]), (slide, "a table row's question", m["duoq"])
        assert all(n <= 1 for n in m["asidek"]), (slide, "a sign's name", m["asidek"])
        assert all(n <= 2 for n in m["aside"]), (slide, "a sign's phrase", m["aside"])
        assert all(n <= 2 for n in m["amh"]), (slide, "the paragraph above the signs", m["amh"])
        assert all(n <= 2 for n in m["fkey"]), (slide, "the key under the rows", m["fkey"])
        assert all(n <= 1 for n in m["hdr"]), (slide, "a column header", m["hdr"])
        assert m["bottom"] <= 1255, (slide, m["bottom"])
        assert all(n <= 0 for n in m["dateOverflow"]), (slide, "a date and its tags stay in their column", m["dateOverflow"])


def worst_case_seuil(seed: int = 0) -> dict:
    """The worst-case deck as a `seuil` deck: free card names, a kicker, an author line, a labelled where-line,
    tags on the points, and the slides in the move's own order."""
    rng = random.Random(seed + 100)
    deck = worst_case_deck(seed)
    deck["move"], deck["order"] = "seuil", ["position", "lecture", "episodes", "tournants", "pieges"]
    deck["hook"]["tagline"] = "**" + _sample(rng, 14) + "** " + _sample(rng, _cap("hook", "tagline") - 18)
    lecture = deck["lecture"]
    lecture |= {"kicker": _sample(rng, _cap("lecture", "kicker")), "where": "", "where_label": "", "author": "",
                "lead": _sample(rng, agent._DUO_LEAD_MAX),
                "heads": [_sample(rng, _cap("lecture", "head1")), _sample(rng, _cap("lecture", "head2"))],
                "aside_heading": _sample(rng, _cap("lecture", "aside_heading")),
                "aside_cards": [{"label": _sample(rng, agent._ASIDE_NAME_MAX), "text": _sample(rng, agent._ASIDE_PHRASE_MAX), "icon": "book"}
                                for _ in range(agent._ASIDE_CARDS[1])],
                "readings": [{"kind": "", "label": label, "signature": _sample(rng, agent._DUO_QUESTION_MAX),
                              "indicator": _sample(rng, agent._DUO_CELL_MAX), "other": _sample(rng, agent._DUO_CELL_MAX), "where": ""}
                             for label in ("Proportion", "Continuité", "interpellé")]}
    for step in ("tournants", "episodes"):
        deck[step]["key"] = _sample(rng, agent._KEY_MAX)
        for point in deck[step]["reperes"]:
            point["tags"] = ["cible", "proportion"]
    # the two layouts of a seuil deck, with the widest dates the format allows (a day and a month, then a range)
    deck["episodes"]["layout"], deck["tournants"]["layout"] = "annees", "axe"
    for step in ("tournants", "episodes"):
        for point, date in zip(deck[step]["reperes"], ("28 sept. 1970", "28 sept. 2018–2019", "1986", "28 oct. 2026", "mars 2023")):
            point["date"] = date
    return deck


@pytest.mark.parametrize("seed", range(4))
def test_a_seuil_deck_at_its_caps_fits_in_its_lines_and_on_the_slide(tmp_path, seed):
    paths = renderer.generate_html(_worst_case_doc(worst_case_seuil(seed)), tmp_path)
    assert [p.stem for p in paths] == ["01_hook", "02_position", "03_lecture", "04_episodes", "05_tournants", "06_pieges", "07_cta"]
    measured = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for f in sorted(tmp_path.glob("*.html")):
            page.set_content(f.read_text(encoding="utf-8"), wait_until="load")
            measured[f.stem] = page.evaluate(_LINES)
        browser.close()
    _assert_every_slide_fits(measured, ("02_position", "03_lecture", "04_episodes", "05_tournants", "06_pieges"),
                             "03_lecture", "05_tournants")



_HOOK_LINES = """() => { const r = (sel) => document.querySelector(sel).getBoundingClientRect();
  const lines = (sel) => { const e = document.querySelector(sel); return Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)); };
  return {head: lines('.cover-head'), promise: lines('.subtitle'), promiseBottom: r('.subtitle').bottom, tagBottom: r('.tagline').bottom, tagLines: lines('.tagline'), tagWidth: document.querySelector('.tagline').scrollWidth,
          swipeTop: r('.swipe').top, footTop: r('.sing-foot').top, pillBottom: r('.src-pill').bottom, headBottom: r('.cover-head').bottom}; }"""


@pytest.mark.parametrize("seed", range(4))
def test_the_hook_on_a_photo_fits_at_its_caps(tmp_path, seed):
    """The headline sits on the photo, the promise below it: at their caps they keep their lines and clear the foot."""
    from PIL import Image
    Image.new("RGB", (1080, 1350), "#223344").save(tmp_path / "background.png")
    out = tmp_path / "temps_long" / "html"
    out.mkdir(parents=True)
    rng = random.Random(seed)
    deck = DECK | {"hook": {"title": _sample(rng, _cap("axe", "fait")), "promise": _sample(rng, _cap("hook", "promise") - 2) + " ?",
                            "tagline": "**" + _sample(rng, 14) + "** " + _sample(rng, _cap("hook", "tagline") - 18)}}
    renderer.generate_html(_worst_case_doc(deck), out)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.set_content((out / "01_hook.html").read_text(encoding="utf-8"), wait_until="load")
        m = page.evaluate(_HOOK_LINES)
        browser.close()
    assert m["head"] <= 3, ("headline", m)
    assert m["promise"] <= 3, ("promise", m)
    assert m["tagLines"] <= 2 and m["tagWidth"] <= 900, ("the second paragraph holds on two lines", m)
    assert m["headBottom"] < m["pillBottom"] < m["promiseBottom"] < m["tagBottom"], m
    assert m["tagBottom"] < m["swipeTop"] and m["tagBottom"] < m["footTop"], m


# ── checking the reference points against the web ───────────────────────────

class _Found:
    def __init__(self, confirming=(), contradicting=()):
        self.confirming, self.contradicting = list(confirming), list(contradicting)


class _Source:
    def __init__(self, url, reason=""):
        self.title, self.url, self.stance_reason = "source", url, reason


def test_a_picked_point_with_no_supporting_source_is_flagged_and_the_results_are_kept(tmp_path):
    import asyncio
    from agent import temps_long_verify as tv

    async def search(text):
        if "Loi contre les violences" in text:
            return _Found(confirming=[_Source("https://example.org/2010")])
        if "Mobilisations" in text:
            return _Found(contradicting=[_Source("https://example.org/x", "autre date")])
        return _Found()

    steps = tmp_path / "adapt_steps"
    sf = agent.StepFile(step="tournants", options=[Option(id="a", slot="a", reason="", fields={
        "rep1": "2010 | Loi contre les violences de groupes | Les participants",
        "rep2": "2016 | Mobilisations contre la loi Travail | Lycéens arrêtés",
        "rep3": "2019 | Loi « anticasseurs » | Une personne, avant les faits", "rep4": "", "rep5": ""})],
        picked=["a"])
    agent._save(steps, sf, "stamp")
    warns = asyncio.run(agent.verify_pick(steps, "tournants", search))
    assert len(warns) == 2
    assert any("tournants.rep2" in w and "contradicts" in w and "example.org/x" in w for w in warns)
    assert any("tournants.rep3" in w and "no source found" in w for w in warns)
    assert not any("rep1" in w for w in warns)                                           # a confirmed point is silent
    saved = json.loads((steps / "2_tournants.verification.json").read_text(encoding="utf-8"))
    assert [r["status"] for r in saved] == ["confirmed", "contradicted", "unconfirmed"]
    assert saved[0]["source"]["url"] == "https://example.org/2010"


def test_a_search_that_cannot_run_is_reported_not_raised(tmp_path):
    import asyncio
    from agent import temps_long_verify as tv

    async def search(text):
        raise RuntimeError("no key")

    results = asyncio.run(tv.verify_points({"rep1": "2010 | Une loi | Une remarque"}, search))
    assert results[0]["status"] == "unavailable" and "could not be checked" in tv.warnings("tournants", results)[0]


def test_only_the_timelines_are_checked(tmp_path):
    import asyncio
    steps = tmp_path / "adapt_steps"
    sf = agent.StepFile(step="pieges", options=[Option(id="a", slot="a", reason="", fields={})], picked=["a"])
    agent._save(steps, sf, "stamp")
    assert asyncio.run(agent.verify_pick(steps, "pieges")) == []


# ── the prompts quote the code's caps, never their own numbers ─────────────

_PROMPT_FILES = sorted((Path(agent.__file__).parent / "prompts" / "temps_long_steps").glob("*.md"))


def test_the_prompts_hold_no_hard_coded_cap():
    """A cap is written {{cap:step.field}} and filled from the rules: a number typed in a prompt would drift from the code."""
    import re
    for path in _PROMPT_FILES:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"≤ ?\d", text), (path.name, "a literal « ≤N » — use {{cap:…}}")


def test_every_cap_placeholder_resolves_and_is_filled():
    import re
    caps = agent.prompt_caps()
    for path in _PROMPT_FILES:
        for name in re.findall(r"\{\{cap:([\w.]+)\}\}", path.read_text(encoding="utf-8")):
            assert name in caps, (path.name, name)
    for step in agent.STEPS:
        rendered = agent._prompt(step) if step.option_model is not None else agent._read_prompt(f"{step.n}_{step.name}.md")
        assert "{{cap:" not in rendered


def test_a_prompt_states_the_caps_the_options_are_checked_against():
    tournants = agent._prompt(agent.STEP_BY_NAME["tournants"])
    assert f"{agent._TOURNANTS_LABEL_MAX} caractères au plus" in tournants and f"≤{agent._TOURNANTS_REMARK_MAX} caractères" in tournants
    assert f"≤{agent._CAPS[('hook', 'tagline')][1]} caractères" in agent._prompt(agent.STEP_BY_NAME["hook"])
    assert "84" not in tournants and "≤56 caractères, UNE ligne" not in agent._read_prompt("0_shared.md")


def test_the_message_of_a_step_carries_the_order_the_examples_and_the_shared_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "examples_for", lambda step: "## Retenus\n- un exemple" if step.name == "pieges" else "")
    frags = {"axe": {"axe": {"move": "seuil", "criteres": "Cible, Proportion, Effet"}}}
    msg = agent._message(agent.STEP_BY_NAME["pieges"], full(), frags, ARTICLE, [], [])
    assert "ORDRE D'ÉCRITURE (mouvement seuil)" in msg and "EXEMPLES (décisions passées de l'auteur)" in msg and "un exemple" in msg
    assert "EXEMPLES" not in agent._message(agent.STEP_BY_NAME["hook"], full(), frags, ARTICLE, [], [])


# ── the deck-level check ────────────────────────────────────────────────────

def _seuil_pres() -> TempsLongPresentation:
    deck = copy.deepcopy(DECK)
    deck["move"], deck["order"] = "seuil", ["position", "lecture", "episodes", "tournants", "pieges"]
    deck["lecture"] = {**deck["lecture"], "readings": [
        {"kind": "", "label": "Cible", "signature": "Qui est visé ?", "indicator": "les auteurs", "other": "des milliers", "where": ""},
        {"kind": "", "label": "Effet", "signature": "Sur le droit ?", "indicator": "aucun effet", "other": "dissuade", "where": ""}],
        "heads": ["Maintien de l'ordre", "Répression"], "aside_heading": "Pour Amnesty, sept signes d'un glissement.",
        "aside_cards": [{"label": "Presse", "text": "attaquer la presse", "icon": "book"},
                        {"label": "Peur", "text": "gouverner par la peur", "icon": "flame"}]}
    deck["hook"]["tagline"] = "Les rapporteurs jugent la réponse, Amnesty la trajectoire : à vous de **juger**."
    deck["episodes"]["reperes"][0]["tags"] = ["cible"]
    deck["tournants"]["reperes"][0]["tags"] = ["presse"]
    deck["episodes"]["key"] = deck["tournants"]["key"] = "Les [[étiquettes]] ne sont pas des verdicts."
    return TempsLongPresentation.model_validate(deck)


def test_the_deck_check_lists_what_no_timeline_uses_and_a_tag_that_names_nothing():
    from agent.temps_long_deck_check import check_deck
    report = check_deck(_seuil_pres())
    assert report["temps_long rules"] == []
    assert any("never used as a tag" in a and "Effet" in a and "Peur" in a and "Presse" not in a for a in report["editorial (advisory)"])
    pres = _seuil_pres()
    pres.episodes.reperes[1].tags = ["dissidence"]
    assert any("« dissidence »" in r for r in check_deck(pres)["temps_long rules"])


def test_the_deck_check_wants_the_camps_named_in_the_tagline_and_the_tags_explained():
    from agent.temps_long_deck_check import check_deck
    pres = _seuil_pres()
    pres.hook.tagline = "Deux grilles de lecture à croiser pour en **juger**."
    pres.tournants.key = ""
    advice = check_deck(pres)["editorial (advisory)"]
    assert any("tagline names none of the camps" in a for a in advice)
    assert any("tournants" in a and "nothing explains them" in a for a in advice)
    assert not any("tagline names none" in a for a in check_deck(_seuil_pres())["editorial (advisory)"])


def test_the_deck_check_reports_the_points_the_web_could_not_confirm(tmp_path):
    from agent.temps_long_deck_check import check_deck
    (tmp_path / "2_tournants.verification.json").write_text(json.dumps([
        {"field": "rep1", "claim": "Une loi (2010)", "status": "confirmed", "source": {}, "reason": ""},
        {"field": "rep2", "claim": "Un texte (2019)", "status": "unconfirmed", "source": None, "reason": ""}]), encoding="utf-8")
    advice = check_deck(_seuil_pres(), tmp_path)["editorial (advisory)"]
    assert any("tournants.rep2" in a and "unconfirmed" in a for a in advice) and not any("rep1" in a for a in advice)


def test_the_check_command_covers_temps_long(tmp_path, capsys):
    import main
    folder = tmp_path / "temps_long"
    folder.mkdir()
    doc = TempsLongDocument.model_validate({"analysis": json.loads(full().model_dump_json()),
                                            "presentation": _seuil_pres().model_dump()})
    (folder / "extract.json").write_text(doc.model_dump_json(), encoding="utf-8")
    assert main._check_temps_long(folder / "extract.json") == 0
    assert "editorial (advisory)" in capsys.readouterr().out


def test_a_second_timeline_that_leaves_criteria_untagged_is_flagged_only_when_the_lecture_is_written():
    lecture = {"lecture": {"lecture": {"readings": [{"label": "Cible", "kind": ""}, {"label": "Effet", "kind": ""}],
                                       "aside_cards": [{"label": "Presse"}, {"label": "Peur"}]}}}
    other = {"episodes": {"episodes": {"reperes": [{"date": "2016", "label": "x", "remark": "", "tags": ["cible"]}]}}}
    frags = {"axe": {"axe": {**AXE, "move": "seuil", "criteres": "Cible, Effet", "criteres2": "Presse, Peur"}}, **lecture, **other}
    fields = {**FIELDS["tournants"], "rep1": FIELDS["tournants"]["rep1"].split(" | ")[0] + " | Une loi | Une remarque | presse"}
    flag = [f for f in agent.field_errors("tournants", fields, frags, ARTICLE)[1] if "is tagged" in f]
    assert flag and "Effet" in flag[0] and "Peur" in flag[0] and "Cible" not in flag[0] and "Presse" not in flag[0]
    assert not [f for f in agent.field_errors("tournants", fields, {k: v for k, v in frags.items() if k != "lecture"}, ARTICLE)[1] if "is tagged" in f]
