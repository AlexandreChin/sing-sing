# Carousel Cover Variation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each regular carousel's slide-1 cover visibly different from the next — a per-carousel procedural line-art background plus a per-category corner glyph — while staying strictly on the graphical charter.

**Architecture:** A new pure `procart.py` deterministically generates gold line-art (style chosen + seeded from the article title). A shared `cover_layers()` helper in `_shared.py` assembles the hook's new context (`rubrique`, `glyph`, `art_svg`). `01_hook.html` is rewritten to a left-aligned composition rendering two background layers. Both carousel renderers (`optimized.py`, `optimized_short.py`) feed the hook via `cover_layers()`.

**Tech Stack:** Python 3.14, Jinja2 templates, Playwright (screenshotting, unchanged), pytest, `uv`.

## Global Constraints

- **Package manager:** `uv` only — never `pip install`. Run tests with `uv run pytest`.
- **Graphical charter:** background black; type/artwork **only** white, gold `#d4aa00`, or light-grey. **No per-category colour** in the cover artwork.
- **Slide canvas:** 1080×1350 px.
- **`procart.py` is pure:** stdlib only (`hashlib`, `random`, `math`); no API, no I/O, no wall-clock/global-random. Determinism comes from `random.Random` seeded via `hashlib.sha256`.
- **Shared template:** `01_hook.html` is used by *both* `instagram_carousel_optimized` and `instagram_carousel_optimized_short`; changes affect both.
- **Hook-specific CSS lives inline** in `01_hook.html` (matching the existing pattern in that file), not in `base.css` — `base.css` stays untouched.
- **Category taxonomy source of truth:** `renderer/categories.py` (`CATEGORY_ICONS`), keys exclude `"Autre"`.

---

### Task 1: `procart.py` — deterministic procedural art module

**Files:**
- Create: `renderer/instagram_carousel/procart.py`
- Test: `tests/test_procart.py`

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces:
  - `constellation(seed_text: str) -> str`, `contours(seed_text: str) -> str`, `orbits(seed_text: str) -> str` — each returns inline SVG **inner** markup for a `1080x1350` viewBox (no colour/opacity attrs).
  - `STYLES: dict[str, callable]` — registry (`{"constellation":…, "contours":…, "orbits":…}`).
  - `pick_style(seed_text: str) -> str` — deterministic style key for a seed.
  - `cover_art(seed_text: str) -> str` — inner markup of the picked style for that seed.

- [ ] **Step 1: Write the failing test**

Create `tests/test_procart.py`:

```python
import xml.etree.ElementTree as ET

from renderer.instagram_carousel.procart import (
    STYLES, constellation, contours, orbits, pick_style, cover_art,
)


def _wellformed(markup: str) -> bool:
    # inner markup must be parseable once wrapped in an <svg> root
    ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{markup}</svg>')
    return True


def test_registry_has_the_three_styles():
    assert set(STYLES) == {"constellation", "contours", "orbits"}
    assert all(callable(fn) for fn in STYLES.values())


def test_each_style_returns_wellformed_nonempty_markup():
    for fn in (constellation, contours, orbits):
        m = fn("seed")
        assert m and _wellformed(m)


def test_cover_art_is_deterministic():
    assert cover_art("Réforme des retraites") == cover_art("Réforme des retraites")
    assert pick_style("Réforme des retraites") == pick_style("Réforme des retraites")


def test_different_seeds_produce_different_art():
    assert cover_art("Article A") != cover_art("Article B")


def test_pick_style_covers_all_styles_over_many_seeds():
    seen = {pick_style(f"title-{i}") for i in range(300)}
    assert seen == set(STYLES)


def test_cover_art_matches_picked_style():
    seed = "Un titre quelconque"
    assert cover_art(seed) == STYLES[pick_style(seed)](seed)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_procart.py -v`
Expected: FAIL — `ModuleNotFoundError: renderer.instagram_carousel.procart`.

- [ ] **Step 3: Write the implementation**

Create `renderer/instagram_carousel/procart.py`:

