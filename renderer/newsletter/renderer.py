"""Newsletter renderer: NewsletterDocument → Markdown + HTML, and (opt-in) PDF.

Reuses the carousel's shared helpers (`_weighted_quality`, logo, `md_bold`) and the
Playwright PDF helper. HTML/PDF use the dark gold-on-black brand look.
"""
import json
import math
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
    """Running header (brand) + footer (centered tagline + page number) drawn on
    every PDF page. Each is a full-bleed dark band (Chromium paints page margins
    white otherwise). Styling must be inline; font-size explicit."""
    _F = "font-family:Helvetica,Arial,sans-serif;"
    _BOX = ("position:relative;height:100%;width:100%;box-sizing:border-box;"
            "display:flex;align-items:center;padding:0 16mm;" + _F)
    # Dark background bled OUTWARD to the page edge only (header up, footer down),
    # behind the content — so it covers Chromium's white inset without hiding text.
    _BG = ("position:absolute;left:0;right:0;background:#0b0b0b;z-index:-1;"
           "-webkit-print-color-adjust:exact;print-color-adjust:exact;")
    logo = (f'<img src="{_LOGO_DATA_URL}" style="height:34px;display:block;">'
            if _LOGO_DATA_URL else "")
    header = (
        f'<div style="{_BOX}justify-content:flex-end;">'
        f'<div style="{_BG}top:-40px;bottom:0;"></div>'
        '<span style="display:inline-flex;align-items:center;gap:9px;">'
        '<span style="font-size:16px;font-weight:900;letter-spacing:-0.01em;color:#d4aa00;">Sing Sing</span>'
        f'{logo}</span>'
        '</div>'
    )
    footer = (
        f'<div style="{_BOX}justify-content:center;">'
        f'<div style="{_BG}top:0;bottom:-40px;"></div>'
        '<span style="font-size:9px;font-style:italic;letter-spacing:.06em;color:#888;">'
        '<span style="color:#d4aa00;">Sing</span>, little bird, <span style="color:#d4aa00;">sing</span></span>'
        '<span style="position:absolute;right:16mm;font-size:8px;color:#777;">'
        '<span class="pageNumber"></span> / <span class="totalPages"></span></span>'
        '</div>'
    )
    return header, footer


# Short axis labels for the radar chart (the 8 review dimensions).
DIM_SHORT = {
    "source_rigor": "Sources",
    "factual_accuracy": "Exactitude",
    "reasoning_structure": "Raisonnement",
    "approach_transparency": "Transparence",
    "context_completeness": "Contexte",
    "treatment_fairness": "Équité",
    "clarity": "Clarté",
    "angle_originality": "Originalité",
}


def _radar_svg(dims) -> str:
    """Radar (spider) chart of the review dimensions (score 1–5), gold on dark —
    the visual breakdown behind the global score. One axis per dimension."""
    if not dims:
        return ""
    n = len(dims)
    cx, cy, R = 210.0, 158.0, 96.0

    def pt(i, r):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        return cx + r * math.cos(ang), cy + r * math.sin(ang)

    def poly(r_of):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, r_of(i)) for i in range(n)))

    rings = "".join(
        f'<polygon points="{poly(lambda i, rr=R*s/5: rr)}" fill="none" stroke="#2b2b2b" stroke-width="1"/>'
        for s in range(1, 6)
    )
    axes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#2b2b2b" stroke-width="1"/>'
        for x, y in (pt(i, R) for i in range(n))
    )
    data = poly(lambda i: R * dims[i].score / 5)
    shape = f'<polygon points="{data}" fill="rgba(212,170,0,0.22)" stroke="#d4aa00" stroke-width="2"/>'
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#d4aa00"/>'
        for x, y in (pt(i, R * dims[i].score / 5) for i in range(n))
    )
    labels = []
    for i in range(n):
        lx, ly = pt(i, R + 16)
        anchor = "middle" if abs(lx - cx) < 3 else ("start" if lx > cx else "end")
        short = DIM_SHORT.get(dims[i].dimension, dims[i].label)
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="middle" '
            f'font-size="11" fill="#9a9a9a" font-family="Helvetica,Arial,sans-serif">{short} '
            f'<tspan fill="#d4aa00" font-weight="700">{dims[i].score}</tspan></text>'
        )
    return (
        '<svg viewBox="0 0 420 300" width="420" height="300" xmlns="http://www.w3.org/2000/svg">'
        + rings + axes + shape + dots + "".join(labels) + '</svg>'
    )


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
        "gauge_pos": wq["pos"] if wq else 50,
        "gauge_level": wq["level"] if wq else "mid",
        "radar_svg": Markup(_radar_svg(full.review.dimensions)) if (full.review and full.review.dimensions) else "",
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
