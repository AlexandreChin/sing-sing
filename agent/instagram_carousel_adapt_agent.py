"""Generate the Instagram carousel presentation layer from a completed ArticleFullAnalysis."""
import json
import sys
from pathlib import Path

from agent._base import _call_with_retry, _j
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import (
    InstagramCarouselPresentation,
    PostReadingQuestion,
)

_PROMPT = (Path(__file__).parent / "prompts" / "instagram_carousel.md").read_text(encoding="utf-8")


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
    if len(d.key_takeaways) != 2:
        errors.append(f"display.key_takeaways must have exactly 2 items, got {len(d.key_takeaways)}")
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
    return errors


def _full_analysis_context(full: ArticleFullAnalysis) -> str:
    verdict = ""
    if full.review:
        v = full.review.verdict
        verdict = (
            "VERDICT (fil conducteur — toute la présentation doit y mener) :\n"
            f"  qualité : {v.quality} · recommandation : {v.reading_recommendation}\n"
            f"  thèse : {v.summary}\n\n"
        )
    return (
        f"ARTICLE METADATA :\n{_j(full.article_metadata.model_dump())}\n\n"
        f"{verdict}"
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
