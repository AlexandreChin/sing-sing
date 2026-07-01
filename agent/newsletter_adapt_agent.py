"""Generate the newsletter presentation layer from a completed ArticleFullAnalysis.

Same analysis as the carousel — but the copy is flowing prose (subject line,
preheader, sections), not slide fragments.
"""
import sys
from pathlib import Path

from agent._base import _call_with_retry, _j
from models.full_analysis import ArticleFullAnalysis
from models.newsletter_presentation import NewsletterPresentation

_PROMPT = (Path(__file__).parent / "prompts" / "newsletter.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    pres = NewsletterPresentation.model_validate(data)
    errors = []
    for field in ("subject", "preheader", "intro", "why_selected", "payoff", "context", "verdict_line", "signoff"):
        if not getattr(pres, field).strip():
            errors.append(f"{field} is empty")
    if len(pres.reflexes) != 2:
        errors.append(f"reflexes must have exactly 2 items, got {len(pres.reflexes)}")
    if not (2 <= len(pres.fact_check) <= 3):
        errors.append(f"fact_check must have 2–3 items, got {len(pres.fact_check)}")
    if len(pres.failles) != 2:
        errors.append(f"failles must have exactly 2 items, got {len(pres.failles)}")
    if not (1 <= len(pres.strengths) <= 2):
        errors.append(f"strengths must have 1–2 items, got {len(pres.strengths)}")
    if not (2 <= len(pres.angles_morts) <= 3):
        errors.append(f"angles_morts must have 2–3 items, got {len(pres.angles_morts)}")
    if not (2 <= len(pres.go_further) <= 3):
        errors.append(f"go_further must have 2–3 items, got {len(pres.go_further)}")
    for i, s in enumerate(pres.failles):
        if not s.heading.strip() or not s.body.strip():
            errors.append(f"failles[{i}] has an empty heading/body")
    for i, s in enumerate(pres.strengths):
        if not s.heading.strip() or not s.body.strip():
            errors.append(f"strengths[{i}] has an empty heading/body")
    return errors


def _context(full: ArticleFullAnalysis) -> str:
    verdict = ""
    if full.review:
        v = full.review.verdict
        verdict = (
            "VERDICT (fil conducteur — toute la newsletter doit y mener) :\n"
            f"  qualité : {v.quality} · recommandation : {v.reading_recommendation}\n"
            f"  thèse : {v.summary}\n\n"
        )
    return (
        f"ARTICLE METADATA :\n{_j(full.article_metadata.model_dump())}\n\n"
        f"{verdict}"
        f"ANALYSE COMPLÈTE :\n{full.model_dump_json(indent=2)}"
    )


def adapt(full: ArticleFullAnalysis, no_api: bool = False) -> NewsletterPresentation:
    user_msg = f"{_context(full)}\n\n---\n\n{_PROMPT}"
    print("Adaptation newsletter…", file=sys.stderr, flush=True)
    data = _call_with_retry(
        user_msg,
        NewsletterPresentation.model_json_schema(),
        validator=_validate,
        no_api=no_api,
    )
    return NewsletterPresentation.model_validate(data)
