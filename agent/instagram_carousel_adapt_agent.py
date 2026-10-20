"""Generate the Instagram carousel presentation layer from a completed ArticleFullAnalysis."""
import json
import re
import unicodedata
import sys
from pathlib import Path

from agent._base import _OUT_OF_SCOPE_CLICHES, _call_with_retry, _fold, _j, medium_directive
from agent.lenses import CANONICAL_LENSES
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import (
    InstagramCarouselPresentation,
    PostReadingQuestion,
)

_PROMPT = (Path(__file__).parent / "prompts" / "instagram_carousel.md").read_text(encoding="utf-8")

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# Sentence end: . ! ? followed by a space+capital or end of string (skips "3 %.", "1967 :").
_SENTENCE_END = re.compile(r"[.!?](?=\s+[A-ZÀ-Þ])|[.!?]$")


def _bold_spans(text: str) -> set[str]:
    return {f for f in (_fold(m) for m in _BOLD_RE.findall(text)) if f}


# Words that reach the slides in our own voice and stop a reader cold. Verbatim
# `quote`s are exempt: those are the article's words, not ours.
_JARGON = {
    "préprint": "« prépublication », ou mieux « pas encore relue par des pairs »",
    "preprint": "« prépublication », ou mieux « pas encore relue par des pairs »",
    "peer-review": "« relue par des pairs »",
    "probatoire": "« de preuve » / « les preuves sont faibles »",
    "dataset": "« jeu de données »",
    "benchmark": "« test de référence »",
    "framework": "« cadre »",
}
_JARGON_RE = {w: re.compile(rf"\b{w}\w*\b", re.I) for w in _JARGON}


def _jargon_errors(label: str, text: str) -> list[str]:
    return [
        f"{label} uses « {m.group(0)} » — write {fix} (the reader has not read the article "
        f"and will not look a word up)"
        for word, fix in _JARGON.items()
        if (m := _JARGON_RE[word].search(text or ""))
    ]


# Content-word stems, for comparing two lines of copy. Five letters is enough to
# match inflections (« frappe » / « frappes ») without collapsing distinct words.
_STEM_STOP = {"le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "au", "aux", "en",
              "que", "qui", "ce", "ces", "cet", "cette", "ses", "son", "sa", "leur", "leurs",
              "pour", "par", "sur", "sans", "dans", "plus", "pas", "ne", "est", "sont", "ont",
              "se", "qu", "il", "elle", "on", "aussi", "tout", "tous", "toute", "toutes"}


def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-zà-öø-ÿ]+", text.lower())
            if w not in _STEM_STOP and len(w) > 2}


def norm_for_match(text: str) -> str:
    """Lowercase and unify apostrophes, quotes, dashes and spaces, so a quote can
    be matched against the article without tripping on typography. Shared with
    `tools/check_deck.py`, which runs the same check after the fact."""
    text = unicodedata.normalize("NFC", text)
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u00a0", " "), ("\u202f", " "), ("\u2014", "-"), ("\u2013", "-")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).lower().strip()


# An elision marker: the quote is chosen for relevance, then made to fit by
# cutting its middle out — « xxx […] yyy » — so each retained fragment is checked
# on its own, in order.
_ELISION = re.compile(r"\s*(?:\[…\]|\[\.\.\.\]|…)\s*")


def quote_is_faithful(quote: str, article_normalised: str) -> bool:
    """Every fragment of the quote appears in the article, word for word and in
    order. Elision is allowed; paraphrase is not."""
    cursor = 0
    for fragment in _ELISION.split(quote.strip().strip("«»")):
        fragment = norm_for_match(fragment)
        if not fragment:
            continue
        found = article_normalised.find(fragment, cursor)
        if found == -1:
            return False
        cursor = found + len(fragment)
    return True


_FR_MARKERS = {"le", "la", "les", "des", "est", "une", "dans", "que", "qui", "pour", "pas", "sur"}
_EN_MARKERS = {"the", "and", "of", "is", "that", "to", "in", "was", "for", "with", "are", "have"}


def is_french(text: str) -> bool:
    """Rough language guess from function words — enough to tell a French article
    from an English one, which is all the quote contract needs."""
    words = re.findall(r"[a-zà-ÿ]+", text.lower())
    return sum(w in _FR_MARKERS for w in words) >= sum(w in _EN_MARKERS for w in words)


def verbatim_quote(b) -> str:
    """The text that must appear in the article: the original-language passage
    when the slide shows a translation, else the quote itself."""
    return b.quote_original.strip() or b.quote


def _quote_errors(d, article_text: str) -> list[str]:
    """Quotes are verbatim by contract. The model rewords them to meet the word
    cap — « frapper au plus fort de son bombardement aérien de la bande » loses
    « de la bande » — so the loop has to see the article to catch it. A
    non-French article is quoted in translation, its original kept alongside."""
    article = norm_for_match(article_text)
    errors = []
    if not is_french(article_text):
        errors += [
            f"display.reading_beats[{i}].quote_original is empty — the article is not in French: "
            f"put the passage as written in quote_original, and its faithful French translation in quote"
            for i, b in enumerate(d.reading_beats)
            if b.selected and b.quote.strip() and not b.quote_original.strip()
        ]
    errors += [
        f"display.reading_beats[{i}].{'quote_original' if b.quote_original.strip() else 'quote'} is not "
        f"in the article word for word — « {verbatim_quote(b)[:60]}… ». Keep the passage and elide its "
        f"middle with « […] » if it is too long; never reword it, and never drop the clause that carries the point"
        for i, b in enumerate(d.reading_beats)
        if b.selected and b.quote.strip() and not quote_is_faithful(verbatim_quote(b), article)
    ]
    return errors


# Openings that ossified across decks: a prompt example becomes the template, and
# a feed of carousels starts sounding machine-made. Add one whenever a new tic
# appears — the point is that the next one gets caught here, not in review.
_TIRED_OPENINGS = {
    "faut-il juger": "the prompt's old formula — ask what this article actually puts at stake",
    "derrière les": "two decks in a row opened this way",
    "et si ": "essayist filler",
}


def _tired_opening_errors(label: str, text: str) -> list[str]:
    stripped = re.sub(r"[*\s]+", " ", text or "").strip().lower()
    return [
        f"{label} opens on « {opening} » — {why}; vary the construction from one deck to the next"
        for opening, why in _TIRED_OPENINGS.items()
        if stripped.startswith(opening)
    ]


