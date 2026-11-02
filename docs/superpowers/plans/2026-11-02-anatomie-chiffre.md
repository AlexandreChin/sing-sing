# Plan — implement the `anatomie_chiffre` archetype

Written 2026-11-02 to be executed from a fresh session. The editorial spec is
`docs/carousels_archetypes.md` §3, **Archétype 3 : `anatomie_chiffre`** (read it first — it is the
source of truth for the slides; this file only says how to build it). The worked example is the BFM
article `samples/articles/bfm_americains/article.txt` (BFM Business, 1 Nov 2026: Fed survey, the over-75s
15× richer than the under-35s).

## Ground rules (from CLAUDE.md and the author's notes)

- `uv add` / `uv sync`, never `pip`. Python 3.14. No new dependency expected.
- Surgical: follow the cadrage / temps_long pattern; do not refactor those agents or renderers. A third
  near-copy of the step runner is accepted for now (factoring it out is a separate task, not to start
  without asking).
- Do not publish Artifacts in this project; show PNGs locally.
- Sober copy: describe plainly, no praise words.
- Do not commit `docs/superpowers/` files or leave pushes unannounced: commit code locally, **ask before
  pushing**. The doc change to `docs/carousels_archetypes.md` is uncommitted — commit it with the code (ask).
- Live API runs cost money (`claude-opus-4-6`): run `--no-api` first; ask before any live run.
- Tests must stay green (`uv run pytest`; 505 passed at the last full run).

## What the deck is (summary of the spec)

6 slides, deck output folder `<stem>/anatomie_chiffre/`:

1. **Hook** — identical to the optimized one. Title = the raw figure in « ». Promise written per figure:
   « <subject in neutral words> : comment il se mesure, et la question qu'il pose ».
2. **La boîte noire** (in frame) — monospace figure cards `valeur | libellé | comparaison` (value ≤ 9 chars),
   "non précisé" when the source is silent, mismatched group definitions reported, plus a fixed card for the
   **primary source and the chain** (`Fed → WSJ → BFM`).
3. **La zone d'éclairage** (in frame) — what the figure establishes + its **decomposition** (the two
   quantities that make a ratio or a variation, as the source gives them; the exceptional starting point the
   source mentions goes here); small visual: two bars and their ratio. No recomputed gap unless flagged.
4. **Le périmètre exclu** (out of frame, no figure added) — two cards: **la statistique** (what a mean/median
   hides: debts, liquidity, spread, self-report) and **la période** (two dates, starting point, a date vs a
   generation followed over time), each with organisations/series to consult.
5. **La question derrière le chiffre** (out of frame) — two columns « Ce que la source énonce » / « Ce que nous
   en tirons », and under them the **variable** as a two-pole bar (A ⟷ B) with a cursor, the implication as a
   consequence to examine (never a conclusion), and where to look at the variable directly (unverified).
6. **CTA** — identical to the optimized one; the « Commentez — … » line opens slide 5's question
   (e.g. « De quoi dépend, selon vous, le patrimoine à 35 ans ? »), neither binary nor normative.

Steps (written in this order, the core first, `writing` = caption without a pause):
`variable` → `boite_noire` → `eclairage` → `perimetre` → `hook` → `writing`.
**Name the core step `variable`, not `question`**: `question` is already a step of the 9-slide format and
shares `_STEP_CHOICES` in `main.py`. The deck-level concept is « la question derrière le chiffre »; the step
fixes its variable (A against B), the proxy reading, the source's facts to join, the implication and where to look.
It is never rendered as such and is the fixed context of every later step; an advisory flag checks that slides
2–4 each tie back to it (as `axe` does in cadrage).

## Files

New:
- `models/anatomie_chiffre_presentation.py` — `AnatomieChiffrePresentation` / `AnatomieChiffreDocument`
  (copy the shape of `models/cadrage_presentation.py`: hook, a core `variable` model not rendered, one model
  per slide 2–5, `caption`, document with `model_rebuild()`).
- `extractors/anatomie_chiffre.py` — passthrough (10 lines, like `extractors/cadrage.py`).
- `agent/anatomie_chiffre_adapt_agent.py` — copy of `agent/cadrage_adapt_agent.py` adapted: STEPS table,
  option models with **flat string fields** (so `--edit ID.field=TEXT` and `fix` reach them), `field_errors`,
  `to_fragment`, `assemble`, the advisory flags, `generate/choose/more/fix`, `adapt`.
- `agent/prompts/anatomie_chiffre_steps/` — `0_shared.md`, `0_options.md`, `1_variable.md`, `2_boite_noire.md`,
  `3_eclairage.md`, `4_perimetre.md`, `5_hook.md`, `6_writing.md` (copy the cadrage ones for the common parts,
  with a worked example from the BFM article in `1_variable.md`).
- `renderer/instagram_carousel/anatomie_chiffre.py` — copy of `renderer/instagram_carousel/cadrage.py`
  (keeps `_nobreak`, hook/CTA from the optimized templates, slides 2–5 from the new templates).
- `renderer/instagram_carousel/templates/article_carousel_anatomie_chiffre_v1/` — `02_boite_noire.html`,
  `03_eclairage.html`, `04_perimetre.html`, `05_variable.html` (reuse `_argument.css` tokens, the notes partial
  and the gauge/cursor styling of `06_boussole.html` from the cadrage templates rather than duplicating them;
  check how those are included).
