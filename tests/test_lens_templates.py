from renderer.instagram_carousel._shared import _env, medium_labels

TPL = "article_carousel_optimized_v0"


def _render(name, **ctx):
    # `L` = the medium's reader-facing labels (lire / écouter / regarder), which
    # every template now reads; the article set is the default.
    base = dict(slide_n=4, slide_total=11, progress=36, logo="", phase="avant", L=medium_labels("article"))
    base.update(ctx)
    return _env().get_template(f"{TPL}/{name}").render(**base)


def _text(html):
    """The rendered text as a reader sees it: the French typography filters put
    no-break spaces before « ? : ; » and inside numbers, and escape apostrophes."""
    for a, b in (("\u202f", " "), ("\u00a0", " "), ("&#39;", "'"), ("&nbsp;", " ")):
        html = html.replace(a, b)
    return html


def test_reperes_renders_lenses_as_reflexes():
    html = _render("03_reperes.html", context="Contexte polaire",
                   lens_count_word="Trois", lenses=[
                       {"n": 1, "name": "Chiffres sans base", "question": "Rapporté à quoi ?"},
                       {"n": 2, "name": "Causalité", "question": "Cause ou corrélation ?"},
                   ])
    html = _text(html)
    assert "Trois réflexes" in html
    assert "01" in html and "02" in html           # numbered like the moments that echo them
    assert "Chiffres sans base" in html
    assert "Rapporté à quoi ?" in html
    assert "Causalité" in html


def test_moment_gamifies_quote_challenge_and_reveal():
    # The challenge is slide 3's réflexe question, repeated verbatim so the
    # reader recognises it; `note` is no longer rendered on the slide.
    html = _render("moment.html", index=1, moment="L'accroche",
                   quote="+4400 %", note="cherchez la **base de départ**",
                   lens_question="Ce pourcentage : quelle base de départ ?",
                   answer="il part de **230 voyageurs** en 2004",
                   lens_name="Chiffres sans base", lens_n=1)
    text = _text(html)
    assert "+4400 %" in text                       # quote (clue)
    assert "Ce pourcentage : quelle base de départ ?" in text   # challenge = réflexe question
    assert "cherchez la" not in text               # note no longer shown
    assert "Chiffres sans base" in text            # lens name in the réflexe kicker
    assert 'class="reveal"' in html                # gold-arrow reveal block
    assert "230 voyageurs" in html                 # answer text
    assert "L&#39;accroche" in html                # apostrophe auto-escaped


def test_moment_hides_reveal_when_answer_absent():
    html = _render("moment.html", index=1, moment="m", quote="q",
                   lens_question="Qui l'affirme ?", lens_name="Sources", lens_n=1)
    assert 'class="reveal"' not in html            # no empty reveal block for old extracts


def test_socle_renders_presupposes_then_objection():
    # « Le socle de l'argument » (was 08_vue_ensemble): optimized.py splits the
    # « Ce qu'il tient pour acquis : a ; b » string into one clause per line, then
    # closes the slide with the objection.
    html = _text(_render("08_socle.html", phase="verdict",
                         headline="Un tourisme polaire aux multiples enjeux",
                         recap_items=[
                             {"label": "Ce qu'il tient pour acquis", "icon": "anchor",
                              "clauses": ["que le coût carbone se compte par passager",
                                          "que la faune pâtit des visites"]},
                             {"label": "L'objection la plus solide", "icon": "shield",
                              "clauses": ["Un tourisme encadré crée des ambassadeurs"]},
                         ]))
    assert "Un tourisme polaire aux multiples enjeux" in html
    assert "que le coût carbone se compte par passager" in html
    assert "que la faune pâtit des visites" in html
    assert html.index("Ce qu'il tient pour acquis") < html.index("L'objection la plus solide")


def test_bilan_shows_takeaways_reflexes_and_engagement():
    html = _render("10_bilan.html", phase="verdict",
                   takeaways=["Le +4400 % est fragile", "La part réelle n'est jamais chiffrée"],
                   reflexes=[{"name": "Chiffres sans base", "question": "Rapporté à quoi ?"}],
                   engagement="Dites-nous en DM : quel chiffre choc vous a marqué ?")
    html = _text(html)
    assert "Le +4400 % est fragile" in html
    assert "Chiffres sans base" in html
    assert "La question" in html
    assert "quel chiffre choc vous a marqué ?" in html


def test_reperes_renders_framing_branch_for_optimized():
    html = _render("03_reperes.html", context="Contexte polaire", framing="Un angle militant")
    assert "Un angle militant" in html


def test_prise_de_recul_shows_root_issue_then_question():
    # The objection moved to the socle slide; the prise de recul goes from the
    # deep stake down to the closing question.
    html = _text(_render("08_prise_de_recul.html", phase="verdict",
                         root_issue="L'enjeu est surtout symbolique : une élite qui affiche son indifférence.",
                         question="Dans quelle mesure un **symbole** pèse-t-il plus qu'un bilan ?"))
    assert "Ce qui est laissé de côté" not in html   # angles morts section removed
    assert "L'objection la plus solide" not in html  # moved to the socle slide
    assert "L'enjeu de fond" in html
    assert "une élite qui affiche son indifférence" in html
    assert "La question" in html and "symbole" in html
    assert html.index("L'enjeu de fond") < html.index("La question")


def test_tracker_uses_four_act_labels_but_keeps_phase_keys():
    html = _text(_render("moment.html", phase="analyse", index=1, moment="m", quote="q",
                         lens_question="Qui l'affirme ?", lens_name="L", lens_n=1))
    # three beats, named by the medium's labels (here: article)
    assert "Avant de lire" in html
    assert "Décryptage" in html
    assert "Prise de recul" in html