# Question shapes that ossified across decks. `_TIRED_OPENINGS` only matches the
# START of a line; these tics sit anywhere in the sentence, so they need their own
# check. Banning a shape in prose is not enough — the first family was banned in
# the prompt and the model simply moved to the second. Add a pattern whenever a
# new one appears: the point is that the NEXT tic is caught here, not three decks
# later in review.
_TIRED_QUESTIONS = {
    r"faut-il juger\b": "« faut-il juger X sur A ou sur B ? » — six decks used it",
    r"\bque\s+faudrait-il\b": "« que faudrait-il constater/observer/voir pour… » — three decks in a row",
    r"\bne\s+(?:tient|tiennent)\s+plus\b": "« …pour dire que X ne tient plus » closes the same formula",
}
_TIRED_QUESTIONS_RE = {p: re.compile(p, re.I) for p in _TIRED_QUESTIONS}


def _tired_question_errors(label: str, text: str) -> list[str]:
    """The closing question must LEAVE the subject (see the adapt prompt): a shape
    that fits any article is the symptom of one that stayed inside this one."""
    stripped = re.sub(r"[*\s]+", " ", text or "").strip()
    return [
        f"{label} reuses a burnt-out question shape — {why}. The closing question ELARGIT : "
        f"it starts from the most far-reaching présupposé and leaves the subject, so it still "
        f"makes sense with the article hidden. Ask what THIS case makes one wonder about "
        f"everything else, and let the form follow from that"
        for pat, why in _TIRED_QUESTIONS.items()
        if _TIRED_QUESTIONS_RE[pat].search(stripped)
    ]


# Slide 1 clamps the hook to four lines at 85px: a 67-character hook rendered
# whole, an 89-character one lost its last word to an ellipsis.
_HOOK_MAX_CHARS = 68
# A moment's answer: four lines at 38px across the text column.
_ANSWER_MAX_CHARS = 150

# Where to look (slide 8, under the closing question): 2–3 short source names.
_LOOK_MAX_CHARS = 60

# Slide 1's promise under the hook: « Comprendre … » on one line at 46px; the
# template adds « En juger soi-même. » on the next.
_SUBTITLE_MAX_CHARS = 38
_SUBTITLE_SHAPE = re.compile(r"^Comprendre [^.?!]+\.$")
# Slide titles (moments, socle) hold two lines at 60px: « Devant le lycée, les contrôles
# du quartier se rejouent » (54) fits, a three-line title pushed slide 5 out of frame.
_TITLE_MAX_CHARS = 54
# A moment with a figure stacks title, figure, caption, quote, réflexe and
# answer: a 25-word answer overflowed it even under a two-line title, 17 fit.
_FIGURE_ANSWER_MAX_WORDS = 18

# A moment's answer hands the reader a tool, it does not report the source's
# failings. These leads turn the reveal into a verdict (« **Constaté** : aucun
# chiffre… », « **Rien ne tranche** »), and the deck reads as a grading.
_VERDICT_LEAD = re.compile(
    r"^(?:constat[ée]e?s?|rien\b|aucun|aucune|jamais|personne|nulle part|à rien|non\b|faux\b|pas d)",
    re.I)

# Every displayed line reads with what it says and what earlier slides said,
# never with what comes after it. Two shapes break that, whatever the field:
# a line that opens on a pronoun with nothing to point at (« Elle repose sur un
# pari », « qu'ils parlent d'une voix »), and a headless « ce que / ce qui »
# that only the quote below fills in (« Ce que l'État exige, les lycéens le
# réclament »). Impersonal « il » (il faut, il y a…) is not a reference. The
# hook is exempt: a teaser's unknown is its point (« Ce que les chiffres ne
# comptent pas »).
_IMPERSONAL = r"(?!\s+(?:y\b|faut|s['’]agit|suffit|semble|reste|manque))"
_OPENING_PRONOUN = re.compile(rf"^(?:qu['’])?(?:il{_IMPERSONAL}|elle|ils|elles|cela|ça|ceci)\b", re.I)
_FORWARD_REFERENCE = re.compile(r"^(?:ce|celui|celle|ceux|celles)\s+(?:que|qu['’]|qui|dont)\b", re.I)
# …unless the line names it itself: after a colon, or in a cleft (« Ce qui
# rapporte, c'est le nombre de retraités »).
_NAMED_AFTER = re.compile(r":|,\s*(?:c['’]est|ce sont|c['’]était)\b", re.I)

# The closing question is open: the reader weighs a degree or a condition, not
# a yes/no. An open interrogative must head the question or one of its clauses
# (« Quand…, qu'a-t-on appris… ? » and « Pour qui… ? » are open; « Peut-on condamner
# ceux qui… ? » is not).
_OPEN_QUESTION = re.compile(
    r"(?:^|[,:;—]\s*)(?:(?:pour|par|avec|chez|selon|sur|contre|envers|à|de)\s+)?(?:dans quelle mesure|à quelles? conditions?|jusqu['’]où|comment|pourquoi|"
    r"en quoi|à quoi|de quoi|sur quoi|combien|que\b|qu['’]|quel(?:le)?s?\b|lequel|laquelle|"
    r"lesquel(?:le)?s|qui\b|où\b)",
    re.I)

# Words that settle the question for the reader: they tilt it before it is asked.
_LOADED_QUESTION = re.compile(
    r"\b(?:légitim\w*|illégitim\w*|injust\w*|ignoré\w*|aucune autre (?:voie|issue|solution)|"
    r"seul moyen|condamn\w*)",
    re.I)


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("**", "")).strip()


