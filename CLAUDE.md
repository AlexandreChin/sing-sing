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
python main.py produce <article.txt> [--format instagram_carousel_optimized] [--no-api] [--render] [--instructions-file <path>] [--stop-after <step>] [--guided]

# The other carousel archetype, CADRAGE & LOGIQUE (7 slides, for opinion pieces) — same loop,
# steps: constat these angle_mort depassement boussole hook (then `writing`, no pause)
python main.py produce <video.txt> --format cadrage_logique --guided [--no-api] [--render] [--medium …] [--title …] [--source …]

# The TEMPS LONG archetype (7 slides, for a position that the perspective of time helps analyse; steps: axe position tournants episodes lecture pieges hook, then `writing`, no pause)
python main.py produce <article.txt> --format temps_long --guided [--no-api] [--render] [--medium …] [--title …] [--source …]

# The ANATOMIE D'UN CHIFFRE archetype (6 slides, for a statistic, a poll, a ranking; steps: axe chiffres recit angle_mort lectures hook, then `writing`, no pause)
python main.py produce <article.txt> --format anatomie_chiffre --guided [--no-api] [--render] [--medium …] [--title …] [--source …]

# The TROIS REGARDS archetype (7 slides, for a large social phenomenon read through one discipline; steps: axe position prismes tensions hook, then `writing`, no pause)
python main.py produce <article.txt> --format trois_regards --guided [--no-api] [--render] [--medium …] [--title …] [--source …]
python main.py choose <fmt_dir> prismes --pick p1a,p2c,p3b          # one option per prism slot
python main.py choose <fmt_dir> prismes --more --prism <p1|p2|p3|prism-id> [--remark "…"]   # regenerate one prism only
python main.py fix    <fmt_dir> prismes.<slot>.<field> "<text>"     # e.g. prismes.p2.head1, prismes.p2.answer3, tensions.view2_3, position.card3

# Individual stages
python main.py analyze <article.txt> [--instructions "..."] [--instructions-file <path>]
python main.py adapt   <analysis.json>   [--format <fmt>] [--no-api] [--stop-after <step>] [--guided]
python main.py extract <analysis.json> <presentation.json> [--format <fmt>] [--render]
python main.py render  <extract.json> [<output_dir>] [--format <fmt>]

# Guided carousel adapt (steps: question enjeu idees moments contexte socle hook)
python main.py choose <fmt_dir> <step> --pick a,b [--edit ID=TEXT] [--reason "…"]   # or --more [--remark "…"]
python main.py fix    <fmt_dir> <field> "<text>"      # rewrite one deck field, no regeneration
python main.py check  <extract.json> [--reader] [--no-api]

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
  carousel_steps/                  steps.py / store.py / run.py — the 8 guided adapt steps (prompts/carousel_steps/)
  instagram_carousel_adapt_agent.py    adapt(): ArticleFullAnalysis → carousel presentation, assembled from the 8 guided steps
  instagram_carousel_simplify_agent.py simplify_carousel(): shrink an existing carousel
  newsletter_adapt_agent.py            adapt(): ArticleFullAnalysis → newsletter prose
  cadrage_adapt_agent.py               adapt() for cadrage_logique: its own guided steps (prompts/cadrage_steps/), choose/more/fix
  temps_long_adapt_agent.py            adapt() for temps_long: its own guided steps (prompts/temps_long_steps/), choose/more/fix; write order per move
  temps_long_verify.py                 web check of the picked reference points (tournants, episodes)
  temps_long_deck_check.py             `check` for a temps_long deck: cross-slide rules
  anatomie_chiffre_adapt_agent.py      adapt() for anatomie_chiffre: its own guided steps (prompts/anatomie_chiffre_steps/), choose/more/fix
  trois_regards_adapt_agent.py         adapt() for trois_regards: its own guided steps (prompts/trois_regards_steps/), choose/more/fix; one pick per prism slot
  trois_regards_prisms.py              PRISMS: the 7 prisms (name, definition, lens icon)
  trois_regards_verify.py              web check of the sources named in the clues (indices) of the picked tensions grid
  media_trend_agent.py
