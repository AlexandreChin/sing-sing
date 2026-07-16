# Candidate Program Analysis — Project Overview

**Date:** 2026-07-15
**Status:** Design approved; decomposed into 3 sub-projects, building 1 → 2 → 3.

## Goal

A new **hors-série** content line for sing-sing: for the 2027 French
presidential election, produce a critical analysis of **one candidate's whole
program** across the major policy domains, published as **two outputs**:

- a **full newsletter** (the destination — the complete analysis in prose), and
- a **teaser carousel** (the funnel — a short, breadth-forward Instagram deck
  whose job is to intrigue and drive newsletter subscriptions).

The carousel does not deliver the full analysis; it teases it. The newsletter
holds it.

## Content family

sing-sing has two content families (see memory `content-families`):

1. **Regular — article analysis** (`produce`): ingest a news article, critique
   its journalism. The existing pipeline.
2. **Hors-série — generated analysis** (new): the agent analyzes a *policy
   program document* (not a journalism piece) with a policy-critique lens and
   produces a multi-output analytical product (newsletter + teaser carousel). It
   still generates its own expert grounding via web search. The candidate-program
   analysis is the first instance. (Both families now take a text file as input;
   the divergence is the analytical structure and the multi-output, not the input
   mechanism.)

The shared "hors-série family" abstraction is deliberately deferred (YAGNI)
until a second hors-série type exists. Built as a standalone track.

## Unit & scope

- **Unit:** one carousel/newsletter = **one candidate**, covering all core
  domains. (Not one-topic-per-carousel — that was rejected as N×M combinatorial
  explosion.) ≈ one deck per candidate (~6 candidates).
- **Input:** the candidate's **program provided as a text file** (like today's
  `article.txt`) — the candidate's own positions are read from the document, not
  researched. The agent still **web-searches for independent specialist sources**
  (`tools/search.py` + `tools/scrape.py`) to ground the *critical* judgments
  (contre-expertise, failles, incidence), which the candidate's document cannot
  supply. Hybrid input: program-in from file, expert grounding from search.
- **Editorial stance:** explainer **+ critical analysis** — sing-sing's
  analytical DNA (diagnostic critique, failles, incidence, verdict).

## Core policy domains (fixed set of 12)

Every candidate's analysis covers the same domains, so decks stay comparable
across candidates:

1. Travail / Emploi
2. Pouvoir d'achat
3. Fiscalité / Impôts
4. Économie & finances publiques (dette, industrie, croissance)
5. Retraites
6. Logement
7. Écologie
8. Santé & Éducation
9. Société (droits des femmes, LGBT+, cause animale…)
10. Immigration
11. Sécurité & Justice
12. Europe / Institutions & politique internationale

(Editable — this list lives in one constant, `CORE_DOMAINS`.)

**Carousel-length note (for sub-project 3):** 12 domains is fine for the
analysis and the full newsletter, but one teaser slide per domain would make a
~17-slide carousel — too long for a hook. **Decision:** the teaser carousel
groups the 12 domains into **4 thematic clusters**, one panorama slide each:

1. **Économie & travail** — Travail/Emploi, Pouvoir d'achat, Fiscalité,
   Économie & finances publiques, Retraites
2. **Cadre de vie** — Logement, Écologie, Santé & Éducation
3. **Société & régalien** — Société, Immigration, Sécurité & Justice
4. **France dans le monde** — Europe / Institutions & politique internationale

Each cluster slide shows a few headline measures + one hook (deliberately
incomplete). This keeps breadth visible while cutting the panorama to 4 slides.
Target teaser shape (~9 slides): Hook → L'essentiel → (optional) 3 trouvailles →
4 cluster slides → Verdict teaser → CTA. Finalize when sub-project 3 is designed.

## Architecture (approach A — parallel track, reuse renderers)

The existing pipeline is two layers: `analyze` → format-agnostic analysis;
then per-format `adapt → extract → render`. The program track **diverges at the
`analyze` layer** (input is a candidate, it researches, the analytical structure
is policy-native) but **reuses the downstream rendering layers** (newsletter
renderer, carousel templates). The article pipeline is left untouched.

Journalism-only concepts are dropped: deontology, emotional register,
cadrage/title analysis, the ethics slide. Cui bono is kept but reframed as
*economic incidence* (who benefits / who pays).

## Decomposition

### Sub-project 1 — Program analysis pipeline (build first)

`analyze_program(candidate)` → `ProgramFullAnalysis`. The deep analytical
backbone both outputs consume. See
`2026-07-15-program-analysis-pipeline-design.md`.

### Sub-project 2 — Program newsletter (build second)

Renders `ProgramFullAnalysis` as the full prose analysis, reusing the existing
newsletter renderer infrastructure (`renderer/newsletter/`). Its own adapt agent
+ presentation model. The destination the carousel points at. Detailed spec to
be written when this sub-project starts.

### Sub-project 3 — Program teaser carousel (build third)

A breadth-forward teaser deck: Hook → L'essentiel (worldview) → Ce qu'on a
analysé (domain panorama) → teased findings across the domains (headline
measure + a hook, deliberately incomplete) → Verdict teaser → **CTA to subscribe
to the newsletter**. Given 12 domains, the panorama must **group or select**
domains rather than one-slide-each (see the length note above); exact slide
count is a sub-project-3 design decision. Reuses the
`article_carousel_optimized_v0` templates. Detailed spec to be written when this
sub-project starts.

**Build order rationale (1 → 2 → 3):** the backbone must exist before either
renderer; the newsletter (destination) must exist before the carousel (funnel)
so the "subscribe for the full analysis" CTA points at something real.

## Cross-cutting decisions (apply to all sub-projects)

- **Strict sourcing:** every measure and root cause references ≥1 gathered
  source URL; every critical judgment (contre-expertise, faille, incidence)
  cites ≥1 independent specialist source (economist, scientist, NGO,
  institutional report — not the candidate). Enforced by an assembly-time audit.
- **Neutral tone:** every step prompt gets an explicit even-handedness
  instruction — critique grounded only in stated/sourced facts, no editorializing
  about the candidate as a person, no partisan framing. The program track uses
  its **own system prompt** (the article system prompt is journalism-specific and
  forbids direct verdicts, which a program verdict needs).
- **Output layout:** reuse `_layout()` with the stem slugified from the
  candidate name: `samples/outputs/<candidate>/{analysis.json, steps/,
  <format>/…}`.