def _displayed_lines(pres, d) -> list[tuple[str, str]]:
    """(label, text) for every line we write that reaches a slide after the hook.
    Présupposés are split into their own lines, as the slide prints them."""
    lines = [(f"display.reperes_facts[{i}].text", f.text) for i, f in enumerate(d.reperes_facts)]
    lines += [(f"display.essentiel[{i}]", p) for i, p in enumerate(d.essentiel)]
    for i, b in enumerate(d.reading_beats):
        if b.selected:
            lines += [(f"display.reading_beats[{i}].{f}", getattr(b, f)) for f in ("moment", "lens_question", "answer")]
    if d.global_analysis:
        lines.append(("display.global_analysis.headline", d.global_analysis.headline))
        for i, point in enumerate(d.global_analysis.core_recap):
            body = point.split(":", 1)[1] if ":" in point else point
            lines += [(f"display.global_analysis.core_recap[{i}] presupposé {j + 1}", c.strip())
                      for j, c in enumerate(c for c in body.split(";") if c.strip())]
    if d.steel_man:
        lines.append(("display.steel_man.argument", d.steel_man.argument))
    lines += [("display.root_issue", d.root_issue), ("cta.engagement_sentence", pres.cta.engagement_sentence)]
    return [(label, _plain(text)) for label, text in lines if text and text.strip()]


def _standalone_errors(pres, d) -> list[str]:
    errors = []
    for label, text in _displayed_lines(pres, d):
        if _OPENING_PRONOUN.match(text):
            errors.append(
                f"{label} opens on a pronoun (« {text[:30]}… ») — a reader who skipped the source "
                f"cannot tell what it points at; name it"
            )
        if _FORWARD_REFERENCE.match(text) and not _NAMED_AFTER.search(text):
            errors.append(
                f"{label} opens on « {text.split()[0]} {text.split()[1]}… » without saying what — "
                f"only the quote or a later slide would tell; name the thing (« Ce que l'État exige, "
                f"les lycéens le réclament » → « L'État prône la non-violence, les lycéens la réclament »)"
            )
    return errors


def _coherence_errors(pres, d, light: bool = False) -> list[str]:
    """The rules a hand-edited deck taught us: each one is a reader who could not
    follow, or a slide that judged where it should have equipped."""
    errors: list[str] = []
    hook = _plain(pres.hook.sub_topic)
    if len(hook) > _HOOK_MAX_CHARS:
        errors.append(
            f"hook.sub_topic is {len(hook)} characters (max {_HOOK_MAX_CHARS}) — slide 1 cuts it "
            f"at four lines and the reader loses its last words"
        )
    # Slide 1's promise, first half: « Comprendre … », picking up what the hook
    # opens. One line; the template adds « En juger soi-même. »
    subtitle = _plain(pres.hook.subtitle)
    if not subtitle:
        errors.append("hook.subtitle is empty — slide 1 states the deck's promise under the hook")
    else:
        if len(subtitle) > _SUBTITLE_MAX_CHARS:
            errors.append(
                f"hook.subtitle is {len(subtitle)} characters (max {_SUBTITLE_MAX_CHARS}) — it holds "
                f"one line under the title"
            )
        if not _SUBTITLE_SHAPE.match(subtitle):
            errors.append(
                "hook.subtitle must be one sentence « Comprendre …. » picking up what the hook "
                "opens (« Comprendre d'où elle vient. ») — the slide adds « En juger soi-même. »"
            )
    if norm_for_match(_plain(d.root_issue)).startswith(("l'enjeu de fond", "enjeu de fond")):
        errors.append(
            "display.root_issue opens with « L'enjeu de fond » — the slide already prints that "
            "label; start with the stake itself"
        )
    for i, b in enumerate(d.reading_beats):
        if not b.selected:
            continue
        moment = _plain(b.moment)
        if len(moment) > _TITLE_MAX_CHARS:
            errors.append(
                f"display.reading_beats[{i}].moment is {len(moment)} characters (max "
                f"{_TITLE_MAX_CHARS}) — the title holds two lines; a third pushes the slide out "
                f"of frame"
            )
        answer = _plain(b.answer)
        visual = (b.figure or "").strip() or getattr(b, "pictogram", None)
        if visual and len(answer.split()) > _FIGURE_ANSWER_MAX_WORDS:
            errors.append(
                f"display.reading_beats[{i}].answer is {len(answer.split())} words with a figure "
                f"or pictogram on the slide (max {_FIGURE_ANSWER_MAX_WORDS}) — the visual takes "
                f"the room of the second sentence, and carries the number"
            )
        if _VERDICT_LEAD.match(answer):
            errors.append(
                f"display.reading_beats[{i}].answer opens on a verdict (« {answer[:30]}… ») — "
                f"lead with the tool or the fact that answers the réflexe, then what to look for; "
                f"the moment equips the reader, it does not grade the source"
            )
    if d.global_analysis:
        headline = _plain(d.global_analysis.headline)
        if len(headline) > _TITLE_MAX_CHARS:
            errors.append(
                f"display.global_analysis.headline is {len(headline)} characters (max "
                f"{_TITLE_MAX_CHARS}) — the socle title holds two lines"
            )
    errors += _standalone_errors(pres, d)
    question = _plain(pres.cta.engagement_sentence)
    if question:
        if not _OPEN_QUESTION.search(question):
            errors.append(
                "cta.engagement_sentence is a yes/no question — make it open (a degree, a "
                "condition, a limit: « Dans quelle mesure… », « À quelles conditions… », "
                "« Jusqu'où… »), varying the form from one deck to the next"
            )
        if (m := _LOADED_QUESTION.search(question)):
            errors.append(
                f"cta.engagement_sentence uses « {m.group(0)} » — a word that answers the question "
                f"before the reader does; ask it neutrally"
            )
        # slide 8 draws the question as following from the enjeu: the word they
        # share (« promet » / « promesse ») is the gold one on both sides
        q_roots = {w[:5] for span in _BOLD_RE.findall(pres.cta.engagement_sentence)
                   for w in re.findall(r"[a-zà-ÿ]{4,}", span.lower())}
        e_roots = {w[:5] for span in _BOLD_RE.findall(d.root_issue or "")
                   for w in re.findall(r"[a-zà-ÿ]{4,}", span.lower())}
        if d.root_issue and not q_roots & e_roots:
            errors.append(
                "cta.engagement_sentence shares no **gilded** word with display.root_issue — slide 8 "
                "ties the two cards by the word they share: gild it on both sides (« la société "
                "**promet** … » / « … tient sa **promesse** ? »)"
            )
        looks = [w for w in getattr(pres.cta, "where_to_look", []) if w.strip()]
        lo, hi = (1, 2) if light else (2, 3)
        if looks and not lo <= len(looks) <= hi:
            errors.append(f"cta.where_to_look has {len(looks)} item(s) — {lo}–{hi} sources, or none")
        for j, w in enumerate(looks):
            if len(w) > _LOOK_MAX_CHARS:
                errors.append(f"cta.where_to_look[{j}] is {len(w)} characters (max {_LOOK_MAX_CHARS}) — one line on slide 8")
        n_bold = len(_BOLD_RE.findall(pres.cta.engagement_sentence))
        if not 1 <= n_bold <= 2:
            errors.append(
                f"cta.engagement_sentence has {n_bold} **bold** span(s) — gild 1 or 2: the terms "
                f"the reader weighs against each other"
            )
    return errors


