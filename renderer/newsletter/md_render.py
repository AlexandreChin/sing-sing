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

    def heading(self, text: str, level: int, **attrs) -> str:
        title, explicit_icon = _heading_meta(text)
        self.section = title
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
