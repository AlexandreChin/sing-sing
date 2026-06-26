"""Render an ArticleFullAnalysis JSON to 6 PNG slides at 1080×1350px (short format).

Reuses the carousel presentation produced by the enrich agent — no extra LLM call.
Slide arc: Hook → Évaluation (gauges) → Repères → Dans le détail → Prise de recul → CTA.
"""

import base64
import io
import json
import re
from pathlib import Path

from markupsafe import Markup, escape
from PIL import Image
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from models.instagram_carousel_presentation import InstagramCarouselDocument

TEMPLATES_DIR = Path(__file__).parent / "templates"
SLIDE_W, SLIDE_H = 1080, 1350

_LOGO_PATH = Path(__file__).parent.parent.parent / "src" / "assets" / "images" / "logo" / "logo.png"

# ── Gauge mappings (dimension scores → weighted global, on one normalized track) ─
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
# How many strengths vs weaknesses to surface on the analysis slide, scaled to
# the weighted quality band (total = 4).
QUALITY_BALANCE = {
    "exemplaire": (3, 1),
    "tres_bonne": (3, 1),
    "bonne": (3, 1),
    "correcte": (2, 2),
    "moyenne": (2, 2),
    "faible": (1, 3),
    "critique": (1, 3),
}
DIM_FR = {
    "source_rigor": "Rigueur des sources",
    "factual_accuracy": "Exactitude factuelle",
    "reasoning_structure": "Structure du raisonnement",
    "approach_transparency": "Transparence",
    "context_completeness": "Contexte & complétude",
    "treatment_fairness": "Équité de traitement",
    "clarity": "Clarté",
    "angle_originality": "Angle & originalité",
}
TYPE_FR = {"editorial": "Éditorial", "news_report": "Reportage", "opinion": "Tribune",
           "investigation": "Enquête", "interview": "Interview", "other": "Article"}
def _level(pos: float) -> str:
    return "bad" if pos < 0.4 else "mid" if pos < 0.7 else "good"


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


def _quality_gauge(full) -> dict:
    """Main gauge: the weighted global quality score."""
    wq = _weighted_quality(full)
    if not wq:
        return {"name": "Qualité de l'article", "val": "—", "pos": 50, "level": "mid"}
    return {"name": "Qualité de l'article", "val": wq["label"], "pos": wq["pos"], "level": wq["level"]}


def _dim_gauges(full) -> list[dict]:
    """Sub-gauges: the article's best-scoring criteria (its strengths)."""
    out = []
    if full.review and full.review.dimensions:
        dims = full.review.dimensions
        best = sorted(range(len(dims)), key=lambda i: (-dims[i].score, i))[:3]
        for i in best:
            d = dims[i]
            pos = (d.score - 1) / 4
            out.append({"name": DIM_FR.get(d.dimension, d.label), "val": f"{d.score}/5",
                        "pos": round(pos * 100), "level": _level(pos)})
    return out


def _balance_points(full) -> list[dict]:
    """Balanced analysis: strengths + weaknesses, the split scaled to the weighted
    quality band (e.g. 'adequate' → 2 good + 2 bad). Strengths = highest-scoring
    dimensions, weaknesses = lowest-scoring; each carries its reader lesson."""
    if not (full.review and full.review.dimensions):
        return []
    dims = full.review.dimensions
    wq = _weighted_quality(full)
    n_good, n_bad = QUALITY_BALANCE.get(wq["band"] if wq else "adequate", (2, 2))
    order = sorted(range(len(dims)), key=lambda i: (-dims[i].score, i))  # best first
    picks = [(i, "good") for i in order[:n_good]] + [(i, "bad") for i in order[len(order) - n_bad:]]
    return [{
        "valence": v,
        "label": DIM_FR.get(dims[i].dimension, dims[i].label),
        "score": dims[i].score,
        "text": dims[i].lesson,
    } for i, v in picks]


def _logo_data_url(path: Path, white_threshold: int = 240) -> str:
    img = Image.open(path).convert("RGBA")
    pixels = img.getdata()
    new_pixels = [
        (r, g, b, 0) if r >= white_threshold and g >= white_threshold and b >= white_threshold else (r, g, b, a)
        for r, g, b, a in pixels
    ]
    img.putdata(new_pixels)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


_LOGO_DATA_URL = _logo_data_url(_LOGO_PATH) if _LOGO_PATH.exists() else ""


def _md_bold(text) -> Markup:
    escaped = str(escape(text))
    return Markup(re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped))


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.filters["md_bold"] = _md_bold
    return env


def _render_html(template_name: str, context: dict) -> str:
    return _env().get_template(template_name).render(logo=_LOGO_DATA_URL, **context)


def _screenshot(html: str, output_path: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=str(output_path), clip={"x": 0, "y": 0, "width": SLIDE_W, "height": SLIDE_H})
        browser.close()


def render_carousel(doc: InstagramCarouselDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    full = doc.analysis
    pres = doc.presentation
    meta = full.article_metadata
    disp = pres.display

    source_meta = " · ".join(x for x in [
        meta.source,
        TYPE_FR.get(meta.type) if meta.type else None,
        f"{meta.reading_time_minutes} min" if meta.reading_time_minutes else None,
    ] if x)

    specs = [
        ("default/slide_01_hook.html", {
            "headline": pres.hook.headline,
            "article_title": meta.title,
            "source_meta": source_meta,
        }),
        ("default/slide_02_evaluation.html", {
            "why_read": disp.payoff,
            "main_gauge": _quality_gauge(full),
            "score_rationale": disp.distill_points[0] if disp.distill_points else "",
            "sub_gauges": _dim_gauges(full),
        }),
        ("default/slide_03_reperes.html", {
            "contexts": full.context.contexts[:1],
            "pre_reading": disp.pre_reading[:2],
            "watch_out": disp.watch_out[:2],
        }),
        ("default/slide_04_dans_le_detail.html", {
            "items": _balance_points(full),
        }),
        ("default/slide_05_prise_de_recul.html", {
            "blind_spots": disp.blind_spots,
            "balance": disp.balance,
        }),
        ("default/slide_06_cta.html", {"cta_title": pres.cta.title}),
    ]

    names = [
        "01_hook.png",
        "02_interet.png",
        "03_clefs_de_lecture.png",
        "04_essentiel.png",
        "05_prise_de_recul.png",
        "06_cta.png",
    ]

    slides = []
    for (template, ctx), name in zip(specs, names):
        html = _render_html(template, ctx)
        path = out_dir / name
        _screenshot(html, path)
        slides.append(path)
        print(f"  ✓ {name}")

    return slides


def render_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    doc = InstagramCarouselDocument.model_validate(data)
    return render_carousel(doc, out_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m renderer.instagram_carousel_short.renderer <carousel.json> [output_dir]")
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / src.stem
    print(f"Rendering {src} → {dst}/")
    paths = render_from_json(src, dst)
    print(f"\nDone. {len(paths)} slides saved to {dst}/")