def _gilded_errors(pres, d) -> list[str]:
    """Every slide carries at least one gilded phrase. The prompt asks for bold in
    each sentence, but nothing checked it, so a generation can arrive with whole
    slides in flat white — slides 7 and 8 did. Checked per slide, not per field:
    which sentence carries the gold is an editorial choice, having none is not."""
    paras = [x for x in d.why_selected.split("\n") if x.strip()]
    ga = d.global_analysis
    slides = {
        "slide 1 (hook)": [pres.hook.sub_topic],
        "slide 2 (en bref)": paras[:1] + list(d.essentiel),
        "slide socle": ([ga.headline] + list(ga.core_recap) if ga else []) + [pres.cta.engagement_sentence],
        "slide prise de recul": [d.root_issue] + ([d.steel_man.argument, d.steel_man.alternative]
                                                  if d.steel_man else []),
    }
    for i, b in enumerate(d.reading_beats):
        if b.selected:
            slides[f"beat {i}"] = [b.answer]
    return [
        f"{slide} has no **gilded** phrase — every slide carries one, the gold is what the eye "
        f"lands on"
        for slide, texts in slides.items()
        if texts and not any(_BOLD_RE.search(t or "") for t in texts)
    ]


def _axis_errors(pres, d) -> list[str]:
    """Slide 8 — the enjeu de fond and « La question » — is where the deck leads.
    Every selected moment says what it gives toward it (`axis_link`), and the hook,
    each slide-2 bullet and the slide-7 thesis share a key word with it, so no
    slide drifts onto a side subject. Only enforced on decks carrying `axis_link`
    at all, so older decks keep validating."""
    beats = d.reading_beats
    if not any(b.axis_link.strip() for b in beats):
        return []
    errors = [
        f"display.reading_beats[{i}].axis_link is empty (required for selected beats) — say what "
        f"this moment gives toward slide 8, or deselect it"
        for i, b in enumerate(beats) if b.selected and not b.axis_link.strip()
    ]
    axis = _stems(_plain(d.root_issue)) | _stems(_plain(pres.cta.engagement_sentence))
    fields = [("hook.sub_topic", pres.hook.sub_topic)]
    fields += [(f"display.essentiel[{i}]", e) for i, e in enumerate(d.essentiel)]
    if d.global_analysis:
        fields.append(("display.global_analysis.headline", d.global_analysis.headline))
    for label, text in fields:
        if text.strip() and not _stems(_plain(text)) & axis:
            errors.append(
                f"{label} shares no key word with slide 8 (root_issue / cta.engagement_sentence) — "
                f"« {_plain(text)[:60]} » reads as a side subject; tie it to the enjeu or the question"
            )
    # The moment slide shows its réflexe question and its answer: that is what the
    # reader carries away, so the link to slide 8 must be visible there, not only
    # in the unrendered axis_link.
    for i, b in enumerate(beats):
        if b.selected and not _stems(_plain(f"{b.lens_question} {b.answer}")) & axis:
            errors.append(
                f"display.reading_beats[{i}] — neither lens_question nor answer shares a key word with "
                f"slide 8: the slide teaches a reading habit but hands the reader nothing toward the "
                f"enjeu or the question; ask and answer in slide 8's terms"
            )
    return errors


# What makes a clue findable: a named place to look. A proper noun past the first
# word (« l'Assemblée », « The Nation », « Acrimed »), or a kind of document.
_CLUE_WORDS = re.compile(
    r"rapport|bilan|compte rendu|chiffres|données|statistique|ministère|préfecture|syndica|"
    r"tribunal|décision|loi|décret|code|enquête|étude|archives|plateforme|registre|budget|"
    r"observatoire|défenseur|conseil|insee|dares|depp|cour des comptes", re.I)


def _names_a_source(text: str) -> bool:
    plain = _plain(text)
    if _CLUE_WORDS.search(plain):
        return True
    words = re.findall(r"[A-ZÀ-Ý][\w'’-]+", plain)
    first = re.match(r"\W*([\w'’-]+)", plain)
    return any(w != (first.group(1) if first else "") for w in words)


def _clue_errors(pres, d) -> list[str]:
    """A moment's answer and slide 8's sources tell the reader where to check. « Comparez
    les arrestations d'un lycée à l'autre » says what to do but not where: each answer
    names a place to look — an institution, a document, a figure, a person quoted.
    Only enforced on decks carrying `axis_link`, so older decks keep validating."""
    if not any(b.axis_link.strip() for b in d.reading_beats):
        return []
    errors = [
        f"display.reading_beats[{i}].answer names no place to look — « {_plain(b.answer)[:60]} »: "
        f"say where the reader checks (an institution, a document, a figure, a person quoted), "
        f"not only what to do"
        for i, b in enumerate(d.reading_beats)
        if b.selected and b.answer.strip() and not _names_a_source(b.answer)
    ]
    errors += [
        f"cta.where_to_look[{j}] is not a findable source — « {w} »: name it (who publishes it, which document)"
        for j, w in enumerate(pres.cta.where_to_look) if w.strip() and not _names_a_source(w)
    ]
    return errors


# The light format's caps, measured on article_14's slides at the light type scale
# (slide 7 sets pillars at 38px and the objection at 44px, so they take full-length lines):
# characters, not words — eight long words still wrap to three lines at 54px.
_LIGHT_CAPS = {"hook": 40, "essentiel": 48, "moment": 45, "quote": 12, "answer": 110,
               "presupposé": 10, "objection": 100, "root_issue": 70, "question": 60,
               "headline": 45, "lens_questions": 120, "source": 48,
               "claim": 30, "detail": 45}


