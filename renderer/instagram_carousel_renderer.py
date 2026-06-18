"""Render an ArticleFullAnalysis JSON to 9 PNG slides at 1080×1350px."""

import base64
import io
import json
from pathlib import Path

from PIL import Image
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from models.full_analysis import ArticleFullAnalysis

TEMPLATES_DIR = Path(__file__).parent / "templates"
SLIDE_W, SLIDE_H = 1080, 1350

_LOGO_PATH = Path(__file__).parent.parent / "src" / "assets" / "images" / "logo" / "logo.png"


def _logo_data_url(path: Path, white_threshold: int = 240) -> str:
    """Load logo PNG and make near-white pixels transparent."""
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


def _seed_text(seeds) -> str:
    """Return excerpt from a SeedsRef object for slide display."""
    if hasattr(seeds, "excerpt"):
        return ("↑ " + seeds.excerpt) if seeds.excerpt else ""
    return str(seeds)


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.filters["seed_text"] = _seed_text
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
        ("slide_02_cadrage.html", {
            "article_title": output.article_metadata.article_title,
            "article_chapo": output.article_metadata.article_chapo,
            "who_is_speaking": output.context.who_is_speaking,
            "contexts": output.context.contexts,
            "important_facts": output.context.important_facts,
        }),
        ("slide_03_watch_out.html", {
            "items": output.watch_out.items,
            "title_bullets": output.cadrage.title_bullets,
            "next_slide_hook": output.watch_out.next_slide_hook,
        }),
        ("slide_04_analysis_fond.html", {
            "main_claim": output.analysis_fond.main_claim,
            "implicit_assumptions": output.analysis_fond.implicit_assumptions,
            "blind_spots": output.analysis_fond.blind_spots,
            "observations": output.analysis_fond.observations,
        }),
        ("slide_05_analysis_forme.html", {
            "title_analysis": output.cadrage.title_analysis,
            "emotional_register": output.analysis_forme.emotional_register,
            "cui_bono": output.analysis_forme.cui_bono,
            "next_slide_hook": output.analysis_forme.next_slide_hook,
        }),
        ("slide_06_facts.html", {
            "claims_and_sources": output.facts_vs_opinions.claims_and_sources,
        }),
        ("slide_07_biases.html", {
            "biases_and_rhetoric": output.biases_and_focus.biases_and_rhetoric,
            "focus": output.biases_and_focus.focus,
            "next_slide_hook": output.biases_and_focus.next_slide_hook,
        }),
        ("slide_08_synthesis.html", {
            "points": output.synthesis.points,
            "open_question": output.synthesis.open_question,
            "engagement_question": output.synthesis.engagement_question,
        }),
        ("slide_09_go_further.html", {
            "items": output.go_further.items,
            "engagement_sentence": output.cta.engagement_sentence,
            "cta_questions": output.cta.post_reading_questions,
        }),
    ]

    names = [
        "slide_01_hook.png", "slide_02_reperes.png", "slide_03_watch_out.png",
        "slide_04_analysis_fond.png", "slide_05_analysis_forme.png",
        "slide_06_facts.png", "slide_07_biases.png", "slide_08_synthesis.png",
        "slide_09_go_further.png",
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
        print("Usage: python -m renderer.instagram_carousel_renderer <carousel.json> [output_dir]")
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / src.stem
    print(f"Rendering {src} → {dst}/")
    paths = render_from_json(src, dst)
    print(f"\nDone. {len(paths)} slides saved to {dst}/")