extractors/
  registry.py                      FORMATS: format name → (adapt agent, extractor, renderer) modules
  instagram_carousel.py            extract(): trim to the 3 most-decisive review dimensions + 1 go_further (both carousel formats)
  newsletter.py                    extract(): passthrough → NewsletterDocument
  cadrage.py                       extract(): passthrough → CadrageDocument
  temps_long.py                    extract(): passthrough → TempsLongDocument
  anatomie_chiffre.py              extract(): passthrough → AnatomieChiffreDocument
  trois_regards.py                 extract(): passthrough → TroisRegardsDocument
renderer/
  instagram_carousel/              the carousel renderer + shared helpers:
    _shared.py                     _env / _weighted_quality / _LOGO_DATA_URL / TYPE_FR (shared)
    optimized.py                   10-slide optimized deck
    cadrage.py                     the CADRAGE & LOGIQUE renderer (templates/article_carousel_cadrage_v1/ for slides 2–6; slides 1 and 7 are the optimized hook and CTA)
    temps_long.py                  the TEMPS LONG renderer (templates/article_carousel_temps_long_v1/ for slides 2–6; slides 1 and 7 are the optimized hook and CTA)
    anatomie_chiffre.py            the ANATOMIE D'UN CHIFFRE renderer (templates/article_carousel_anatomie_chiffre_v1/ for slides 2–5, reusing the cadrage `_argument.css` and notes macro; slides 1 and 6 are the optimized hook and CTA)
    trois_regards.py               the TROIS REGARDS renderer (slide 2 is the temps_long `02_position.html`; templates/article_carousel_trois_regards_v1/ for slides 3–6 (the three « Le prisme … » slides, the tensions grid); slides 1 and 7 are the optimized hook and CTA)
    templates/article_carousel_optimized_v0/  Jinja2 templates → PNG slides (1080×1350)
  newsletter/                      newsletter renderer → Markdown + HTML (rich + email); dark brand
  shoot.py                         Playwright HTML → PNG (carousel slides)
models/
  full_analysis.py                 ArticleFullAnalysis (analysis schema)
  instagram_carousel_presentation.py  InstagramCarouselPresentation / Document
  newsletter_presentation.py       NewsletterPresentation / NewsletterDocument
  cadrage_presentation.py          CadragePresentation / CadrageDocument
  temps_long_presentation.py       TempsLongPresentation / TempsLongDocument
  anatomie_chiffre_presentation.py AnatomieChiffrePresentation / AnatomieChiffreDocument
  trois_regards_presentation.py    TroisRegardsPresentation / TroisRegardsDocument
tools/
  scrape.py, search.py, validate.py, verify.py, graph_generator.py
  feeds.py                         curated free FR news feeds → candidates / fetch
