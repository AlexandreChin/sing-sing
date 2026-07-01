# sing-sing

`sing-sing` turns a news article into a publishable **Instagram carousel**. It runs a
multi-step Claude analysis of the article (source rigour, reasoning, rhetoric, ethics,
a scored review, a verdict…), adapts that analysis into reader-facing carousel copy,
trims it to fit, and renders it to **1080×1350 PNG slides**.

```
article.txt ──▶ analyze ──▶ adapt ──▶ extract ──▶ render ──▶ slides/*.png
              (9 steps)   (copy)    (trim)      (HTML→PNG)
```

- **analyze** — a 9-step Claude pipeline → `ArticleFullAnalysis` (cached per step).
- **adapt** — one Claude call → an `InstagramCarouselPresentation` (punchy, slide-ready copy).
- **extract** — no LLM; selects/trims the presentation into a render-ready document.
- **render** — Jinja2 templates → HTML → Playwright screenshots → PNG slides.

> New here? The **[COOKBOOK](COOKBOOK.md)** walks through running a pipeline end to end
> with copy-paste examples.

## Requirements

- **Python 3.14+**
- **[uv](https://docs.astral.sh/uv/)** for dependency management (use `uv add`, never `pip install`)
- A **Chromium** browser for Playwright (screenshots)
- An **Anthropic API key** (or the `claude` CLI, for `--no-api` mode)

## Setup

```bash
# 1. install dependencies
uv sync

# 2. install the Playwright browser used for screenshots
uv run playwright install chromium

# 3. configure keys
cp .env.example .env      # then fill in ANTHROPIC_API_KEY (and a search provider if you use the tools)
```

`.env` keys:

| Key | Purpose |
|-----|---------|
| `ANTHROPIC_API_KEY` | Claude API (all LLM steps). Not needed in `--no-api` mode. |
| `SEARCH_API_PROVIDER` | `duckduckgo` (default, no key) · `brave` · `serper` · `tavily` · `newsapi` · … — used only by the `verify`/search tools. |
| `SEARCH_API_KEY` | Key for the chosen search provider (if it requires one). |

The Claude model is set in `config.py` (`MODEL = "claude-opus-4-8"`).

## Quick start

```bash
# Full pipeline + render, on a bundled sample article:
uv run python main.py produce samples/articles/article_2.txt \
    --format instagram_carousel_optimized --render
```

Slides land in `samples/outputs/article_2/instagram_carousel_optimized/slides/`.

No API key? Use the local Claude CLI instead:

```bash
uv run python main.py produce samples/articles/article_2.txt --no-api --render
```

## Commands

Run `uv run python main.py <command> --help` for details.

| Command | What it does |
|---------|--------------|
| `produce <article.txt>` | Full pipeline: analyze → adapt → extract → (render) |
| `analyze <article.txt>` | Run the 9-step analysis only → `analysis.json` |
| `adapt <analysis.json>` | Analysis → carousel presentation (`adapt.json`) |
| `extract <analysis.json> <presentation.json>` | Presentation → render-ready `extract.json` |
| `render <extract.json>` | `extract.json` → HTML + PNG slides |
| `html <extract.json>` | Write standalone HTML slides (no screenshots) |
| `shoot <html_dir>` | Screenshot existing HTML slides → PNG |
| `pdf <file.md\|.html>` | Render a newsletter `.md`/`.html` to PDF (for edit-then-regenerate) |
| `simplify <analysis.json>` | Shrink an existing analysis for readability |
| `validate <analysis.json>` | Node-graph integrity checks |
| `verify <analysis.json>` | Find sources for/against the article's claims |
| `graph <analysis.json>` | Render the analysis node-graph to HTML |

Common flags: `--format {instagram_carousel_optimized, instagram_carousel_optimized_short, newsletter}`,
`--no-api` (use the `claude` CLI instead of the API), `--render` (also produce the output files),
`--pdf` (newsletter: also emit a PDF).

## Formats

All formats are fed by the **same** `analyze` stage. The two carousel formats also share the
same `adapt()` copy; the newsletter has its own prose adapt. Registered in `extractors/registry.py`.

| Format | Output | Shape |
|--------|--------|-------|
| `instagram_carousel_optimized` *(default)* | 10 PNG slides | Hook → Curation → Repères → Vérif. des faits → Faille 1 → Faille 2 → Point fort → Prise de recul → Verdict → CTA |
| `instagram_carousel_optimized_short` | 6 PNG slides | Hook → Curation → Repères → Le décryptage → Verdict → CTA |
| `newsletter` | Markdown + HTML + PDF | the carousel beats as detailed prose: Intro → Pourquoi cet article → Avant de lire → Vérification des faits → Les failles → Ce qui tient → Angles morts & nuances → Verdict → Pour aller plus loin → sign-off |

```bash
# Newsletter (Markdown + HTML, plus PDF with --pdf):
uv run python main.py produce samples/articles/article_2.txt --format newsletter --render --pdf
```

## Output layout

One folder per article under `samples/outputs/`:

```
samples/outputs/<article-stem>/
  analysis.json                 ArticleFullAnalysis
  steps/                        step1…step9 cache (re-used on re-runs)
  <format>/
    adapt.json                  presentation layer (carousel or newsletter)
    extract.json                render input
    # carousel formats:
    html/                       one HTML file per slide
    slides/                     NN_*.png  ← the deliverable
    # newsletter format:
    newsletter.md / .html / .pdf   ← the deliverables
```

## Project structure

```
main.py                      CLI dispatcher (argparse)
config.py                    MODEL constant
agent/
  full_analysis_agent.py     the 9-step analysis pipeline
  steps/step1_scan.py … step9_guide.py
  instagram_carousel_adapt_agent.py   adapt(): analysis → carousel presentation
  newsletter_adapt_agent.py           adapt(): analysis → newsletter prose
extractors/
  registry.py                format name → (adapt agent, extractor, renderer)
  instagram_carousel.py      extract(): trim the carousel presentation
  newsletter.py              extract(): passthrough → NewsletterDocument
renderer/
  instagram_carousel/        the carousel renderers + shared helpers
    optimized.py             10-slide deck
    optimized_short.py       6-slide deck
    _shared.py               Jinja env, gauge, logo helpers
    templates/               Jinja2 slide templates
  newsletter/                newsletter renderer → Markdown + HTML (+ PDF)
  shoot.py                   Playwright HTML → PNG (slides)
  pdf.py                     Playwright HTML → PDF (newsletter)
models/                      Pydantic schemas
tools/                       scrape · search · validate · verify · graph
```

See [CLAUDE.md](CLAUDE.md) for deeper architecture notes.
