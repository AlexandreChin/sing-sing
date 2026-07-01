"""HTML → PDF via headless Chromium — reuses the Playwright install already used
for slide screenshots. Separate from `shoot.py` because this paginates a long
document (`page.pdf`) rather than screenshotting a fixed-size slide.

Supports Chromium running header/footer templates (repeated on every page) — used
for the newsletter's brand header and page-number + tagline footer.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright


def to_pdf(html: str, out_path, *, page_format: str = "A4",
           margin_top: str = "34mm", margin_bottom: str = "26mm",
           header_html: str | None = None, footer_html: str | None = None) -> Path:
    """Render a full HTML document to a paginated PDF. `print_background` keeps the
    dark theme (the root background propagates to the whole sheet). Top/bottom
    margins give every page breathing room and hold the running header/footer;
    sides are 0 so the dark background bleeds full-width."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    opts = dict(
        path=str(out_path),
        format=page_format,
        print_background=True,
        margin={"top": margin_top, "bottom": margin_bottom, "left": "0", "right": "0"},
    )
    if header_html is not None or footer_html is not None:
        opts.update(
            display_header_footer=True,
            header_template=header_html or "<span></span>",
            footer_template=footer_html or "<span></span>",
        )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(**opts)
        browser.close()
    print(f"  ✓ {out_path.name}")
    return out_path
