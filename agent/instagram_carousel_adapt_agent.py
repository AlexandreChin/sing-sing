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


def _quote_errors(d, article_text: str) -> list[str]:
    """Quotes are verbatim by contract. The model rewords them to meet the word
    cap — « frapper au plus fort de son bombardement aérien de la bande » loses
    « de la bande » — so the loop has to see the article to catch it."""
    article = norm_for_match(article_text)
    return [
        f"display.reading_beats[{i}].quote is not in the article word for word — "
        f"« {b.quote[:60]}… ». Keep the passage and elide its middle with « […] » if it is "
        f"too long; never reword it, and never drop the clause that carries the point"
        for i, b in enumerate(d.reading_beats)
        if b.selected and b.quote.strip() and not quote_is_faithful(b.quote, article)
    ]


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


def _lens_layer_errors(d) -> list[str]:
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
            # 24 words ≈ the three lines the quote block holds. Over that, the
            # model elides the middle rather than picking a shorter, weaker
            # passage: a 15-word cap disqualified 16 of the analysis's own 20
            # key quotes and left fragments that carried no claim.
            n_quote = len(b.quote.split())
            if n_quote > 24:
                errors.append(
                    f"display.reading_beats[{i}].quote is {n_quote} words (max 24) — elide its "
                    f"middle with « […] », keeping the clauses that carry the point"
                )
            # 28, not 22: glossing an unfamiliar tool and naming the mechanism
            # cost words, and a short line the reader cannot use is worse than a
            # long one. A ceiling, not a target.
            n_answer = len(b.answer.split())
            if n_answer > 28:
                errors.append(f"display.reading_beats[{i}].answer is {n_answer} words (max 28)")
            if len(_SENTENCE_END.findall(b.answer.strip())) > 1:
                errors.append(
                    f"display.reading_beats[{i}].answer runs to more than one sentence — "
                    f"state the finding, not the finding plus its interpretation"
                )
        # `role` (what the quote does for the thesis) keeps the reveal from
        # contradicting the passage it annotates — see the prompt's coherence rule.
        # slide 4 shows one réflexe per selected beat; without its own question it
        # falls back to the canonical constant, identical across every article.
        if b.selected and not b.lens_question.strip():
            errors.append(f"display.reading_beats[{i}].lens_question is empty (required for selected beats)")
        # Printed twice — slide 4's list and the beat header — so it has to stay
        # one line in both. The cap was documented and never enforced.
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
    # The argumentative spine. A pool can hold eight candidates, cover every lens
    # and still stop at the demonstration — the article's own conclusion (what it
    # recommends) then never reaches a slide. Only enforced on decks that carry
    # `thesis_step` at all, so decks produced before the field keep validating.
    if any(b.thesis_step for b in beats):
        for i, b in enumerate(beats):
            if b.selected and not b.thesis_step:
                errors.append(f"display.reading_beats[{i}].thesis_step is empty (required for selected beats)")
        steps = {b.thesis_step for b in beats if b.thesis_step}
        missing = [s for s in ("premisse", "preuve", "conclusion") if s not in steps]
        if missing:
            errors.append(
                f"display.reading_beats (candidate pool) covers no {'/'.join(missing)} beat — "
                f"the pool must offer one candidate per step of the article's argument, "
                f"the conclusion included (its last section is where it states what it advocates)"
            )
        if "conclusion" in steps and not any(b.selected and b.thesis_step == "conclusion" for b in beats):
            errors.append(
                "display.reading_beats: the pool has a 'conclusion' candidate but none is selected — "
                "three beats that stop at the demonstration leave out what the article advocates"
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
    return errors


def _validate(data: dict, article_text: str | None = None) -> list[str]:
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
    lede_stems = _stems(paras[0] if paras else "")
    for i, point in enumerate(d.essentiel):
        stems = _stems(point)
        if stems and len(stems & lede_stems) / len(stems) >= 0.6:
            errors.append(
                f"display.essentiel[{i}] restates the lede printed two lines above it "
                f"(« {point[:50]}… ») — the claims develop §1, they do not repeat it"
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
    errors += _tired_opening_errors("hook.sub_topic", pres.hook.sub_topic)
    errors += _tired_opening_errors("cta.engagement_sentence", pres.cta.engagement_sentence)
    errors += _tired_opening_errors("display.selection_headline", d.selection_headline)
    errors.extend(_lens_layer_errors(d))
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
    return (
        f"ARTICLE METADATA :\n{_j(full.article_metadata.model_dump(mode="json"))}\n\n"
        f"{core}"
        f"ANALYSE COMPLÈTE :\n{full.model_dump_json(indent=2)}"
    )


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
    return pres.model_copy(update={"cta": pres.cta.model_copy(update={"post_reading_questions": questions})})
