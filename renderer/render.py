"""Render a CarouselOutput JSON to 5 PNG slides at 1080×1350px."""

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from models.carousel import CarouselOutput

TEMPLATES_DIR = Path(__file__).parent / "templates"
SLIDE_W, SLIDE_H = 1080, 1350


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    return env


def _render_html(template_name: str, context: dict) -> str:
    return _env().get_template(template_name).render(**context)


def _screenshot(html: str, output_path: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=str(output_path), clip={"x": 0, "y": 0, "width": SLIDE_W, "height": SLIDE_H})
        browser.close()


def render_carousel(output: CarouselOutput, out_dir: Path) -> list[Path]:
    """Render all 5 slides to PNG. Returns list of output paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = []

    # Slide 1 — Hook
    html = _render_html("slide_1_hook.html", {
        "headline": output.hook.headline,
        "context_line": output.hook.context_line,
        "why_read": output.hook.why_read,
        "pull_quote": output.hook.pull_quote,
        "article_type": output.article_metadata.article_type,
    })
    path = out_dir / "slide_1_hook.png"
    _screenshot(html, path)
    slides.append(path)
    print(f"  ✓ {path.name}")

    # Slide 2 — Before You Read
    byr = output.before_you_read
    html = _render_html("slide_2_before_you_read.html", {
        "contexts": byr.contexts,
        "who_is_speaking": byr.who_is_speaking,
        "important_facts": byr.important_facts,
        "key_terms": byr.key_terms,
        "watch_out": byr.watch_out,
    })
    path = out_dir / "slide_2_before_you_read.png"
    _screenshot(html, path)
    slides.append(path)
    print(f"  ✓ {path.name}")

    # Slide 3 — Global Analysis
    ga = output.global_analysis
    html = _render_html("slide_3_global_analysis.html", {
        "observations": ga.observations,
        "emotional_register": ga.emotional_register,
        "cui_bono": ga.cui_bono,
    })
    path = out_dir / "slide_3_global_analysis.png"
    _screenshot(html, path)
    slides.append(path)
    print(f"  ✓ {path.name}")

    # Slide 4 — Local Annotations
    la = output.local_annotations
    html = _render_html("slide_4_annotations.html", {
        "claims_and_sources": la.claims_and_sources,
        "biases_and_rhetoric": la.biases_and_rhetoric,
        "quote_deep_dive": la.quote_deep_dive,
    })
    path = out_dir / "slide_4_annotations.png"
    _screenshot(html, path)
    slides.append(path)
    print(f"  ✓ {path.name}")

    # Slide 5 — Go Further
    html = _render_html("slide_5_go_further.html", {
        "synthesis_points": output.synthesis.points,
        "go_further": output.go_further,
        "post_reading_questions": output.post_reading_questions,
    })
    path = out_dir / "slide_5_go_further.png"
    _screenshot(html, path)
    slides.append(path)
    print(f"  ✓ {path.name}")

    return slides


def render_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    output = CarouselOutput.model_validate(data)
    return render_carousel(output, out_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m renderer.render <carousel.json> [output_dir]")
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / src.stem
    print(f"Rendering {src} → {dst}/")
    paths = render_from_json(src, dst)
    print(f"\nDone. {len(paths)} slides saved to {dst}/")
