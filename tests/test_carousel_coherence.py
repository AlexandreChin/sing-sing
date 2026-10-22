"""Coherence rules learnt from hand-editing the podcast_1 deck: each case below is
the generated line that a reader could not follow, then the line it became."""
from types import SimpleNamespace as NS

from agent.instagram_carousel_adapt_agent import _coherence_errors
from models.full_analysis import FullAnalysisInput

_GOOD_QUESTION = ("Dans quelle mesure le recours à la **violence** peut-il se justifier quand ces "
                  "**inégalités** persistent malgré les demandes ?")


def _errors(hook="Derrière les **poubelles** brûlées, une école à deux vitesses",
            root_issue="L'école publique promet l'**égalité** ; selon le lycée, les moyens varient et "
                       "les **inégalités** demeurent.",
            question=_GOOD_QUESTION,
            answer="**Les mêmes jeunes** : un jeune homme perçu noir ou arabe a **20 fois plus** de "
                   "risques d'être contrôlé. Repérez si l'épisode situe les lycées bloqués.",
            presupposes="Ce qu'il tient pour acquis : qu'un **manque ancien** explique l'explosion ; "
                        "que les 180 lycées bloqués partagent les **mêmes** revendications",
            headline="La colère lycéenne vient d'**inégalités anciennes**",
            subtitle="Comprendre d'où elle vient."):
    pres = NS(hook=NS(sub_topic=hook, subtitle=subtitle), cta=NS(engagement_sentence=question))
    d = NS(root_issue=root_issue, reperes_facts=[], reperes_context="",
           essentiel=[], steel_man=None,
           reading_beats=[NS(selected=True, moment="Un titre", lens_question="Une question ?",
                             answer=answer, figure="")],
           global_analysis=NS(headline=headline, core_recap=[presupposes]))
    return _coherence_errors(pres, d)


def test_hand_edited_deck_is_clean():
    assert _errors() == []


def test_hook_too_long_for_four_lines():
    errs = _errors(hook="Des profs, des locaux dignes, une vraie égalité des chances : ce que cachent "
                        "les **poubelles** brûlées")
    assert any("hook.sub_topic" in e and "characters" in e for e in errs)


def test_root_issue_repeating_its_label():
    errs = _errors(root_issue="L’enjeu de fond : une **égalité** promise par l'école publique.")
    assert any("root_issue" in e for e in errs)


def test_answer_opening_on_a_verdict():
    for verdict in ("**Constaté** : aucun chiffre de postes vacants n'est donné.",
                    "**Rien ne tranche** : les lycées touchés ne sont pas situés.",
                    "**Aucun** lycéen ne prend la parole."):
        assert any("verdict" in e for e in _errors(answer=verdict)), verdict


def test_presupposé_with_a_bare_pronoun():
    errs = _errors(presupposes="Ce qu'il tient pour acquis : qu'un manque ancien explique "
                               "l'explosion ; qu'ils parlent d'une voix")
    assert any("pronoun" in e for e in errs)


def test_yes_no_closing_question():
    errs = _errors(question="Expliquer une **colère** par ses causes, est-ce déjà parler à la place "
                            "de ceux qui la portent ?")
    assert any("yes/no" in e for e in errs)


def test_open_question_after_a_clause_passes():
    errs = _errors(question="Si seules les **poubelles** qui brûlent font parler des lycées, "
                            "qu'a-t-on appris à ceux qui réclamaient des profs ?")
    assert not any("yes/no" in e for e in errs)
    # an interrogative after a preposition is open too
    assert not any("yes/no" in e for e in _errors(
        question="Pour **qui** l'école tient-elle encore sa promesse d'**avenir** ?"))


def test_loaded_word_in_closing_question():
    errs = _errors(question="Dans quelle mesure la **violence** devient-elle légitime quand les "
                            "demandes restent sans réponse ?")
    assert any("légitime" in e for e in errs)


