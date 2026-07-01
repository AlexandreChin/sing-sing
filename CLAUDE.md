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
python main.py produce <article.txt> [--format instagram_carousel_optimized] [--no-api] [--render] [--pdf]

# Individual stages
python main.py analyze <article.txt> [--instructions "..."] [--instructions-file <path>]
python main.py adapt   <analysis.json>   [--format <fmt>] [--no-api]
python main.py extract <analysis.json> <presentation.json> [--format <fmt>] [--render]
python main.py render  <extract.json> [<output_dir>] [--format <fmt>] [--pdf]
python main.py pdf     <newsletter.md|.html> [out.pdf]   # newsletter → PDF (edit-then-regenerate)

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
  instagram_carousel_adapt_agent.py    adapt(): ArticleFullAnalysis → carousel presentation
  instagram_carousel_simplify_agent.py simplify_carousel(): shrink an existing carousel
  newsletter_adapt_agent.py            adapt(): ArticleFullAnalysis → newsletter prose
  media_trend_agent.py
extractors/
  registry.py                      FORMATS: format name → (adapt agent, extractor, renderer) modules
  instagram_carousel.py            extract(): trim to the 3 most-decisive review dimensions + 1 go_further (both carousel formats)
  newsletter.py                    extract(): passthrough → NewsletterDocument
renderer/
  instagram_carousel/              the two carousel renderers + shared helpers:
    _shared.py                     _env / _weighted_quality / _LOGO_DATA_URL / TYPE_FR (shared)
    optimized.py                   10-slide optimized deck
    optimized_short.py             6-slide optimized deck
    templates/article_carousel_optimized_v0/  Jinja2 templates → PNG slides (1080×1350)
  newsletter/                      newsletter renderer → Markdown + HTML (+ PDF); dark brand
  shoot.py                         Playwright HTML → PNG (carousel slides)
  pdf.py                           Playwright HTML → paginated PDF (newsletter)
models/
  full_analysis.py                 ArticleFullAnalysis (analysis schema)
  instagram_carousel_presentation.py  InstagramCarouselPresentation / Document
  newsletter_presentation.py       NewsletterPresentation / NewsletterDocument
tools/
  scrape.py, search.py, validate.py, verify.py, graph_generator.py
```

**Data flow (`produce`):** `analyze_for_full_analysis(text)` → `ArticleFullAnalysis` JSON → `adapt()` → presentation JSON → `extract()` → trimmed render document (`extract.json`) → `render_from_json()` → PNG slides.

**Output layout:** one folder per analysis (see `_layout()` in `main.py`):
```
samples/outputs/<stem>/
  analysis.json            ArticleFullAnalysis
  steps/                   step1…step9 cache
  <format>/                e.g. instagram_carousel_optimized/
    adapt.json             InstagramCarouselPresentation
    extract.json           InstagramCarouselDocument
    slides/                NN_*.png
```

**Formats:** registered in `extractors/registry.py`, all fed by the same `analyze`. The two carousel formats also share the same `adapt()` copy; the newsletter has its own prose adapt.
- `instagram_carousel_optimized` (default) — 10-slide deck on the `article_carousel_optimized_v0` templates: Hook → Curation → Repères → Vérif. des faits → Faille 1 → Faille 2 → Point fort → Prise de recul → Verdict → CTA. renderer builds the slide list conditionally, so absent sections drop out and numbering (`slide_n`/`slide_total`) adapts.
- `instagram_carousel_optimized_short` — 6-slide cut of the above (same templates + one merged `decryptage.html`): Hook → Curation → Repères → Le décryptage (failles merged) → Verdict → CTA.
- `newsletter` — prose, not slides. Own adapt agent (`newsletter_adapt_agent`) + `NewsletterPresentation`. Renders **Markdown + HTML**, and a **PDF** with `--pdf` (Chromium `page.pdf`, dark gold-on-black). Edit `newsletter.md` and run `pdf <file>` to regenerate the PDF without the LLM.

**Rendering interface:** every renderer module exposes `render_from_json(extract_path, out_dir, pdf=False)` and lays out its own files under `out_dir` — carousels write `html/` + `slides/`, the newsletter writes `newsletter.md`/`.html`/`.pdf`. `produce` and `render` call this uniformly.

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
