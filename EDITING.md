# Editing carousel text and re-shooting slides

How to change the text on an already-generated carousel and re-render the PNGs
by hand — no LLM calls.

## TL;DR

The renderer reads **`extract.json`**, not `adapt.json`. So:

1. Edit the text in
   `samples/outputs/<article>/instagram_carousel_optimized/extract.json`
2. Re-shoot every slide:
   ```bash
   python main.py render \
     samples/outputs/<article>/instagram_carousel_optimized/extract.json \
     --format instagram_carousel_optimized
   ```
3. Updated PNGs land in `.../slides/`, the HTML in `.../html/`.

> Use `render` on `extract.json` — **not** `extract --render`, which writes to a
> scratch folder instead of the canonical one.

(`instagram_carousel_optimized` is the 10-slide deck; use
`instagram_carousel_optimized_short` for the 6-slide cut.)

## Where each slide's text lives

All paths are inside `extract.json`. Content is under `presentation.…`; the
source line also reads `analysis.article_metadata`.

| Slide | Field(s) |
|-------|----------|
| 1 — Hook | `presentation.hook.topic` (big title), `presentation.hook.sub_topic` (question); source line: `analysis.article_metadata.source`, `.published_at`, `.type`, `.reading_time_minutes` |
| 2 — Sélection | `presentation.display.selection_headline` (subtitle), `presentation.display.why_selected` (body) |
| 3 — Repères | `presentation.display.reperes_headline` (headline), `analysis.context.contexts[0].text` ("Le contexte"); the réflexe list is **derived from the selected reading beats** (see Cherry-picking) |
| 4–6 — Moments | `presentation.display.reading_beats[]` — a **candidate pool**; the `selected` ones render (see Cherry-picking). Per beat: `moment` (subtitle), `quote`, `note`, `lens_ref`, `factcheck` |
| 7 — Architecture de l'argument | `presentation.display.global_analysis` → `headline`, `core_recap[]` |
| 8 — À emporter | `presentation.display.bilan_headline` (headline), `presentation.display.key_takeaways[]` (a **pool** — the `selected` ones render, see Cherry-picking); the réflexe pills are **derived from the selected beats** |
| 9 — À vous de juger | `presentation.display.root_issue` ("L'enjeu de fond"), `presentation.display.steel_man` (`argument`), `presentation.cta.engagement_sentence` ("La question") |
| 10 — CTA | `presentation.cta.post_reading_questions[]` |

## Cherry-picking the reading beats (slides 4–6)

`reading_beats` is a **candidate pool** (~6–8). Only the beats with
`"selected": true` render — as slides 4, 5, 6 in list order (max 3). To pick a
different beat, flip `selected` on the one you want to `true` and the one you
want to drop to `false`, then re-shoot. Keep **2–3 selected** (a distinct
`lens_ref` each reads best).

The réflexe lenses on **slides 3, 8 and 9's pills are derived automatically**
from the selected beats (via the canonical vocabulary in `agent/lenses.py`) —
so you don't edit any lens list; picking a beat updates those slides for you.

Each candidate also carries editor-only aids (not rendered) to help you choose:
`theme`, `centrality` (1–5), `kind`, `rationale`.

Canonical `lens_ref` ids: `sources`, `chiffres`, `causalite`, `cadrage`,
`equilibre`, `sophismes`, `angles_morts` (a beat's `lens_ref` must be one of
these).

## Cherry-picking À-retenir (slide 8)

`key_takeaways` is also a pool of `{"text": …, "selected": …}`. The
`selected: true` ones (keep **2–3**) render; flip flags to swap, then re-shoot.

## Alternatives menus (paste-to-swap)

For the fields you re-word most, `adapt` also writes a **menu of alternatives**
right next to the live value. They're **not rendered** — pick one and paste it
into the live field, then re-shoot:

| Live field | Menu |
|---|---|
| `hook.sub_topic` (hook question) | `hook.sub_topic_alt[]` |
| `display.selection_headline` (slide-2 subtitle) | `display.selection_headline_alt[]` |
| `cta.engagement_sentence` (slide-9 question) | `cta.engagement_sentence_alt[]` |
| `display.global_analysis.headline` (slide-7 title) | `display.global_analysis.headline_alt[]` |

## Formatting tricks

- `**mot**` renders as **gold bold**. Wrap the words you want emphasized.
- In `why_selected`, a newline (`\n`) splits the two paragraphs on slide 2.

## Fact-check pill (slides 4–6)

The pill (e.g. **À recouper**) is half data, half code:

- **Which state shows** → `reading_beats[].factcheck` in `extract.json`, one of:
  `consensual`, `true`, `likely true`, `disputed`, `likely false`, `false`,
  `unverifiable` (empty = no pill).
- **The label text** for each state ("À recouper", "À confirmer", …) is mapped
  in `renderer/instagram_carousel/optimized.py` (`_READING`). Edit there to
  rename a label.

## Fixed "chrome" — edit the templates, not `extract.json`

These recurring labels are baked into the Jinja templates under
`renderer/instagram_carousel/templates/article_carousel_optimized_v0/` (a few
live in `optimized.py`). Change them there, then re-shoot:

- Kickers: "Pourquoi cet article", "Au fil de la lecture", "Lecture critique",
  "Vue d'ensemble", "Bilan", "Clefs de lecture", "Sélection"
- Section labels: "Pourquoi on l'a retenu", "À retenir",
  "Les réflexes critiques", "La question", "Réflexe →",
  "L'objection la plus solide", "L'enjeu de fond", "Le contexte"
- Tracker ("Avant de lire · Pendant la lecture · Après la lecture"),
  transition bars ("Comment bien le lire", "Prendre du recul",
  "Avant de partir"), brand ("Sing Sing"), CTA chrome ("NEWSLETTER",
  "Commentez", …)

All per-slide *headlines* are now data-driven (slides 1, 2, 3, 4–6, 7, 9).

## One caveat

`extract.json` is a **generated** file. If you later re-run
`python main.py produce` / `adapt` / `extract` for that article, your manual
edits there are overwritten. For a one-off reshoot, editing `extract.json` is
perfect. For permanent changes, edit `adapt.json` (then re-extract) or the
adapt prompt (`agent/prompts/instagram_carousel.md`).
