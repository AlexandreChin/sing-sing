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
from models.temps_long_presentation import TempsLongPresentation
from renderer.instagram_carousel import temps_long as renderer
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/temps_long_deck.json").read_text(encoding="utf-8"))
ARTICLE = ("Le Figaro, 29 Oct 2026. Amnesty évoque sept points d'alerte sur un «glissement vers des pratiques "
           "autoritaires». «la France n'est plus à l'abri de cette tendance mondiale.» L'ampleur des "
           "interpellations «apparaît disproportionnée», et une «surenchère sécuritaire» dans la législation.")


def _frise(f: dict) -> dict:
    reps = [f"{r['date']} | {r['label']} | {r['remark']}" for r in f["reperes"]]
    return {"title": f["title"], "lead": f["lead"], **dict(zip(("rep1", "rep2", "rep3", "rep4", "rep5"), reps + [""] * 5))}


def option_fields(deck: dict) -> dict[str, dict]:
    """Each step's flat option fields, cut from the finished deck."""
    le, pi = deck["lecture"], deck["pieges"]
    traps = [f"{x['title']} | {x['question']}" for x in pi["pieges"]]
    return {
        "tournants": _frise(deck["tournants"]),
        "episodes": _frise(deck["episodes"]),
        "lecture": {"title": le["title"], "lead": le["lead"],
                    **{r["kind"]: f"{r['signature']} | {r['indicator']}" for r in le["readings"]},
                    "question": le["question"]},
        "pieges": {"title": pi["title"], "lead": pi["lead"], **dict(zip(("piege1", "piege2", "piege3"), traps))},
        "hook": dict(deck["hook"]),
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
    assert [r.kind for r in pres.lecture.readings] == ["rupture", "continuite", "cycle"]
    assert pres.episodes.reperes[1].date == "2018–2019" and pres.episodes.reperes[1].remark
    assert len(pres.episodes.reperes) == 5 and len(pres.tournants.reperes) == 4 and len(pres.pieges.pieges) == 3
    assert "mineurs" not in pres.lecture.lead and pres.lecture.lead.startswith("Pour trancher")
    assert pres.tournants.reperes[-1].date == "oct. 2026"


def test_an_older_deck_with_the_old_keys_still_loads():
    old = {k: v for k, v in copy.deepcopy(DECK).items() if k not in ("tournants", "episodes")}
    old["vague_de_fond"], old["palier"] = DECK["tournants"], DECK["episodes"]
    old["palier"]["reperes"][0]["where"] = "Légifrance"
    old["lecture"]["words_line"] = "« Glissement » suppose la continuité."
    old["mots"] = {"title": "x", "lead": "y", "words": []}
    pres = TempsLongPresentation.model_validate(old)
    assert pres.episodes.reperes[0].remark and pres.tournants.title == DECK["tournants"]["title"]


def test_the_steps_run_noyau_first_and_every_step_has_its_prompt():
    assert agent.STEP_NAMES == ["tournants", "episodes", "lecture", "pieges", "hook"]
    for s in agent.STEPS:
        assert Path(f"agent/prompts/temps_long_steps/{s.n}_{s.name}.md").exists(), s.name


def test_the_shared_prompt_lists_every_step():
    shared = Path("agent/prompts/temps_long_steps/0_shared.md").read_text(encoding="utf-8")
    for name in ("Les tournants", "Les épisodes qu'on retient", "La lecture temporelle", "Les pièges du temps",
                 "L'accroche", "La rédaction"):
        assert name in shared, name
    assert "Six étapes" in shared


def test_fragments_rebuild_the_deck():
    frags = {s.name: agent.to_fragment(s, Option(id="a", slot="a", reason="", fields=FIELDS[s.name]))
             for s in agent.STEPS}
    assert TempsLongPresentation.model_validate(agent.assemble(frags)) == TempsLongPresentation.model_validate(DECK)


def test_an_empty_reference_point_is_left_out():
    frag = agent.to_fragment(agent.STEP_BY_NAME["episodes"], Option(id="a", slot="a", reason="", fields=FIELDS["episodes"]))
    assert len(frag["episodes"]["reperes"]) == 5
    assert frag["episodes"]["reperes"][0] == {"date": "2016", "label": "Mobilisations contre la loi Travail",
                                              "remark": "Lycéens et étudiants dans la rue"}


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
    eighty = "Partisans : faire payer les dégâts. Opposants : un frein au droit de manifester."
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
    assert any("figure" in e for e in hard("lecture", rupture="Un bond de 3 millions | Les séries"))
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


def test_a_reading_needs_a_signature_and_an_indicator():
    assert any("lecture.cycle" in e for e in hard("lecture", cycle="Des pics à chaque mobilisation"))
    assert any("continuite is empty" in e for e in hard("lecture", continuite=""))
    assert any("indicator" in e for e in hard("lecture", cycle="Des pics | " + "mot " * 20))


def test_a_line_that_refers_to_nothing_of_the_lead_or_slides_2_and_3_is_flagged_not_blocked():
    off = "Des pics à chaque mobilisation | Les mêmes données, ordonnées dans le temps"
    frags = {**_fragment("tournants"), **_fragment("episodes")}
    assert hard("lecture", cycle=off) == []
    assert any(f.startswith("lecture.cycle: the line refers to nothing") for f in flags("lecture", frags, cycle=off))
    assert not [f for f in flags("lecture", frags) if "refers to nothing" in f]


def test_a_line_can_point_at_an_episode_a_text_or_a_year():
    frags = {**_fragment("tournants"), **_fragment("episodes")}
    for line in ("Le dernier épisode contre les gilets jaunes", "Les textes de 1970 à 2026, dans l'ordre",
                 "Les mois calmes de 2023 à 2025"):
        assert not [f for f in flags("lecture", frags, rupture=f"Un saut net | {line}") if "refers to nothing" in f], line


def test_the_closing_line_is_a_question():
    assert any("must be a question" in e for e in hard("lecture", question="Dites-nous votre lecture."))


def test_a_trap_needs_a_title_and_a_question():
    assert any("piege1 must read" in e for e in hard("pieges", piege1="Le point de départ"))
    assert any("must be a question" in e for e in hard("pieges", piege1="Le point de départ | Changer de date."))
    assert any("piege3 is empty" in e for e in hard("pieges", piege3=""))


def test_the_slide_5_lead_states_a_principle_and_need_not_name_the_measure():
    generic = "Avant de comparer deux manifestations : sont-elles comparables, et comptées de la même façon ?"
    assert hard("pieges", lead=generic) == []
    assert not [f for f in flags("pieges", _fragment("lecture"), lead=generic) if "pieges.lead" in f]


def test_a_trap_that_cites_nothing_of_the_measure_is_flagged_not_blocked():
    off = {**FIELDS["pieges"], "piege1": "Le point de départ | Le résultat change-t-il si l'on commence plus tard ?"}
    hard_, flags_ = agent.field_errors("pieges", off, _fragment("lecture"), ARTICLE)
    assert hard_ == [] and any(f.startswith("pieges.piege1 cites nothing") for f in flags_)


def test_caps_and_accusing_words_are_hard_unless_quoted():
    assert any("hook.title" in e for e in hard("hook", title="x" * 65))
    assert any("accusing" in e for e in hard("pieges", lead="Une lecture trompeuse du temps."))
    assert hard("lecture", lead="L'ONG parle de « manipulation » de l'opinion.") == []


def test_the_hook_promise_is_flagged_not_blocked():
    assert hard("hook", promise="Un regard sur la séquence.") == []
    assert any("Prendre du recul" in f for f in flags("hook", promise="Un regard sur la séquence."))


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


def test_unattended_runs_six_steps_and_rebuilds_the_deck(fake, tmp_path):
    pres = agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE)
    assert fake.labels == [s.name for s in agent.STEPS] and len(fake.labels) == 6
    assert all(e == [] for e in fake.errors.values())
    assert pres.model_dump() == TempsLongPresentation.model_validate(DECK).model_dump()


