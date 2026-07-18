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
    for field in ("subject", "preheader", "intro", "why_selected", "payoff", "context", "wrap_up", "open_question", "signoff"):
        if not getattr(pres, field).strip():
            errors.append(f"{field} is empty")
    if len(pres.reflexes) != 2:
        errors.append(f"reflexes must have exactly 2 items, got {len(pres.reflexes)}")
    n = len(pres.decryptage)
    if not (4 <= n <= 6):
        errors.append(f"decryptage must have 4–6 items, got {n}")
    for i, d in enumerate(pres.decryptage):
        if not d.quote.strip() or not d.reading.strip():
            errors.append(f"decryptage[{i}] has an empty quote/reading")
    if not (2 <= len(pres.angles_morts) <= 3):
        errors.append(f"angles_morts must have 2–3 items, got {len(pres.angles_morts)}")
    if not (2 <= len(pres.go_further) <= 3):
        errors.append(f"go_further must have 2–3 items, got {len(pres.go_further)}")
    if len(pres.prolongements) != 2:
        errors.append(f"prolongements must have exactly 2 items, got {len(pres.prolongements)}")
    for i, p in enumerate(pres.prolongements):
        if not p.heading.strip() or not p.body.strip():
            errors.append(f"prolongements[{i}] has an empty heading/body")
    return errors


def _context(full: ArticleFullAnalysis) -> str:
    core = ""
    if full.core_elements and full.core_elements.elements:
        lines = "\n".join(
            f"  - [{e.kind}, centralité {e.centrality}] {e.statement}"
            for e in full.core_elements.elements
        )
        core = (
            "ÉLÉMENTS CENTRAUX (la newsletter doit les COUVRIR — ne pas se limiter "
            "à l'angle du titre) :\n" + lines + "\n\n"
        )
    return (
        f"ARTICLE METADATA :\n{_j(full.article_metadata.model_dump())}\n\n"
        f"{core}"
        "ANALYSE COMPLÈTE :\n"
        f"{full.model_dump_json(indent=2, exclude={'review', 'deontology'})}"
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