```

**Data flow (`produce`):** `analyze_for_full_analysis(text)` → `ArticleFullAnalysis` JSON → `adapt()` → presentation JSON → `extract()` → trimmed render document (`extract.json`) → `render_from_json()` → PNG slides.

**Carousel adapt, eight guided steps** (`agent/instagram_carousel_adapt_agent.py` assembles the deck;
`agent/carousel_steps/` — `steps.py` the step table, `store.py` files/stamps/log, `run.py` the
options, choices and `fix`; prompts in `agent/prompts/carousel_steps/`, with worked `examples/`).
Slide 8 is written first and everything is written toward it: `question` (« La question »), `enjeu`
(root issue), `idees` (the 3 `essentiel` claims), `moments` (the reading-beat pool, 3 selected),
`contexte` (the repères facts), `socle` (thesis, présupposés, objection), `hook`, then `writing`
(réflexes/answers, slides 2–3, sources, caption — no pause). Steps 1–7 each produce several
**options**, each with its text, a **reason** (↳) and a ★ recommended one; the author picks, edits
or asks for others. The deck rulebook is split in two (`split_rules`): **hard checks** make a generated
step repair itself, but on the author's own pick or rewrite they come back as ⚠ warnings (the author has
the last word; `choose` refuses only slot-rule violations); **editorial flags** are advisory (⚠ on an option, listed
under « editorial (advisory) » by `check`). Every choice, edit and reason is appended to
`<format>/choices.jsonl`; reusable corrections are promoted by hand to `prompts/carousel_steps/examples/`.
Each step gets the earlier ones as fixed context, the article text and only its slice of the analysis
(never review, ethics, blend, distill or guide). Steps are cached in `<format>/adapt_steps/` with an
input hash: a hand-edited or chosen step is kept and the later ones rerun.
- `--guided` stops at each step with no pick (options on stdout, the exact `choose` command on stderr);
  `choose <fmt_dir> <step> --pick a,b [--edit ID=TEXT] [--reason …]` or `--more [--remark …]`, then
  rerun. Without `--guided`, `adapt`/`produce` run unattended on the recommended picks;
  `--stop-after <step>` stops after any of steps 1–7 for review.
- `fix <fmt_dir> <field> "<text>"` rewrites one deck field and re-stamps the steps without regenerating.
- `check <extract.json> [--reader]` runs the hard checks and lists the flags; `--reader` adds the
  model-driven reader and fidelity passes. The skill `.claude/skills/carousel-guided/` drives the loop.
Fields no slide shows (watch_out, strengths, distill_points, payoff, interest, the
*_next_slide_hook…) are no longer produced; they stay in the model as empty defaults so older decks load.

**Instructions (editorial angle):** `--instructions`/`--instructions-file` on `analyze` or `produce`
reach every analysis step and are kept in `analysis.json` (`article_metadata.extra_instructions`),
so the adapt agent leads its prompt with them. `steps/` is stamped with their hash
(`instructions.sha256`); changed instructions move the cached steps to `steps/stale_<hash>/`
and every step reruns.

**Output layout:** one folder per analysis (see `_layout()` in `main.py`):
```
samples/<medium>/<stem>/     (medium = articles | podcasts | videos)
  <stem>.txt               the input (image.png, background.png, instructions.txt beside it)
  analysis.json            ArticleFullAnalysis
  steps/                   step1…step9 cache
  <format>/                e.g. instagram_carousel_optimized/
    adapt_steps/           1_question … 8_writing .json (+ .sha256); stale_legacy/ holds the old 3-stage files
    choices.jsonl          the choice log (picks, edits, reasons)
    adapt.json             InstagramCarouselPresentation
    extract.json           InstagramCarouselDocument
    slides/                NN_*.png
