# Carousel cover variation — design

**Date:** 2026-07-16
**Status:** approved (pending spec review)

## Problem

Every carousel's slide 1 (the hook/cover) is structurally identical, so a profile
grid of Sing Sing posts reads as monotonous. We want the cover to differ visibly
from one carousel to the next while staying strictly inside the graphical charter:
**black background, white / gold (`#d4aa00`) / light-grey type only** — no
per-category colour in the artwork.

## Chosen approach — hybrid background (per-category glyph + per-carousel procedural art)

The hook cover gains two gold, non-colour background layers over the existing
category-tinted radial (`carousel_theme`), and adopts a left-aligned composition:

- **Layer 1 — procedural art** (per *carousel*): a gold line-drawing filling the
  slide at `stroke-opacity ≈ .11`, generated deterministically from the article
  title. The *style* is itself chosen deterministically from the same seed among a
  small registry — **constellation** (node/edge graph, echoing the product's own
  node-graph analysis, `tools/graph_generator.py`), **contours** (topographic
  waves), **orbits** (concentric rings) — extensible with more (e.g. waves). So two
  carousels differ both in style and in instance; same title always reproduces the
  same art.
- **Layer 2 — category glyph** (per *category*): the existing `CATEGORY_ICONS`
  glyph, blown up and bled off the bottom-right corner at `stroke-opacity ≈ .17`.
  Carries rubrique identity.

Uniqueness comes from Layer 1 (style + instance); identity from Layer 2 + the
rubrique tab + the existing background tint. No API call, no randomness — pure and
deterministic.

Rejected: model-generated SVG art (quality/cost/consistency risk); procedural-only
(no category identity); big-glyph-only (repeats within a rubrique).

## Cover composition (redesigned `01_hook.html`)

