# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`sing-sing` is a Python 3.14 agent that analyzes news articles and turns the analysis into a publishable Instagram carousel. It runs a multi-step Claude analysis (via the Anthropic API, `claude-opus-4-6`), then adapts, trims, and renders the result into PNG slides.

## Commands

```bash
# Install / sync dependencies
uv add <package>
uv sync

# Full pipeline: analyze → adapt → extract → render
python main.py produce <article.txt> [--format instagram_carousel_optimized] [--no-api] [--render] [--instructions-file <path>] [--stop-after axis|selection]
python main.py produce <article.txt> --format instagram_carousel_light [--no-api] [--render]   # light version (after or instead of the full one)

# Individual stages
python main.py analyze <article.txt> [--instructions "..."] [--instructions-file <path>]
python main.py adapt   <analysis.json>   [--format <fmt>] [--no-api] [--stop-after axis|selection]
python main.py extract <analysis.json> <presentation.json> [--format <fmt>] [--render]
python main.py render  <extract.json> [<output_dir>] [--format <fmt>]

# Find source material (free-to-read French news feeds)
python main.py fetch                       # list latest candidates from every feed
python main.py fetch --list-sources        # the 13 feed slugs
python main.py fetch -s lapresse -s reporterre --limit 10
python main.py fetch <article-url>         # scrape into samples/articles/<slug>.txt

# Utilities
python main.py simplify <analysis.json>              # reduce an existing carousel
python main.py validate <analysis.json>              # node-graph integrity checks
python main.py verify   <analysis.json> [--claim N]  # find sources for/against claims
python main.py graph    <analysis.json> [out.html]   # render the node graph
```

Always use `uv add` to install new packages — never `pip install`.

## Architecture

```
main.py                            CLI dispatcher for all subcommands
agent/
  full_analysis_agent.py           analyze_for_full_analysis — 9-step pipeline (steps/ 1–9), cached per step
  steps/step1_scan.py … step9_guide.py
  instagram_carousel_adapt_agent.py    adapt(): ArticleFullAnalysis → carousel presentation, in 3 cached stages
  instagram_carousel_simplify_agent.py simplify_carousel(): shrink an existing carousel
  newsletter_adapt_agent.py            adapt(): ArticleFullAnalysis → newsletter prose
  media_trend_agent.py
extractors/
  registry.py                      FORMATS: format name → (adapt agent, extractor, renderer) modules
  instagram_carousel.py            extract(): trim to the 3 most-decisive review dimensions + 1 go_further (both carousel formats)
  newsletter.py                    extract(): passthrough → NewsletterDocument
renderer/
  instagram_carousel/              the carousel renderer + shared helpers:
    _shared.py                     _env / _weighted_quality / _LOGO_DATA_URL / TYPE_FR (shared)
    optimized.py                   10-slide optimized deck
    templates/article_carousel_optimized_v0/  Jinja2 templates → PNG slides (1080×1350)
  newsletter/                      newsletter renderer → Markdown + HTML (rich + email); dark brand
  shoot.py                         Playwright HTML → PNG (carousel slides)
models/
  full_analysis.py                 ArticleFullAnalysis (analysis schema)
  instagram_carousel_presentation.py  InstagramCarouselPresentation / Document
  newsletter_presentation.py       NewsletterPresentation / NewsletterDocument
tools/
  scrape.py, search.py, validate.py, verify.py, graph_generator.py
  feeds.py                         curated free FR news feeds → candidates / fetch
```

**Data flow (`produce`):** `analyze_for_full_analysis(text)` → `ArticleFullAnalysis` JSON → `adapt()` → presentation JSON → `extract()` → trimmed render document (`extract.json`) → `render_from_json()` → PNG slides.

**Carousel adapt, three stages** (`agent/instagram_carousel_adapt_agent.py`, prompts
`agent/prompts/carousel_shared.md` + `carousel_{1_axis,2_selection,3_writing}.md`): slide 8 is
written first and everything is written toward it. (1) **axis** — `thesis_frame`, `root_issue`,
« La question », the 3 `essentiel` claims, the slide-7 thesis; (2) **selection** — the beat pool,
the 3 selected, présupposés, objection; (3) **writing** — moments' réflexe/answer, slides 2–3,
sources, hook, caption. Each call gets the earlier stages as fixed context, the article text, and
only its slice of the analysis (`_STAGE_ANALYSIS`: `fond`, context, quotes, claims — never review,
ethics, blend, distill or guide). `_validate()` stays the whole-deck rulebook; `_stage_of()` routes
each error to the stage that owns its field, so a stage repairs only its own. Stages are cached in
`<format>/adapt_steps/` with an input hash: a hand-edited stage is kept and the later ones rerun;
`--stop-after axis|selection` stops for review. Fields no slide shows (watch_out, strengths,
distill_points, payoff, interest, the *_next_slide_hook…) are no longer produced; they stay in the
model as empty defaults so older decks load.

