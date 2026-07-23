"""Generate the newsletter presentation layer from a completed ArticleFullAnalysis.

Same analysis as the carousel — but the copy is flowing prose (subject line,
preheader, sections), not slide fragments.
"""
import json
import sys
from pathlib import Path

from agent._base import _call_with_retry, _j
from agent.lenses import LENS_IDS
from models.full_analysis import ArticleFullAnalysis
from models.newsletter_presentation import NewsletterPresentation

_PROMPT = (Path(__file__).parent / "prompts" / "newsletter.md").read_text(encoding="utf-8")

# Sibling carousel output, relative to the analysis file's own output folder
# (outputs/<stem>/analysis.json → outputs/<stem>/instagram_carousel_optimized/adapt.json).
_CAROUSEL_ADAPT_REL = Path("instagram_carousel_optimized") / "adapt.json"


def _load_carousel_backbone(analysis_path: str | Path | None) -> str | None:
    """Load the sibling carousel `adapt.json` (if present) and render it as the
    structural backbone the newsletter must expand — same beats, same
    architecture, same à-retenir. Returns None (→ standalone) if there is no
    analysis_path, no sibling file, or it fails to parse."""
    if analysis_path is None:
        return None
    sibling = Path(analysis_path).parent / _CAROUSEL_ADAPT_REL
    if not sibling.exists():
        return None
    try:
        carousel = json.loads(sibling.read_text(encoding="utf-8"))
        hook = carousel["hook"]
        display = carousel["display"]
        backbone = {
            "hook": {"topic": hook["topic"], "sub_topic": hook["sub_topic"]},
            "selection_headline": display["selection_headline"],
            "why_selected": display["why_selected"],
            "reading_beats": [
                {"moment": b["moment"], "quote": b["quote"], "note": b["note"], "answer": b.get("answer", ""), "lens_ref": b["lens_ref"]}
                for b in display.get("reading_beats", [])
                if b.get("selected", True)
            ],
            "global_analysis": display.get("global_analysis"),
            "key_takeaways": [
                t["text"] for t in display.get("key_takeaways", [])
                if t.get("selected", True)
            ],
            "root_issue": display.get("root_issue", ""),
            "steel_man": display.get("steel_man"),
            "engagement_sentence": carousel.get("cta", {}).get("engagement_sentence", ""),
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None
    return (
        "STRUCTURE DU CAROUSEL (à reprendre) — la newsletter DÉVELOPPE cette "
        "structure en prose, elle n'en invente pas une autre :\n" + _j(backbone)
    )


def _validate(data: dict) -> list[str]:
    pres = NewsletterPresentation.model_validate(data)
    errors = []
    for field in ("subject", "preheader", "selection_headline", "why_selected",
                  "payoff", "essentiel", "context", "reading_posture", "framing", "signoff"):
        if not getattr(pres, field).strip():
            errors.append(f"{field} is empty")
    n = len(pres.decryptage)
    if not (5 <= n <= 7):
        errors.append(f"decryptage must have 5–7 items, got {n}")
    for i, d in enumerate(pres.decryptage):
        if not d.quote.strip() or not d.reading.strip() or not (d.prompt or "").strip():
            errors.append(f"decryptage[{i}] has an empty quote/prompt/reading")
        if d.lens_ref not in LENS_IDS:
            errors.append(f"decryptage[{i}].lens_ref must be a canonical lens id, got {d.lens_ref!r}")
    # L'architecture de l'argument
    if not pres.architecture.keystone.strip():
        errors.append("architecture.keystone is empty")
    if not (2 <= len(pres.architecture.presupposes) <= 4):
        errors.append(f"architecture.presupposes must have 2–4 items, got {len(pres.architecture.presupposes)}")
    # À emporter
    if not (3 <= len(pres.a_emporter.key_takeaways) <= 4):
        errors.append(f"a_emporter.key_takeaways must have 3–4 items, got {len(pres.a_emporter.key_takeaways)}")
    if not (3 <= len(pres.a_emporter.reflexes_critiques) <= 5):
        errors.append(f"a_emporter.reflexes_critiques must have 3–5 items, got {len(pres.a_emporter.reflexes_critiques)}")
    for i, r in enumerate(pres.a_emporter.reflexes_critiques):
        if r.lens_ref not in LENS_IDS:
            errors.append(f"a_emporter.reflexes_critiques[{i}].lens_ref must be a canonical lens id, got {r.lens_ref!r}")
        if not r.rule.strip():
            errors.append(f"a_emporter.reflexes_critiques[{i}] has an empty rule")
    # À vous de juger
    if not (1 <= len(pres.verdict.enjeux) <= 3):
        errors.append(f"verdict.enjeux must have 1–3 items, got {len(pres.verdict.enjeux)}")
    if not (1 <= len(pres.verdict.objections) <= 3):
        errors.append(f"verdict.objections must have 1–3 items, got {len(pres.verdict.objections)}")
    if not (2 <= len(pres.verdict.angles_morts) <= 3):
        errors.append(f"verdict.angles_morts must have 2–3 items, got {len(pres.verdict.angles_morts)}")
    if not (2 <= len(pres.verdict.nuances) <= 3):
        errors.append(f"verdict.nuances must have 2–3 items, got {len(pres.verdict.nuances)}")
    # Prolonger la réflexion
    if not (4 <= len(pres.go_further) <= 6):
        errors.append(f"go_further must have 4–6 items, got {len(pres.go_further)}")
    return errors


def _context(full: ArticleFullAnalysis, backbone: str | None = None) -> str:
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
        + (f"\n\n{backbone}" if backbone else "")
    )


def adapt(
    full: ArticleFullAnalysis,
    no_api: bool = False,
    analysis_path: str | Path | None = None,
) -> NewsletterPresentation:
    backbone = _load_carousel_backbone(analysis_path)
    if backbone is not None:
        print("Backbone carousel détecté — expansion en prose.", file=sys.stderr, flush=True)
    user_msg = f"{_context(full, backbone)}\n\n---\n\n{_PROMPT}"
    print("Adaptation newsletter…", file=sys.stderr, flush=True)
    data = _call_with_retry(
        user_msg,
        NewsletterPresentation.model_json_schema(),
        validator=_validate,
        no_api=no_api,
    )
    return NewsletterPresentation.model_validate(data)
