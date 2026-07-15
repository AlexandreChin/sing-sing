"""Category (rubrique) → pill colours, shared by the newsletter and carousel
renderers so a rubrique looks identical on every surface. The taxonomy itself
is the source of truth on `ArticleMetadata.category` (models/full_analysis.py);
`Autre` is intentionally absent here so it resolves to "no pill" (see `pill`)."""

# category -> {dark_text, dark_bg, light_text, light_bg}. Dark values are for the
# rich newsletter, the carousel, and the dark email theme; light values for the
# light email theme. Each text colour clears ≥4.5:1 on its own pill background.
CATEGORY_COLORS: dict[str, dict[str, str]] = {
    "Politique":        {"dark_text": "#ef8a8a", "dark_bg": "#3a1c1c", "light_text": "#b02a2a", "light_bg": "#f7e3e3"},
    "Économie":         {"dark_text": "#e3b341", "dark_bg": "#322914", "light_text": "#8a6410", "light_bg": "#f6efd8"},
    "International":     {"dark_text": "#7fb2ef", "dark_bg": "#16283e", "light_text": "#1f5aa8", "light_bg": "#e2ecfa"},
    "Société":          {"dark_text": "#c59cf0", "dark_bg": "#2a1d3e", "light_text": "#7a3fc0", "light_bg": "#efe6fb"},
    "Écologie":         {"dark_text": "#6fca8f", "dark_bg": "#143526", "light_text": "#1f7a4d", "light_bg": "#e0f3e8"},
    "Sciences & Santé": {"dark_text": "#5cc7c7", "dark_bg": "#123232", "light_text": "#157a7a", "light_bg": "#ddf1f1"},
    "Tech":             {"dark_text": "#9a9cf0", "dark_bg": "#1e1f40", "light_text": "#4646c0", "light_bg": "#e7e7fb"},
    "Culture":          {"dark_text": "#ef92c4", "dark_bg": "#351c2b", "light_text": "#b03a7f", "light_bg": "#fae3ef"},
    "Sport":            {"dark_text": "#ef9f5c", "dark_bg": "#38230f", "light_text": "#b0561a", "light_bg": "#fbe9d8"},
}

# One monochrome line icon per rubrique, as inline-SVG inner markup. Rendered
# with stroke="currentColor", so the icon inherits the pill's text colour and
# always matches it. (Emoji can't be recoloured by CSS; hence SVG.)
CATEGORY_ICONS: dict[str, str] = {
    "Politique":        '<polygon points="12 2 20 7 4 7"/><line x1="6" x2="6" y1="7" y2="18"/><line x1="10" x2="10" y1="7" y2="18"/><line x1="14" x2="14" y1="7" y2="18"/><line x1="18" x2="18" y1="7" y2="18"/><line x1="3" x2="21" y1="21" y2="21"/>',
    "Économie":         '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "International":    '<circle cx="12" cy="12" r="10"/><path d="M12 2a15 15 0 0 0 0 20 15 15 0 0 0 0-20"/><line x1="2" x2="22" y1="12" y2="12"/>',
    "Société":          '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "Écologie":         '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/><path d="M2 21c0-3 1.9-5.4 5.1-6C9.5 14.5 12 13 13 12"/>',
    "Sciences & Santé": '<path d="M9 2h6"/><path d="M10 2v6.3L4.6 18a2 2 0 0 0 1.7 3h11.4a2 2 0 0 0 1.7-3L14 8.3V2"/><path d="M6.5 15h11"/>',
    "Tech":             '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M20 9h2M20 15h2M2 9h2M2 15h2"/>',
    "Culture":          '<circle cx="13.5" cy="6.5" r=".8" fill="currentColor" stroke="none"/><circle cx="17.5" cy="10.5" r=".8" fill="currentColor" stroke="none"/><circle cx="8.5" cy="7.5" r=".8" fill="currentColor" stroke="none"/><circle cx="6.5" cy="12.5" r=".8" fill="currentColor" stroke="none"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.9 0 1.6-.7 1.6-1.7 0-.4-.2-.8-.4-1.1-.3-.3-.4-.6-.4-1.1a1.6 1.6 0 0 1 1.6-1.6H16c3 0 5.5-2.5 5.5-5.5C21.9 6 17.5 2 12 2Z"/>',
    "Sport":            '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.7V17c0 .6-.5 1-1 1.2C7.9 18.8 7 20.2 7 22"/><path d="M14 14.7V17c0 .6.5 1 1 1.2 1.1.6 2 2 2 4.8"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
}


def _icon_svg(inner: str) -> str:
    """Wrap an icon's inner markup as an inline SVG that scales with the pill's
    font-size and inherits its colour (stroke=currentColor)."""
    return (
        '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" style="display:inline-block;vertical-align:-0.14em">'
        f'{inner}</svg>'
    )


# Deep, dark tinted inner-radial colour for the carousel background (#1). Kept
# separate from the pill palette: these are near-black atmospheres, not chips.
CATEGORY_BG: dict[str, str] = {
    "Politique":        "#0a0404",
    "Économie":         "#080703",
    "International":    "#04060a",
    "Société":          "#07040b",
    "Écologie":         "#040805",
    "Sciences & Santé": "#040909",
    "Tech":             "#05050a",
    "Culture":          "#08050b",
    "Sport":            "#0a0703",
}


def carousel_theme(category: str | None) -> dict:
    """Per-deck carousel background theme: a deep category-tinted radial (#1)
    plus an accent-tinted grain + watermark ghost (a touch of #2). Returns {} for
    "Autre"/missing so base.css keeps today's pure-black look. Touches no gold
    element — only the (black) background, (white) grain, and (white) watermark."""
    colors = CATEGORY_COLORS.get(category or "")
    bg_in = CATEGORY_BG.get(category or "")
    if not (colors and bg_in):
        return {}
    accent = colors["dark_text"]
    return {
        "slide_bg_in": bg_in,
        "slide_bg_out": "#000000",
        "grain_tint": accent + "12",       # ~7% — accent-tinted grain
        "watermark_color": accent + "0f",  # ~6% — large faint colour ghost
    }


def pill(category: str | None, theme: str = "dark") -> dict | None:
    """Resolve a category to its pill `{label, text, bg}` for `theme` ("dark" |
    "light"). Returns None when there is nothing meaningful to show — a missing
    category or the "Autre" fallback — so templates drop the pill entirely."""
    colors = CATEGORY_COLORS.get(category or "")
    if not colors:
        return None
    inner = CATEGORY_ICONS.get(category, "")
    return {"label": category, "icon": _icon_svg(inner) if inner else "",
            "text": colors[f"{theme}_text"], "bg": colors[f"{theme}_bg"]}
