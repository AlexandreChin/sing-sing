# Newsletter as a 4-phase reading workflow

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan

## Goal

Restructure the `newsletter` format so it explicitly follows the editorial reading
workflow the newsletter is meant to guide:

1. **Why this article is worth reading**
2. **Context, clues and insights before reading**
3. **Tips while reading** — merged with (4) because the article itself can't be
   shipped (copyright)
4. **Analysis after reading**

Because (3) and (4) are merged, the analysis is delivered in two movements: first a
**detailed, chronological pass** (fact-checking + fallacies in the order they appear
in the article), then a **global synthesis** (what holds, blind spots, verdict).

## Current state

The `newsletter` format (`newsletter_adapt_agent` → `NewsletterPresentation` →
`renderer/newsletter/`) already mirrors the `instagram_carousel_optimized` beats as
prose. Its section order today:

```
Objet / intro
Pourquoi cet article        (why_selected + payoff)
Avant de lire               (context + reflexes + repères + glossaire)
Vérification des faits       (fact_check: 2–4, ranked by decisiveness)
Les failles                  (failles: 2–4, ranked by decisiveness)
Ce qui tient                 (strengths: 2–4)
Angles morts & nuances       (angles_morts: 2–4)
Notre verdict                (verdict_line)
Pour aller plus loin         (go_further: 3–4)
signoff
```

Phases 1 and 2 of the target workflow already map cleanly onto **Pourquoi cet
article** and **Avant de lire**. The gap is entirely in the analysis half: today it
is split by _type_ (facts, then failles) and ranked by _decisiveness_, not organised
by _reading phase_ and _article order_.

### Two constraints discovered during design

- **Raw article text is NOT retained** in `analysis.json` (top-level keys:
  `article_metadata, extraction, context, analysis, annotations, deontology, review,
blend, distill, guide`). So chronological order cannot be computed at render time
  by matching quote positions against the source text.
- **`annotations.facts_vs_opinions.claims_and_sources` is already in article
  order** (the extraction steps emit it top-to-bottom). Failles, by contrast, are
  prose syntheses of the weakest `review.dimensions` — they have no intrinsic
  position.

**Consequence:** the chronological ordering is produced by the adapt LLM, which
reads the (already article-ordered) analysis and emits the detailed pass pre-sorted.
No render-time string-matching, no dependency on retaining article text.

## Target section order

```
Objet / intro                              (unchanged)
── Phase 1 ── Pourquoi cet article          why_selected + payoff          (unchanged)
── Phase 2 ── Avant de lire                 context + reflexes + repères + glossaire  (unchanged)
── Phase 3+4a ── Le décryptage, pas à pas    NEW: one chronological stream (facts + failles)
── Phase 3+4b ── La vue d'ensemble           Ce qui tient → Angles morts → Verdict  (regrouped under one heading)
Pour aller plus loin + signoff              (unchanged)
```

## Design decisions

- **One interleaved chronological stream** (not two ordered lists). The newsletter
  substitutes for reading the article, so a single top-to-bottom commentary that
  quotes the article and flags "claim to check / reasoning flaw" as each appears
  reconstructs the reading-along experience. Facts (is it true?) and fallacies (is
  the reasoning sound?) are different lenses on the same sentence; showing them
  together at that point in the article is more instructive than in two disconnected
  blocks.
- **Curated highlights (~4–6 items)**, not an exhaustive pass. Keeps roughly today's
  volume — the 2 decisive failles + 2–4 key fact-checks, merged and reordered. No
  new analysis surfacing, no bloat.
- **LLM emits the pass pre-ordered.** Robust; avoids brittle render-time matching and
  the missing-article-text problem.

## Changes

### 1. Model — `models/newsletter_presentation.py`

Replace the separate `fact_check` and `failles` fields with one ordered list.

```python
class DecryptageItem(BaseModel):
    kind: Literal["fait", "faille"]    # drives the badge + which fields render
    quote: str                          # the article sentence being examined (verbatim)
    presentation: str                   # fait: how the article frames it;
                                        # faille: short mechanism title
    reading: str                        # our critical reading / the mechanism (2–4 sentences)
    clue: str | None = None             # failles only — echoes the paired pre-reading reflex
```

