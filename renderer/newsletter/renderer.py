"""Newsletter renderer: NewsletterDocument → Markdown + HTML, and (opt-in) PDF.

Reuses the carousel's shared helpers (`_weighted_quality`, logo, `md_bold`) and the
Playwright PDF helper. HTML/PDF use the dark gold-on-black brand look.
"""
import json
from pathlib import Path

import markdown as md_lib
from markupsafe import Markup
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.newsletter_presentation import NewsletterDocument
from renderer.instagram_carousel._shared import _weighted_quality, _LOGO_DATA_URL, _md_bold, TYPE_FR
from renderer.pdf import to_pdf

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _fr_num(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def _pdf_chrome() -> tuple[str, str]:
    """Running header (brand) + footer (tagline + page number) drawn on every PDF
    page in the margins. Chromium renders these in an isolated context, so all
    styling must be inline and font-size explicit."""
    logo = (f'<img src="{_LOGO_DATA_URL}" style="height:20px;display:block;">'
            if _LOGO_DATA_URL else "")
    header = (
        '<div style="width:100%;box-sizing:border-box;padding:0 18mm;'
        'font-family:Helvetica,Arial,sans-serif;-webkit-print-color-adjust:exact;'
        'display:flex;align-items:center;justify-content:space-between;">'
        '<span style="font-size:12px;font-weight:800;letter-spacing:.14em;color:#d4aa00;">SING SING</span>'
        f'<span>{logo}</span>'
        '</div>'
    )
    footer = (
        '<div style="width:100%;box-sizing:border-box;padding:0 18mm;'
        'font-family:Helvetica,Arial,sans-serif;-webkit-print-color-adjust:exact;'
        'display:flex;align-items:center;justify-content:space-between;font-size:9px;">'
        '<span style="font-style:italic;letter-spacing:.06em;color:#666;">'
        '<span style="color:#d4aa00;">Sing</span>, little bird, <span style="color:#d4aa00;">sing</span></span>'
        '<span style="color:#888;"><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
        '</div>'
    )
    return header, footer


def _env() -> Environment:
    # Autoescape HTML templates only — the .md template is plain text, so escaping
    # would turn apostrophes into &#39; etc.
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html",), default_for_string=False),
    )
    env.filters["md_bold"] = _md_bold
    return env


def _ctx(doc: NewsletterDocument) -> dict:
    full, pres = doc.analysis, doc.presentation
    meta = full.article_metadata
    wq = _weighted_quality(full)
    verdict = full.review.verdict if full.review else None

    meta_line = " · ".join(x for x in [
        meta.source,
        TYPE_FR.get(meta.type) if meta.type else None,
        meta.published_at,
    ] if x)

    return {
        "subject": pres.subject,
        "preheader": pres.preheader,
        "intro": pres.intro,
        "why_selected": pres.why_selected,
        "payoff": pres.payoff,
        "context": pres.context,
        "reflexes": list(pres.reflexes),
        "fact_check": list(pres.fact_check),
        "failles": list(pres.failles),
        "strengths": list(pres.strengths),
        "angles_morts": list(pres.angles_morts),
        "verdict_line": pres.verdict_line,
        "go_further": list(pres.go_further),
        "signoff": pres.signoff,
        "score": _fr_num(wq["score"]) if wq else "",
        "band": wq["label"] if wq else "",
        "for_whom": verdict.for_whom if verdict else "",
        "meta_line": meta_line,
    }


def generate_markdown(doc: NewsletterDocument) -> str:
    return _env().get_template("newsletter.md").render(**_ctx(doc))


def generate_html(doc: NewsletterDocument) -> str:
    return _env().get_template("newsletter.html").render(logo=_LOGO_DATA_URL, **_ctx(doc))


def render_from_json(json_path, out_dir, pdf: bool = False) -> list[Path]:
    """Write newsletter.md + newsletter.html into out_dir; add newsletter.pdf when
    `pdf=True`. (The `pdf` flag is opt-in via `--pdf`.)"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = NewsletterDocument.model_validate(json.loads(Path(json_path).read_text(encoding="utf-8")))

    md_path = out_dir / "newsletter.md"
    md_path.write_text(generate_markdown(doc), encoding="utf-8")
    print(f"  ✓ {md_path.name}")

    html = generate_html(doc)
    html_path = out_dir / "newsletter.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  ✓ {html_path.name}")

    outs = [md_path, html_path]
    if pdf:
        header, footer = _pdf_chrome()
        outs.append(to_pdf(html, out_dir / "newsletter.pdf", header_html=header, footer_html=footer))
    return outs


def md_to_pdf(md_path, out_path) -> Path:
    """Regenerate a PDF from a hand-edited newsletter.md — converts the markdown to
    HTML, wraps it in the branded shell, and prints it."""
    body = md_lib.markdown(Path(md_path).read_text(encoding="utf-8"),
                           extensions=["extra", "sane_lists"])
    html = _env().get_template("newsletter_shell.html").render(body=Markup(body), logo=_LOGO_DATA_URL)
    header, footer = _pdf_chrome()
    return to_pdf(html, out_path, header_html=header, footer_html=footer)
