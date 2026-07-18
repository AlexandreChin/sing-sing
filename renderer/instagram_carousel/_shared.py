"""Shared rendering helpers for the optimized carousel renderers.

`optimized.py` and `optimized_short.py` import from here: the Jinja environment
(`_env`), the logo data URL, the weighted global-quality gauge (`_weighted_quality`),
and the `TYPE_FR` label map. Slide generation itself lives in each renderer module.
"""

import base64
import io
import re
from pathlib import Path

from markupsafe import Markup, escape
from PIL import Image
from jinja2 import Environment, FileSystemLoader

from renderer.categories import CATEGORY_ICONS
from renderer.instagram_carousel.procart import cover_art

TEMPLATES_DIR = Path(__file__).parent / "templates"

_LOGO_PATH = Path(__file__).parent.parent.parent / "src" / "assets" / "images" / "logo" / "logo.png"

# Importance weights for the global quality score (Σ = 15). Factual accuracy and
# reasoning structure are the epistemic core and weigh most; craft axes least.
DIMENSION_WEIGHTS = {
    "factual_accuracy": 3.0,
    "reasoning_structure": 3.0,
    "source_rigor": 2.0,
    "context_completeness": 2.0,
    "treatment_fairness": 1.5,
    "approach_transparency": 1.5,
    "clarity": 1.0,
    "angle_originality": 1.0,
}
TYPE_FR = {"editorial": "Éditorial", "news_report": "Reportage", "opinion": "Tribune",
           "investigation": "Enquête", "interview": "Interview", "other": "Article"}


def _weighted_quality(full) -> dict | None:
    """Global score = weighted average of the review dimensions (1–5), mapped to a
    French band + gauge position. Weights from DIMENSION_WEIGHTS."""
    if not (full.review and full.review.dimensions):
        return None
    dims = full.review.dimensions
    num = sum(DIMENSION_WEIGHTS.get(d.dimension, 1.0) * d.score for d in dims)
    den = sum(DIMENSION_WEIGHTS.get(d.dimension, 1.0) for d in dims) or 1.0
    score = num / den
    if score >= 4.0:
        label, band = "Exemplaire", "exemplaire"
    elif score >= 3.5:
        label, band = "Très bonne", "tres_bonne"
    elif score >= 3.2:
        label, band = "Bonne", "bonne"
    elif score >= 2.8:
        label, band = "Correcte", "correcte"
    elif score >= 2.0:
        label, band = "Moyenne", "moyenne"
    elif score >= 1.5:
        label, band = "Faible", "faible"
    else:
        label, band = "Critique", "critique"
    level = "good" if band in ("bonne", "tres_bonne", "exemplaire") else "bad" if band in ("faible", "critique") else "mid"
    return {"score": score, "label": label, "band": band, "pos": round((score - 1) / 4 * 100), "level": level}


def _logo_data_url(path: Path, white_threshold: int = 240, crop: bool = False) -> str:
    img = Image.open(path).convert("RGBA")
    pixels = img.getdata()
    new_pixels = [
        (r, g, b, 0) if r >= white_threshold and g >= white_threshold and b >= white_threshold else (r, g, b, a)
        for r, g, b, a in pixels
    ]
    img.putdata(new_pixels)
    if crop:  # trim the transparent padding so the bird can be sized to the text
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


_LOGO_DATA_URL = _logo_data_url(_LOGO_PATH) if _LOGO_PATH.exists() else ""
_LOGO_TIGHT_DATA_URL = _logo_data_url(_LOGO_PATH, crop=True) if _LOGO_PATH.exists() else ""


def _md_bold(text) -> Markup:
    escaped = str(escape(text))
    return Markup(re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped))


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.filters["md_bold"] = _md_bold
    return env


def cover_layers(meta, headline: str) -> dict:
    """Hook slide-1 background context, shared by both carousel renderers.

    `rubrique`/`glyph` carry category identity (dropped for "Autre"/missing,
    mirroring `pill()==None`); `art_svg` is the per-carousel procedural art,
    seeded from the article title (headline as fallback for a title-less article).
    """
    glyph = CATEGORY_ICONS.get(meta.category or "", "")
    seed = (meta.title or "").strip() or (headline or "")
    return {
        "rubrique": meta.category if glyph else None,
        "glyph": glyph,
        "art_svg": cover_art(seed),
    }
