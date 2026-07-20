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


# section title → default list style ("plain" gold ›, "box")
LIST_STYLE = {
    "À retenir": "box",
}
# sections whose items are each rendered as a standalone sub-card (::: card in the
# template); in email the heading becomes a plain label instead of a wrapping card.
CARD_LIST_SECTIONS = {"Pour aller plus loin"}
# section title → default block-quote style ("openq" keystone, "claim", "plain")
QUOTE_STYLE = {
    "L'architecture de l'argument": "keystone",
    "Les questions à se poser": "keystone",
    "Au fil de la lecture": "claim",
}
# section title → kicker icon (an ICONS key)
ICON_BY_TITLE = {
    # acts
    "Pourquoi cet article": "bookmark",
    "Avant de vous lancer": "eye",
    "Au fil de la lecture": "book",
    "Après la lecture": "hierarchy",
    # subheads
    "Le contexte": "info",
    "Comment le lire": "eye",
    "Les faits à garder en tête": "pushpin",
    "Le lexique": "info",
    "L'architecture de l'argument": "hierarchy",
    "À retenir": "pushpin",
    "Les réflexes critiques": "lightbulb",
    "Les enjeux de fond": "anchor",
    "Les objections les plus solides": "shield",
    "Angles morts": "eye",
    "Nuances": "info",
    "Les questions à se poser": "speech_bubble",
    "À qui profite ce cadrage ?": "widen",
    "Pour aller plus loin": "widen",
    "Avant de partir": "speech_bubble",
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
        if level >= 2:
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
        rows = "".join(
            f'<div class="row"><span class="mk gold">›</span><span>{it}</span></div>'
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
        if stripped.startswith("→"):   # beat answer — gold arrow, no "Réponse" label
            return f'<div class="answer"><span class="ans-mk">›</span> {stripped[1:].strip()}</div>\n'
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


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _norm_url(u: str) -> str:
    return u if "://" in u else "https://" + u


def _gofurther_rich(items: list) -> str:
    """« Pour aller plus loin » — one card, each resource a type-pill + title +
    source + why, separated by a divider (mirrors the 6221e68 layout)."""
    if not items:
        return ""
    rows = []
    for i, r in enumerate(items):
        if i:
            rows.append('<div class="res-sep"></div>')
        if r.get("type"):
            rows.append(f'<div class="restype"><span class="pill">{_html.escape(r["type"])}</span></div>')
        title = _html.escape(r.get("title", ""))
        if r.get("url"):
            title = f'<a href="{_html.escape(_norm_url(r["url"]))}">{title}</a>'
        rows.append(f'<div class="rtitle">{title}</div>')
        if r.get("source"):
            rows.append(f'<div class="rsource">{_html.escape(r["source"])}</div>')
        if r.get("why"):
            rows.append(f'<div class="rwhy">{_BOLD_RE.sub(r"<strong>\1</strong>", _html.escape(r["why"]))}</div>')
    icon = _icon_svg("widen")
    return (f'<div class="kicker">{icon}Pour aller plus loin</div>\n'
            f'<div class="subcard reslist">{"".join(rows)}</div>\n')


def _gofurther_email(items: list, s: dict, t: dict) -> str:
    """Email « Pour aller plus loin » — label + one surface card, verbatim 6221e68
    resource layout (type pill on top, title, source, why), divider between."""
    if not items:
        return ""
    rows = []
    for i, r in enumerate(items):
        if i:
            rows.append(f'<hr style="{s["divider"]}">')
        if r.get("type"):
            rows.append('<div style="padding-bottom:9px;"><span style="display:inline-block;'
                        'font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;'
                        f'color:#1a1400;background-color:{t["accent"]};padding:3px 9px;border-radius:4px;">'
                        f'{_html.escape(r["type"])}</span></div>')
        title = _html.escape(r.get("title", ""))
        if r.get("url"):
            title = (f'<a href="{_html.escape(_norm_url(r["url"]))}" '
                     f'style="color:{t["heading"]};text-decoration:underline;">{title}</a>')
        rows.append(f'<div style="font-size:18px;font-weight:800;color:{t["heading"]};line-height:1.3;">{title}</div>')
        if r.get("source"):
            rows.append(f'<div style="font-size:13px;color:{t["muted"]};text-transform:uppercase;'
                        f'letter-spacing:0.08em;padding-top:4px;">{_html.escape(r["source"])}</div>')
        if r.get("why"):
            why = _BOLD_RE.sub(rf'<strong style="color:{t["accent_text"]};font-weight:700;">\1</strong>',
                               _html.escape(r["why"]))
            rows.append(f'<div style="font-size:16px;color:{t["text"]};line-height:1.55;padding-top:10px;">{why}</div>')
    label = f'<div style="{s["card_label"]}">📚&nbsp;&nbsp;Pour aller plus loin</div>'
    card = f'<div style="{s["card"]}"><div style="{s["card_pad"]}">{"".join(rows)}</div></div>'
    return label + card


def render_body_html(body_md: str, go_further: list | None = None) -> str:
    renderer = _RichBody()
    md = mistune.create_markdown(renderer=renderer)
    out = []
    for forced, chunk in segment(body_md):
        if forced == "gofurther":   # structured resource cards (from front-matter)
            out.append(_gofurther_rich(go_further or []))
        elif forced == "card":   # each beat in its own sub-card
            renderer.forced = None
            out.append(f'<div class="subcard">\n{md(chunk)}</div>\n')
        else:
            renderer.forced = forced
            out.append(md(chunk))
    renderer.forced = None
    return "".join(out)


# The four acts, in order — the email renders each `##` act as a gold progress
# band listing all four with the active one highlighted, mirroring the 6221e68
# pillar band. Emoji echo the original email's card icons.
_ACTS = ["Pourquoi cet article", "Avant de vous lancer",
         "Au fil de la lecture", "Après la lecture"]
_ACT_EMOJI = {
    "Pourquoi cet article": "🔥", "Avant de vous lancer": "🧭",
    "Au fil de la lecture": "📖", "Après la lecture": "🧠",
}
# subsection (`###`) title → card emoji (6221e68 emoji where the section existed,
# sensible additions for the 4-act subsections).
EMOJI_BY_TITLE = {
    "Le contexte": "🌍", "Comment le lire": "👓", "Les faits à garder en tête": "📌",
    "Le lexique": "📖", "L'architecture de l'argument": "🧭",
    "À retenir": "🛍", "Les réflexes critiques": "💡", "Les enjeux de fond": "🤔",
    "Les objections les plus solides": "🛡️", "Angles morts": "⚠️", "Nuances": "⚖️",
    "Les questions à se poser": "❓", "À qui profite ce cadrage ?": "🎯",
    "Pour aller plus loin": "📚", "Avant de partir": "📣",
}


def _email_styles(t: dict) -> dict:
    """Inline style strings keyed by role, resolved for an EMAIL_THEMES entry `t`."""
    return {
        "p": f"font-size:17px;line-height:1.62;color:{t['text']};margin:0 0 12px;",
        "intro": f"font-size:19px;line-height:1.62;color:{t['text']};margin:0;",
        "subtitle": f"font-size:20px;font-style:italic;line-height:1.4;color:{t['heading']};margin:0 0 14px;",
        "clue": f"font-size:15px;font-style:italic;color:{t['muted']};margin-top:8px;",
        "answer": f"font-size:17px;line-height:1.55;color:{t['text']};margin:10px 0 0;",
        "card_label": f"margin:26px 32px 4px;font-size:15px;font-weight:800;letter-spacing:0.13em;"
                      f"text-transform:uppercase;color:{t['accent_text']};",
        "row": f"font-size:17px;line-height:1.55;color:{t['text']};margin:0 0 10px;",
        "mark_gold": f"color:{t['accent_text']};font-weight:900;",
        "mark_salmon": "color:#e8a07a;font-weight:900;",
        # quotes sit inside surface cards, so no nested box — border-left only.
        "quote": f"border-left:3px solid {t['accent']};padding:2px 0 2px 18px;"
                 f"font-style:italic;color:{t['text']};margin:14px 0;",
        "divider": f"border:0;border-top:2px solid {t['accent']};margin:24px 0;",
        "n": f"color:{t['accent_text']};font-weight:900;",
        # lead intro (before the first act band) + section cards + act band
        "intro_wrap": "padding:30px 32px 0;",
        "card": f"margin:16px 32px 0;background:{t['surface']};border-radius:12px;",
        "card_pad": "padding:28px 30px;",
        "card_head": f"font-size:15px;font-weight:800;letter-spacing:0.13em;"
                     f"text-transform:uppercase;color:{t['accent_text']};padding-bottom:16px;",
        "banner": f"background:{t['accent']};background-image:linear-gradient(135deg,"
                  f"#e6c04a 0%,#d4aa00 55%,#c09800 100%);padding:22px 32px;margin-top:44px;",
        "banner_on": "font-size:22px;font-weight:900;letter-spacing:-0.01em;"
                     "line-height:1.3;color:#1a1400;padding:5px 0;",
        "banner_chip": "display:inline-block;background-color:#1a1400;border-radius:8px;"
                       "padding:4px 9px;vertical-align:middle;",
        "banner_off": "font-size:14px;font-weight:700;line-height:1.35;color:#3d3100;padding:5px 0;",
    }


class _EmailBody(HTMLRenderer):
    """Card-based email renderer echoing the 6221e68 layout: each `##` act is a
    gold band listing all four acts (active one highlighted), each `###`
    subsection a rounded surface card with an emoji+title header; content before
    the first act is the lead intro. Rebuilt from the edited markdown."""

    def __init__(self, s: dict, t: dict) -> None:
        super().__init__()
        self.s, self.t = s, t
        self.section = ""
        self.forced: str | None = None
        self._seen_act = False
        self._card_open = False

    # --- card / band chrome ---
    def close_card(self) -> str:
        if self._card_open:
            self._card_open = False
            return "</div></div>\n"
        return ""

    def _open_card(self, title: str = "") -> str:
        self._card_open = True
        head = ""
        if title:
            emoji = EMOJI_BY_TITLE.get(title, "")
            chip = f'<span style="font-size:17px;">{emoji}</span>&nbsp;&nbsp;' if emoji else ""
            head = f'<div style="{self.s["card_head"]}">{chip}{title}</div>'
        return f'<div style="{self.s["card"]}"><div style="{self.s["card_pad"]}">{head}'

    def _band(self, active: str) -> str:
        rows = []
        for name in _ACTS:
            if name == active:
                emoji = _ACT_EMOJI.get(name, "")
                rows.append(
                    f'<div style="{self.s["banner_on"]}"><span style="{self.s["banner_chip"]}">'
                    f'<span style="font-size:20px;line-height:1;">{emoji}</span></span>'
                    f'&nbsp;&nbsp;{name}</div>')
            else:
                rows.append(f'<div style="{self.s["banner_off"]}">{name}</div>')
        return f'<div style="{self.s["banner"]}">{"".join(rows)}</div>\n'

    def _content(self, html: str) -> str:
        """Route a content block: into the open card, into a fresh untitled card
        (act with direct content), or into the lead-intro region (pre-act)."""
        if self._card_open:
            return html
        if self._seen_act:
            return self._open_card() + html
        return f'<div style="{self.s["intro_wrap"]}">{html}</div>\n'

    # --- block renderers ---
    def heading(self, text: str, level: int, **attrs) -> str:
        title, _ = _heading_meta(text)
        self.section = title
        if level <= 2:
            out = self.close_card() + self._band(title)
            self._seen_act = True
            return out
        if title in CARD_LIST_SECTIONS:
            # heading is a plain label; each item becomes its own sub-card (no nesting)
            emoji = EMOJI_BY_TITLE.get(title, "")
            chip = f'<span style="font-size:17px;">{emoji}</span>&nbsp;&nbsp;' if emoji else ""
            return self.close_card() + f'<div style="{self.s["card_label"]}">{chip}{title}</div>\n'
        return self.close_card() + self._open_card(title)

    def list_item(self, text: str) -> str:
        # strip <p> tags (loose lists wrap item content in <p>…</p>) so
        # re-wrapping in <div>/<span> doesn't nest a block element inline.
        return re.sub(r"</?p>", "", text).strip() + "\x00"

    def list(self, text: str, ordered: bool, **attrs) -> str:
        items = [t for t in text.split("\x00") if t]
        if ordered:
            html = "".join(
                f'<div style="{self.s["row"]}"><span style="{self.s["n"]}">{i}.</span> {it}</div>'
                for i, it in enumerate(items, 1))
            return self._content(html)
        style = self.forced or LIST_STYLE.get(self.section, "plain")
        if style == "box":
            html = "".join(
                f'<div style="{self.s["row"]}"><span style="{self.s["mark_gold"]}">›</span> {it}</div>'
                for it in items)
            return self._content(html)
        html = "".join(
            f'<div style="{self.s["row"]}"><span style="{self.s["mark_gold"]}">›</span> {it}</div>'
            for it in items)
        return self._content(html)

    def block_quote(self, text: str) -> str:
        inner = re.sub(r"</?p[^>]*>", "", text).strip()
        return self._content(f'<div style="{self.s["quote"]}">{inner}</div>')

    def paragraph(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("→"):   # beat answer — gold arrow, no "Réponse" label
            return self._content(
                f'<div style="{self.s["answer"]}"><span style="{self.s["mark_gold"]}">›</span> '
                f'{stripped[1:].strip()}</div>')
        if stripped.startswith("↩"):
            return self._content(f'<div style="{self.s["clue"]}">↩ {stripped[1:].strip()}</div>')
        if stripped.startswith("<em>") and stripped.endswith("</em>"):
            return self._content(f'<div style="{self.s["subtitle"]}">{stripped[4:-5]}</div>')
        role = "intro" if not self._seen_act else "p"
        return self._content(f'<p style="{self.s[role]}">{stripped}</p>')

    def thematic_break(self) -> str:
        return self._content(f'<hr style="{self.s["divider"]}">')

    def strong(self, text: str) -> str:
        return f'<strong style="color:{self.t["accent_text"]};font-weight:700;">{text}</strong>'


def render_email_body_html(body_md: str, theme: str, go_further: list | None = None) -> str:
    from renderer.newsletter.renderer import EMAIL_THEMES
    t = EMAIL_THEMES[theme]
    renderer = _EmailBody(_email_styles(t), t)
    md = mistune.create_markdown(renderer=renderer)
    out = []
    for forced, chunk in segment(body_md):
        if forced == "gofurther":   # structured resource cards (from front-matter)
            out.append(renderer.close_card() + _gofurther_email(go_further or [], renderer.s, renderer.t))
        elif forced == "card":   # each beat in its own surface sub-card
            renderer.forced = None
            out.append(renderer.close_card() + renderer._open_card() + md(chunk) + renderer.close_card())
        else:
            renderer.forced = forced
            out.append(md(chunk))
    renderer.forced = None
    out.append(renderer.close_card())  # close the final card
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
    ctx["body"] = render_body_html(body_md, fm.get("go_further"))
    return _env().get_template("newsletter.html").render(logo=_LOGO_DATA_URL, **ctx)


def render_email_html(md_text: str, theme: str = "light") -> str:
    from renderer.newsletter.renderer import _env, _EMAIL_LOGO, EMAIL_THEMES
    from renderer.categories import pill
    fm, body_md = parse_source(md_text)
    ctx = _shell_ctx(fm)
    ctx["cat_pill"] = pill(fm.get("category"), theme)
    ctx["body"] = render_email_body_html(body_md, theme, fm.get("go_further"))
    return _env().get_template("newsletter.email.html").render(
        logo=_EMAIL_LOGO, t=EMAIL_THEMES[theme], **ctx)
