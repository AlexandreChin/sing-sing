"""Render an edited newsletter.md (YAML front-matter + Markdown body) to the
brand HTML + email HTML. Markdown is the editable source of truth; per-block
styling is inferred from the enclosing section title and overridable with
`:::` containers and `{icon=…}` heading attributes."""
from __future__ import annotations

import html as _html
import re

import mistune
import yaml
from mistune.renderers.html import HTMLRenderer

from renderer.instagram_carousel._shared import ICONS

_FM_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
_OPEN = re.compile(r"^:::\s*([A-Za-z]+)\s*$")
_CLOSE = re.compile(r"^:::\s*$")


def parse_source(md_text: str) -> tuple[dict, str]:
    """Split a leading `---`-fenced YAML front-matter block from the body.
    No front-matter → ({}, md_text)."""
    m = _FM_RE.match(md_text)
    if not m:
        return {}, md_text
    fm = yaml.safe_load(m.group(1)) or {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, m.group(2)


def segment(body_md: str) -> list[tuple[str | None, str]]:
    """Split the body into (forced_style, chunk) pairs. `::: name` … `:::`
    fences delimit a forced-style chunk; text outside carries style None."""
    segs: list[tuple[str | None, str]] = []
    cur: list[str] = []
    style: str | None = None
    for line in body_md.splitlines():
        opn, cls = _OPEN.match(line), _CLOSE.match(line)
        if opn and style is None:
            if cur:
                segs.append((None, "\n".join(cur)))
                cur = []
            style = opn.group(1)
        elif cls and style is not None:
            segs.append((style, "\n".join(cur)))
            cur = []
            style = None
        else:
            cur.append(line)
    if cur:
        segs.append((style, "\n".join(cur)))
    return segs


# section title → default list style ("plain" gold ›, "salmon" ~, "box")
LIST_STYLE = {
    "Angles morts & nuances": "salmon",
    "À retenir": "box",
}
# section title → default block-quote style ("openq" keystone, "claim", "plain")
QUOTE_STYLE = {
    "L'architecture de l'argument": "keystone",
    "La question": "keystone",
    "Les questions à se poser": "keystone",
    "Au fil de la lecture": "claim",
}
# section title → kicker icon (an ICONS key)
ICON_BY_TITLE = {
    "L'intérêt": "flame",
    "Les repères": "eye",
    "Au fil de la lecture": "book",
    "L'architecture de l'argument": "hierarchy",
    "À emporter": "bag",
    "À vous de juger": "widen",
    "Prolonger la réflexion": "lightbulb",
    "Le contexte": "info",
    "Les réflexes": "lightbulb",
    "Les réflexes critiques": "lightbulb",
    "À retenir": "pushpin",
    "La question": "speech_bubble",
}

_ATTR_RE = re.compile(r"\s*\{([^}]*)\}\s*$")


def _heading_meta(rendered_text: str) -> tuple[str, str | None]:
    """From a heading's (HTML-escaped) inner text, return (clean_title, icon_key).
    Strips a trailing `{icon=key}` / `{.class}` attribute block."""
    title = _html.unescape(re.sub(r"<[^>]+>", "", rendered_text)).strip()
    icon = None
    m = _ATTR_RE.search(title)
    if m:
        title = title[: m.start()].strip()
        for tok in m.group(1).split():
            if tok.startswith("icon="):
                icon = tok[5:]
    return title, icon


def _icon_svg(key: str | None) -> str:
    glyph = ICONS.get(key) if key else None
    if not glyph:
        return ""
    return f'<svg viewBox="0 0 24 24">{glyph}</svg>'


class _RichBody(HTMLRenderer):
    """Renders the body with section-title inference; `forced` (set per segment
    by the caller) overrides the inferred list/quote style."""

    def __init__(self) -> None:
        super().__init__()
        self.section = ""
        self.forced: str | None = None
        self._seen_heading = False

    def heading(self, text: str, level: int, **attrs) -> str:
        title, explicit_icon = _heading_meta(text)
        self.section = title
        self._seen_heading = True
        icon = explicit_icon or ICON_BY_TITLE.get(title)
        if level <= 2:
            return f'<div class="kicker">{_icon_svg(icon)}{title}</div>\n'
        return f'<h3 class="subhead">{_icon_svg(icon)}{title}</h3>\n'

    def _items(self, text: str) -> list[str]:
        # text is the concatenation of list_item()s; each item is wrapped below.
        return [t for t in text.split("\x00") if t]

    def list_item(self, text: str) -> str:
        # sentinel-delimit items so list() can re-wrap per style; strip <p>
        # tags (loose lists wrap item content in <p>…</p>) so re-wrapping in
        # <span>/<li> doesn't nest a block element inside an inline one.
        return re.sub(r"</?p>", "", text).strip() + "\x00"

    def list(self, text: str, ordered: bool, **attrs) -> str:
        items = self._items(text)
        if ordered:
            rows = "".join(
                f'<div class="row"><span class="n">{i}</span><span>{it}</span></div>'
                for i, it in enumerate(items, 1)
            )
            return f'<div class="spine">{rows}</div>\n'
        style = self.forced or LIST_STYLE.get(self.section, "plain")
        if style == "box":
            lis = "".join(f"<li>{it}</li>" for it in items)
            return f'<div class="box"><ul>{lis}</ul></div>\n'
        mark = "~" if style == "salmon" else "›"
        cls = "salmon" if style == "salmon" else "gold"
        rows = "".join(
            f'<div class="row"><span class="mk {cls}">{mark}</span><span>{it}</span></div>'
            for it in items
        )
        return f'<div class="plain">{rows}</div>\n'

    def block_quote(self, text: str) -> str:
        style = self.forced or QUOTE_STYLE.get(self.section, "plain")
        inner = re.sub(r"</?p>", "", text).strip()
        if style == "claim":
            return f'<div class="decrypt"><div class="claim">{inner}</div></div>\n'
        return f'<div class="openq">{inner}</div>\n'

    def paragraph(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("↩"):
            body = stripped[1:].strip()
            return f'<div class="clue"><span class="ret">↩</span> {body}</div>\n'
        if stripped.startswith("<em>") and stripped.endswith("</em>"):
            return f'<p class="subtitle">{stripped[4:-5]}</p>\n'
        if not self._seen_heading:
            return f'<p class="intro">{stripped}</p>\n'
        return f"<p>{stripped}</p>\n"

    def thematic_break(self) -> str:
        return '<div class="divider"></div>\n'


def render_body_html(body_md: str) -> str:
    renderer = _RichBody()
    md = mistune.create_markdown(renderer=renderer)
    out = []
    for forced, chunk in segment(body_md):
        renderer.forced = forced
        out.append(md(chunk))
    renderer.forced = None
    return "".join(out)


def _email_styles(t: dict) -> dict:
    """Inline style strings keyed by role, resolved for an EMAIL_THEMES entry `t`."""
    return {
        "kicker": f"font-size:14px;font-weight:800;letter-spacing:.16em;"
                  f"text-transform:uppercase;color:{t['accent_text']};"
                  f"margin:32px 0 12px;",
        "subhead": f"font-size:15px;font-weight:800;letter-spacing:.1em;"
                   f"text-transform:uppercase;color:{t['heading']};margin:22px 0 8px;",
        "p": f"font-size:17px;line-height:1.6;color:{t['text']};margin:10px 0;",
        "intro": f"font-size:19px;line-height:1.62;color:{t['text']};margin:0 0 10px;",
        "subtitle": f"font-size:20px;font-style:italic;color:{t['heading']};margin:0 0 12px;",
        "clue": f"font-size:15px;font-style:italic;color:{t['muted']};margin-top:8px;",
        "row": f"font-size:17px;line-height:1.5;color:{t['text']};margin:8px 0;",
        "mark_gold": f"color:{t['accent_text']};font-weight:900;",
        "mark_salmon": "color:#e8a07a;font-weight:900;",
        "box": f"background:{t['surface']};border-left:4px solid {t['accent']};"
               f"padding:18px 22px;margin:12px 0;",
        "quote": f"background:{t['surface']};border-left:3px solid {t['accent']};"
                 f"padding:14px 20px;margin:16px 0;font-style:italic;color:{t['text']};",
        "quote_claim": f"border-left:3px solid {t['accent']};padding:2px 0 2px 18px;"
                       f"font-style:italic;color:{t['text']};margin:16px 0;",
        "divider": f"border:0;border-top:2px solid {t['accent']};margin:28px 0;",
        "n": f"color:{t['accent_text']};font-weight:900;",
    }


class _EmailBody(HTMLRenderer):
    def __init__(self, s: dict, t: dict) -> None:
        super().__init__()
        self.s, self.t = s, t
        self.section = ""
        self.forced: str | None = None
        self._seen_heading = False

    def heading(self, text: str, level: int, **attrs) -> str:
        title, _ = _heading_meta(text)
        self.section = title
        self._seen_heading = True
        role = "kicker" if level <= 2 else "subhead"
        return f'<div style="{self.s[role]}">{title}</div>\n'

    def list_item(self, text: str) -> str:
        # strip <p> tags (loose lists wrap item content in <p>…</p>) so
        # re-wrapping in <div>/<span> doesn't nest a block element inline.
        return re.sub(r"</?p>", "", text).strip() + "\x00"

    def list(self, text: str, ordered: bool, **attrs) -> str:
        items = [t for t in text.split("\x00") if t]
        if ordered:
            return "".join(
                f'<div style="{self.s["row"]}"><span style="{self.s["n"]}">{i}.</span> {it}</div>'
                for i, it in enumerate(items, 1)
            ) + "\n"
        style = self.forced or LIST_STYLE.get(self.section, "plain")
        if style == "box":
            rows = "".join(f'<div style="{self.s["row"]}">→ {it}</div>' for it in items)
            return f'<div style="{self.s["box"]}">{rows}</div>\n'
        mark = "~" if style == "salmon" else "›"
        mstyle = self.s["mark_salmon"] if style == "salmon" else self.s["mark_gold"]
        return "".join(
            f'<div style="{self.s["row"]}"><span style="{mstyle}">{mark}</span> {it}</div>'
            for it in items
        ) + "\n"

    def block_quote(self, text: str) -> str:
        style = self.forced or QUOTE_STYLE.get(self.section, "plain")
        inner = re.sub(r"</?p[^>]*>", "", text).strip()
        role = "quote_claim" if style == "claim" else "quote"
        return f'<div style="{self.s[role]}">{inner}</div>\n'

    def paragraph(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("↩"):
            return f'<div style="{self.s["clue"]}">↩ {stripped[1:].strip()}</div>\n'
        if stripped.startswith("<em>") and stripped.endswith("</em>"):
            return f'<div style="{self.s["subtitle"]}">{stripped[4:-5]}</div>\n'
        if not self._seen_heading:
            return f'<p style="{self.s["intro"]}">{stripped}</p>\n'
        return f'<p style="{self.s["p"]}">{stripped}</p>\n'

    def thematic_break(self) -> str:
        return f'<hr style="{self.s["divider"]}">\n'

    def strong(self, text: str) -> str:
        return f'<strong style="color:{self.t["accent_text"]};font-weight:700;">{text}</strong>'


def render_email_body_html(body_md: str, theme: str) -> str:
    from renderer.newsletter.renderer import EMAIL_THEMES
    t = EMAIL_THEMES[theme]
    renderer = _EmailBody(_email_styles(t), t)
    md = mistune.create_markdown(renderer=renderer)
    out = []
    for forced, chunk in segment(body_md):
        renderer.forced = forced
        out.append(md(chunk))
    renderer.forced = None
    return "".join(out)


def _shell_ctx(fm: dict) -> dict:
    """Chrome context from front-matter (keys mirror the current _ctx names the
    shell templates already use)."""
    return {
        "subject": fm.get("subject", ""),
        "preheader": fm.get("preheader", ""),
        "hook_title": fm.get("hook_title") or fm.get("subject", ""),
        "orig_title": fm.get("article_title", ""),
        "orig_url": fm.get("article_url", ""),
        "meta_line": fm.get("meta_line", ""),
        "signoff": fm.get("signoff", ""),
    }


def render_html(md_text: str) -> str:
    from renderer.newsletter.renderer import _env, _LOGO_DATA_URL
    from renderer.categories import pill
    fm, body_md = parse_source(md_text)
    ctx = _shell_ctx(fm)
    ctx["cat_pill"] = pill(fm.get("category"), "dark")
    ctx["body"] = render_body_html(body_md)
    return _env().get_template("newsletter.html").render(logo=_LOGO_DATA_URL, **ctx)


def render_email_html(md_text: str, theme: str = "light") -> str:
    from renderer.newsletter.renderer import _env, _EMAIL_LOGO, EMAIL_THEMES
    from renderer.categories import pill
    fm, body_md = parse_source(md_text)
    ctx = _shell_ctx(fm)
    ctx["cat_pill"] = pill(fm.get("category"), theme)
    ctx["body"] = render_email_body_html(body_md, theme)
    return _env().get_template("newsletter.email.html").render(
        logo=_EMAIL_LOGO, t=EMAIL_THEMES[theme], **ctx)
