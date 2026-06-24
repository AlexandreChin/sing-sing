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

# ── Gauge mappings (quality verdict + dimension scores → one normalized track) ─
QUALITY = {
    "exemplary": ("Exemplaire", .95, "good"),
    "solid": ("Solide", .78, "good"),
    "adequate": ("Correcte", .55, "mid"),
    "instructive_by_contrast": ("Instructif", .35, "bad"),
    "weak": ("Faible", .15, "bad"),
}
DIM_FR = {
    "source_rigor": "Rigueur des sources",
    "reasoning_structure": "Structure du raisonnement",
    "approach_transparency": "Transparence",
    "treatment_fairness": "Équité de traitement",
    "clarity": "Clarté",
    "angle_originality": "Angle & originalité",
}
TYPE_FR = {"editorial": "Éditorial", "news_report": "Reportage", "opinion": "Tribune",
           "investigation": "Enquête", "interview": "Interview", "other": "Article"}
def _level(pos: float) -> str:
    return "bad" if pos < 0.4 else "mid" if pos < 0.7 else "good"


def _quality_gauge(full) -> dict:
    """Main gauge: overall article quality from the review verdict."""
    q = full.review.verdict.quality if full.review else "adequate"
    label, pos, level = QUALITY.get(q, ("Correcte", .55, "mid"))
    return {"name": "Qualité de l'article", "val": label, "pos": round(pos * 100), "level": level}


def _dim_gauges(full) -> list[dict]:
    """Sub-gauges: the (already-trimmed) most-decisive review dimensions, scored 1–5."""
    out = []
    if full.review:
        for d in full.review.dimensions:
            pos = (d.score - 1) / 4
            out.append({"name": DIM_FR.get(d.dimension, d.label), "val": f"{d.score}/5",
                        "pos": round(pos * 100), "level": _level(pos)})
    return out


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
        ("slide_01_hook.html", {
            "headline": pres.hook.headline,
            "article_title": meta.title,
            "source_meta": source_meta,
        }),
        ("slide_02_evaluation.html", {
            "why_read": disp.payoff,
            "main_gauge": _quality_gauge(full),
            "sub_gauges": _dim_gauges(full),
        }),
        ("slide_03_reperes.html", {
            "contexts": full.context.contexts[:1],
            "pre_reading": disp.pre_reading[:2],
            "watch_out": disp.watch_out[:2],
        }),
        ("slide_04_dans_le_detail.html", {
            "points": disp.distill_points,
        }),
        ("slide_05_prise_de_recul.html", {
            "blind_spots": disp.blind_spots,
            "balance": disp.balance,
        }),
        ("slide_06_cta.html", {}),
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
