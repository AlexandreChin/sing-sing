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


# ── The wire ──────────────────────────────────────────────────────────────────
# One gold line runs through the whole carousel. On each slide it lies level
# along the top edge of the key element (`data-perch`, where the bird sits) and
# changes height only in the side margins; at each edge between two slides it
# sits at the same height on both sides, so a swipe reads it as unbroken and the
# bird seems to hop along it. Drawn here because it needs every slide measured.
WIRE_MARGIN = 90        # the slides' side padding: the wire is level between them
WIRE_FLOOR = 1318       # a slide with no perch: the wire runs along its foot, under all content
WIRE_CLASS = "ss-wire"


def wire_paths(tops: list[float | None], width: int = SLIDE_W, margin: int = WIRE_MARGIN,
               floor: float = WIRE_FLOOR) -> list[str]:
    """SVG path data per slide, from each slide's perch top (None = no perch).

    The wire runs from the first perch to the last: slides before and after
    (the bird at home on the hook and the sign-off) get none, and it starts and
    ends at the text column's edge rather than at the slide's. A slide without a
    perch between two perched ones is crossed along its foot, under the content,
    so the wire stays unbroken without running through text or images."""
    perched = [i for i, t in enumerate(tops) if t is not None]
    if not perched:
        return ["" for _ in tops]
    first, last = perched[0], perched[-1]
    level = [t if t is not None else floor for t in tops]
    edges = [level[0]] + [(a + b) / 2 for a, b in zip(level, level[1:])] + [level[-1]]
    L, R = margin, width - margin
    paths = []
    for i, t in enumerate(level):
        if i < first or i > last:
            paths.append("")
            continue
        y_in, y_out, y = edges[i], edges[i + 1], t - 1
        start = (f"M{L} {y:.1f}" if i == first else
                 f"M0 {y_in:.1f} C {L * .6:.1f} {y_in:.1f}, {L * .4:.1f} {y:.1f}, {L} {y:.1f}")
        end = (f"L {R} {y:.1f}" if i == last else
               f"L {R} {y:.1f} C {R + (width - R) * .6:.1f} {y:.1f}, {R + (width - R) * .4:.1f} "
               f"{y_out:.1f}, {width} {y_out:.1f}")
        paths.append(f"{start} {end}")
    return paths


_MEASURE = """() => { const s = document.querySelector('.slide'), el = document.querySelector('[data-perch]');
  return (s && el) ? el.getBoundingClientRect().top - s.getBoundingClientRect().top : null; }"""
_DRAW = """([d, cls]) => { document.querySelectorAll('.' + cls).forEach(e => e.remove());
  if (!d) return; const s = document.querySelector('.slide'); if (!s) return;
  s.insertAdjacentHTML('beforeend', '<svg class="' + cls + '" viewBox="0 0 1080 1350" style="position:absolute;' +
    'inset:0;width:1080px;height:1350px;pointer-events:none;z-index:3"><path d="' + d + '" fill="none" ' +
    'stroke="#d4aa00" stroke-width="3" stroke-linecap="round"/></svg>'); }"""


def shoot_dir(html_dir, out_dir=None) -> list[Path]:
    """Screenshot every *.html in `html_dir` to a .png (sorted by name).

    PNGs land in `out_dir` if given, otherwise next to the HTML. When the slides
    mark a perch, the wire is measured across all of them, drawn into each HTML
    (saved back, so html/ matches slides/) and shot with it."""
    html_dir = Path(html_dir)
    out_dir = Path(out_dir) if out_dir else html_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(html_dir.glob("*.html"))
    out: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        tops = []
        for f in files:
            page.set_content(f.read_text(encoding="utf-8"), wait_until="networkidle")
            tops.append(page.evaluate(_MEASURE))
        for f, d in zip(files, wire_paths(tops)):
            page.set_content(f.read_text(encoding="utf-8"), wait_until="networkidle")
            page.evaluate(_DRAW, [d, WIRE_CLASS])
            if d:
                f.write_text("<!DOCTYPE html>\n" + page.content(), encoding="utf-8")
            png = out_dir / (f.stem + ".png")
            page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": SLIDE_W, "height": SLIDE_H})
            print(f"  ✓ {png.name}")
            out.append(png)
        page.close()
        browser.close()
    return out
