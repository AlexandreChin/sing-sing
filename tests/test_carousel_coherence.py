"""Coherence rules learnt from hand-editing the podcast_1 deck: each case below is
the generated line that a reader could not follow, then the line it became."""
from types import SimpleNamespace as NS

from agent.instagram_carousel_adapt_agent import _coherence_errors
from models.full_analysis import FullAnalysisInput

_GOOD_QUESTION = ("Dans quelle mesure le recours à la **violence** peut-il se justifier quand ces "
                  "**inégalités** persistent malgré les demandes ?")


def _errors(hook="Derrière les **poubelles** brûlées, une école à deux vitesses",
            root_issue="L'école publique promet l'**égalité** ; selon le lycée, elle n'offre pas les "
                       "mêmes moyens, et encore moins les mêmes **chances**.",
            question=_GOOD_QUESTION,
            answer="**Les mêmes jeunes** : un jeune homme perçu noir ou arabe a **20 fois plus** de "
                   "risques d'être contrôlé. Repérez si l'épisode situe les lycées bloqués.",
            presupposes="Ce qu'il tient pour acquis : qu'un **manque ancien** explique l'explosion ; "
                        "que les 180 lycées bloqués partagent les **mêmes** revendications",
            headline="La colère lycéenne vient d'**inégalités anciennes**"):
    pres = NS(hook=NS(sub_topic=hook), cta=NS(engagement_sentence=question))
    d = NS(root_issue=root_issue, reperes_headline="Avant d'écouter : le contexte et trois réflexes",
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
        assert _build_parser().parse_args([cmd, "a.txt", "--duration", "40"]).duration == 40


def _beat_errors(moment, answer, figure=""):
    pres = NS(hook=NS(sub_topic="Une accroche"), cta=NS(engagement_sentence=_GOOD_QUESTION))
    d = NS(root_issue="L'école publique promet l'**égalité**.", reperes_headline="Avant d'écouter",
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