def test_closing_question_bold_count():
    assert any("bold" in e for e in _errors(question=_GOOD_QUESTION.replace("**", "")))
    many = "Dans quelle **mesure** le **recours** à la **violence** peut-il se justifier ?"
    assert any("bold" in e for e in _errors(question=many))


def test_duration_overrides_the_word_count_estimate():
    assert FullAnalysisInput(body="x", duration_minutes=40).duration_minutes == 40
    assert FullAnalysisInput(body="x").duration_minutes is None


def test_duration_flag_on_analyze_and_produce():
    from main import _build_parser
    for cmd in ("analyze", "produce"):
        args = _build_parser().parse_args([cmd, "a.txt", "--duration", "40", "--title", "Un titre"])
        assert args.duration == 40 and args.title == "Un titre"


def _beat_errors(moment, answer, figure=""):
    pres = NS(hook=NS(sub_topic="Une accroche", subtitle="Comprendre qui la paie."),
              cta=NS(engagement_sentence=_GOOD_QUESTION))
    d = NS(root_issue="L'école publique promet l'égalité ; les **inégalités** demeurent.", reperes_facts=[], reperes_context="",
           essentiel=[], steel_man=None,
           reading_beats=[NS(selected=True, moment=moment, lens_question="Une question ?",
                             answer=answer, figure=figure)],
           global_analysis=None)
    return _coherence_errors(pres, d)


def test_moment_title_holds_two_lines():
    assert _beat_errors("Devant le lycée, les contrôles du quartier se rejouent", "**Un fait**.") == []
    errs = _beat_errors("Des garçons contrôlés au faciès devant chez eux, sans délit et sans recours",
                        "**Un fait**.")
    assert any("moment" in e and "characters" in e for e in errs)


def test_figure_moment_has_a_shorter_answer():
    long = ("**Le Défenseur des droits**, autorité indépendante, a mesuré ce risque en 2017. En 2016, "
            "la Cour de cassation a condamné l'État pour ces contrôles discriminatoires.")
    assert any("figure" in e for e in _beat_errors("Un titre", long, figure="×20"))
    assert not any("figure" in e for e in _beat_errors("Un titre", long))


def test_socle_title_holds_two_lines():
    errs = _errors(headline="Une colère lycéenne née d'**inégalités anciennes**, scolaires et policières")
    assert any("headline" in e for e in errs)


def test_forward_reference_in_any_line():
    errs = _beat_errors("Ce que l'État exige, les lycéens le réclament", "**Un fait**.")
    assert any("without saying what" in e for e in errs)
    # naming the thing, or a colon that names it, passes
    assert _beat_errors("L'État prône la non-violence, les lycéens la réclament", "**Un fait**.") == []
    assert not any("without saying what" in e
                   for e in _beat_errors("Ce qui fait monter les prix : le loyer", "**Un fait**."))
    assert not any("without saying what" in e
                   for e in _beat_errors("Ce qui rapporte, c'est le nombre de retraités", "**Un fait**."))
    # not only titles: an answer or an enjeu fails the same way
    errs = _errors(root_issue="Ce que les critiques mesurent, l'auteur le juge **incomplet**.")
    assert any("root_issue" in e and "without saying what" in e for e in errs)


def test_opening_pronoun_in_any_line():
    errs = _beat_errors("Un titre", "Elle repose sur un **pari** que rien ne vérifie.")
    assert any("opens on a pronoun" in e for e in errs)
    # impersonal « il » is not a reference
    assert not any("pronoun" in e for e in _beat_errors("Un titre", "Il faut **chercher** la date du sondage."))


def test_subtitle_shape_and_length():
    assert any("hook.subtitle is empty" in e for e in _errors(subtitle=""))
    assert any("one sentence" in e for e in _errors(subtitle="Tout comprendre sur la colère."))
    assert any("one sentence" in e for e in _errors(subtitle="Comprendre d'où elle vient. En juger."))
    long = "Comprendre d'où vient la colère des lycéens d'Île-de-France."
    assert any("characters" in e and "subtitle" in e for e in _errors(subtitle=long))