```python
"""Deterministic 'naive' vector-art generator for carousel covers.

Every style returns inline SVG *inner* markup sized to a 1080x1350 viewBox, so it
drops straight into a full-bleed background <svg>. No colour/opacity is set here —
the template owns stroke + opacity. Same seed_text -> same art (reproducible);
`cover_art` also picks the *style* deterministically from the seed.
"""
import hashlib
import math
from random import Random

W, H = 1080, 1350


def _seed(seed_text: str) -> Random:
    h = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16)
    return Random(h)


def constellation(seed_text: str) -> str:
    """A node/edge graph — echoes the product's own node-graph analysis."""
    r = _seed(seed_text)
    n = r.randint(11, 16)
    cols, rows = 4, 5
    pts = []
    for i in range(n):
        cx = (i % cols + 0.5) / cols * W + r.uniform(-90, 90)
        cy = (i // cols + 0.5) / rows * H + r.uniform(-90, 90)
        pts.append((cx, cy))
    parts = []
    for i, (x1, y1) in enumerate(pts):
        near = sorted(range(len(pts)), key=lambda j: (pts[j][0] - x1) ** 2 + (pts[j][1] - y1) ** 2)
        for j in near[1:1 + r.randint(1, 2)]:
            x2, y2 = pts[j]
            parts.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}"/>')
    for (x, y) in pts:
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.randint(6, 16)}"/>')
    return "".join(parts)


def contours(seed_text: str) -> str:
    """Stacked topographic / sound-wave lines."""
    r = _seed(seed_text)
    lines = r.randint(7, 10)
    amp = r.uniform(60, 120)
    parts = []
    for k in range(lines):
        base = (k + 0.5) / lines * H
        phase = r.uniform(0, math.tau)
        freq = r.uniform(1.4, 2.6)
        pts = []
        for sx in range(0, W + 1, 40):
            t = sx / W
            y = base + amp * math.sin(t * math.tau * freq + phase) * (0.5 + 0.5 * math.sin(t * math.pi))
            pts.append(f"{sx},{y:.0f}")
        parts.append(f'<polyline points="{" ".join(pts)}"/>')
    return "".join(parts)


def orbits(seed_text: str) -> str:
    """Concentric rotated ellipses with bodies sitting on them."""
    r = _seed(seed_text)
    cx, cy = W * r.uniform(0.4, 0.62), H * r.uniform(0.42, 0.6)
    rings = r.randint(3, 5)
    parts = []
    for k in range(rings):
        rx = (k + 1) / rings * r.uniform(360, 520)
        ry = rx * r.uniform(0.55, 0.9)
        rot = r.uniform(0, 180)
        parts.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" '
                     f'transform="rotate({rot:.0f} {cx:.0f} {cy:.0f})"/>')
        ang = r.uniform(0, math.tau)
        bx = cx + rx * math.cos(ang) * math.cos(math.radians(rot)) - ry * math.sin(ang) * math.sin(math.radians(rot))
        by = cy + rx * math.cos(ang) * math.sin(math.radians(rot)) + ry * math.sin(ang) * math.cos(math.radians(rot))
        parts.append(f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="{r.randint(10, 22)}"/>')
    parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r.randint(20, 34)}"/>')
    return "".join(parts)


STYLES = {"constellation": constellation, "contours": contours, "orbits": orbits}


def pick_style(seed_text: str) -> str:
    """Deterministically choose a style key from the seed (sorted keys = stable)."""
    keys = sorted(STYLES)
    idx = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16) % len(keys)
    return keys[idx]


def cover_art(seed_text: str) -> str:
    """Inner SVG markup of the seed-picked style for this seed."""
    return STYLES[pick_style(seed_text)](seed_text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_procart.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add renderer/instagram_carousel/procart.py tests/test_procart.py
git commit -m "feat(carousel): deterministic procedural cover-art generator"
```

---

### Task 2: `cover_layers()` helper in `_shared.py`

**Files:**
- Modify: `renderer/instagram_carousel/_shared.py`
- Test: `tests/test_cover_layers.py`