def _light_errors(pres, d) -> list[str]:
    c, errors = _LIGHT_CAPS, []
    def words(t): return len(_plain(t).split())
    if len(_plain(pres.hook.sub_topic)) > c["hook"]:
        errors.append(f"light: hook.sub_topic is over {c['hook']} characters")
    def chars(t): return len(_plain(t))
    # slide 2 shows « claim : detail » as a short claim over a grey detail line:
    # each part holds one line
    for i, e in enumerate(d.essentiel):
        claim, sep, detail = _plain(e).partition(" : ")
        if not sep and chars(e) > c["essentiel"]:
            errors.append(f"light: display.essentiel[{i}] is {chars(e)} characters (max {c['essentiel']}) — "
                          f"or write it « claim : detail »")
        elif sep and (len(claim) > c["claim"] or len(detail) > c["detail"]):
            errors.append(f"light: display.essentiel[{i}] — claim ≤{c['claim']} and detail ≤{c['detail']} characters "
                          f"(one line each), got {len(claim)} / {len(detail)}")
    picked = [b for b in d.reading_beats if b.selected]
    total_q = sum(chars(b.lens_question) for b in picked)
    if total_q > c["lens_questions"]:
        errors.append(f"light: the réflexe questions total {total_q} characters (max {c['lens_questions']}) — "
                      f"slide 3 holds one two-line question, not three")
    for i, b in enumerate(d.reading_beats):
        if not b.selected:
            continue
        if len(_plain(b.moment)) > c["moment"]:
            errors.append(f"light: display.reading_beats[{i}].moment is over {c['moment']} characters")
        if words(b.quote) > c["quote"]:
            errors.append(f"light: display.reading_beats[{i}].quote is {words(b.quote)} words (max {c['quote']})")
        if len(_plain(b.answer)) > c["answer"]:
            errors.append(f"light: display.reading_beats[{i}].answer is over {c['answer']} characters")
    if d.global_analysis and chars(d.global_analysis.headline) > c["headline"]:
        errors.append(f"light: display.global_analysis.headline is over {c['headline']} characters")
    if d.global_analysis:
        for rec in d.global_analysis.core_recap:
            body = _plain(rec).split(":", 1)[-1]
            errors += [f"light: présupposé « {p.strip()} » is {len(p.split())} words (max {c['presupposé']})"
                       for p in body.split(";") if len(p.split()) > c["presupposé"]]
    if d.steel_man and chars(d.steel_man.argument) > c["objection"]:
        errors.append(f"light: display.steel_man.argument is {chars(d.steel_man.argument)} characters (max {c['objection']})")
    if chars(d.root_issue) > c["root_issue"]:
        errors.append(f"light: display.root_issue is {chars(d.root_issue)} characters (max {c['root_issue']})")
    errors += [f"light: cta.where_to_look[{j}] is {chars(w)} characters (max {c['source']}) — one line"
               for j, w in enumerate(pres.cta.where_to_look) if chars(w) > c["source"]]
    if chars(pres.cta.engagement_sentence) > c["question"]:
        errors.append(f"light: cta.engagement_sentence is {chars(pres.cta.engagement_sentence)} characters (max {c['question']})")
    return errors


