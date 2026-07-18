"""Newsletter renderer: NewsletterDocument → Markdown + HTML (rich + email).

Reuses the carousel's shared helpers (`_weighted_quality`, logo, `md_bold`).
The rich HTML uses the dark gold-on-black brand look; the email HTML is a
table-based, inline-styled variant that survives email clients.
"""
import base64
import io
import json
import re
from pathlib import Path

from PIL import Image
from markupsafe import Markup, escape
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.newsletter_presentation import NewsletterDocument
from renderer.categories import pill
from renderer.radar import radar_svg, DIM_SHORT
from renderer.instagram_carousel._shared import _weighted_quality, _LOGO_DATA_URL, _LOGO_PATH, _md_bold, TYPE_FR

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _fr_num(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def _email_logo_data_url(px: int = 160) -> str:
    """Small (retina-sized) logo for the email header. The full asset is ~240 KB,
    which would blow past Gmail's ~102 KB clip limit; downscaled it is a few KB.
    White → transparent so the gold mark sits on any background. (Data-URI images
    still don't render in Gmail, but do in Apple/iOS/Outlook — the wordmark carries
    the brand where they're stripped.)"""
    if not _LOGO_PATH.exists():
        return ""
    img = Image.open(_LOGO_PATH).convert("RGBA")
    img.putdata([
        (r, g, b, 0) if r >= 240 and g >= 240 and b >= 240 else (r, g, b, a)
        for r, g, b, a in img.getdata()
    ])
    img = img.resize((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


_EMAIL_LOGO = _email_logo_data_url()


# Level → accent colour, shared by the gauge and the per-dimension bars in the
# email build (matches the .lv-* classes in newsletter.css).
_LEVEL_COLOR = {"good": "#7ec8a0", "mid": "#e8a07a", "bad": "#e87a7a"}


def _unwrap_quote(q: str) -> str:
    """Strip surrounding « » / whitespace: every template wraps the quote in
    guillemets, and the model sometimes returns it already wrapped — without this
    the rendered quote would be double-wrapped (« « … » »)."""
    return q.strip().strip("«»").strip()


def _decryptage_ctx(doc: NewsletterDocument) -> list[dict]:
    """The "Au fil de la lecture" pass as render-ready dicts (article order kept):
    each item is a neutral reading moment — quote, our reading, and the
    transferable reflex (`clue`). No fait/faille grade badge."""
    return [
        {"quote": _unwrap_quote(d.quote), "reading": d.reading, "clue": d.clue}
        for d in doc.presentation.decryptage
    ]


def _dim_color(score: float) -> str:
    """Per-dimension bar colour (score 1–5): green → gold → salmon → red."""
    if score >= 4:
        return "#7ec8a0"
    if score >= 3:
        return "#d4aa00"
    if score >= 2:
        return "#e8a07a"
    return "#e87a7a"


def _md_bold_email(text, color: str = "#d4aa00") -> Markup:
    """Like `_md_bold` but carries the accent colour inline — email clients strip
    the stylesheet, so `<strong>` needs its colour on the element itself. `color`
    is theme-driven (readable gold differs on dark vs light backgrounds)."""
    escaped = str(escape(text))
    return Markup(re.sub(
        r'\*\*(.+?)\*\*',
        rf'<strong style="color:{color};font-weight:700;">\1</strong>',
        escaped,
    ))


# Email colour themes. Only "chrome" (backgrounds, text, borders) is themed; the
# semantic gauge/bar colours (red→green) are fixed since they read on either
# background. `accent` is the decorative gold (rails, bars, wordmark rule);
# `accent_text` is a version dark enough to read as text/links on the background.
EMAIL_THEMES = {
    "dark": {
        "color_scheme": "dark",
        "bg": "#141414", "surface": "#1e1e1e", "track": "#2a2a2a", "border": "#2f2f2f",
        "text": "#e6e6e6", "text_soft": "#dedede", "heading": "#ededed", "muted": "#9a9a9a",
        "accent": "#d4aa00", "accent_text": "#d4aa00",
    },
    "light": {
        "color_scheme": "light",
        "bg": "#fbf8f1", "surface": "#f4efe4", "track": "#e7e0d0", "border": "#e2d9c6",
        "text": "#33322e", "text_soft": "#454339", "heading": "#1c1a15", "muted": "#6f6a5d",
        "accent": "#d4aa00", "accent_text": "#9a7a06",
    },
}


def _env() -> Environment:
    # Autoescape HTML templates only — the .md template is plain text, so escaping
    # would turn apostrophes into &#39; etc.
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html",), default_for_string=False),
    )
    env.filters["md_bold"] = _md_bold
    env.filters["md_bold_email"] = _md_bold_email
    return env


def _ctx(doc: NewsletterDocument, hook_title: str = "") -> dict:
    full, pres = doc.analysis, doc.presentation
    meta = full.article_metadata
    wq = _weighted_quality(full)
    verdict = full.review.verdict if full.review else None

    reading = f"{meta.reading_time_minutes} min de lecture" if meta.reading_time_minutes else None
    meta_line = " · ".join(x for x in [
        meta.source,
        TYPE_FR.get(meta.type) if meta.type else None,
        reading,
        meta.published_at,
    ] if x)

    return {
        "subject": pres.subject,
        # H1 headline: the carousel's hook when available (shared voice across
        # formats), otherwise the newsletter's own subject line.
        "hook_title": hook_title or pres.subject,
        "preheader": pres.preheader,
        "intro": pres.intro,
        "why_selected": pres.why_selected,
        "payoff": pres.payoff,
        "context": pres.context,
        "reflexes": list(pres.reflexes),
        "decryptage": _decryptage_ctx(doc),
        "strengths": list(pres.strengths),
        "angles_morts": list(pres.angles_morts),
        "wrap_up": pres.wrap_up,
        "go_further": list(pres.go_further),
        "prolongements": list(pres.prolongements),
        "open_question": pres.open_question,
        "signoff": pres.signoff,
        "score": _fr_num(wq["score"]) if wq else "",
        "band": wq["label"] if wq else "",
        "gauge_pos": wq["pos"] if wq else 50,
        "gauge_level": wq["level"] if wq else "mid",
        "radar_svg": Markup(radar_svg(full.review.dimensions)) if (full.review and full.review.dimensions) else "",
        "for_whom": verdict.for_whom if verdict else "",
        "meta_line": meta_line,
        # Category pill (dark by default — rich newsletter); the email overrides
        # it per theme in _email_ctx. None for "Autre"/missing → no pill.
        "cat_pill": pill(meta.category, "dark"),
        "orig_title": meta.title or "",
        "orig_url": str(meta.url) if meta.url else "",
        # extra pre-reading material pulled straight from the analysis (no API):
        # key facts to keep in mind + a short glossary of the article's terms.
        "repere_facts": [f.text for f in full.context.important_facts] if full.context else [],
        "key_terms": [{"term": kt.term, "definition": kt.definition}
                      for kt in full.context.key_terms] if full.context else [],
        # watch-out reflexes the curated `reflexes` didn't cover (the analysis
        # often lists more pre-reading tips than the 2 kept in the presentation).
        "extra_reflexes": (list(full.guide.pre_reading)[len(pres.reflexes):] if full.guide else []),
    }


def generate_markdown(doc: NewsletterDocument) -> str:
    return _env().get_template("newsletter.md").render(**_ctx(doc))


def generate_html(doc: NewsletterDocument, hook_title: str = "") -> str:
    return _env().get_template("newsletter.html").render(
        logo=_LOGO_DATA_URL, **_ctx(doc, hook_title=hook_title))


def _carousel_hook(nl_json_path) -> str:
    """The carousel's hook headline for this article, so the newsletter can lead
    with the same line. Read from the sibling carousel `adapt.json` under the
    analysis folder; "" if no carousel was produced. First letter capitalised
    (the carousel stores it lowercase)."""
    stem_dir = Path(nl_json_path).resolve().parent.parent
    for fmt in ("instagram_carousel_optimized",):
        f = stem_dir / fmt / "adapt.json"
        if not f.exists():
            continue
        try:
            headline = json.loads(f.read_text(encoding="utf-8")).get("hook", {}).get("headline", "")
        except (ValueError, OSError):
            headline = ""
        if headline:
            return headline[:1].upper() + headline[1:]
    return ""


def _email_ctx(doc: NewsletterDocument, theme: str = "light", hook_title: str = "") -> dict:
    """`_ctx` plus the bits the email needs as data (no SVG): a table-based bar
    per review dimension and the gauge's accent colour."""
    ctx = _ctx(doc, hook_title=hook_title)
    full = doc.analysis
    # Re-resolve the category pill for the email's theme (light or dark).
    ctx["cat_pill"] = pill(full.article_metadata.category, theme)
    dims = full.review.dimensions if (full.review and full.review.dimensions) else []
    ctx["dims_bars"] = [{
        "label": DIM_SHORT.get(d.dimension, d.label),
        "score": d.score,
        "pct": round(d.score / 5 * 100),
        "color": _dim_color(d.score),
    } for d in dims]
    ctx["gauge_color"] = _LEVEL_COLOR.get(ctx["gauge_level"], "#e8a07a")
    return ctx


def generate_email_html(doc: NewsletterDocument, theme: str = "light", hook_title: str = "") -> str:
    """Responsive, email-client-safe HTML (table layout + inline styles, no SVG/
    flexbox) that can be pasted straight into an email send. `theme` is "light"
    (default) or "dark" (see EMAIL_THEMES). `hook_title` overrides the H1 headline
    (used to share the carousel's hook)."""
    return _env().get_template("newsletter.email.html").render(
        logo=_EMAIL_LOGO, t=EMAIL_THEMES[theme], **_email_ctx(doc, theme=theme, hook_title=hook_title))


def render_from_json(json_path, out_dir, pdf: bool = False) -> list[Path]:
    """Write newsletter.md + newsletter.html + newsletter.email.html into out_dir.

    (`pdf` is accepted for a uniform renderer interface but unused.)"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = NewsletterDocument.model_validate(json.loads(Path(json_path).read_text(encoding="utf-8")))
    hook = _carousel_hook(json_path)

    md_path = out_dir / "newsletter.md"
    md_path.write_text(generate_markdown(doc), encoding="utf-8")
    print(f"  ✓ {md_path.name}")

    html_path = out_dir / "newsletter.html"
    html_path.write_text(generate_html(doc, hook_title=hook), encoding="utf-8")
    print(f"  ✓ {html_path.name}")

    email_path = out_dir / "newsletter.email.html"
    email_path.write_text(generate_email_html(doc, "light", hook_title=hook), encoding="utf-8")
    print(f"  ✓ {email_path.name}")

    email_dark_path = out_dir / "newsletter.email.dark.html"
    email_dark_path.write_text(generate_email_html(doc, "dark", hook_title=hook), encoding="utf-8")
    print(f"  ✓ {email_dark_path.name}")

    return [md_path, html_path, email_path, email_dark_path]
