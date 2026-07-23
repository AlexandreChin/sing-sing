"""Shared rendering helpers for the carousel renderer.

`optimized.py` imports from here: the Jinja environment (`_env`), the logo data
URL, the weighted global-quality gauge (`_weighted_quality`, used by the
newsletter), and the `TYPE_FR` label map. Slide generation lives in the renderer.
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

# Section glyphs shared by the carousel templates and the newsletter renderer,
# so the two stay visually in sync (same icon per matching section). Values are
# the raw <svg> children (paths/shapes only, no wrapping <svg> tag) — each
# consumer wraps them in its own `<svg viewBox="0 0 24 24" ...>`.
ICONS = {
    "bookmark": '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/>',
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "lightbulb": '<line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="22" x2="14" y2="22"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1.22.5 2.54 1.5 3.5.76.76 1.23 1.52 1.41 2.5"/>',
    "eye": '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/>',
    "info": '<circle cx="12" cy="12" r="10"/><line x1="12" y1="11" x2="12" y2="16"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    "book": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "hierarchy": '<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="2" y="16" width="6" height="5" rx="1"/><rect x="16" y="16" width="6" height="5" rx="1"/><path d="M12 8v5M5 13h14M5 13v3M19 13v3"/>',
    "bag": '<path d="M6 2L4 6v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6l-2-4z"/><line x1="4" y1="6" x2="20" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>',
    "pushpin": '<path d="M9 4v6l-2 4v2h10v-2l-2-4V4"/><path d="M12 16v5"/><path d="M8 4h8"/>',
    "widen": '<path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>',
    "anchor": '<circle cx="12" cy="5" r="3"/><line x1="12" y1="22" x2="12" y2="8"/><path d="M5 12H2a10 10 0 0 0 20 0h-3"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "speech_bubble": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "frame": '<path d="M4 8V5a1 1 0 0 1 1-1h3"/><path d="M16 4h3a1 1 0 0 1 1 1v3"/><path d="M20 16v3a1 1 0 0 1-1 1h-3"/><path d="M8 20H5a1 1 0 0 1-1-1v-3"/>',
    "eye_off": '<path d="M9.88 9.88a3 3 0 0 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 11 7 11 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 1 12s4 7 11 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" y1="2" x2="22" y2="22"/>',
    "roots": '<path d="M12 3v18"/><path d="M12 8c-2 0-4-1.5-4-4 2 0 4 1.5 4 4z"/><path d="M12 8c2 0 4-1.5 4-4-2 0-4 1.5-4 4z"/><path d="M12 14c-2 1-3.5 3-4 5"/><path d="M12 14c2 1 3.5 3 4 5"/>',
}


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
    env.globals["ICONS"] = ICONS
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