def _lens_layer_errors(d, light: bool = False) -> list[str]:
    """Validate the 4-act lens layer (Task: lens-arc). Additive — leaves the
    legacy checks in _validate untouched so the short format keeps working."""
    errors: list[str] = []
    # reading_beats is a candidate POOL; the renderer shows the `selected` ones and
    # derives the lenses from them, so we validate the pool, not an authored lens list.
    # The thesis frame is the guard-rail every other field is checked against:
    # without it written down, off-frame remarks read as legitimate findings.
    tf = d.thesis_frame
    if tf is None or not tf.main_claim.strip():
        errors.append("display.thesis_frame.main_claim is empty (the frame every field is checked against)")
    elif not (2 <= len(tf.out_of_scope) <= 3):
        errors.append(f"display.thesis_frame.out_of_scope must have 2–3 items, got {len(tf.out_of_scope)}")
    if tf is not None:
        for i, item in enumerate(tf.out_of_scope):
            if _fold(item) in _OUT_OF_SCOPE_CLICHES:
                errors.append(
                    f"display.thesis_frame.out_of_scope[{i}] repeats a generic example "
                    f"({item!r}) instead of a debate THIS text leaves aside — derive it from the article"
                )
    beats = d.reading_beats
    if len(beats) < 3:
        errors.append(f"display.reading_beats (candidate pool) should have ≥3 items, got {len(beats)}")
    for i, b in enumerate(beats):
        if b.lens_ref not in CANONICAL_LENSES:
            errors.append(f"display.reading_beats[{i}].lens_ref '{b.lens_ref}' is not a canonical lens id")
        if not b.quote.strip():
            errors.append(f"display.reading_beats[{i}].quote is empty")
        # selected beats render as gamified slides: they need both the challenge
        # (`note`) and the reveal (`answer`).
        if b.selected and not b.answer.strip():
            errors.append(f"display.reading_beats[{i}].answer is empty (required for selected beats)")
        # A moment slide stacks title + quote + réflexe + answer. Caps keep the
        # four blocks readable; the second sentence of an answer almost always
        # restates the réflexe printed two lines above it.
        if b.selected:
            # 18 words ≈ three lines of the quote block. Over that, the model
            # elides the middle rather than picking a shorter, weaker passage (a
            # 15-word cap disqualified most key quotes); 24 words read as four
            # lines, which a hand-edited deck trimmed back to the passage's core.
            n_quote = len(b.quote.split())
            if n_quote > 18:
                errors.append(
                    f"display.reading_beats[{i}].quote is {n_quote} words (max 18) — elide its "
                    f"middle with « […] », keeping the clauses that carry the point"
                )
            # Four lines on the slide (38px over the text column) — about 150
            # characters, bold markers aside: the fact or tool that answers the
            # réflexe, then what to look or listen for. A 31-word answer passed
            # the old 32-word cap and ran to six lines.
            n_chars = len(_plain(b.answer))
            if n_chars > _ANSWER_MAX_CHARS:
                errors.append(
                    f"display.reading_beats[{i}].answer is {n_chars} characters (max "
                    f"{_ANSWER_MAX_CHARS}) — it holds four lines on the slide"
                )
            if len(_SENTENCE_END.findall(b.answer.strip())) > 2:
                errors.append(
                    f"display.reading_beats[{i}].answer runs to more than two sentences — "
                    f"the answer, then what to look for; nothing more"
                )
        # `role` (what the quote does for the thesis) keeps the reveal from
        # contradicting the passage it annotates — see the prompt's coherence rule.
        # slide 4 shows one réflexe per selected beat; without its own question it
        # falls back to the canonical constant, identical across every article.
        if b.selected and not b.lens_question.strip():
            errors.append(f"display.reading_beats[{i}].lens_question is empty (required for selected beats)")
        # Printed twice — slide 4's list and the beat header — so it has to stay
        # one line in both. The cap was documented and never enforced.
        # slide 3 sets each question on one line (28px, beside the lens icon);
        # the light deck lets it wrap to two, so it gets more room
        if b.selected and len(b.lens_question.strip()) > (70 if light else 54):
            errors.append(
                f"display.reading_beats[{i}].lens_question is {len(b.lens_question.strip())} characters "
                f"(max {70 if light else 54}) — slide 3 holds it on {'two lines' if light else 'one line'}"
            )
        if b.selected and len(b.lens_question.split()) > 12:
            errors.append(
                f"display.reading_beats[{i}].lens_question is {len(b.lens_question.split())} "
                f"words (max 12)"
            )
        if b.selected and not b.role.strip():
            errors.append(f"display.reading_beats[{i}].role is empty (required for selected beats)")
    n_selected = sum(1 for b in beats if b.selected)
    if not (2 <= n_selected <= 3):
        errors.append(f"display.reading_beats must have 2–3 selected, got {n_selected}")
    # At most one selected beat may annotate the article's staging rather than a
    # piece of its demonstration (prompt rule: ≥2 beats on `fond.main_claim`).
    staging = sum(1 for b in beats if b.selected and b.role.strip() == "mise en scène")
    if staging > 1:
        errors.append(f"display.reading_beats: at most 1 selected beat may have role 'mise en scène', got {staging}")
    # The spine. Slide 2 states it in three bullets — premise 1, premise 2,
    # conclusion — and the three selected beats illustrate them one for one, in
    # the same order. Derived separately on each slide the two drift apart, and
    # the deck reads as parts that never build on each other. Only enforced on
    # decks carrying `spine_ref` at all, so older decks keep validating.
    if any(b.spine_ref for b in beats):
        for i, b in enumerate(beats):
            if b.selected and not b.spine_ref:
                errors.append(
                    f"display.reading_beats[{i}].spine_ref is 0 (required for selected beats) — "
                    f"name the `essentiel` bullet it illustrates: 1/2 the premises, 3 the conclusion"
                )
        refs = [b.spine_ref for b in beats if b.selected and b.spine_ref]
        for n, what in ((1, "first premise"), (2, "second premise"), (3, "conclusion")):
            if refs.count(n) != 1:
                errors.append(
                    f"display.reading_beats: {refs.count(n)} selected beat(s) carry spine_ref={n} "
                    f"(the {what} — bullet {n} of slide 2), expected exactly 1. One moment per "
                    f"bullet, in order, so the three walk the argument instead of crowding one step"
                )
        if not any(b.spine_ref == 3 for b in beats):
            errors.append(
                "display.reading_beats (candidate pool) offers no spine_ref=3 candidate — the pool "
                "must reach what the article advocates (its last section), not stop at the demonstration"
            )
        roles = {b.role.strip() for b in beats if b.selected and b.role.strip()}
        if len(roles) < 2:
            errors.append(
                f"display.reading_beats: the selected beats cover {len(roles)} distinct role(s) "
                f"(min 2) — three quotes doing the same thing give the reader the same move three times"
            )
    # Slide 3 stacks the three lens questions one under the other, where two
    # that open the same way read as one line printed twice. Only visible
    # once rendered, so it is caught here instead.
    openings: dict[str, int] = {}
    for i, b in enumerate(beats):
        if not (b.selected and b.lens_question.strip()):
            continue
        key = " ".join(_fold(b.lens_question).split()[:3])
        if key in openings:
            errors.append(
                f"display.reading_beats[{i}].lens_question opens like beats[{openings[key]}]'s "
                f"(« {key}… ») — the three are stacked on slide 3, so each needs its own opening"
            )
        else:
            openings[key] = i
    ga = d.global_analysis
    if ga is None:
        errors.append("display.global_analysis is missing")
    else:
        if not ga.headline.strip():
            errors.append("display.global_analysis.headline is empty")
        if not (1 <= len(ga.core_recap) <= 3):
            errors.append(f"display.global_analysis.core_recap must have 1–3 items, got {len(ga.core_recap)}")
        # Slide 8 stands on the beats the reader was actually shown: one presupposé
        # per selected beat, `;`-separated, on a single slide-sized line.
        for i, point in enumerate(ga.core_recap):
            body = point.split(":", 1)[1] if ":" in point else point
            n_presupposes = len([c for c in body.split(";") if c.strip()])
            if n_presupposes != n_selected:
                errors.append(
                    f"display.global_analysis.core_recap[{i}] holds {n_presupposes} presupposé(s) "
                    f"for {n_selected} selected beats — one per selected beat, in slide order, "
                    f"so each rests on a finding the reader has seen"
                )
            # Each presupposé is its own line on the slide, so the budget is per
            # clause. The old 16-word cap on the whole run is what compressed the
            # third one into "les critiques valent Harrison" — a reference the deck
            # never introduces, and nobody can decode.
            for j, clause in enumerate([c.strip() for c in body.split(";") if c.strip()]):
                n_words = len(clause.split())
                if n_words > 10:
                    errors.append(
                        f"display.global_analysis.core_recap[{i}] presupposé {j + 1} is "
                        f"{n_words} words (max 10)"
                    )
    if not d.root_issue.strip():
        errors.append("display.root_issue is empty")
    if not d.essentiel_summary.strip():
        errors.append("display.essentiel_summary is empty")
    if len(d.essentiel) != 3 or any(not p.strip() for p in d.essentiel):
        errors.append(f"display.essentiel must have exactly 3 non-empty points, got {len(d.essentiel)}")
    # Slide 2 renders these as 01/02/03 with the bold span gilded, so a bullet
    # without one renders flat, and a term gilded twice hierarchises nothing.
    seen_bold: set[str] = set()
    for i, point in enumerate(d.essentiel):
        n_words = len(point.split())
        if n_words > 13:
            errors.append(f"display.essentiel[{i}] is {n_words} words (max 13)")
        spans = _bold_spans(point)
        if not spans:
            errors.append(
                f"display.essentiel[{i}] has no **bold** span — slide 2 gilds one key "
                f"expression per bullet"
            )
        if spans & seen_bold:
            errors.append(
                f"display.essentiel[{i}] repeats a bold term already gilded in an earlier "
                f"bullet ({', '.join(sorted(spans & seen_bold))})"
            )
        seen_bold |= spans
    # Plain French on every field we write ourselves (quotes stay verbatim).
    errors += _jargon_errors("display.why_selected", d.why_selected)
    errors += _jargon_errors("display.selection_headline", d.selection_headline)
    for i, point in enumerate(d.essentiel):
        errors += _jargon_errors(f"display.essentiel[{i}]", point)
    for i, b in enumerate(d.reading_beats):
        if not b.selected:
            continue
        for field in ("moment", "lens_question", "note", "answer"):
            errors += _jargon_errors(f"display.reading_beats[{i}].{field}", getattr(b, field, ""))
    if d.global_analysis:
        for i, point in enumerate(d.global_analysis.core_recap):
            errors += _jargon_errors(f"display.global_analysis.core_recap[{i}]", point)
    errors += _jargon_errors("display.root_issue", d.root_issue)

    n_takeaways = sum(1 for t in d.key_takeaways if t.selected)
    if not (2 <= n_takeaways <= 3):
        errors.append(f"display.key_takeaways must have 2–3 selected, got {n_takeaways}")
    sm = d.steel_man
    if sm is None:
        errors.append("display.steel_man is missing")
    else:
        if not sm.argument.strip():
            errors.append("display.steel_man.argument is empty")
        if not sm.alternative.strip():
            errors.append("display.steel_man.alternative is empty")
        # slide 7 points the objection at a pillar: it must be one the slide shows
        if not 0 <= sm.targets <= n_selected:
            errors.append(
                f"display.steel_man.targets is {sm.targets} — the présupposé (1–{n_selected}) the "
                f"objection weakens, or 0"
            )
    # A pictogram draws one real ratio as people: at most one per deck, never on a
    # beat that already has the figure slot, counts that fit a row, a sourced caption.
    pictos = [(i, b) for i, b in enumerate(beats) if b.selected and b.pictogram]
    if len(pictos) > 1:
        errors.append(f"display.reading_beats: {len(pictos)} pictograms (max 1 per deck)")
    for i, b in pictos:
        pg = b.pictogram
        if (b.figure or "").strip():
            errors.append(f"display.reading_beats[{i}] has both a figure and a pictogram — keep one")
        for field in ("reference_count", "subject_count"):
            if not 1 <= getattr(pg, field) <= 30:
                errors.append(f"display.reading_beats[{i}].pictogram.{field} is {getattr(pg, field)} (1–30)")
        if not pg.caption.strip() or not pg.reference_label.strip() or not pg.subject_label.strip():
            errors.append(f"display.reading_beats[{i}].pictogram needs both labels and a caption naming the source")
    return errors