Left-aligned, top-anchored (replaces today's centered layout):

```
[rubrique tab: glyph + NAME]      (gold)        [logo]
— L'article —                                   (grey)
Article title (italic)                          (light-grey)
SOURCE · DATE                                    (grey)
BIG HEADLINE with **gold** emphasis             (white/gold)
...
Avant de lire › Le décryptage › Verdict          (grey, bottom)
```

Dropped from today's hook: the gold zigzag separator and the "— Notre analyse —"
eyebrow (their visual job is now done by the artwork). The coloured category
**pill** is replaced by a **gold rubrique tab** (glyph + name), so the cover holds
to the gold/white/grey charter.

## Components

### `renderer/instagram_carousel/procart.py` (new)
Pure, deterministic procedural-art module.
- Style functions `constellation`/`contours`/`orbits`(`seed_text: str) -> str` —
  each returns inline SVG **inner** markup (`<line>`/`<circle>`/`<polyline>`/
  `<ellipse>`), sized to a `1080x1350` viewBox, no colour/opacity set (the template
  owns stroke + opacity). Seeded via
  `Random(int(hashlib.sha256(seed_text.encode()).hexdigest(), 16))`.
- `STYLES: dict[str, callable]` — the registry; adding a style = adding one entry.
- `cover_art(seed_text: str) -> str` — selects a style deterministically
  (`sha256(seed_text) % len(STYLES)`, over a **sorted** key list for stable
  ordering) and returns that style's markup for the same seed.
- Depends on: stdlib only (`hashlib`, `random`, `math`). No API, no I/O.
- Contract: same `seed_text` → identical style + markup; different titles → a
  different-looking cover (often a different style, always a different instance).

### `renderer/instagram_carousel/_shared.py` (extend)
- `cover_layers(meta, headline: str) -> dict` — single source of the hook's new
  context, so both renderers stay in sync. Returns:
  - `rubrique`: `meta.category` or `None`
  - `glyph`: `CATEGORY_ICONS.get(meta.category)` inner markup, or `""`
  - `art_svg`: `cover_art(meta.title or headline)` (`headline` =
    `pres.hook.headline`, passed by the caller as the seed fallback for a
    title-less article)
- Fallback: missing / `Autre` category → `rubrique=None`, `glyph=""` (template
  drops the tab and the big glyph, keeping the procedural art only) — mirrors today's
  `pill()==None` / `carousel_theme()=={}` conventions.

### `renderer/instagram_carousel/templates/article_carousel_optimized_v0/01_hook.html` (rewrite)
Left-aligned composition above; two new background layers (`.artbg` full-bleed
procedural art `z-index:-2`; `.giant` corner glyph `z-index:-1`), both gold with the
opacities above. Consumes `rubrique`, `glyph`, `art_svg` alongside existing
`article_title`, `source_meta`, `headline`.

### `optimized.py` / `optimized_short.py` (edit)
In each `01_hook` context, replace `"cat_pill": pill(meta.category)` with the
`cover_layers(meta, pres.hook.headline)` dict (spread in). No other slides change. Both formats share
`01_hook.html`, so both pick up the redesign.

### `base.css` (edit)
Add the `.artbg` / `.giant` / `.rubrique-tab` rules (currently prototyped inline in
the mockups). Touches no existing rule.

## Data flow

`render → generate_html →` for slide 01: `cover_layers(meta, pres.hook.headline)`
computes `{rubrique, glyph, art_svg}` (art seeded from `meta.title`) → merged into the hook
context → Jinja renders `01_hook.html` → `shoot_dir` screenshots to PNG. Unchanged
elsewhere.

## Hors-série cover — reserved design (NOT built in this spec)

Per `content_families`, Sing Sing has two families: **regular** (article analysis,
built here) and **hors-série** (generated analysis; first instance = candidate-
program, unit = one candidate over 7 fixed domains; carousel is a teaser funnelling
to the newsletter). The hors-série teaser carousel is **sub-project 3, not yet
built** — no program carousel format / adapt agent / presentation model exists. We
therefore only *document* its cover so it lands obviously-different by design, and
add **no family abstraction to code now** (honours the YAGNI note in
`content_families`).

When sub-project 3 is built it gets its **own format** (own registry entry +
renderer/templates), like `newsletter` today — so the families diverge by having
separate covers, not a `family` flag on the regular renderer. Distinct signature,
all inside the black/gold/white/grey charter (mockup: `tmp_cover_mockups/hs_cover.png`):

- **Solid gold masthead band** (gold background, black text) reading
  `HORS-SÉRIE · PRÉSIDENTIELLE 2027`. A regular cover never has a gold-filled block,
  so the two families are unmistakable at grid scale.
- **Candidate name** is the hero (not an article headline); eyebrow "— Le programme
  de —"; a row of the 7 domain pills.
- **Newsletter funnel** line ("Le décryptage complet dans la newsletter ›") instead
  of the regular swipe hint.
- **No rubrique tab / category glyph** (hors-série has no news category).
- **Reuses `procart.py`** for the faint procedural texture (shared low-level util —
  not a family abstraction), seeded from the candidate name.

## Testing / verification

- **Unit:** `cover_art(x) == cover_art(x)` (determinism, incl. stable style pick);
  two different titles yield different markup; over many seeds every style in
  `STYLES` is selected at least once (distribution); output parses as an SVG
  fragment.
- **Fallback:** `cover_layers` with `category=None` / `"Autre"` → empty
  `rubrique`/`glyph`, non-empty `art_svg`.
- **Visual (manual):** render the hook for ≥3 categories + ≥2 titles within one
  category; confirm (a) covers differ between categories and between titles,
  (b) headline stays legible, (c) only black/gold/white/grey appears, (d) both
  `instagram_carousel_optimized` and `_short` render without layout regressions.

## Out of scope

Slides 2–10; the newsletter format; category colour palette; the short deck's
merged `decryptage.html`; any model/API change. **Building** the hors-série teaser
cover (sub-project 3) — its visual language is documented above but not implemented
here; no `family` abstraction is added to code.
