"""The 'render slides' step: screenshot standalone HTML slide files to PNG.

Format-agnostic — each carousel's `generate_html()` writes self-contained HTML
files (CSS inlined) into a folder; this turns them into 1080×1350 PNGs. Decoupled
from generation so the HTML can be hand-edited between the two steps.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

SLIDE_W, SLIDE_H = 1080, 1350


def shoot_dir(html_dir, out_dir=None) -> list[Path]:
    """Screenshot every *.html in `html_dir` to a .png (sorted by name).

    PNGs land in `out_dir` if given, otherwise next to the HTML."""
    html_dir = Path(html_dir)
    out_dir = Path(out_dir) if out_dir else html_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(html_dir.glob("*.html"))
    out: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for f in files:
            page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
            page.set_content(f.read_text(encoding="utf-8"), wait_until="networkidle")
            png = out_dir / (f.stem + ".png")
            page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": SLIDE_W, "height": SLIDE_H})
            page.close()
            out.append(png)
            print(f"  ✓ {png.name}")
        browser.close()
    return out
