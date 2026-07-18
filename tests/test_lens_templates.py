from renderer.instagram_carousel._shared import _env

TPL = "article_carousel_optimized_v0"


def _render(name, **ctx):
    base = dict(slide_n=4, slide_total=11, progress=36, logo="", phase="avant")
    base.update(ctx)
    return _env().get_template(f"{TPL}/{name}").render(**base)


def test_reperes_renders_lenses_as_reflexes():
    html = _render("03_reperes.html", context="Contexte polaire",
                   lens_count_word="Trois", lenses=[
                       {"name": "Chiffres sans base", "question": "Rapporté à quoi ?"},
                       {"name": "Causalité", "question": "Cause ou corrélation ?"},
                   ])
    assert "Trois réflexes" in html
    assert "Chiffres sans base" in html
    assert "Rapporté à quoi ?" in html
    assert "Causalité" in html


def test_moment_shows_quote_note_and_single_line_reflexe():
    html = _render("moment.html", index=1, moment="L'accroche",
                   quote="+4400 %", note="pas de base de référence",
                   lens_name="Chiffres sans base")
    assert "+4400 %" in html
    assert "pas de base de référence" in html
    assert "Réflexe" in html                  # single-line reflexe tag
    assert "Chiffres sans base" in html       # lens name on one line
    assert "L&#39;accroche" in html           # apostrophe auto-escaped
    assert 'class="fc-row"' not in html       # no fact-check pill element when factcheck absent


def test_moment_shows_factcheck_pill_when_present():
    html = _render("moment.html", index=1, moment="Le bilan carbone",
                   quote="15 à 25 tonnes de CO2", note="fourchette non sourcée",
                   lens_name="Sources", factcheck={"label": "Plutôt solide", "cls": "likely_true"})
    assert "fc-chip likely_true" in html
    assert "Plutôt solide" in html


def test_vue_ensemble_renders_core_recap():
    html = _render("08_vue_ensemble.html", phase="verdict",
                   headline="Un tourisme polaire aux multiples enjeux",
                   core_recap=["Un fort coût carbone par passager",
                               "Une concurrence directe avec la faune"])
    assert "Un fort coût carbone par passager" in html
    assert "Une concurrence directe avec la faune" in html


def test_bilan_shows_takeaways_reflexes_and_engagement():
    html = _render("10_bilan.html", phase="verdict",
                   takeaways=["Le +4400 % est fragile", "La part réelle n'est jamais chiffrée"],
                   reflexes=[{"name": "Chiffres sans base", "question": "Rapporté à quoi ?"}],
                   engagement="Dites-nous en DM : quel chiffre choc vous a marqué ?")
    assert "Le +4400 % est fragile" in html
    assert "Chiffres sans base" in html
    assert "La question" in html
    assert "quel chiffre choc vous a marqué ?" in html


def test_reperes_renders_framing_branch_for_optimized():
    html = _render("03_reperes.html", context="Contexte polaire", framing="Un angle militant")
    assert "Un angle militant" in html


def test_reperes_still_renders_clues_branch_for_short():
    html = _render("03_reperes.html", context="Contexte polaire", clues=["Surveille les chiffres", "Note le cadrage"])
    assert "Surveille les chiffres" in html


def test_reperes_omits_deux_reflexes_heading_when_no_clues():
    html = _render("03_reperes.html", context="Contexte polaire", framing="Un angle militant")
    assert "Deux réflexes" not in html


def test_prise_de_recul_shows_steelman_then_root_issue():
    html = _render("08_prise_de_recul.html", phase="verdict",
                   steel_man={"argument": "Un tourisme encadré crée des ambassadeurs",
                              "alternative": "le bilan net pourrait s'inverser"},
                   root_issue="L'enjeu est surtout symbolique : une élite qui affiche son indifférence.")
    assert "Ce qui est laissé de côté" not in html   # angles morts section removed
    assert "L'objection la plus solide" in html
    assert "Un tourisme encadré crée des ambassadeurs" in html
    assert "le bilan net pourrait s&#39;inverser" not in html   # consequence line removed
    assert "L'enjeu de fond" in html
    assert "une élite qui affiche son indifférence" in html
    # order: objection → enjeu de fond
    assert html.index("L'objection la plus solide") < html.index("L'enjeu de fond")


def test_tracker_uses_four_act_labels_but_keeps_phase_keys():
    html = _render("moment.html", phase="analyse", index=1, moment="m", quote="q",
                   note="n", lens_name="L")
    assert "Pendant la lecture" in html
    assert "Après la lecture" in html
    assert "Avant de lire" in html