```

**Formats:** registered in `extractors/registry.py`, all fed by the same `analyze`. The carousel has its own `adapt()` copy; the newsletter has its own prose adapt.
- `instagram_carousel_optimized` (default) — 9-slide "lens to read with" deck on the `article_carousel_optimized_v0` templates: Hook (source pill, title, promise) → En bref (lede + the 3 numbered `essentiel` claims; the prose `essentiel_summary` is the fallback) → À savoir, à se demander (`reperes_facts`: 2–3 labelled facts chosen from the analysis's context, then the réflexes) → 3 moments (one réflexe each, its question repeated word for word) → Le socle de l'argument (thesis, présupposés, objection) → Prise de recul (enjeu de fond, « La question », and under it `cta.where_to_look`: 2–3 sources to find answers; the `go_further` items that carry a URL are appended to the post caption by `caption_with_sources()`) → CTA. The bird and the wire: the Sing Sing bird leaves the wordmark and perches on each slide's key element (marked `data-perch` in the template, fixed per slide type: the idées-clés card, the réflexes card, each moment's question, the targeted pillar, the enjeu card); `renderer/shoot.py` measures every perch and draws one gold wire through the whole deck (`wire_paths()`), level along each perch and continuous at every slide edge, so a swipe reads it unbroken. A slide without a perch is crossed along its foot. Before the perches are measured, `shoot.py` fits each slide's foot (`_FIT`): the stage marked `data-fit` is pinned at its title, and the room left above the page number (less 40 px) is shared between the blocks marked `data-gap`, +60 px each at most — spacing only, type sizes never change; question and answer get no extra gap between them. Visual layer: each réflexe wears its lens icon (`CANONICAL_LENSES[…]["icon_svg"]`) on slide 3 and on its moment; a moment may draw one sourced count as people or things (`reading_beats[].pictogram`, max one per deck, never a relative risk); slide 7 draws the présupposés as pillars under the thesis, and the bird perches on the pillar `steel_man.targets` names. On slides 1 and 9 the bird sits at home, beside the wordmark top right (the original logo), and those slides carry no wire: it runs from the first perch to the last, starting and ending at the text column's edge. The renderer builds the slide list conditionally (numbering adapts); reading beats are a candidate pool (`selected`), and the réflexe lenses are derived from the selected beats. The axis: slide 8 (`root_issue` + « La question ») is written first and the deck leads to it — each selected beat carries an `axis_link` (not rendered), and an editorial flag (advisory, not a hard check) marks the hook, an `essentiel` bullet or the slide-7 thesis that shares no key word with slide 8. Quotes from a non-French source show in French (`quote`), with the passage as written in `quote_original`, which the verbatim checks match.
  Clues: each moment's `answer` and each `cta.where_to_look` should name where to check (an institution, a document, a figure, a person quoted); `_clue_errors()` flags one that does not — an editorial flag (advisory), not a hard check.
- `cadrage_logique` — the CADRAGE & LOGIQUE archetype (`docs/carousels_archetypes.md`): 7 slides that follow an opinion
  piece, an essay or an expert interview, in the optimized deck's visual language — Hook (identical to the optimized one,
  photo included; pill = medium · source · date, no length; the title is the speaker's central claim in « », the promise
  « Décryptage d'une prise de position sur … ») → Le constat (the speaker's figures or short facts in monospace + what they establish) →
  La thèse (thesis, solution, one remark/source line under it) → L'angle mort (what the solution risks, from outside the
  speaker's frame: a catchy title, a first card — the regularity: claim, detail, remarks and sources — and a second
  card on a *different* blind spot, never a restatement or a description of a process: `second_claim`, `second_detail`, `second_note1`/`second_note2`) → Le dépassement (a lead line, three
  levers that attenuate the risk — « atténuer », never « sans » — and cost something; at least one acts on the *how* of the decision: criteria, advice, passerelles; the first lever may carry one remark/source line, `lever1_note`, shown under it) → La boussole (the arbitrage: a
  gauge with a pointer, two questions side by side — two positions of one variable, e.g. when to select, never two values — each with a pour ✓ and a contre ✕) → CTA (identical to the optimized
  one). Seven guided steps (`agent/cadrage_adapt_agent.py`, prompts in `agent/prompts/cadrage_steps/`): `axe` first — the arbitrage
  the deck leads to (a variable, two positions, the speaker's thesis), never rendered, fixed context for every later step, which an
  advisory flag checks slide by slide — then in slide order `constat`, `these`, `angle_mort`, `depassement`, `boussole`, `hook`; `writing` (the caption) follows without a pause.
  Slides 2–3 stay in the speaker's frame (figures and facts as he gives them); slides 4–6 leave it and rest on the model's general
  knowledge — sources there are organisations and series to consult, named, never a URL or a figure, and unverified.
  An option's fields are flat strings so `--edit ID.field=TEXT` and `fix` reach them: a figure is `valeur | libellé |
  comparaison` (value ≤9 characters) (`fig1`…`fig4`), a note `source | texte` or `remarque | texte` (`note1`…`note3`, shown with a lens or a
  bookmark icon), a lever `titre | détail` (`lever1`…`lever3`). Same semantics as the 9-slide guided run — options with a
  reason and a ★, `choose --pick/--edit/--more`, `fix <fmt_dir> <step>.<field>` (e.g. `constat.fig1`,
  `these.solution_claim`, `boussole.pro2`, `hook.title`) or `caption`, choice log in `choices.jsonl` — but a module of its
  own: `agent/carousel_steps` is bound to the 9-slide deck. Hard rules (word caps, figure/note/lever format, no accusing
  word — *biais, manipulation, mensonge, trompeur* — outside « », 4 hashtags) repair a generated option and come back as ⚠
  on the author's pick; one advisory flag (a figure that does not appear as digits in the source — a figure spelled out
  in words is flagged too, check it). Layout: the title sits at the same height on slides 2–6 and the gaps are fixed
  (`_argument.css` tokens), so nothing stretches; the bird perches on slides 2–5 (the wire runs through them) and on the
  boussole's pointer, which has no wire. Three text tiers inside a card: the heading, the claim (bold), the detail (one
  size down); sources are the third, small and dim. `check` does not cover this format. Output folder:
  `<stem>/cadrage_logique/`.
- `temps_long` — the TEMPS LONG archetype (full spec: `docs/temps_long_spec.md`; author-facing description: `docs/carousels_archetypes.md`): use it when the perspective of time is particularly helpful to analyse a position — the media or its author asserts a novelty, a trend, a drift or a return that dated reference points (episodes, texts) can test; without such an assertion it is a poor fit. 7 slides in the optimized deck's visual language: hook (the optimized one, photo included) → position → the lecture slide and the two timelines (episodes, tournants) → pièges → CTA (the optimized one). One word per idea: *critères* (what each camp applies), *signes* (the second camp's), *étiquettes* (the marks on the timelines, « pills » in the code), *ligne* (the limit the question looks for).
  Steps (`agent/temps_long_adapt_agent.py`, prompts in `agent/prompts/temps_long_steps/`): `axe` first — never rendered: the hook's fact, the question the deck tests, the **move** that answers it (`forme`, `seuil`, … — only these two have a template and layout tests), the criteria — then `position`, `lecture`, `episodes`, `tournants`, `pieges`, `hook`, then `writing` (the caption, no pause). The write order depends on the move (`_WRITE_ORDER`): `seuil` writes `lecture` before the timelines, the others after. Same guided semantics as the other archetypes: options with a reason and a ★, `choose --pick/--edit/--more`, `fix <fmt_dir> <step>.<field>` or `caption`, choice log in `choices.jsonl`. Output folder `<stem>/temps_long/`.
  Rules to keep when changing it: (1) a character cap is never typed in a prompt — write `{{cap:step.field}}`, filled from the rules (`prompt_caps()`); a test refuses a literal « ≤N ». (2) Every text field is capped to fit its lines and guarded by the seeded worst-case render tests in `tests/test_temps_long.py`: change a cap or a layout, rerun them. (3) Everything outside the quoted media word is the model's general knowledge: dates only, never a trend figure; the web check after a pick on `tournants` / `episodes` (`agent/temps_long_verify.py`) is advisory. (4) Hard rules repair a generated option and come back as ⚠ on the author's pick; flags are advice. (5) For wording on an early step use `fix`, not `choose --edit` (it re-runs the later steps). (6) `python main.py check <extract.json>` runs the deck-level check (`agent/temps_long_deck_check.py`), no model call. The author's past decisions live in `agent/prompts/temps_long_steps/examples/`.
- `anatomie_chiffre` — the ANATOMIE D'UN CHIFFRE archetype (`docs/carousels_archetypes.md`): 6 slides that follow a striking figure
  (a statistic, a poll, a ranking) and the story the article builds on it, in the optimized deck's visual language — Hook (identical to the optimized one; the title is the raw figure
  in « », the promise « <sujet> : ce que le chiffre dit, et ce qu'on en conclut ») → Les chiffres (slide 2, in the article's frame: 3–4 monospace figure cards
  `valeur | libellé | comparaison` as the article gives them, the title saying what is measured (not the movement), the first the key figure drawn big showing « avant → après » (« 9 → 15 ») with a plain-sentence label, one remark line under it glossing the statistical term (« médian : … »), the optional fourth an overall reference figure drawn small; a recomputed figure must say « calculé ») → Le fil logique (slide 3, in frame: the title is specific to the article — it names the elements of the story the cards unroll (« Actifs en hausse, économie « en G » »), never the key figure again — then 2–3 same-style cards
  `type | texte | remarque`, type `explication` / `interpretation` / `consequence` (each its own), two lines at most, the remark saying the statement's status and what it depends on, never a shortfall; quoted passages verified word for word) → Ce que ces chiffres
  ne comptent pas (slide 4, out of frame, **no digit**: four blind spots of *these* figures — how they are computed, what is missing — each a card with a short assertion as its title (`headN`, ≤36 characters), the same blind spot as a question ending in « ? » (`claimN`) as its comment, and a line saying how to validate or invalidate its assumption (no sources); the title names the article's interpretation as one among others; its `ouvre` pair is not drawn) → Les alternatives (slide 5, out of frame, no digit: a question about the alternative to the article's reading (title ≤30 characters, one line), a lead line sharing the frame of the cards (`lead`, ≤64), then four icon cards
  `nom | hypothèse | chiffre à suivre`, one per alternative of the axe; the hypothesis is one line (≤56) and the last part starts with the bold measure and says, in the conditional, what one would observe if the alternative held — no « validé »; each alternative follows from the blind spots of slide 4 whose `ouvre` pair names it) → CTA (identical to the optimized one; its « Commentez — … » line is fixed: « quelle lecture les séries que vous trouverez
  soutiennent-elles ? »). Six guided steps (`agent/anatomie_chiffre_adapt_agent.py`, prompts in `agent/prompts/anatomie_chiffre_steps/`): `axe` first — never rendered as such, the fact to
  explain, the article's own reading (`article`) and four alternatives (`lecture1`…`lecture4`, each `nom | formule` and explaining the rise, never a mere measurement problem), the fixed context of every later step — then in slide order
  `chiffres`, `recit`, `angle_mort`, `lectures`, `hook`; `writing` (the caption) follows without a pause. Same guided semantics as the other archetypes (options with a reason and a ★,
  `choose --pick/--edit/--more`, `fix <fmt_dir> <step>.<field>` or `caption` — `fix` re-checks the rewritten field and every later step and prints the hard-rule failures as ⚠, like `choose` —, choice log in `choices.jsonl`). Flat option strings: a figure `fig1`…`fig4` (`fig1` the key figure, `fig4` optional), a row `row1`…`row3` (`type | texte | remarque`),
  a reading `article`, `lecture1`…`lecture4` (`nom | formule`; on slide 5 `nom | hypothèse | **mesure** : il <conditionnel> …`; older decks carry three), the slide 2 note `note1` (`remarque | texte`), a blind spot `headN`/`claimN`/`verifierN`/`ouvreN` (N = 1–4; `ouvreN` = two reading numbers (`1,3`, not drawn). Hard rules (repair a generated option,
  ⚠ on the author's pick): every rendered field is capped in characters (`_CAPS`, and `_PART_CAPS` per part of a « a | b | c » field), measured on the rendered slides and guarded by a
  seeded worst-case render test; figure, row, reading and note formats; each `recit` row has its own type and a remark; each blind-spot claim ends in « ? » and its sources hold no URL; each reading's last part starts with the measure in bold, and the slide 5 title is a question; the four `ouvre` pairs are two distinct readings each and **together cover the four
  readings** (the link between slides 4 and 5); the reading names of `lectures` equal the axe's; no digit on slides 4 and 5; no accusing word outside « »; 4 hashtags. Advisory flags: a slide 5 alternative sharing no key word with the slide 4 blind spots that leave it open; a slide 3 remark that names a shortfall (« pas », « sans » — it must say the statement's status, never criticise the author), a figure
  not found as written in the source (a recomputed one must say « calculé »), a quoted passage not in the source, an article reading (axe `article`) sharing no
  key word with an explanation or interpretation row, a hook title that is not a figure in « », a statistical term (« médian »…) in a figure that `note1` does not gloss. Slides 4–5 rest on the model's general knowledge: the clues there are unverified pointers.
  The bird perches on the figure card (slide 2), the story card (slide 3) and the first blind-spot card (slide 4) and the first alternative card (slide 5); the wire runs through them. `check` does not cover
  this format. Output folder: `<stem>/anatomie_chiffre/`.
- `trois_regards` — the TROIS REGARDS archetype (`docs/carousels_archetypes.md`; spec `docs/superpowers/specs/2026-11-12-trois-regards-design.md`, « Revision 4 »): 7 slides for a large social phenomenon (housing, AI, birth rate) that the article treats through one discipline; the deck shows that the answer to one broad question changes with the discipline called in, and which one the article used — in the optimized deck's visual language. The arc: the article's account (2), three regards each answer the question in full (3–5), they are confronted on three topics (6). Hook (slide 1, identical to the optimized one, photo included; pill = medium · source · date, no length; the title is **the deck's question**, a broad question each prism can answer, not the article's narrower one, ending in « ? », not in « »; the promise has a fixed shape: « Trois regards sur <sujet> ; à vous d'en juger. », the subject being the axe's — a no-break space before « ; » or a typographic ’ is accepted; the renderer sets a no-break space before « ; : ? ! » on the hook's title and promise) → La position (slide 2, in the article's frame, drawn with the trois_regards copy of the `temps_long` position template, `02_position.html`: kicker — « Ce que dit l'article » when empty —, title with a gold passage, a lead saying which narrower question the article answers, three or four `libellé | texte` cards (the fourth optional) in this order and with these labels: « Le déclencheur » (what happened, when), « Les causes avancées » (the causes, with the source the article names), « Les réponses des acteurs » (who does or says what), « Les conséquences » (what follows); actors, dates and sources named, quotes verbatim, a figure only as the article gives it) → three prism slides (slides 3–5, out of frame: kicker « Le prisme <nom> » with the prism's icon; the prism's **answer** to the deck's question as title; a two-line `lead` that complements the title; **four cards with fixed roles**, the renderer tagging each on the head's line — ORIGINE · / MÉCANISME · / AMPLIFICATEUR · / CE QU'ON EN VOIT · — each a `head` (a short, concrete claim a reader could contradict) and an `answer` (**one sentence** with a causal link, in the regard's voice, never an established fact, never a question); no clue line, no « regard du média » badge: `axe.media` stays as non-rendered context) → Les tensions (slide 6, out of frame: a **grid** — a header row naming the three regards once (icon + name, in the axe's order), a left column with three precise `topic`s of the case, nine cells holding one short `view` per topic and prism, without the discipline's name, and under each row a thin clue line « source | what to read »; no verdict, no « il faut ») → CTA (slide 7, identical to the optimized one; its « Commentez — … » line is the axe's `closing`, lowercased: it asks which regard was missing from the reader's reading of the article, names the three prisms and ends in « ? »). Slides 2–6 share one title block (kicker, title centred at 70 px, a two-line lead, a short gold bar); the deck's question appears only on the hook, in the position lead and in the closing line. Catalogue of 7 prisms (`agent/trois_regards_prisms.py`, `PRISMS`, its own icons, not `CANONICAL_LENSES`): `economique`, `sociologique`, `juridique`, `historique` (dated landmarks only, never a trend figure), `politique`, `ecologique`, `technologique`. Six guided steps (`agent/trois_regards_adapt_agent.py`, prompts in `agent/prompts/trois_regards_steps/`): `axe` first — never rendered as such: the deck's question, the article's own question, the subject, three distinct prisms of the catalogue, the media's prism (always the closest one; when none dominates its `media_grounding` says so) and the sentence grounding it, the closing line; options are alternative prism sets — then `position`, `prismes` (one pause for slides 3–5), `tensions`, `hook`; `writing` (the caption) follows without a pause. Same guided semantics as the other archetypes (options with a reason and a ★, `choose --pick/--edit/--more`, `fix <fmt_dir> <step>.<field>` or `caption` — `fix` re-checks the rewritten field and the re-stamped later steps and prints the hard-rule failures as ⚠; a fix of `axe.prism1`…`prism3` or `axe.media` re-stamps nothing, the later steps rerun —, choice log in `choices.jsonl`). `prismes` is picked **one option per prism slot**: slot `pN` writes the Nth prism of the axe, its options are `p1a`, `p1b`, …, and `--pick p1b,p2a,p3c` must keep exactly one per slot (`choose` refuses zero or two); `--more --prism <p1|p2|p3 or the prism id>` regenerates that prism's options only, the others keeping their options and picks (shown « ✔ gardée »): while that prism awaits its pick, `choose … prismes --pick <its id>` names only the missing slot and the kept picks complete the set (naming a kept slot replaces its pick), and `fix` says which `choose` to run; `fix <fmt_dir> prismes.<slot>.<field>` (e.g. `prismes.p2.head1`, `prismes.p2.answer3`), `fix <fmt_dir> tensions.<field>` (e.g. `tensions.view2_3`, `tensions.topic1`), `fix <fmt_dir> position.<field>` (e.g. `position.card3`). Flat option strings: axe `question`, `article_question`, `subject`, `prism1`…`prism3`, `media`, `media_grounding`, `closing`; position `kicker`, `title`, `lead`, `card1`…`card4` (`libellé | texte`, `card4` optional); a prism (`PrismesOption`) `title`, `lead`, `head1`…`head4`, `answer1`…`answer4` (card N = role N); tensions (`TensionsOption`) `title`, `lead`, `topic1`…`topic3`, `view1_1`…`view3_3` (`viewN_P` = topic N, the axe's prism P), `indice1`…`indice3` (« source | find »); hook `title`, `promise`. Hard rules (repair a generated option, ⚠ on the author's pick): every rendered field capped in characters (`_CAPS` / `_PART_CAPS`: axe question 60, subject 36, closing 110, media_grounding 120; position kicker 26, title 32, lead 90, card label 24 / text 150; prism title 38, lead 95, head 30, answer 120; tensions title 28, lead 90, topic 40, view 45, clue source 30 / find 60; hook title 70, promise 100); a cap is never typed in a prompt — write `{{cap:step.field}}`, filled from the rules (`prompt_caps()`), a test refuses a literal « ≤N » — and every cap is guarded by the seeded worst-case render tests in `tests/test_trois_regards.py`: change a cap or a layout, rerun them; required fields (all but `card4`; every prism `lead`, answer and tension view is required); three distinct prisms of the catalogue, the media's one of them; the `a | b` formats (both parts of a clue and of a position card); a `lead` is a line, never a question; an `answerN` is never a question; the deck's question, the closing line and the hook title end in « ? »; a tension view may not contain the name of its own discipline (the first six letters of the axe's prism name); the promise's fixed shape; no accusing word (*biais, manipulation, mensonge, trompeur, fallacieux, sophisme*) and no wording that blames the article (*oublie, ignore, omet, néglige, ne dit pas*) outside « »; no prescriptive verb (*il faut, il faudrait, faut-il, doit, devrait*) on any tensions field; no URL in a clue (a bare domain such as `ine.es` counts); **the figures rule**: on the position, the prism slides and the tensions a digit string is allowed only if it is written in the article text (`_unsourced_figures`, with no article text only a year, a date or a reference passes), and on the axe's question only a year (1500–2099), a date (« 15 mai », « 1er ») or a reference (« 12/2023 »); 4 hashtags. Advisory flags: no prism clearly dominates the article (the media's prism is the closest); a closing line holding « ou » (may read binary), ranking the regards, or not naming the three prisms; a prism or tensions title or lead repeating the deck's question (equal, or three key words in common); a prism `answer` with no causal marker (donc, parce que, faute de, quand, si, car, ce qui, d'où, entraîne…, or a colon) or restating its `head` (key-word overlap ≥ 0.8); a prism slide sharing no key word with the article; two cards of a prism slide opening their `head` with the same word; the subject phrase appearing in two or more cards of a slide; two prism slides saying nearly the same thing; two views of one topic saying nearly the same thing; a prism title naming a capitalised word after its first (a person, a place: say it with a role or an institution); an acronym of the position cards or of a prism slide that is never spelled out on the slide (« Parti socialiste (PSOE) »; UE, ONU, PIB, TVA, SMIC, RSA, USA, IA, OTAN are exempt); a quoted passage of the position not found word for word in the source; a promise whose subject is not the axe's. After a pick on `tensions`, the source of every clue (the part before « | ») is checked on the web (`agent/trois_regards_verify.py`, through `tools/verify.py`; `VERIFIED_STEPS = ("tensions",)`), advisory: kept beside the step (`<n>_<step>.verification.json`, outside the stamp) and in the choice log, « no result found » is a ⚠ that says the search is built for news and may miss well-known institutions; skipped with `--no-api`. Slides 3–6 rest on the model's general knowledge plus the article's own facts and stay unverified except for those clues. Layout: the bird perches on the first card of each of slides 2–5, on the grid's top edge on slide 6, the wire running along it and the title above; the first prism card starts at the same height on the three prism slides. Older decks still load and render with their own templates: the first version (matrix as slide 6, prism `question` / `lines` / `sources`) and revision 3 (`limites` as slide 7, `claim` and clue on the prism cards, `media_note` and the « Le regard du média » badge, pair tags on the tensions); the renderer picks the revision-4 layout when a tension card carries `views`. An old `adapt_steps/` folder (`5_limites.json`, `5_arbitrage.json`, `4_matrice.json`) is never read: the steps whose fields changed are retired to `stale_<hash>/` and rerun. `check` does not cover this format. Output folder: `<stem>/trois_regards/`.
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
hook title (`sub_topic`), the promise — `hook.subtitle` (« Comprendre … ») — then « Glissez → », and the
sign-off line « Sing, little bird, sing » as the footer; a deck may add a second paragraph under the promise (`tagline`, 34 px, two lines at most, key words in gold `**…**`) — the `temps_long` adds its own `tagline` (empty = « Des épisodes, des textes, trois lectures pour **en juger**. ») and its promise is ≤100 characters, in plain words. On a full-bleed photo (`background.*`) the title sits ON the
photo (84/72/60 px by length, with a soft veil), the source block under it, then the promise below on black, sized by length
(72 px up to 45 characters, 62 up to 64, 52 up to 100, then 44); the photo reaches about 70 % of the slide height.
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
