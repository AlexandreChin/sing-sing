"""The 'render slides' step: screenshot standalone HTML slide files to PNG.

Format-agnostic — each carousel's `generate_html()` writes self-contained HTML
files (CSS inlined) into a folder; this turns them into 1080×1350 PNGs. Decoupled
from generation so the HTML can be hand-edited between the two steps.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

SLIDE_W, SLIDE_H = 1080, 1350


def shoot_page(html_file, png=None, width=720, scale=2) -> Path:
    """Full-page screenshot of a single self-contained HTML file to PNG.

    Unlike `shoot_dir` (fixed-size carousel slides), this captures the whole
    scroll height — for previewing the newsletter's html/email renders, which
    have no fixed dimensions. PNG lands at `png` if given, else next to the HTML.
    """
    html_file = Path(html_file)
    png = Path(png) if png else html_file.with_suffix(".png")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1000},
                                device_scale_factor=scale)
        page.set_content(html_file.read_text(encoding="utf-8"), wait_until="networkidle")
        page.screenshot(path=str(png), full_page=True)
        browser.close()
    print(f"  ✓ {png.name}")
    return png


def _shoot_slide(browser, html_file: Path, png: Path) -> Path:
    """One fixed-size slide, in an already-open browser."""
    page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
    page.set_content(html_file.read_text(encoding="utf-8"), wait_until="networkidle")
    page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": SLIDE_W, "height": SLIDE_H})
    page.close()
    print(f"  ✓ {png.name}")
    return png


def shoot_slide(html_file, png=None) -> Path:
    """Screenshot ONE carousel slide, at slide size — for re-shooting a single
    slide after a copy edit, without regenerating the whole deck. `shoot_page`
    would capture it full-page at a device scale factor, giving a 2160×2700 PNG
    that does not belong in `slides/`."""
    html_file = Path(html_file)
    png = Path(png) if png else html_file.with_suffix(".png")
    png.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        out = _shoot_slide(browser, html_file, png)
        browser.close()
    return out


def is_slide(html_file) -> bool:
    """A carousel slide (fixed 1080×1350 frame), as opposed to a newsletter page."""
    return 'class="slide"' in Path(html_file).read_text(encoding="utf-8")


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
            out.append(_shoot_slide(browser, f, out_dir / (f.stem + ".png")))
        browser.close()
    return out
