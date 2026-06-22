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
    n_cta = len(pres.cta.post_reading_questions)
    if not (1 <= n_cta <= 4):
        errors.append(f"cta.post_reading_questions: expected 1–4, got {n_cta}")
    if not any(q.type == "blind_spot" for q in pres.cta.post_reading_questions):
        errors.append("cta.post_reading_questions: at least one must be type 'blind_spot'")
    n_go = len(pres.go_further)
    if not (1 <= n_go <= 6):
        errors.append(f"go_further: expected 1–6 items, got {n_go}")
    for i, item in enumerate(pres.go_further):
        if item.cta_question_index is not None and not (0 <= item.cta_question_index < n_cta):
            errors.append(
                f"go_further[{i}].cta_question_index={item.cta_question_index} out of range (0–{n_cta - 1})"
            )
    return errors


def _full_analysis_context(full: ArticleFullAnalysis) -> str:
    return (
        f"ARTICLE METADATA :\n{_j(full.article_metadata.model_dump())}\n\n"
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
