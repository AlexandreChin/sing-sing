"""Render an ArticleFullAnalysis JSON to 6 PNG slides at 1080×1350px (short format)."""

import base64
import io
import json
import re
from pathlib import Path

from markupsafe import Markup, escape
from PIL import Image
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from models.full_analysis import ArticleFullAnalysis

TEMPLATES_DIR = Path(__file__).parent / "templates" / "instagram_carousel_short"
SLIDE_W, SLIDE_H = 1080, 1350

_LOGO_PATH = Path(__file__).parent.parent / "src" / "assets" / "images" / "logo" / "logo.png"


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


def render_carousel(output: ArticleFullAnalysis, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = []

    url_str = str(output.article_metadata.url) if output.article_metadata.url else None

    specs = [
        ("slide_01_hook.html", {
            "topic": output.hook.topic,
            "sub_topic": output.hook.sub_topic,
            "headline": output.hook.headline,
            "context_line": output.interest.why_read,
            "article_title": output.article_metadata.article_title,
            "source": output.article_metadata.source,
            "article_url": url_str,
        }),
        ("slide_02_context_watchout.html", {
            "contexts": output.context.contexts,
            "items": output.watch_out.items,
            "next_hook": output.watch_out.next_slide_hook,
        }),
        ("slide_03_au_global.html", {
            "main_claim": output.analysis_fond.main_claim,
            "observations": output.analysis_fond.observations,
            "title_analysis": output.cadrage.title_analysis,
            "emotional_register": output.analysis_forme.emotional_register,
            "next_hook": output.analysis_forme.next_slide_hook,
        }),
        ("slide_04_dans_le_detail.html", {
            "claims_and_sources": output.facts_vs_opinions.claims_and_sources,
            "biases_and_rhetoric": output.biases_and_focus.biases_and_rhetoric,
            "next_hook": output.biases_and_focus.next_slide_hook,
        }),
        ("slide_05_go_further.html", {
            "items": output.go_further.items,
        }),
        ("slide_06_cta.html", {
            "engagement_question": output.synthesis.engagement_question,
        }),
    ]

    names = [
        "slide_01_hook.png",
        "slide_02_context_watchout.png",
        "slide_03_au_global.png",
        "slide_04_dans_le_detail.png",
        "slide_05_go_further.png",
        "slide_06_cta.png",
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
    output = ArticleFullAnalysis.model_validate(data)
    return render_carousel(output, out_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m renderer.instagram_carousel_short_renderer <carousel.json> [output_dir]")
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / src.stem
    print(f"Rendering {src} → {dst}/")
    paths = render_from_json(src, dst)
    print(f"\nDone. {len(paths)} slides saved to {dst}/")
