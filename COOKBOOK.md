# Cookbook

Practical, copy-paste recipes for running `sing-sing`. All commands assume you're at
the repo root and use `uv run` (so the right Python/venv is used).

> First time? Do **Recipe 0** once, then jump to **Recipe 1**.

---

## Recipe 0 — One-time setup

```bash
uv sync                              # install dependencies
uv run playwright install chromium   # browser used to screenshot slides
cp .env.example .env                 # then edit .env → set ANTHROPIC_API_KEY
```

You only need a search provider key (`SEARCH_API_*`) for the `verify` tool. The default
provider is `duckduckgo`, which needs no key.

---

## Recipe 1 — The whole thing in one command

`produce` runs **analyze → adapt → extract → render** and writes everything into a tidy
per-article folder. Add `--render` to also generate the PNG slides.

```bash
uv run python main.py produce samples/articles/article_2.txt \
    --format instagram_carousel_optimized \
    --render
```

**Result:**

```
samples/outputs/article_2/
  analysis.json                                  # the full analysis
  steps/                                         # step1…step9 cache
  instagram_carousel_optimized/
    adapt.json                                   # carousel copy
    extract.json                                 # render input
    html/                                        # one HTML file per slide
    slides/  01_hook.png … 10_cta.png            # ← your deliverable
```

Open `samples/outputs/article_2/instagram_carousel_optimized/slides/` to see the 10 PNGs.

---

## Recipe 2 — The short (6-slide) deck

Same command, different `--format`:

```bash
uv run python main.py produce samples/articles/article_2.txt \
    --format instagram_carousel_optimized_short \
    --render
```

→ `samples/outputs/article_2/instagram_carousel_optimized_short/slides/` (6 PNGs:
Hook → Curation → Repères → Le décryptage → Verdict → CTA).

Both formats share the **same** `adapt.json`, so if you've already produced one format
you can generate the other cheaply — see Recipe 5.

---

## Recipe 3 — Run it without an API key (`--no-api`)

`--no-api` swaps the Anthropic API for your local `claude` CLI (each LLM step shells out
to `claude -p`). Everything else is identical.

```bash
uv run python main.py produce samples/articles/article_2.txt --no-api --render
```

The CLI occasionally returns an empty response; the pipeline retries automatically, so a
single blank won't abort the run. Analysis steps are cached, so re-running only re-does
what's missing.

---

## Recipe 4 — Run each stage by hand (to understand the pipeline)

`produce` is these four steps bundled. Running them individually is useful for
inspecting intermediate output or re-doing just one stage.

```bash
# 1) analyze — 9-step analysis (writes analysis.json + steps/ cache)
uv run python main.py analyze samples/articles/article_2.txt
#   → samples/outputs/article_2/analysis.json

# 2) adapt — analysis → carousel presentation copy
uv run python main.py adapt samples/outputs/article_2/analysis.json \
    --format instagram_carousel_optimized
#   → samples/outputs/article_2/analysis_instagram_carousel_optimized_adapt.json

# 3) extract — trim the presentation into a render-ready document
uv run python main.py extract \
    samples/outputs/article_2/analysis.json \
    samples/outputs/article_2/analysis_instagram_carousel_optimized_adapt.json \
    --format instagram_carousel_optimized
#   → samples/outputs/article_2/analysis_instagram_carousel_optimized_extract.json

# 4) render — HTML + PNG (writes html/ and slides/ next to the extract file)
uv run python main.py render \
    samples/outputs/article_2/analysis_instagram_carousel_optimized_extract.json \
    --format instagram_carousel_optimized
```

> Note: the standalone `adapt`/`extract` commands write **flat sibling files**
> (`analysis_<format>_adapt.json`, …). `produce` instead uses the tidy
> `<format>/adapt.json` + `<format>/extract.json` layout. Use whichever fits.

Only `analyze` and `adapt` call the LLM. `extract` and `render` are deterministic —
re-run them freely.

---

## Recipe 5 — Re-render after tweaking the copy (no LLM)

Rendering reads `extract.json`. To fix a headline or a slide's text and regenerate the
PNGs without re-running any Claude calls, **edit the field in `extract.json`, then
`render`**.

```bash
# edit e.g. presentation.hook.headline (or display.why_selected, …) in:
#   samples/outputs/article_2/instagram_carousel_optimized/extract.json

uv run python main.py render \
    samples/outputs/article_2/instagram_carousel_optimized/extract.json \
    --format instagram_carousel_optimized
#   → regenerates that folder's html/ + slides/
```

Where common slide text lives in `extract.json`:

| Slide | Field |
|-------|-------|
| Hook | `presentation.hook.headline` |
| Curation | `presentation.display.selection_headline`, `.why_selected`, `.payoff` |
| Repères | `presentation.display.pre_reading[]` (+ `analysis.context.contexts[0].text`) |
| Failles | `analysis.guide.watch_out.items[].label` / `.text` |
| Verdict | `analysis.review.verdict.main_blind_side`, `.reading_recommendation` |

> `extract.json` is a **generated** file — it's overwritten if you re-run `produce`,
> `adapt`, or `extract`. Hand-edits are for one-off final polish. For a permanent
> change, fix it upstream (the adapt prompt / analysis).

**Render in two steps** (e.g. to inspect the HTML first): `html` writes the HTML into a
directory, `shoot` screenshots that same directory to PNG.

```bash
uv run python main.py html  <extract.json> myslides --format instagram_carousel_optimized
uv run python main.py shoot myslides      # PNGs land next to the HTML
```

---

## Recipe 6 — Generate the second format cheaply from an existing run

Because both formats share `adapt.json`/`extract.json`, you can render the short deck
from an already-produced `extract.json` without re-analyzing or re-adapting:

```bash
mkdir -p samples/outputs/article_2/instagram_carousel_optimized_short
cp samples/outputs/article_2/instagram_carousel_optimized/extract.json \
   samples/outputs/article_2/instagram_carousel_optimized_short/extract.json

uv run python main.py render \
   samples/outputs/article_2/instagram_carousel_optimized_short/extract.json \
   --format instagram_carousel_optimized_short
```

---

## Recipe 7 — Utilities

```bash
# Node-graph integrity checks on an analysis
uv run python main.py validate samples/outputs/article_2/analysis.json

# Find corroborating / contradicting sources for the article's claims
uv run python main.py verify samples/outputs/article_2/analysis.json
uv run python main.py verify samples/outputs/article_2/analysis.json --claim 0 --claim 3

# Render the analysis node-graph to an interactive HTML page
uv run python main.py graph samples/outputs/article_2/analysis.json graph.html

# Shrink an existing analysis for readability
uv run python main.py simplify samples/outputs/article_2/analysis.json
```

---

## Recipe 8 — Use your own article

Any UTF-8 `.txt` works. For scraped articles, keep the **title on the first line**
(byline/date below) — step 1 uses that as the title fallback.

```bash
uv run python main.py produce path/to/my_article.txt \
    --format instagram_carousel_optimized_short --render
# → samples/outputs/my_article/instagram_carousel_optimized_short/slides/
```

You can also pipe text via stdin to `analyze`:

```bash
cat my_article.txt | uv run python main.py analyze
```

---

## Recipe 9 — Generate a newsletter (Markdown + HTML + PDF)

The `newsletter` format is fed by the same analysis, but produces prose instead of slides.
`--pdf` adds a PDF (dark gold-on-black, via Chromium); without it you get `.md` + `.html`.

```bash
uv run python main.py produce samples/articles/article_2.txt \
    --format newsletter --render --pdf
```

**Result:**

```
samples/outputs/article_2/newsletter/
  adapt.json         newsletter prose (structured)
  extract.json       render input
  newsletter.md      ← paste into Substack/Beehiiv/Ghost/…
  newsletter.html    ← web/print view
  newsletter.pdf     ← the printable deliverable
```

## Recipe 10 — Edit the newsletter, then regenerate the PDF (no LLM)

Two ways to hand-tune before the final PDF:

**A. Edit the prose (`newsletter.md`)** → regenerate the PDF straight from the markdown:

```bash
# edit samples/outputs/article_2/newsletter/newsletter.md
uv run python main.py pdf samples/outputs/article_2/newsletter/newsletter.md
#   → newsletter.pdf (markdown → branded shell → PDF)
```

**B. Edit the structured copy (`extract.json`)** → re-render all three outputs:

```bash
# edit e.g. presentation.subject / presentation.decryptage[].body in extract.json
uv run python main.py render samples/outputs/article_2/newsletter/extract.json \
    --format newsletter --pdf
```

> Use **A** for quick wording tweaks (fastest), **B** when you want `.md`/`.html`/`.pdf` to
> stay in sync. `pdf` also accepts an `.html` file if you prefer editing that.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `playwright` / browser errors on render | `uv run playwright install chromium` |
| `analyze`/`produce` fails on a missing key | set `ANTHROPIC_API_KEY` in `.env`, or use `--no-api` |
| `--no-api` run aborts with empty/JSON error | transient `claude -p` blank; just re-run — steps are cached and it retries |
| Re-ran and nothing recomputed | expected: `steps/` is cached. Delete a `steps/stepN_*.json` to force that step |
| Slides look stale | you're viewing an old folder — the live output is `<format>/slides/` |