**Interfaces:**
- Consumes: `cover_art` (Task 1); `CATEGORY_ICONS` from `renderer.categories`; `ArticleMetadata` (`.title`, `.category`).
- Produces: `cover_layers(meta, headline: str) -> dict` with keys `rubrique` (`str | None`), `glyph` (`str`, inner SVG or `""`), `art_svg` (`str`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_cover_layers.py`:

```python
from models.full_analysis import ArticleMetadata
from renderer.categories import CATEGORY_ICONS
from renderer.instagram_carousel._shared import cover_layers
from renderer.instagram_carousel.procart import cover_art


def test_known_category_yields_tab_and_glyph_and_art():
    meta = ArticleMetadata(title="Titre", category="Tech")
    out = cover_layers(meta, "fallback")
    assert out["rubrique"] == "Tech"
    assert out["glyph"] == CATEGORY_ICONS["Tech"]
    assert out["art_svg"]


def test_autre_and_missing_drop_rubrique_and_glyph():
    for cat in ("Autre", None):
        out = cover_layers(ArticleMetadata(title="T", category=cat), "fallback")
        assert out["rubrique"] is None
        assert out["glyph"] == ""
        assert out["art_svg"]  # art still present


def test_seed_uses_title_then_falls_back_to_headline():
    with_title = cover_layers(ArticleMetadata(title="Le vrai titre", category="Tech"), "HL")
    assert with_title["art_svg"] == cover_art("Le vrai titre")
    no_title = cover_layers(ArticleMetadata(title=None, category="Tech"), "La retombée")
    assert no_title["art_svg"] == cover_art("La retombée")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cover_layers.py -v`
Expected: FAIL — `ImportError: cannot import name 'cover_layers'`.

- [ ] **Step 3: Write the implementation**

In `renderer/instagram_carousel/_shared.py`, add imports near the top (after the existing imports):

```python
from renderer.categories import CATEGORY_ICONS
from renderer.instagram_carousel.procart import cover_art
```

Then append this function to the module:

```python
def cover_layers(meta, headline: str) -> dict:
    """Hook slide-1 background context, shared by both carousel renderers.

    `rubrique`/`glyph` carry category identity (dropped for "Autre"/missing,
    mirroring `pill()==None`); `art_svg` is the per-carousel procedural art,
    seeded from the article title (headline as fallback for a title-less article).
    """
    glyph = CATEGORY_ICONS.get(meta.category or "", "")
    seed = (meta.title or "").strip() or (headline or "")
    return {
        "rubrique": meta.category if glyph else None,
        "glyph": glyph,
        "art_svg": cover_art(seed),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cover_layers.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add renderer/instagram_carousel/_shared.py tests/test_cover_layers.py
git commit -m "feat(carousel): cover_layers() helper for hook slide background"
```

---

### Task 3: Rewrite `01_hook.html` — left-aligned composition + two background layers

**Files:**
- Modify (full rewrite): `renderer/instagram_carousel/templates/article_carousel_optimized_v0/01_hook.html`
- Test: `tests/test_hook_template.py`

**Interfaces:**
- Consumes (template context): `rubrique` (`str | None`), `glyph` (`str`), `art_svg` (`str`), `article_title`, `source_meta`, `headline`, `slide_n`, `slide_total`, `progress`, `logo`. The `headline` runs through the `md_bold` filter (registered by `_env`).
- Produces: rendered hook HTML with `<div class="artbg">` always present, `<div class="giant">` only when `glyph` truthy, `<div class="rubrique-tab">` only when `rubrique` truthy. No `cat-pill`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_hook_template.py`:

```python
from renderer.categories import CATEGORY_ICONS
from renderer.instagram_carousel._shared import _env

TPL = "article_carousel_optimized_v0/01_hook.html"


def _render(**over):
    ctx = dict(
        slide_n=1, slide_total=10, progress=10, logo="",
        article_title="Titre de l'article", source_meta="LE MONDE · 2026",
        headline="Un **mot** en gras", rubrique="Tech",
        glyph=CATEGORY_ICONS["Tech"], art_svg='<line x1="0" y1="0" x2="10" y2="10"/>',
    )
    ctx.update(over)
    return _env().get_template(TPL).render(**ctx)


def test_hook_renders_layers_rubrique_and_headline():
    html = _render()
    assert '<div class="artbg">' in html
    assert '<div class="giant">' in html
    assert '<div class="rubrique-tab">' in html
    assert "Tech" in html
    assert "Titre de l'article" in html
    assert "<strong>mot</strong>" in html          # md_bold applied
    assert "cat-pill" not in html                   # old coloured pill gone
    assert 'x1="0" y1="0" x2="10" y2="10"' in html  # art_svg injected


def test_hook_drops_category_elements_when_absent():
    html = _render(rubrique=None, glyph="")
    assert '<div class="rubrique-tab">' not in html
    assert '<div class="giant">' not in html
    assert '<div class="artbg">' in html            # art still present
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_hook_template.py -v`
Expected: FAIL — the current hook has no `artbg`/`giant`/`rubrique-tab` and still renders `cat-pill`.

- [ ] **Step 3: Write the implementation**

Replace the entire contents of `renderer/instagram_carousel/templates/article_carousel_optimized_v0/01_hook.html` with:

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
{% include 'base.css' %}
.eyebrow { font-size: 26px; font-weight: 800; letter-spacing: .20em; text-transform: uppercase; color: #888; }
.art-title { font-size: 34px; font-weight: 700; font-style: italic; line-height: 1.3; color: #d0d0d0; max-width: 760px; margin-top: 10px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.art-meta { font-size: 21px; font-weight: 600; letter-spacing: .10em; text-transform: uppercase; color: #888; margin-top: 12px; }
.cover-head { font-size: 78px; font-weight: 900; line-height: 1.05; letter-spacing: -0.02em; color: #f0f0f0; max-width: 840px; margin-top: 28px; text-wrap: balance; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.cover-head strong { color: #d4aa00; font-weight: 900; }
.rubrique-tab { display: inline-flex; align-items: center; gap: 14px; font-size: 28px; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; color: #d4aa00; }
.rubrique-tab svg { width: 40px; height: 40px; stroke: #d4aa00; fill: none; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.swipe { position: absolute; bottom: 120px; left: 90px; right: 90px; font-size: 27px; font-weight: 700; color: #aaa; letter-spacing: .04em; }
.sw-sep { color: #d4aa00; font-weight: 800; }
/* layer 1: faint per-carousel procedural art */
.artbg { position: absolute; inset: 0; z-index: -2; }
.artbg svg { width: 100%; height: 100%; stroke: #d4aa00; stroke-opacity: .11; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.artbg svg circle, .artbg svg ellipse { fill: none; }
/* layer 2: big per-category glyph, corner-bleed */
.giant { position: absolute; right: -220px; bottom: -200px; width: 1000px; height: 1000px; z-index: -1; }
.giant svg { width: 100%; height: 100%; stroke: #d4aa00; stroke-opacity: .17; fill: none; stroke-width: .7; stroke-linecap: round; stroke-linejoin: round; }
</style>
</head>
<body>
<div class="slide" style="justify-content: flex-start; text-align: left; padding-top: 220px;">
  <div class="artbg"><svg viewBox="0 0 1080 1350" preserveAspectRatio="xMidYMid slice">{{ art_svg | safe }}</svg></div>
  {% if glyph %}<div class="giant"><svg viewBox="0 0 24 24">{{ glyph | safe }}</svg></div>{% endif %}
  {% include '_brand.html' %}

  {% if rubrique %}<div class="rubrique-tab"><svg viewBox="0 0 24 24">{{ glyph | safe }}</svg>{{ rubrique }}</div>{% endif %}

  {% if article_title %}<span class="eyebrow" style="margin-top:34px;">— L'article —</span>
  <p class="art-title">{{ article_title }}</p>{% endif %}
  {% if source_meta %}<p class="art-meta">{{ source_meta }}</p>{% endif %}

  <h1 class="cover-head">{{ headline | md_bold }}</h1>

  <div class="swipe">Avant de lire <span class="sw-sep">&#8250;</span> Le décryptage <span class="sw-sep">&#8250;</span> Verdict</div>
  <div class="slide-num">{{ slide_n }} / {{ slide_total }}</div>
  <div class="progress-track"><div class="progress-bar" style="width: {{ progress }}%;"></div></div>
</div>
</body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_hook_template.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add renderer/instagram_carousel/templates/article_carousel_optimized_v0/01_hook.html tests/test_hook_template.py
git commit -m "feat(carousel): left-aligned hook cover with art + glyph layers"
```

---

### Task 4: Wire `cover_layers()` into both renderers

**Files:**
- Modify: `renderer/instagram_carousel/optimized.py:169-170` (hook spec + imports)
- Modify: `renderer/instagram_carousel/optimized_short.py:48-49` (hook spec + imports)
- Test: `tests/test_hook_wiring.py`

**Interfaces:**
- Consumes: `cover_layers` (Task 2), rewritten `01_hook.html` (Task 3).
- Produces: both renderers pass `**cover_layers(meta, pres.hook.headline)` into the `01_hook` context and no longer pass `cat_pill`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_hook_wiring.py` (verifies the exact seam both renderers use: real `cover_layers` output rendered through the real hook template):

```python
from models.full_analysis import ArticleMetadata
from renderer.instagram_carousel._shared import _env, cover_layers

TPL = "article_carousel_optimized_v0/01_hook.html"


def test_cover_layers_output_renders_in_hook():
    meta = ArticleMetadata(title="Réforme des retraites", category="Politique")
    layers = cover_layers(meta, "Fallback headline")
    html = _env().get_template(TPL).render(
        slide_n=1, slide_total=10, progress=10, logo="",
        article_title="Réforme des retraites", source_meta="LE MONDE",
        headline="Un **texte** technique", **layers,
    )
    assert "Politique" in html
    assert '<div class="artbg">' in html
    assert '<div class="giant">' in html
    assert "cat-pill" not in html


def test_renderers_no_longer_pass_cat_pill():
    # guard against a half-done wiring edit
    import renderer.instagram_carousel.optimized as opt
    import renderer.instagram_carousel.optimized_short as short
    import inspect
    for mod in (opt, short):
        src = inspect.getsource(mod.generate_html)
        assert "cat_pill" not in src
        assert "cover_layers(" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_hook_wiring.py -v`
Expected: FAIL — `test_renderers_no_longer_pass_cat_pill` fails because both renderers still pass `cat_pill` and don't call `cover_layers`.

- [ ] **Step 3: Edit `optimized.py`**

Change the import on line 12 from:

```python
from renderer.categories import pill, carousel_theme
```

to (drop `pill` — it becomes unused; add `cover_layers` to the `._shared` import group on lines 13-16):

```python
from renderer.categories import carousel_theme
```

Add `cover_layers` to the existing `from ._shared import (...)` block, e.g.:

```python
from ._shared import (
    _env, _LOGO_DATA_URL,
    _weighted_quality, TYPE_FR, cover_layers,
)
```

Replace the `01_hook` spec (lines 169-170):

```python
        ("01_hook", {"article_title": (meta.title or "").strip(), "source_meta": source_meta,
                     "cat_pill": pill(meta.category), "headline": pres.hook.headline}),
```

with:

```python
        ("01_hook", {"article_title": (meta.title or "").strip(), "source_meta": source_meta,
                     "headline": pres.hook.headline, **cover_layers(meta, pres.hook.headline)}),
```

- [ ] **Step 4: Edit `optimized_short.py`**

On line 15, drop `pill` from the import (verify no other `pill(` usage remains in the file first: `grep -n "pill(" renderer/instagram_carousel/optimized_short.py` — expect only the hook line):

```python
from renderer.categories import carousel_theme
```

Add `cover_layers` to its `from ._shared import (...)` block. Then replace the `01_hook` spec (lines 48-49):

```python
        ("01_hook", "01_hook", {"article_title": (meta.title or "").strip(),
                                "source_meta": source_meta, "cat_pill": pill(meta.category),
```

with (keep the rest of that dict/tuple intact — only swap `cat_pill` for the spread):

```python
        ("01_hook", "01_hook", {"article_title": (meta.title or "").strip(),
                                "source_meta": source_meta,
                                **cover_layers(meta, pres.hook.headline),
```

Note: confirm `pres` is in scope in `optimized_short.generate_html` (it defines `full, pres = doc.analysis, doc.presentation` like `optimized.py`); if the variable is named differently, use the local presentation variable.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_hook_wiring.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Run the full suite (no regressions)**

Run: `uv run pytest -q`
Expected: PASS — all tests green (existing + the four new files).

- [ ] **Step 7: Manual visual smoke-test (real PNGs)**

Write `/tmp/cover_smoke.py`:

```python
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from renderer.categories import CATEGORY_ICONS, carousel_theme
from renderer.instagram_carousel._shared import TEMPLATES_DIR, _md_bold, _LOGO_DATA_URL, cover_layers
from renderer.instagram_carousel.procart import cover_art
from renderer.shoot import shoot_dir
from models.full_analysis import ArticleMetadata

env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
env.filters["md_bold"] = _md_bold
out = Path("/tmp/cover_smoke"); ready = out / "html"; ready.mkdir(parents=True, exist_ok=True)

CASES = [
    ("Politique", "Réforme des retraites : ce que change le nouveau texte", "Un texte **technique**, un choix **politique**"),
    ("Tech", "OpenAI dévoile un nouveau modèle", "Une avancée **réelle**, un marketing **emballé**"),
    ("Écologie", "Sécheresse : les nappes au plus bas", "Un constat **solide**, des solutions **survolées**"),
]
for cat, title, head in CASES:
    meta = ArticleMetadata(title=title, category=cat)
    ctx = dict(slide_n=1, slide_total=10, progress=10, logo=_LOGO_DATA_URL,
               article_title=title, source_meta="SOURCE · 2026", headline=head,
               **carousel_theme(cat), **cover_layers(meta, head))
    (ready / f"{cat}.html").write_text(env.get_template("article_carousel_optimized_v0/01_hook.html").render(**ctx), encoding="utf-8")
shoot_dir(ready, out / "png")
print("open", out / "png")
```

Run: `uv run python /tmp/cover_smoke.py`
Expected: three PNGs in `/tmp/cover_smoke/png`. Open them and confirm: (a) each category looks different, (b) headline legible over the art, (c) only black/gold/white/grey appears, (d) the corner glyph matches the category and the constellation/contours/orbits texture is faint.

- [ ] **Step 8: Commit**

```bash
git add renderer/instagram_carousel/optimized.py renderer/instagram_carousel/optimized_short.py tests/test_hook_wiring.py
git commit -m "feat(carousel): feed hook cover via cover_layers in both formats"
```

---

## Self-Review

**Spec coverage:**
- Layer 1 procedural art (multi-style, seeded) → Task 1. ✅
- Layer 2 category glyph + rubrique tab + fallback → Tasks 2 & 3. ✅
- Left-aligned hook redesign, drop zigzag/"Notre analyse"/coloured pill → Task 3. ✅
- Wire both formats, share `01_hook.html` → Task 4. ✅
- Determinism / style-distribution / fallback / visual tests → Tasks 1, 2, 3, 4 (Step 7). ✅
- Hook CSS inline (base.css untouched) → recorded in Global Constraints + Task 3 (deliberate deviation from the spec's "add to base.css", following the file's existing inline-style pattern; `base.css` is not modified). ✅
- Hors-série cover → intentionally NOT built (spec "reserved"/out-of-scope); no task, by design. ✅

**Placeholder scan:** No TBD/TODO; every code step shows full code; every run step shows an exact command + expected result.

**Type consistency:** `cover_art(seed_text: str) -> str`, `pick_style(seed_text) -> str`, `STYLES` dict, and `cover_layers(meta, headline) -> {rubrique, glyph, art_svg}` are used identically across Tasks 1→2→3→4. Template context keys (`artbg`/`giant`/`rubrique-tab`, `art_svg`, `glyph`, `rubrique`) match between Task 3's template and Task 4's render call.