def _validate(data: dict, article_text: str | None = None, light: bool = False) -> list[str]:
    """Every rule the deck must meet. `light` checks the light format: the same
    deck, condensed — tighter caps, one context line, no lede on slide 2."""
    pres = InstagramCarouselPresentation.model_validate(data)
    errors = []
    # The caption is the post's own copy, not a slide: no hashtags, ever.
    if "#" in pres.caption:
        tags = " ".join(re.findall(r"#\S+", pres.caption)) or "#"
        errors.append(f"caption contains hashtag(s) ({tags}) — the caption carries none, ever")
    if not pres.cta.title.strip():
        errors.append("cta.title is empty")
    n_cta = len(pres.cta.post_reading_questions)
    if not (1 <= n_cta <= 4):
        errors.append(f"cta.post_reading_questions: expected 1–4, got {n_cta}")
    if not any(q.type == "blind_spot" for q in pres.cta.post_reading_questions):
        errors.append("cta.post_reading_questions: at least one must be type 'blind_spot'")
    n_go = len(pres.go_further)
    if n_go != 3:
        errors.append(f"go_further: expected exactly 3 items, got {n_go}")
    for i, item in enumerate(pres.go_further):
        if item.cta_question_index is not None and not (0 <= item.cta_question_index < n_cta):
            errors.append(
                f"go_further[{i}].cta_question_index={item.cta_question_index} out of range (0–{n_cta - 1})"
            )
    d = pres.display
    for field in ("payoff", "framing", "why_selected", "selection_headline", "ethics"):
        if not getattr(d, field).strip():
            errors.append(f"display.{field} is empty")
    # Slides 2 and 3 are one swipe apart: slide 2 summarises the article, slide 3
    # says why it is worth reading. When §1 of `why_selected` re-highlights a term
    # already gilded on slide 2, the two slides read as the same sentence twice.
    # Word caps: slide 3 is read in three seconds in a feed, and the 64px title
    # wraps to three lines past ~7 words.
    n_title = len(d.selection_headline.split())
    if n_title > 7:
        errors.append(f"display.selection_headline is {n_title} words (max 7)")
    paras = [p.strip() for p in d.why_selected.split("\n") if p.strip()]
    if len(paras) != 2:
        errors.append(f"display.why_selected must be exactly 2 paragraphs, got {len(paras)}")
    caps = (25, 20)
    for i, (para, cap) in enumerate(zip(paras, caps), 1):
        n = len(para.split())
        if n > cap:
            errors.append(f"display.why_selected §{i} is {n} words (max {cap})")
    n_total = len(d.why_selected.split())
    if n_total > 45:
        errors.append(f"display.why_selected is {n_total} words in total (max 45)")
    # §1 and the `essentiel` claims now share slide 2, so they must cohere rather
    # than stay apart: the old non-overlap rule enforced the opposite. What is
    # forbidden now is a claim that merely repeats a figure from the lede.
    # The light deck shows no lede: §1 stays in the data (the newsletter uses it).
    lede_stems = set() if light else _stems(paras[0] if paras else "")
    for i, point in enumerate(d.essentiel):
        stems = _stems(point)
        if stems and len(stems & lede_stems) / len(stems) >= 0.6:
            errors.append(
                f"display.essentiel[{i}] restates the lede printed two lines above it "
                f"(« {point[:50]}… ») — the claims develop §1, they do not repeat it"
            )
    # Slide 3 « À savoir »: 2–3 labelled facts chosen from the analysis's context,
    # so the reader can weigh the source on each side — read two swipes after
    # slide 2's lede, so none says the news again.
    facts = d.reperes_facts
    lo, hi = (1, 1) if light else (2, 3)
    if not lo <= len(facts) <= hi:
        errors.append(f"display.reperes_facts must have {lo}–{hi} items, got {len(facts)}")
    for i, f in enumerate(facts):
        text = _plain(f.text)
        if not f.label.strip() or len(f.label.split()) > 2:
            errors.append(f"display.reperes_facts[{i}].label must be 1–2 words (« L'école », « La police »)")
        if len(text.split()) > 14:
            errors.append(f"display.reperes_facts[{i}].text is {len(text.split())} words (max 14)")
        stems = _stems(text)
        if stems and len(stems & lede_stems) / len(stems) >= 0.5:
            errors.append(
                f"display.reperes_facts[{i}] restates slide 2's lede (« {text[:50]}… ») — choose what "
                f"came before, a reference point or who speaks, not the news again"
            )
    if not (1 <= len(d.blind_spots) <= 2):
        errors.append(f"display.blind_spots must have 1–2 items, got {len(d.blind_spots)}")
    if not (1 <= len(d.balance) <= 2):
        errors.append(f"display.balance must have 1–2 items, got {len(d.balance)}")
    if len(d.pre_reading) != 2:
        errors.append(f"display.pre_reading must have exactly 2 items, got {len(d.pre_reading)}")
    if len(d.distill_points) != 3:
        errors.append(f"display.distill_points must have exactly 3 items, got {len(d.distill_points)}")
    if len(d.after_reading) != 3:
        errors.append(f"display.after_reading must have exactly 3 items, got {len(d.after_reading)}")
    if not (1 <= len(d.watch_out) <= 2):
        errors.append(f"display.watch_out must have 1–2 items, got {len(d.watch_out)}")
    for i, item in enumerate(d.watch_out):
        if not item.label.strip():
            errors.append(f"display.watch_out[{i}].label is empty")
        if not item.text.strip():
            errors.append(f"display.watch_out[{i}].text is empty")
    if not (1 <= len(d.strengths) <= 2):
        errors.append(f"display.strengths must have 1–2 items, got {len(d.strengths)}")
    for i, item in enumerate(d.strengths):
        if not item.label.strip():
            errors.append(f"display.strengths[{i}].label is empty")
        if not item.text.strip():
            errors.append(f"display.strengths[{i}].text is empty")
    errors += _gilded_errors(pres, d)
    errors += _coherence_errors(pres, d, light)
    errors += _tired_opening_errors("hook.sub_topic", pres.hook.sub_topic)
    errors += _tired_opening_errors("cta.engagement_sentence", pres.cta.engagement_sentence)
    errors += _tired_question_errors("cta.engagement_sentence", pres.cta.engagement_sentence)
    errors += _tired_opening_errors("display.selection_headline", d.selection_headline)
    errors.extend(_lens_layer_errors(d, light))
    errors += _axis_errors(pres, d)
    errors += _clue_errors(pres, d)
    if light:
        errors += _light_errors(pres, d)
    if article_text:
        errors.extend(_quote_errors(d, article_text))
    return errors