def test_guided_pauses_at_the_first_step(fake, tmp_path, capsys):
    assert agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE, guided=True) is None
    assert fake.labels == ["tournants"]
    assert agent.pending_step(tmp_path / "adapt_steps") == "tournants"
    assert "[tournants]" in capsys.readouterr().out


def test_stop_after_a_step(fake, tmp_path):
    assert agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE, stop_after="episodes") is None
    assert fake.labels == ["tournants", "episodes"]


def test_a_later_step_receives_the_earlier_picks(fake, tmp_path, monkeypatch):
    messages = []
    monkeypatch.setattr(agent, "_call_with_retry",
                        lambda msg, *a, **kw: messages.append(msg) or fake(msg, *a, **kw))
    agent.adapt(full(), steps_dir=tmp_path / "adapt_steps", article_text=ARTICLE, stop_after="pieges")
    fixed = messages[3].split("CHOIX FIXÉS (ne les réécris pas) :")[1]
    assert "casseurs-payeurs" in fixed and "loi Travail" in fixed and "recours à la force" in fixed


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


def test_six_slides_are_rendered(tmp_path):
    doc = extract(full(), TempsLongPresentation.model_validate(DECK))
    paths = renderer.generate_html(doc, tmp_path / "html")
    assert [p.stem for p in paths] == ["01_hook", "02_episodes", "03_tournants", "04_lecture", "05_pieges", "06_cta"]
    texts = {p.stem: html.unescape(p.read_text(encoding="utf-8")).replace("⁠", "").replace(" ", " ")
             for p in paths}
    assert "Prendre du recul" in texts["01_hook"]
    assert "Les épisodes qu'on retient" in texts["02_episodes"] and "2018–2019" in texts["02_episodes"]
    assert "Des mutilés, un débat sur la force" in texts["02_episodes"]
    assert texts["02_episodes"].count('class="rep"') == 5 and "Légifrance" not in texts["02_episodes"]
    for slide in ("02_episodes", "03_tournants"):          # the bird perches above the first row
        first = texts[slide].index('class="rep"')
        assert texts[slide][first:].startswith('class="rep" data-perch'), slide
        assert texts[slide].split("<body>")[1].count("data-perch") == 1
    assert "Les tournants" in texts["03_tournants"] and "casseurs-payeurs" in texts["03_tournants"]
    assert "Une responsabilité civile : payer les dégâts du groupe, même sans en être l'auteur" in texts["03_tournants"]
    assert "Une sanction pénale, au-delà des auteurs identifiés" in texts["03_tournants"]
    assert "vidéosurveillance algorithmique" in texts["03_tournants"]
    assert texts["03_tournants"].count('class="rep"') == 4
    lecture = texts["04_lecture"]
    assert all(label in lecture for label in ("Rupture", "Continuité", "Cycle")) and lecture.count('class="read"') == 3
    assert "Pour trancher" in lecture and "Mesure suivie" not in lecture
    assert 'class="ask"' not in lecture and "soutiennent-elles" not in lecture and "mineurs" not in lecture
    assert "Le retour à la moyenne" in texts["05_pieges"] and texts["05_pieges"].count('class="card piege"') == 3
    assert "Vous jugez." in texts["06_cta"]
    assert "quelle lecture les séries que vous trouverez soutiennent-elles ?</span>" in texts["06_cta"]


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
    assert '<div class="bg"' in texts["01_hook"] and 'class="shot"' not in texts["01_hook"]
    assert '<div class="book"' in texts["06_cta"]
    assert photo in texts["01_hook"] and photo in texts["06_cta"]          # the same picture, twice


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
    assert '<div class="bg"' not in texts["01_hook"] and '<div class="book"' not in texts["06_cta"]


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
                          "reperes": [{"date": "2018–2019", "label": _sample(rng, agent._LABEL_MAX),
                                       "remark": _sample(rng, agent._TOURNANTS_REMARK_MAX if step == "tournants"
                                                         else agent._REMARK_MAX)}
                                      for _ in range(4 if step == "tournants" else 5)]}
    return DECK | {
        "hook": {"title": _sample(rng, _cap("hook", "title")), "promise": _sample(rng, _cap("hook", "promise"))},
        "tournants": frise("tournants"), "episodes": frise("episodes"),
        "lecture": {"title": _sample(rng, _cap("lecture", "title")), "lead": _sample(rng, _cap("lecture", "lead")),
                    "readings": [{"kind": k, "signature": _sample(rng, agent._SIGNATURE_MAX),
                                  "indicator": _sample(rng, agent._INDICATOR_MAX)}
                                 for k in ("rupture", "continuite", "cycle")],
                    "question": _sample(rng, _cap("lecture", "question") - 2) + " ?"},
        "pieges": {"title": _sample(rng, _cap("pieges", "title")), "lead": _sample(rng, _cap("pieges", "lead")),
                   "pieges": [{"title": _sample(rng, agent._PIEGE_TITLE_MAX),
                               "question": _sample(rng, agent._PIEGE_QUESTION_MAX - 2) + " ?"} for _ in range(3)]},
    }