In `NewsletterPresentation`:

- **Remove** `fact_check: list[FactCheckItem]` and `failles: list[NewsletterSection]`.
- **Add** `decryptage: list[DecryptageItem]` — 4–6 items, already in article order.
- Keep `strengths`, `angles_morts`, `verdict_line`, `go_further`, and all Phase-1/2
  fields unchanged.
- **Remove** `FactCheckItem` (no longer referenced). **Keep** `NewsletterSection` —
  still used by `strengths`.

### 2. Validator — `agent/newsletter_adapt_agent.py`

- Replace the `fact_check` (2–4) and `failles` (2-4) count checks with a `decryptage`
  check: 4–6 items; at least 2 `kind=="faille"` and at least 2 `kind=="fait"`; each
  item has non-empty `quote` and `reading`; every `faille` item has a non-empty
  `clue`.
- Keep `strengths`, `angles_morts`, `go_further` checks unchanged.

### 3. Adapt prompt — `agent/prompts/newsletter.md`

- Replace the `fact_check` + `failles` instruction blocks with one `decryptage`
  block: produce 4–6 items — the 2 decisive failles + 2–4 key fact-checks —
  **sorted in the order they appear in the article** (follow the order of
  `annotations.facts_vs_opinions.claims_and_sources`; interleave failles at the
  article position of the passage they concern). Each item carries `kind`, the
  verbatim `quote`, its `presentation`, our `reading`, and for failles the `clue`.
- Move the reflexes↔failles pairing note onto the faille items (`clue` still echoes
  the paired pre-reading reflex; keep same order among failles).
- Update the bold-emphasis field list: drop `fact_check.reading` / `failles.body`,
  add `decryptage.reading`. Bold must not appear in `quote` or `presentation`.

### 4. Renderer — `renderer/newsletter/renderer.py`

- Keep `_fc_verdict` keyword-matching; apply it per `kind=="fait"` item to attach the
  verdict pill + colour. `kind=="faille"` items render with a ⚠️ badge, no pill.
- Build a single `decryptage` context list (rich + email); the email variant attaches
  `verdict`/`color` only to `fait` items (mirrors current `_email_ctx` fact_check
  loop). Remove the separate `fact_check`/`failles` context wiring.

### 5. Templates — `renderer/newsletter/templates/`

- `newsletter.md`, `newsletter.html`, `newsletter.email.html`: replace the two blocks
  (**Vérification des faits** + **Les failles**) with one loop over `decryptage`
  under the heading **Le décryptage, pas à pas**. Each item is a card with a type
  badge (⚖️ Fait / ⚠️ Faille); `fait` shows its verdict pill, `faille` shows its
  `clue`.
- Group **Ce qui tient** → **Angles morts & nuances** → **Notre verdict** under one
  **La vue d'ensemble** heading (a heading/intro line; the three sub-sections keep
  their own subheadings).
- Radar / gauge / repères / glossaire / go_further markup unchanged.

## Out of scope (untouched)

- Analysis pipeline (`full_analysis_agent`, steps 1–9) and its models.
- Both carousel formats and their shared adapt/extract.
- `extractors/newsletter.py` passthrough (structure unchanged; still wraps
  analysis + presentation).
- Radar/gauge rendering, repères, glossaire, go_further, email theme colour logic.
- No new API cost — same single adapt call.

## Verification

- `python main.py adapt <analysis.json> --format newsletter` produces a
  `NewsletterPresentation` with a valid `decryptage` list (validator passes).
- `python main.py render <extract.json> --format newsletter` writes
  `newsletter.md` + `.html` + `.email.html` + `.email.dark.html` with the new
  section order; the détaillé pass is a single chronological stream with visible
  Fait/Faille badges; fait items show verdict pills.
- Re-run on `samples/outputs/article_1` and `article_2`; eyeball both email themes
  (light + dark) that Phase order reads 1 → 2 → 3+4a → 3+4b → resources.

```

```