def _full_analysis_context(full: ArticleFullAnalysis) -> str:
    core = ""
    if full.core_elements and full.core_elements.elements:
        lines = "\n".join(
            f"  - [{e.kind}, centralité {e.centrality}] {e.statement}"
            for e in full.core_elements.elements
        )
        core = (
            "ÉLÉMENTS CENTRAUX (la présentation doit les COUVRIR — ne pas se limiter "
            "à l'angle du titre) :\n" + lines + "\n\n"
        )
    angle = ""
    if full.article_metadata.extra_instructions:
        angle = (
            "CONSIGNES ÉDITORIALES (prioritaires — elles fixent l'angle de la "
            "présentation, l'enjeu de fond et la question de la slide 8 ; elles "
            "l'emportent sur les choix de l'analyse) :\n"
            f"{full.article_metadata.extra_instructions.strip()}\n\n"
        )
    return (
        f"{angle}"
        f"ARTICLE METADATA :\n{_j(full.article_metadata.model_dump(mode="json"))}\n\n"
        f"{core}"
        f"ANALYSE COMPLÈTE :\n{full.model_dump_json(indent=2)}"
    )


def caption_with_sources(caption: str, go_further) -> str:
    """Append the « Pour chercher par vous-même » block to the post caption, from
    the go_further resources that carry a link — slide 8 names the sources, the
    caption gives where to find them. No link, no block; never added twice."""
    linked = [g for g in go_further if (g.url or "").startswith(("http://", "https://"))]
    if not linked or "Pour chercher par vous-même" in caption:
        return caption
    lines = [f"— {g.source}, « {g.title} » : {g.url}" for g in linked]
    return caption.rstrip() + "\n\n📚 Pour chercher par vous-même :\n" + "\n".join(lines)


def adapt(
    full: ArticleFullAnalysis,
    no_api: bool = False,
    article_text: str | None = None,
) -> InstagramCarouselPresentation:
    user_msg = f"{_full_analysis_context(full)}\n\n---\n\n{_PROMPT}"
    if (directive := medium_directive(full.article_metadata.medium)):
        user_msg += f"\n\n---\n\n{directive}"
    print("Adaptation carousel…", file=sys.stderr, flush=True)
    data = _call_with_retry(
        user_msg,
        InstagramCarouselPresentation.model_json_schema(),
        validator=lambda data: _validate(data, article_text),
        no_api=no_api,
    )
    pres = InstagramCarouselPresentation.model_validate(data)
    # Assign IDs to CTA questions
    questions = [
        q.model_copy(update={"id": f"q_{i}"})
        for i, q in enumerate(pres.cta.post_reading_questions)
    ]
    return pres.model_copy(update={"cta": pres.cta.model_copy(update={"post_reading_questions": questions}),
                                   "caption": caption_with_sources(pres.caption, pres.go_further)})
