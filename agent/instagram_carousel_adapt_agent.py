"""Generate the Instagram carousel presentation layer from a completed ArticleFullAnalysis."""
import json
import sys
from pathlib import Path

from agent._base import _call_with_retry, _j
from agent.lenses import CANONICAL_LENSES
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import (
    InstagramCarouselPresentation,
    PostReadingQuestion,
)

_PROMPT = (Path(__file__).parent / "prompts" / "instagram_carousel.md").read_text(encoding="utf-8")


def _lens_layer_errors(d) -> list[str]:
    """Validate the 4-act lens layer (Task: lens-arc). Additive — leaves the
    legacy checks in _validate untouched so the short format keeps working."""
    errors: list[str] = []
    # reading_beats is a candidate POOL; the renderer shows the `selected` ones and
    # derives the lenses from them, so we validate the pool, not an authored lens list.
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
    n_selected = sum(1 for b in beats if b.selected)
    if not (2 <= n_selected <= 3):
        errors.append(f"display.reading_beats must have 2–3 selected, got {n_selected}")
    ga = d.global_analysis
    if ga is None:
        errors.append("display.global_analysis is missing")
    else:
        if not ga.headline.strip():
            errors.append("display.global_analysis.headline is empty")
        if not (2 <= len(ga.core_recap) <= 3):
            errors.append(f"display.global_analysis.core_recap must have 2–3 items, got {len(ga.core_recap)}")
    if not d.root_issue.strip():
        errors.append("display.root_issue is empty")
    if not d.essentiel_summary.strip():
        errors.append("display.essentiel_summary is empty")
    if len(d.essentiel) != 3 or any(not p.strip() for p in d.essentiel):
        errors.append(f"display.essentiel must have exactly 3 non-empty points, got {len(d.essentiel)}")
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


def _validate(data: dict) -> list[str]:
    pres = InstagramCarouselPresentation.model_validate(data)
    errors = []
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
    errors.extend(_lens_layer_errors(d))
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
        f"ARTICLE METADATA :\n{_j(full.article_metadata.model_dump())}\n\n"
        f"{core}"
        f"ANALYSE COMPLÈTE :\n{full.model_dump_json(indent=2)}"
    )


def adapt(
    full: ArticleFullAnalysis,
    no_api: bool = False,
) -> InstagramCarouselPresentation:
    user_msg = f"{_full_analysis_context(full)}\n\n---\n\n{_PROMPT}"
    print("Adaptation carousel…", file=sys.stderr, flush=True)
    data = _call_with_retry(
        user_msg,
        InstagramCarouselPresentation.model_json_schema(),
        validator=_validate,
        no_api=no_api,
    )
    pres = InstagramCarouselPresentation.model_validate(data)
    # Assign IDs to CTA questions
    questions = [
        q.model_copy(update={"id": f"q_{i}"})
        for i, q in enumerate(pres.cta.post_reading_questions)
    ]
    return pres.model_copy(update={"cta": pres.cta.model_copy(update={"post_reading_questions": questions})})