**Instructions (editorial angle):** `--instructions`/`--instructions-file` on `analyze` or `produce`
reach every analysis step and are kept in `analysis.json` (`article_metadata.extra_instructions`),
so the adapt agent leads its prompt with them. `steps/` is stamped with their hash
(`instructions.sha256`); changed instructions move the cached steps to `steps/stale_<hash>/`
and every step reruns.

**Output layout:** one folder per analysis (see `_layout()` in `main.py`):
```
samples/outputs/<stem>/
  analysis.json            ArticleFullAnalysis
  steps/                   step1…step9 cache
  <format>/                e.g. instagram_carousel_optimized/
    adapt_steps/           carousel adapt stages: 1_axis / 2_selection / 3_writing .json (+ .sha256)
    adapt.json             InstagramCarouselPresentation
    extract.json           InstagramCarouselDocument
    slides/                NN_*.png
```

**Formats:** registered in `extractors/registry.py`, all fed by the same `analyze`. The carousel has its own `adapt()` copy; the newsletter has its own prose adapt.
- `instagram_carousel_optimized` (default) — 9-slide "lens to read with" deck on the `article_carousel_optimized_v0` templates: Hook (source pill, title, promise) → En bref (lede + the 3 numbered `essentiel` claims; the prose `essentiel_summary` is the fallback) → À savoir, à se demander (`reperes_facts`: 2–3 labelled facts chosen from the analysis's context, then the réflexes) → 3 moments (one réflexe each, its question repeated word for word) → Le socle de l'argument (thesis, présupposés, objection) → Prise de recul (enjeu de fond, « La question », and under it `cta.where_to_look`: 2–3 sources to find answers; the `go_further` items that carry a URL are appended to the post caption by `caption_with_sources()`) → CTA. The bird and the wire: the Sing Sing bird leaves the wordmark and perches on each slide's key element (marked `data-perch` in the template, fixed per slide type: the idées-clés card, the réflexes card, each moment's answer, the targeted pillar, the enjeu card); `renderer/shoot.py` measures every perch and draws one gold wire through the whole deck (`wire_paths()`), level along each perch and continuous at every slide edge, so a swipe reads it unbroken. A slide without a perch is crossed along its foot. Visual layer: each réflexe wears its lens icon (`CANONICAL_LENSES[…]["icon_svg"]`) on slide 3 and on its moment; a moment may draw one sourced count as people or things (`reading_beats[].pictogram`, max one per deck, never a relative risk); slide 7 draws the présupposés as pillars under the thesis, and the bird perches on the pillar `steel_man.targets` names. On slides 1 and 9 the bird sits at home, beside the wordmark top right (the original logo), and those slides carry no wire: it runs from the first perch to the last, starting and ending at the text column's edge. The renderer builds the slide list conditionally (numbering adapts); reading beats are a candidate pool (`selected`), and the réflexe lenses are derived from the selected beats. The axis: slide 8 (`root_issue` + « La question ») is written first and the deck leads to it — each selected beat carries an `axis_link` (not rendered), and the validator requires the hook, each `essentiel` bullet and the slide-7 thesis to share a key word with slide 8. Quotes from a non-French source show in French (`quote`), with the passage as written in `quote_original`, which the verbatim checks match.
- `instagram_carousel_light` — the same deck, condensed: same 9 slides, angle, moments, enjeu and question, about a third of the words, larger type. `agent/instagram_carousel_light_agent.py` condenses the full deck's `adapt.json` (reused from the sibling `instagram_carousel_optimized/` folder, or produced first) through a short pass that returns only the displayed copy (`LightCopy`), merged into the full presentation — so the selection and the newsletter fields stay the full deck's. Rendered by `renderer/instagram_carousel/light.py`: the same templates with `light=True` (type scale 72 / 60 / 54 / 48 / 44 / 38, the bird on each moment's question, no lede on slide 2, the photo kept on slides 1 and 9). `_validate(..., light=True)` holds its caps; `check` and `render` infer the format from the deck's folder name.
  Clues, both formats: each moment's `answer` and each `cta.where_to_look` names where to check (an institution, a document, a figure, a person quoted) — `_clue_errors()`.
- `newsletter` — prose, not slides. Own adapt agent (`newsletter_adapt_agent`) + `NewsletterPresentation`. Renders **Markdown** + a rich `newsletter.html` (dark gold-on-black, SVG radar) + email-safe HTML in two themes (table layout, inline styles, no SVG/flexbox): `newsletter.email.html` (light, default) and `newsletter.email.dark.html`. Themes live in `EMAIL_THEMES`; only chrome is themed, the semantic gauge/bar colours are fixed.
  Manual editing: the newsletter's editable source is `newsletter.md` (YAML
  front-matter + Markdown body). Edit it, then `python main.py render
  <newsletter.md> --format newsletter` to rebuild html/email from it. Per-block
  styling is inferred from section titles; override with `::: salmon|box|keystone`
  containers or a `## Title {icon=<name>}` attribute. (The carousel, by contrast,
  is edited as JSON — format matches the medium; same `render <file>` workflow.)
  Re-running `produce`/`render <extract.json>` regenerates `newsletter.md` and
  overwrites hand edits — the edit-safe loop always renders from the `.md`.