- `tests/test_anatomie_chiffre.py` (model on `tests/test_cadrage.py`, 333 lines, and the worst-case render test
  of `tests/test_temps_long.py`).

Modified: `extractors/registry.py` (FORMATS entry), `main.py` (`ANATOMIE_FORMAT`, `GUIDED_AGENTS`,
`_STEP_CHOICES`, help strings), `CLAUDE.md` (commands block, architecture tree, Formats section),
`.claude/skills/carousel-guided/SKILL.md` (a paragraph like the cadrage/temps_long ones),
`docs/carousels_archetypes.md` (status « à réaliser » → « réalisé », and the final field names).

Sample input: rename `samples/articles/bfm_americains/article.txt` → `bfm_americains.txt` (`_base_dir()` expects
`<stem>/<stem>.txt`, else it nests under a second folder). Untracked, so no git move.

## Flat option fields (proposal — finalise while writing step 1, keep the cadrage conventions)

- `variable`: `title` (« A ou B », neutral words of equal weight), `variable`, `pole_a`, `pole_b`, `proxy`
  (why the figure stands for it — our reading), `fact1`…`fact3` (what the source states, to join), `implication`,
  `look1`/`look2` (`organisme | texte`).
- `boite_noire`: `fig1`…`fig4` (`valeur | libellé | comparaison`), `source_card` (`valeur | libellé | comparaison`,
  e.g. `Fed → WSJ → BFM | source primaire citée ? | …`), `claim`, `detail`.
- `eclairage`: `claim`, `detail`, `part1`, `part2` (`valeur | libellé`), `ratio` (`valeur | libellé`), `note1`.
- `perimetre`: `title`, `claim1`, `detail1`, `note1_1`…, `claim2`, `detail2`, `note2_1`… (card 1 la statistique,
  card 2 la période).
- slide 5 columns come from `variable` (`fact1…3` left, the question right); no extra step.
- `hook`: `title`, `promise`; `writing`: `caption`.

## Rules to encode

Hard (repair a generated option, ⚠ on the author's pick; `choose` refuses only slot-rule violations):
word/character caps measured on the rendered slides, figure format (value ≤ 9 chars), note `source | texte` /
`remarque | texte`, no accusing word (*biais, manipulation, mensonge, trompeur…*) outside « », 4 hashtags,
**no digit on slides 4 and 5** (slide 4 adds no figure; slide 5 states facts only inside the « source » column),
"non précisé" allowed on slide 2, slide 5 conclusion words (« donc », « prouve »…) refused.
Advisory flags: a figure not found as digits in the source (spelled-out figures flagged too); a slide 2–4 field
with no tie to the variable; a variable the source supports with no fact (left column empty); a derived figure
(recomputed gap) not marked as derived.

## Tasks, in order — each ends with its check

1. **Model + extractor + registry.**
   Verify: the model loads a hand-written sample JSON; `FORMATS["anatomie_chiffre"]` resolves its three modules.
2. **Agent: steps table, option models, rules, flags** (no prompts yet), TDD.
   Verify: unit tests for `field_errors`, `to_fragment`, `assemble`, flags; the choose/more/fix cycle with
   `--no-api`.
3. **Prompts** (`agent/prompts/anatomie_chiffre_steps/`).
   Verify: a prompt-rendering test like `tests/test_carousel_step_prompts.py` (each step's message contains the
   earlier steps as fixed context, the article text and only its slice of the analysis).
4. **CLI wiring** in `main.py`.
   Verify: `python main.py produce --help` shows the format and the new step names; no name collision in
   `_STEP_CHOICES`.
5. **Renderer + templates.** Build slides 2–5 one at a time, screenshot each with a hand-written sample
   (`render <extract.json> --format anatomie_chiffre`).
   Verify: the PNGs are 1080×1350; the bird perches on the figure card (2), the bars (3), the cursor (5); no
   horizontal overflow; then a **seeded worst-case render test** measuring every text field against its box
   (as temps_long's), and set the character caps from those measurements.
6. **Docs and skill**: CLAUDE.md, carousel-guided skill, archetypes doc status.
   Verify: `grep -rn anatomie_chiffre` hits each.
7. **Run on the BFM article.** Rename the sample, then `python main.py produce
   samples/articles/bfm_americains/bfm_americains.txt --format anatomie_chiffre --guided --no-api --render
   --medium … --title … --source …` for the plumbing. **Then ask before the live run** (real API calls, pauses at
   each step for the author's pick; follow the `carousel-guided` skill).
   Verify: 6 PNGs render; show them to the author; `uv run pytest` green.

## Not touched

`grand_dossier`, `cadrage_logique`, `temps_long` and `newsletter` code; `agent/steps/` (the analysis);
`agent/carousel_steps/`; the press-media files in `data/`; the other untracked `docs/superpowers/` files and
`samples/articles/article_9/` and the other new article folders.

## Open points to settle with the author during the run

- Whether a second context source (e.g. the Fed survey page, `--context-file`) may feed slide 2 when the article
  gives half the method; the spec only says "non précisé" for now.
- The 5-slide fallback (no slide 5 when no underlying variable holds) was suggested but **not** written into the
  spec; decide before building the step table (affects the CTA and the renderer's slide list).
- Whether the hook's promise length fits one line on the hook slide (« Un écart de patrimoine entre générations :
  comment il se mesure, et la question qu'il pose » is long): measure it in the worst-case test.
