# Program Analysis Pipeline — Design (Sub-project 1)

**Date:** 2026-07-15
**Status:** Approved (design), pending implementation plan
**Parent:** `2026-07-15-candidate-program-overview.md`

## Goal

Build `analyze_program(candidate)` → `ProgramFullAnalysis`: a deep, per-candidate
critical analysis of the candidate's whole program across the 12 core policy
domains. This is the shared backbone that both the newsletter (sub-project 2)
and the teaser carousel (sub-project 3) will consume. This sub-project produces
**only the analysis JSON** — no rendering.

## Scope

- **In:** the analysis agent, its steps, the `ProgramFullAnalysis` schema, the
  research/gather infrastructure, the assembly-time sourcing audit, an
  `--no-api` end-to-end test on cached fixtures, and a CLI entry point to run it.
- **Out:** newsletter rendering, carousel rendering, adapt/extract layers (those
  are sub-projects 2 and 3).

## Data flow

Input is the candidate's **program text file**. The candidate's positions are
read from the document; the *critical* steps (3, 4-faille, 5) additionally
web-search for independent specialist sources.

```
ProgramAnalysisInput(candidate, program_text)
  → step1 ingest & structure (parse the document → domain-tagged statements; NO web search)
  → step2 vision & diagnostic
  → step3 contre-expertise (test the diagnostic; web-search specialist sources)
  → step4 per-topic analysis (loop over 12 domains; failles web-search specialist sources)
  → step5 incidence (program-level winners/payers; web-search specialist sources)
  → step6 review dimensions (4)
  → step7 distill + verdict
  → assemble + assign IDs + sourcing audit
  → ProgramFullAnalysis
```

Per-step JSON cache in `steps/` (mirrors the article pipeline's `_load_or_run`),
so a rerun resumes from cache and `--no-api` tests run against fixtures.

## Schema (`models/program_analysis.py`)

New module. Policy-native structures; reuses the `confidence` →
`confidence_label` computed-field pattern from `models/full_analysis.py`.

```
ProgramAnalysisInput(candidate: str, program_text: str, extra_instructions: str | None)

# sourcing primitives
SourceRef(quote: str, url: str | None, outlet: str | None)   # candidate statement: verbatim passage
                                                             # from the program document; url optional
SpecialistSource(name: str, kind: Literal["academic","official_data","ngo",
                 "think_tank","media","other"], url: str, finding: str)

# step 1
SourcedStatement(id: str, domain: str, quote: str, source: SourceRef)
ProgramResearch(statements: list[SourcedStatement])

# step 2 — vision + overall diagnostic (merged worldview beat)
RootCause(id: str, cause: str, sources: list[SourceRef])     # what the candidate says is broken
VisionDiagnostic(vision: str,                                # the throughline / where they'd take the country
                 root_causes: list[RootCause],
                 values: str | None)

# step 3 — contre-expertise (tests the diagnostic)
DiagnosticAssessmentItem(id: str, root_cause_id: str, verdict: str,
                         confidence: int | None,             # → confidence_label computed
                         expert_sources: list[SpecialistSource])
ContreExpertise(items: list[DiagnosticAssessmentItem])

# step 4 — per-topic analysis (one per core domain)
Measure(id: str, measure: str, detail: str | None, sources: list[SourceRef])
Faille(kind: Literal["efficacy","funding","feasibility","coherence","legal"],
       label: str, explanation: str, expert_sources: list[SpecialistSource])
TopicAnalysis(domain: str, headline_measures: list[Measure], faille: Faille)
ProgramTopics(topics: list[TopicAnalysis])                   # exactly 12, one per domain

# step 5 — incidence (program-level)
IncidenceItem(id: str, group: str, effect: Literal["benefits","pays"],
              explanation: str, expert_sources: list[SpecialistSource])
Incidence(items: list[IncidenceItem])

# step 6 — review dimensions
ProgramReviewDimension(dimension: Literal["funding_clarity","feasibility",
                       "internal_coherence","evidence_grounding"],
                       label: str, score: int, rationale: str)  # score 1–5
ProgramReview(dimensions: list[ProgramReviewDimension])         # exactly 4

# step 7 — distill + verdict
ProgramVerdict(summary: str, open_question: str)
ProgramDistill(points: list[str], verdict: ProgramVerdict)      # 3 points

ProgramMetadata(candidate: str, generated_at: str | None, domains: list[str])

ProgramFullAnalysis(metadata, research, vision_diagnostic, contre_expertise,
                    topics, incidence, review, distill)
```

The 12 domains are a constant `CORE_DOMAINS` in `models/program_analysis.py`
(the list from the overview spec).

## Agent (`agent/program_analysis_agent.py` + `agent/program_steps/`)

Mirrors the article pipeline's structure (`agent/full_analysis_agent.py` +
`agent/steps/`): one module per step, each exposing `run(...)`, cached via
`_load_or_run`. Reuses `agent/_base.py` for the LLM call, extended minimally:

- **`_base._call` / `_call_with_retry` gain an optional `system: str | None`
  parameter** (defaults to the existing article system prompt — backward
  compatible). The program steps pass a **program-specific system prompt**
  (`agent/program_steps/prompts/system.md`) that establishes the neutral,
  even-handed policy-analyst role and *permits* a verdict (unlike the article
  system prompt).