**Slide 1 (hook) — source, title, promise:** top to bottom, a gold source pill
(medium · length · source · date, from `pill_parts()`; ▶ for podcast/video), the
hook title (`sub_topic`), the promise — `hook.subtitle` (« Comprendre … ») with
« En juger soi-même. » added by the template in gold — then « Glissez → ».
Two image modes, both picked up at `render` time — no schema field, no API rerun. Images are looked for beside the analysis, then beside the input file when the analysis sits in a `<stem>/` folder next to it (`article_14/article.txt` → `article_14/article/`):
- **Full-bleed photo:** a `background.png|jpg|webp` beside the analysis
  (`samples/.../<stem>/`) fills the slide under a black band (the logo stays on
  dark) and fades to black behind the text. Opt-in by file: crop a real photo,
  never a text-only capture. The same photo returns on the last slide, fading
  behind the sign-off, so the deck opens and closes on it.
- **Card:** otherwise a `cover.*` (preferred) or `image.*` capture renders as a
  card under the pill, keeping its aspect ratio (`cover_thumb()`, `hook_metrics()`).
With neither, the pill and the title stand alone. The source's own title shows under the pill on the full-bleed slide only (the capture carries it otherwise).
Pass `--title`/`--source`/`--url`/`--published-at`/`--duration` to
`analyze`/`produce` to fill the pill; nothing infers them from the article body.
For a non-French source, `--language espagnol` (the language in French) makes the
full-bleed label read « Article original en espagnol » (`source_label()`).

**Rendering interface:** every renderer module exposes `render_from_json(extract_path, out_dir, pdf=False)` and lays out its own files under `out_dir` — carousels write `html/` + `slides/`, the newsletter writes `newsletter.md`/`.html`/`.email.html`. `produce` and `render` call this uniformly. (`pdf` is a vestigial no-op kept for interface uniformity.)

To add a format, add a `FORMATS` entry mapping to its adapt agent, extractor, and renderer modules.

**Search providers:** Configured via `SEARCH_API_PROVIDER` env var (`brave` | `serper` | `tavily`). The provider routing lives in `tools/search.py`.

## Environment

Copy `.env.example` to `.env` and fill in keys before running:

```bash
cp .env.example .env
```

# Behavioral guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 0. Before Acting — Mandatory Protocol

**Every task, no exceptions.**

**Simple tasks** (single file, single obvious change): state your assumption in one sentence, then proceed.

**Complex tasks** (multiple files, config + code + regeneration, or any task where the right approach requires classification or reasoning across the codebase): write a numbered plan before touching anything:

```
1. [What you will do] → verify: [how you will check it worked]
2. [What you will do] → verify: [how you will check it worked]
...
What you will NOT touch: [list]
```

Then **STOP and wait for approval** before executing anything.

If you are unsure which category a task falls into, treat it as complex.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