_LINES = """() => { const n = (sel) => [...document.querySelectorAll(sel)].map(e =>
    Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)));
  const bottom = Math.max(0, ...[...document.querySelectorAll('.stage *')].map(e => e.getBoundingClientRect().bottom));
  const trapTitle = [...document.querySelectorAll('.piege .t')].map(t => Math.round(
    (t.getBoundingClientRect().height - t.querySelector('small').getBoundingClientRect().height - 10) /
    (parseFloat(getComputedStyle(t).fontSize) * 1.1)));
  return {subtitle: n('.subtitle'), lead: n('.lead'), label: n('.rep .l'), head: n('.head'),
          remark: n('.rep .w span'), one: n('.read .w span'), two: n('.read .s, .piege .t small'),
          trap: trapTitle, bottom}; }"""


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
    assert measured["01_hook"]["subtitle"] == [3], "the promise is two lines, then « En juger soi-même. »"
    for slide in ("02_episodes", "03_tournants", "04_lecture", "05_pieges"):
        m = measured[slide]
        assert all(n <= 2 for n in m["lead"]), (slide, "lead", m["lead"])
        assert all(n <= 2 for n in m["head"]), (slide, "title", m["head"])
        assert all(n <= 2 for n in m["label"]), (slide, "label", m["label"])
        assert all(n <= (2 if slide == "03_tournants" else 1) for n in m["remark"]), (slide, "remark", m["remark"])
        assert all(n <= 1 for n in m["one"]), (slide, "one-line fields", m["one"])
        assert all(n <= 2 for n in m["two"]), (slide, "two-line fields", m["two"])
        assert all(n <= 1 for n in m["trap"]), (slide, "trap title", m["trap"])
        assert m["bottom"] <= 1255, (slide, m["bottom"])