- **Specialist-source gather helper (`agent/program_steps/_gather.py`):**
  `async gather_corpus(queries: list[str], per_query: int = 5) -> tuple[str, list[dict]]`
  runs `search_news` for each query concurrently, scrapes results via
  `scrape_article`, and returns `(corpus_text, sources)` where `sources` is a
  list of `{title, url, snippet}`. Used by the **expert-grounding** steps only
  (3, 4-faille, 5). Step 1 does **not** gather — it reads the provided document.

**Steps** (each `run()` is async because the expert-grounding ones await gather;
pure-LLM steps are async too, for a uniform orchestrator):

1. **Ingest & structure** — no web search. One LLM call over the provided
   `program_text` to extract `SourcedStatement`s tagged by domain, each carrying
   a **verbatim passage** from the document as its `SourceRef.quote`. Also
   captures the candidate name if not supplied. Assign `st_N` ids.
2. **Vision & diagnostic** — LLM over the research corpus → `VisionDiagnostic`
   (vision line + root causes with source refs + values). Assign `rc_N` ids to
   root causes.
3. **Contre-expertise** — for each root cause, `gather_corpus` for specialist
   analysis, then LLM → `DiagnosticAssessmentItem`s referencing `rc_N`, each
   with `expert_sources`. Assign `ce_N` ids.
4. **Per-topic analysis** — loop the 12 domains; for each, LLM over the
   domain-tagged research → `TopicAnalysis` (headline measures + one faille,
   expert-sourced). Assign `m_N` ids within each topic.
5. **Incidence** — `gather_corpus` for distributional analysis of the flagship
   measures, then LLM → program-level `IncidenceItem`s (winners/payers),
   expert-sourced. Assign `inc_N` ids.
6. **Review dimensions** — LLM over the assembled analysis → 4 scored
   `ProgramReviewDimension`s.
7. **Distill + verdict** — LLM → 3 distill points + `ProgramVerdict`
   (summary + open question).

Each step's prompt lives in `agent/program_steps/prompts/stepN_*.md`. Every
prompt carries the neutral-tone + strict-sourcing instructions.

## Orchestrator

`async def analyze_program(input: ProgramAnalysisInput, no_api=False,
steps_dir=None) -> ProgramFullAnalysis`. Runs the 7 steps through an async
`_load_or_run`, assembles `ProgramFullAnalysis`, assigns IDs, then runs the
sourcing audit.

## Assembly-time sourcing audit

`_audit_program(data: dict) -> list[str]` (in the agent module), analogous to
`_audit_connections`. Flags:

- any `Measure` with no `SourceRef` carrying a non-empty verbatim quote;
- any `RootCause` with no `SourceRef` carrying a non-empty verbatim quote;
- any `DiagnosticAssessmentItem` whose `root_cause_id` doesn't resolve;
- any critical judgment (`DiagnosticAssessmentItem`, `Faille`, `IncidenceItem`)
  with an empty `expert_sources` list.

Issues are printed as warnings (like the article pipeline's audit); they do not
abort. A future step could add an LLM repair pass, but that is out of scope here.

Note on measure/root-cause sourcing: since the candidate's positions come from
the provided document, their `SourceRef.quote` must be a **non-empty verbatim
passage** from the program text (not a URL). The audit checks for a non-empty
quote, not a URL. Only the specialist sources (`SpecialistSource`) carry URLs.

## CLI

New subcommand `python main.py program <program.txt> [--candidate NAME]
[--no-api]` → `cmd_program`. Reads the program text from the file, runs
`analyze_program`, and writes `samples/outputs/<stem>/analysis.json` + `steps/`,
reusing `_layout(stem)`. The output stem and candidate default to the file's
slugified stem; `--candidate` overrides the display name (step 1 also captures
the candidate name from the document when discernible). Mirrors the article
`analyze <article.txt>` entry point. (Rendering subcommands come with
sub-projects 2 and 3.)

## Testing

- **Schema test** (`tests/test_program_model.py`): a hand-written fixture dict
  validates against `ProgramFullAnalysis`; `confidence_label` maps correctly.
- **Gather test** (`tests/test_program_gather.py`): monkeypatch `search_news`
  and `scrape_article`; assert `gather_corpus` (used by the expert-grounding
  steps) returns merged corpus text + the source list, and runs queries
  concurrently without raising on a scrape failure.
- **Audit test** (`tests/test_program_audit.py`): feed `_audit_program` a dict
  with an unsourced measure and an unsourced faille; assert both are flagged;
  feed a clean dict; assert no issues.
- **End-to-end `--no-api` test** (`tests/test_program_pipeline.py`): pre-populate
  a temp `steps/` with fixture JSON for all 7 steps; run `analyze_program(input,
  no_api=True)` with a short fixture `program_text`; assert the result validates
  as `ProgramFullAnalysis`, has 12 topics, 4 review dimensions, and the audit
  passes on the fixture. (Cached steps mean no LLM/search calls fire.)

Tests use the existing pytest setup (`pytest-asyncio`, `asyncio_mode=auto`,
`pytest-httpx`). Content correctness is LLM-driven and out of scope; tests
cover schema integrity, gather behavior, the audit, and pipeline assembly.

## Out of scope (this sub-project)

- Any rendering (newsletter or carousel), adapt, or extract layers.
- The LLM repair pass for audit gaps.
- The shared hors-série family abstraction.
