"""Render an ArticleFullAnalysis JSON to 6 PNG slides at 1080×1350px (long format)."""

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
    slides = []
    full = doc.analysis
    pres = doc.presentation

    url_str = str(full.article_metadata.url) if full.article_metadata.url else None

    specs = [
        ("slide_01_hook.html", {
            "topic": pres.hook.topic,
            "sub_topic": pres.hook.sub_topic,
            "headline": pres.hook.headline,
            "context_line": pres.hook.sub_topic,
            "article_title": full.article_metadata.title,
            "source": full.article_metadata.source,
            "article_url": url_str,
        }),
        ("slide_02_context_watchout.html", {
            "verdict_payoff": pres.display.payoff,
            "framing": pres.display.framing,
            "ethics_summary": pres.display.ethics,
            "ethics_verdict": full.deontology.verdict.overall if full.deontology else "clean",
            "ethics_violations": full.deontology.violations if full.deontology else [],
        }),
        ("slide_03_au_global.html", {
            "contexts": full.context.contexts[:2],
            "pre_reading": pres.display.pre_reading,
            "watch_out_items": pres.display.watch_out,
        }),
        ("slide_05_analyse.html", {
            "main_claim": full.analysis.fond.main_claim,
            "logical_strongest": full.analysis.fond.logical_reasoning[0] if full.analysis.fond.logical_reasoning else None,
            "logical_weakest": full.analysis.fond.logical_reasoning[-1] if len(full.analysis.fond.logical_reasoning) > 1 else None,
            "cui_bono": full.analysis.forme.cui_bono[:1],
            "emotional_register": full.analysis.forme.emotional_register[:2],
        }),
        ("slide_claims_biases.html", {
            "claims_and_sources": full.annotations.facts_vs_opinions.claims_and_sources,
            "biases_and_rhetoric": full.annotations.biases_and_focus.biases_and_rhetoric,
        }),
        ("slide_04_dans_le_detail.html", {
            "after_reading": pres.display.after_reading,
            "blind_spots": pres.display.blind_spots,
            "balance": pres.display.balance,
        }),
        ("slide_06_go_further.html", {
            "items": pres.go_further,
        }),
        ("slide_07_cta.html", {}),
    ]

    names = [
        "01_hook.png",
        "02_pourquoi_lire.png",
        "03_avant_de_lire.png",
        "04_synthese.png",
        "05_dans_le_detail.png",
        "06_prise_de_recul.png",
        "07_pour_aller_plus_loin.png",
        "08_cta.png",
    ]

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
        print("Usage: python -m renderer.instagram_carousel_long.renderer <carousel.json> [output_dir]")
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / src.stem
    print(f"Rendering {src} → {dst}/")
    paths = render_from_json(src, dst)
    print(f"\nDone. {len(paths)} slides saved to {dst}/")
