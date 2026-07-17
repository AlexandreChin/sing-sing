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
| 3 — Repères | `presentation.display.reperes_headline` (headline), `analysis.context.contexts[0].text` ("Le contexte"), `presentation.display.lenses[].name` / `.question` |
| 4–6 — Moments | `presentation.display.reading_beats[]` → `moment`, `quote`, `note`, `lens_ref`, `factcheck` |
| 7 — Vue d'ensemble | `presentation.display.global_analysis` → `headline`, `core_recap[]`, `note` |
| 8 — Prise de recul | `presentation.display.steel_man` (`argument`, `alternative`), `presentation.display.root_issue` |
| 9 — Bilan | `presentation.display.bilan_headline` (headline), `presentation.display.key_takeaways[]`, `presentation.display.lenses` (the pills), `presentation.cta.engagement_sentence` ("La question") |
| 10 — CTA | `presentation.cta.post_reading_questions[]` |

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