def test_reperes_facts_are_chosen_not_the_news_again():
    import json
    from pathlib import Path
    from agent.instagram_carousel_adapt_agent import _validate
    data = json.loads(Path("samples/podcasts/podcast_1/instagram_carousel_optimized/adapt.json")
                      .read_text(encoding="utf-8"))
    good = data["display"]["reperes_facts"]

    def errs(facts):
        data["display"]["reperes_facts"] = facts
        return [e for e in _validate(data) if "reperes_facts" in e]

    assert errs(good) == []
    assert any("2–3 items" in e for e in errs(good[:1]))
    news = {"label": "Le mouvement", "text": "Un mouvement de blocages de lycées touche près de 180 établissements."}
    assert any("restates slide 2" in e for e in errs(good[:2] + [news]))
    long = {"label": "L'école", "text": " ".join(["mot"] * 15) + "."}
    assert any("max 14" in e for e in errs(good[:2] + [long]))
    assert any("1–2 words" in e for e in errs(good[:2] + [{"label": "Le contexte de l'école", "text": "Un fait."}]))


def test_question_shares_a_gilded_word_with_the_enjeu():
    errs = _errors(root_issue="La société **promet** l'avenir par l'école ; la jeunesse n'y croit plus.",
                   question="Quels signes montreraient que l'école tient sa **promesse** ?")
    assert not any("shares no" in e for e in errs)
    errs = _errors(root_issue="La société **promet** l'avenir par l'école.",
                   question="Quels **signes** montreraient que l'école tient sa promesse ?")
    assert any("shares no" in e for e in errs)


def test_where_to_look_is_two_or_three_short_sources():
    import json
    from pathlib import Path
    from agent.instagram_carousel_adapt_agent import _validate
    data = json.loads(Path("samples/podcasts/podcast_1/instagram_carousel_optimized/adapt.json")
                      .read_text(encoding="utf-8"))

    def errs(looks):
        data["cta"]["where_to_look"] = looks
        return [e for e in _validate(data) if "where_to_look" in e]

    assert errs([]) == []                                       # optional
    assert errs(["Le Cnesco sur l'école et les inégalités (2016)",
                 "France Stratégie sur la promesse scolaire (2018)"]) == []
    # each source bears on the question or the enjeu, not only on a moment's figures
    assert any("shares no key word" in e for e in errs(["Le Cnesco (2016)", "France Stratégie (2018)"]))
    assert any("2–3 sources" in e for e in errs(["Une seule source"]))
    assert any("max 60" in e for e in errs(["x" * 61, "Une autre source"]))


def test_caption_lists_the_linked_sources_once():
    from types import SimpleNamespace as NS
    from agent.instagram_carousel_adapt_agent import caption_with_sources
    gf = [NS(source="Cnesco", title="Inégalités", url="https://cnesco.fr/x"),
          NS(source="Un livre", title="Sans lien", url=None)]
    out = caption_with_sources("Légende.", gf)
    assert "📚 Pour chercher par vous-même :" in out and "— Cnesco, « Inégalités » : https://cnesco.fr/x" in out
    assert "Sans lien" not in out                                # no URL, not listed
    assert caption_with_sources(out, gf) == out                  # never twice
    assert caption_with_sources("Légende.", gf[1:]) == "Légende."  # no link, no block


def test_root_issue_holds_three_lines():
    errs = _errors(root_issue="Selon le lycée où il est inscrit, un élève n'a ni les mêmes **moyens** ni les mêmes "
                              "profs ; mineurs, sans droit de vote, les lycéens mobilisés n'ont trouvé que la rue "
                              "pour **inégalités**.")
    assert any("display.root_issue is" in e and "three lines" in e for e in errs)
