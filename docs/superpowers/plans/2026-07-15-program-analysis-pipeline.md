# Program Analysis Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `analyze_program(candidate_program_text)` → `ProgramFullAnalysis`: a deep, per-candidate critical analysis of a candidate's whole program across 12 core policy domains, producing only the analysis JSON (no rendering).

**Architecture:** A parallel analysis track mirroring the article pipeline (`agent/full_analysis_agent.py` + `agent/steps/`). A new `agent/program_analysis_agent.py` orchestrates 7 cached steps in `agent/program_steps/`, each calling the shared LLM helpers in `agent/_base.py`. The candidate's positions are read from a provided program text file (step 1, no search); the critical steps (contre-expertise, failles, incidence) additionally web-search for independent specialist sources via `tools/search.py` + `tools/scrape.py`. Output is `ProgramFullAnalysis` (new schema in `models/program_analysis.py`), assembled, ID-assigned, and passed through an assembly-time sourcing audit. A new `python main.py program <program.txt>` CLI entry runs it.

**Tech Stack:** Python 3.14, Pydantic v2, `anthropic` SDK (streaming + `json_schema` output), `httpx` + `duckduckgo-search` (via existing `tools/search.py`), pytest + pytest-asyncio (`asyncio_mode=auto`) + pytest-httpx.

## Global Constraints

- **Model:** all LLM calls use `config.MODEL` (currently `"claude-opus-4-8"`). Never hardcode a model id.
- **Package management:** use `uv add` / `uv sync` — never `pip install`. Run code with `uv run …`.
- **Language:** all generated content and all prompts are in **French**.
- **Strict sourcing:** every `Measure` and `RootCause` must carry ≥1 `SourceRef` with a non-empty verbatim quote from the program document. Every critical judgment (`DiagnosticAssessmentItem`, `Faille`, `IncidenceItem`) must carry ≥1 `SpecialistSource` (independent expert — not the candidate).
- **Neutral tone:** every step prompt includes an even-handedness instruction — critique grounded only in stated/sourced facts, no editorializing about the candidate as a person, no partisan framing.
- **Program system prompt:** program steps use `agent/program_steps/prompts/system.md` (NOT the article `agent/prompts/system.md`, which is journalism-specific and forbids direct verdicts). This is passed via a new optional `system=` parameter on `_base._call` / `_call_with_retry` (backward compatible; default keeps the article prompt).
- **12 core domains** live in one constant `CORE_DOMAINS` in `models/program_analysis.py`.
- **Do not touch** the article pipeline (`agent/full_analysis_agent.py`, `agent/steps/`, `models/full_analysis.py`) beyond the additive, backward-compatible `system=` parameter on `_base._call`/`_call_with_retry`.

---

### Task 1: `ProgramFullAnalysis` schema + `CORE_DOMAINS`

**Files:**
- Create: `models/program_analysis.py`
- Test: `tests/test_program_model.py`

**Interfaces:**
- Produces: `CORE_DOMAINS: list[str]` (12 items); models `ProgramAnalysisInput`, `SourceRef`, `SpecialistSource`, `SourcedStatement`, `ProgramResearch`, `RootCause`, `VisionDiagnostic`, `DiagnosticAssessmentItem`, `ContreExpertise`, `Measure`, `Faille`, `TopicAnalysis`, `ProgramTopics`, `IncidenceItem`, `Incidence`, `ProgramReviewDimension`, `ProgramReview`, `ProgramVerdict`, `ProgramDistill`, `ProgramMetadata`, `ProgramFullAnalysis`.
- `DiagnosticAssessmentItem.confidence_label` is a computed field mapping the 0–100 `confidence` to a French band (mirrors `ClaimAndSource.confidence_label` in `models/full_analysis.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_program_model.py
from models.program_analysis import (
    CORE_DOMAINS, ProgramFullAnalysis, DiagnosticAssessmentItem,
)


def _minimal_analysis_dict() -> dict:
    src = {"quote": "Nous porterons le SMIC à 1600 euros.", "url": None, "outlet": None}
    espec = {"name": "OFCE", "kind": "think_tank", "url": "https://ofce.fr/x", "finding": "Coût estimé à 10 Md€."}
    topic = {
        "domain": d,
        "headline_measures": [{"id": "", "measure": f"Mesure {d}", "detail": None, "sources": [src]}],
        "faille": {"kind": "funding", "label": "Financement", "explanation": "Non chiffré.", "expert_sources": [espec]},
    }
    return {
        "metadata": {"candidate": "Candidat X", "generated_at": None, "domains": CORE_DOMAINS},
        "research": {"statements": [{"id": "", "domain": CORE_DOMAINS[0], "quote": "…", "source": src}]},
        "vision_diagnostic": {"vision": "Une France plus juste.", "values": None,
                              "root_causes": [{"id": "", "cause": "Inégalités croissantes.", "sources": [src]}]},
        "contre_expertise": {"items": [{"id": "", "root_cause_id": "rc_0", "verdict": "Partiellement étayé.",
                                        "confidence": 55, "expert_sources": [espec]}]},
        "topics": {"topics": [dict(topic, domain=d) for d in CORE_DOMAINS]},
        "incidence": {"items": [{"id": "", "group": "Ménages modestes", "effect": "benefits",
                                 "explanation": "Hausse du pouvoir d'achat.", "expert_sources": [espec]}]},
        "review": {"dimensions": [
            {"dimension": "funding_clarity", "label": "Clarté du financement", "score": 2, "rationale": "…"},
            {"dimension": "feasibility", "label": "Faisabilité", "score": 3, "rationale": "…"},
            {"dimension": "internal_coherence", "label": "Cohérence interne", "score": 3, "rationale": "…"},
            {"dimension": "evidence_grounding", "label": "Fondement factuel", "score": 2, "rationale": "…"},
        ]},
        "distill": {"points": ["a", "b", "c"],
                    "verdict": {"summary": "Programme ambitieux mais peu chiffré.", "open_question": "Comment financer ?"}},
    }


def test_core_domains_has_twelve():
    assert len(CORE_DOMAINS) == 12


def test_full_analysis_validates():
    a = ProgramFullAnalysis.model_validate(_minimal_analysis_dict())
    assert len(a.topics.topics) == 12
    assert len(a.review.dimensions) == 4


def test_confidence_label_bands():
    assert DiagnosticAssessmentItem(root_cause_id="rc_0", verdict="x", confidence=10, expert_sources=[]).confidence_label == "faux"
    assert DiagnosticAssessmentItem(root_cause_id="rc_0", verdict="x", confidence=95, expert_sources=[]).confidence_label == "consensuel"
    assert DiagnosticAssessmentItem(root_cause_id="rc_0", verdict="x", confidence=None, expert_sources=[]).confidence_label == "invérifiable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_program_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'models.program_analysis'`.

- [ ] **Step 3: Write the schema**

```python
# models/program_analysis.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, computed_field

# The 12 core policy domains every candidate analysis covers (see overview spec).
CORE_DOMAINS: list[str] = [
    "Travail / Emploi",
    "Pouvoir d'achat",
    "Fiscalité / Impôts",
    "Économie & finances publiques",
    "Retraites",
    "Logement",
    "Écologie",
    "Santé & Éducation",
    "Société",
    "Immigration",
    "Sécurité & Justice",
    "Europe / Institutions & International",
]


class ProgramAnalysisInput(BaseModel):
    candidate: str
    program_text: str
    extra_instructions: str | None = None


# ── Sourcing primitives ───────────────────────────────────────────────────────

class SourceRef(BaseModel):
    """A candidate statement source: a verbatim passage from the program document."""
    quote: str
    url: str | None = None
    outlet: str | None = None


class SpecialistSource(BaseModel):
    """An independent expert source grounding a critical judgment (not the candidate)."""
    name: str
    kind: Literal["academic", "official_data", "ngo", "think_tank", "media", "other"]
    url: str
    finding: str


# ── Step 1: Ingest & structure ────────────────────────────────────────────────

class SourcedStatement(BaseModel):
    id: str = ""
    domain: str
    quote: str
    source: SourceRef


class ProgramResearch(BaseModel):
    statements: list[SourcedStatement]


# ── Step 2: Vision & diagnostic ───────────────────────────────────────────────

class RootCause(BaseModel):
    id: str = ""
    cause: str
    sources: list[SourceRef] = Field(default_factory=list)


class VisionDiagnostic(BaseModel):
    vision: str
    root_causes: list[RootCause]
    values: str | None = None


# ── Step 3: Contre-expertise ──────────────────────────────────────────────────

class DiagnosticAssessmentItem(BaseModel):
    id: str = ""
    root_cause_id: str
    verdict: str
    confidence: int | None = None
    expert_sources: list[SpecialistSource] = Field(default_factory=list)

    @computed_field
    @property
    def confidence_label(self) -> str:
        if self.confidence is None: return "invérifiable"
        if self.confidence <= 20: return "faux"
        if self.confidence <= 40: return "peu probable"
        if self.confidence <= 60: return "disputé"
        if self.confidence <= 80: return "probable"
        if self.confidence <= 90: return "avéré"
        return "consensuel"


class ContreExpertise(BaseModel):
    items: list[DiagnosticAssessmentItem]


# ── Step 4: Per-topic analysis ────────────────────────────────────────────────

class Measure(BaseModel):
    id: str = ""
    measure: str
    detail: str | None = None
    sources: list[SourceRef] = Field(default_factory=list)


class Faille(BaseModel):
    kind: Literal["efficacy", "funding", "feasibility", "coherence", "legal"]
    label: str
    explanation: str
    expert_sources: list[SpecialistSource] = Field(default_factory=list)


class TopicAnalysis(BaseModel):
    domain: str
    headline_measures: list[Measure]
    faille: Faille


class ProgramTopics(BaseModel):
    topics: list[TopicAnalysis]


# ── Step 5: Incidence ─────────────────────────────────────────────────────────

class IncidenceItem(BaseModel):
    id: str = ""
    group: str
    effect: Literal["benefits", "pays"]
    explanation: str
    expert_sources: list[SpecialistSource] = Field(default_factory=list)


class Incidence(BaseModel):
    items: list[IncidenceItem]


# ── Step 6: Review dimensions ─────────────────────────────────────────────────

class ProgramReviewDimension(BaseModel):
    dimension: Literal["funding_clarity", "feasibility", "internal_coherence", "evidence_grounding"]
    label: str
    score: int  # 1–5
    rationale: str


class ProgramReview(BaseModel):
    dimensions: list[ProgramReviewDimension]


# ── Step 7: Distill + verdict ─────────────────────────────────────────────────

class ProgramVerdict(BaseModel):
    summary: str
    open_question: str


class ProgramDistill(BaseModel):
    points: list[str]
    verdict: ProgramVerdict


# ── Composite ─────────────────────────────────────────────────────────────────

class ProgramMetadata(BaseModel):
    candidate: str
    generated_at: str | None = None
    domains: list[str] = Field(default_factory=lambda: list(CORE_DOMAINS))


class ProgramFullAnalysis(BaseModel):
    metadata: ProgramMetadata
    research: ProgramResearch
    vision_diagnostic: VisionDiagnostic
    contre_expertise: ContreExpertise
    topics: ProgramTopics
    incidence: Incidence
    review: ProgramReview
    distill: ProgramDistill
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_program_model.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add models/program_analysis.py tests/test_program_model.py
git commit -m "feat(program): ProgramFullAnalysis schema + CORE_DOMAINS"
```

---

### Task 2: Add optional `system=` to the shared LLM helpers

**Files:**
- Modify: `agent/_base.py` (functions `_call`, `_call_with_retry`, `_call_no_api`)
- Test: `tests/test_base_system_param.py`

**Interfaces:**
- Consumes: existing `agent/_base.py` helpers.
- Produces: `_call(user_message, schema, no_api=False, system=None)`, `_call_with_retry(user_message, schema, validator, no_api=False, label="", system=None)`. When `system is None`, behavior is identical to today (uses the module `_SYSTEM_PROMPT`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_base_system_param.py
import inspect
from agent import _base


def test_call_accepts_system_param():
    assert "system" in inspect.signature(_base._call).parameters
    assert "system" in inspect.signature(_base._call_with_retry).parameters


def test_no_api_uses_override_system(monkeypatch):
    captured = {}
    def fake_run(cmd, capture_output, text, encoding):
        captured["prompt"] = cmd[2]
        class R:  # minimal CompletedProcess stand-in
            returncode = 0
            stdout = '{"ok": true}'
            stderr = ""
        return R()
    monkeypatch.setattr(_base.subprocess, "run", fake_run)
    _base._call("hello", {"type": "object"}, no_api=True, system="SYSTEME PROGRAMME")
    assert "SYSTEME PROGRAMME" in captured["prompt"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_base_system_param.py -v`
Expected: FAIL — `_call` has no `system` parameter.

- [ ] **Step 3: Thread `system` through the helpers**

In `agent/_base.py`, change the three functions (keep everything else identical):

```python
def _call_no_api(user_message: str, schema: dict, system: str | None = None) -> dict:
    system_prompt = system or _SYSTEM_PROMPT
    prompt = (
        f"{system_prompt}\n\n"
        "---\n\n"
        f"{user_message}\n\n"
        "---\n\n"
        "Réponds UNIQUEMENT avec un objet JSON valide correspondant exactement à ce schéma :\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        "N'ajoute aucun texte avant ni après le JSON. Pas de balises markdown. Pas d'explication."
    )
    # … rest unchanged …
```

```python
def _call(user_message: str, schema: dict, no_api: bool = False, system: str | None = None) -> dict:
    if no_api:
        return _call_no_api(user_message, schema, system=system)
    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=system or _SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    ) as stream:
        response = stream.get_final_message()
    return json.loads(next(b.text for b in response.content if b.type == "text"))
```

```python
def _call_with_retry(user_message, schema, validator, no_api=False, label="", system=None):
    # add `system=system` to BOTH _call(...) invocations inside this function.
    # (initial call and the correction-loop call)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_base_system_param.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Confirm the article pipeline is unaffected**

Run: `uv run pytest tests/ -q`
Expected: PASS — existing tests still green (default `system=None` preserves old behavior).

- [ ] **Step 6: Commit**

```bash
git add agent/_base.py tests/test_base_system_param.py
git commit -m "feat(agent): optional system override on _call/_call_with_retry"
```

---

### Task 3: Program step scaffolding — package, system prompt, and `_gather`

**Files:**
- Create: `agent/program_steps/__init__.py` (empty)
- Create: `agent/program_steps/prompts/system.md`
- Create: `agent/program_steps/_gather.py`
- Test: `tests/test_program_gather.py`

**Interfaces:**
- Produces: `gather_corpus(queries: list[str], per_query: int = 5) -> tuple[str, list[dict]]` (async). Returns `(corpus_text, sources)` where `sources` is a list of `{title, url, snippet}` and `corpus_text` concatenates scraped bodies (or snippets when a scrape fails). Never raises on an individual search/scrape failure.
- `PROGRAM_SYSTEM_PROMPT: str` loadable via `Path`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_program_gather.py
import pytest
from agent.program_steps import _gather


@pytest.mark.asyncio
async def test_gather_corpus_merges_and_tolerates_failure(monkeypatch):
    async def fake_search(query, num_results=5):
        return [{"title": f"T-{query}", "url": f"https://ex/{query}", "snippet": f"snip-{query}"}]

    async def fake_scrape(url):
        if "boom" in url:
            raise RuntimeError("scrape failed")
        return {"url": url, "title": "t", "body": f"BODY::{url}"}

    monkeypatch.setattr(_gather, "search_news", fake_search)
    monkeypatch.setattr(_gather, "scrape_article", fake_scrape)

    corpus, sources = await _gather.gather_corpus(["retraites", "boom"], per_query=1)

    assert len(sources) == 2
    assert "BODY::https://ex/retraites" in corpus
    # failed scrape falls back to the snippet, does not raise
    assert "snip-boom" in corpus
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_program_gather.py -v`
Expected: FAIL — `agent.program_steps._gather` does not exist.

- [ ] **Step 3: Write `_gather.py`**

```python
# agent/program_steps/_gather.py
"""Specialist-source gathering for the expert-grounding program steps.

Runs the configured news search for each query concurrently, scrapes each
result's body (falling back to the snippet on failure), and returns a merged
corpus plus the flat source list. Used by steps 3 (contre-expertise), 4
(failles) and 5 (incidence). Step 1 does not gather — it reads the document."""
import asyncio

from tools.search import search_news
from tools.scrape import scrape_article


async def _one_query(query: str, per_query: int) -> list[dict]:
    try:
        return await search_news(query, num_results=per_query)
    except Exception:
        return []


async def gather_corpus(queries: list[str], per_query: int = 5) -> tuple[str, list[dict]]:
    result_lists = await asyncio.gather(*(_one_query(q, per_query) for q in queries))

    sources: list[dict] = []
    seen: set[str] = set()
    for results in result_lists:
        for r in results:
            url = r.get("url", "")
            if url and url not in seen:
                seen.add(url)
                sources.append(r)

    async def _body(src: dict) -> str:
        try:
            scraped = await scrape_article(src["url"])
            body = (scraped.get("body") or "").strip()
            if body:
                return body
        except Exception:
            pass
        return src.get("snippet", "")

    bodies = await asyncio.gather(*(_body(s) for s in sources))
    corpus = "\n\n".join(f"[{s['title']}] ({s['url']})\n{b}" for s, b in zip(sources, bodies))
    return corpus, sources
```

- [ ] **Step 4: Write the program system prompt**

```markdown
<!-- agent/program_steps/prompts/system.md -->
**Rôle :** Tu es un analyste des politiques publiques, rigoureux et impartial. Tu analyses le programme d'un·e candidat·e à l'élection présidentielle française de 2027 pour un public francophone curieux, sans parti pris.

**Langue :** Tout le contenu produit est en français.

**Neutralité (impératif) :**
- Traite chaque candidat·e avec une exigence identique. Aucune connotation partisane, aucun jugement sur la personne.
- Toute critique s'appuie uniquement sur des faits établis ou des sources citées — jamais sur une opinion de l'analyste.
- Distingue toujours ce que le·la candidat·e affirme de ce que les faits établissent.

**Sourçage (impératif) :**
- Les positions du·de la candidat·e proviennent EXCLUSIVEMENT du document de programme fourni : chaque mesure et chaque cause citée doit reposer sur une citation verbatim extraite du document.
- Tout jugement critique (contre-expertise, faille, incidence) doit s'appuyer sur au moins une source spécialiste indépendante (économiste, scientifique, ONG, rapport institutionnel) — jamais le·la candidat·e.

**Concision :** phrases courtes, une idée par phrase. Pas d'introductions ni de transitions.

**Verdict :** contrairement à l'analyse d'article, un verdict global argumenté est attendu à l'étape finale — il synthétise les constats sourcés, sans prendre parti pour ou contre le·la candidat·e.
```

- [ ] **Step 5: Create the package init**

```python
# agent/program_steps/__init__.py
```
(empty file)

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_program_gather.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add agent/program_steps/__init__.py agent/program_steps/_gather.py agent/program_steps/prompts/system.md tests/test_program_gather.py
git commit -m "feat(program): step package, program system prompt, _gather helper"
```

---

### Task 4: Steps 1–2 (ingest & structure, vision & diagnostic)

**Files:**
- Create: `agent/program_steps/step1_ingest.py`, `agent/program_steps/prompts/step1_ingest.md`
- Create: `agent/program_steps/step2_vision.py`, `agent/program_steps/prompts/step2_vision.md`
- Test: `tests/test_program_steps_1_2.py`

**Interfaces:**
- Produces:
  - `step1_ingest.run(input: ProgramAnalysisInput, steps_dir: Path, no_api=False) -> dict` (async) → validates as `ProgramResearch`; statements get `st_N` ids; saved to `step1_ingest.json`.
  - `step2_vision.run(input, research_data: dict, steps_dir, no_api=False) -> dict` (async) → validates as `VisionDiagnostic`; root causes get `rc_N` ids; saved to `step2_vision.json`.
- Consumes: `_base._call_with_retry`, `_base.save_step`, `PROGRAM_SYSTEM_PROMPT`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_program_steps_1_2.py
import pytest
from pathlib import Path
from agent.program_steps import step1_ingest, step2_vision
from models.program_analysis import ProgramAnalysisInput, ProgramResearch, VisionDiagnostic, CORE_DOMAINS


@pytest.mark.asyncio
async def test_step1_assigns_ids_and_validates(tmp_path, monkeypatch):
    fake = {"statements": [
        {"id": "", "domain": CORE_DOMAINS[0], "quote": "SMIC à 1600€", "source": {"quote": "SMIC à 1600€"}},
        {"id": "", "domain": CORE_DOMAINS[1], "quote": "Bloquer les prix", "source": {"quote": "Bloquer les prix"}},
    ]}
    monkeypatch.setattr(step1_ingest, "_call_with_retry", lambda *a, **k: fake)
    inp = ProgramAnalysisInput(candidate="X", program_text="… programme …")
    data = await step1_ingest.run(inp, tmp_path, no_api=True)
    r = ProgramResearch.model_validate(data)
    assert [s.id for s in r.statements] == ["st_0", "st_1"]
    assert (tmp_path / "step1_ingest.json").exists()


@pytest.mark.asyncio
async def test_step2_assigns_rootcause_ids(tmp_path, monkeypatch):
    fake = {"vision": "Une France plus juste.", "values": None, "root_causes": [
        {"id": "", "cause": "Inégalités.", "sources": [{"quote": "…"}]},
        {"id": "", "cause": "Désindustrialisation.", "sources": [{"quote": "…"}]},
    ]}
    monkeypatch.setattr(step2_vision, "_call_with_retry", lambda *a, **k: fake)
    inp = ProgramAnalysisInput(candidate="X", program_text="…")
    data = await step2_vision.run(inp, {"statements": []}, tmp_path, no_api=True)
    v = VisionDiagnostic.model_validate(data)
    assert [c.id for c in v.root_causes] == ["rc_0", "rc_1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_program_steps_1_2.py -v`
Expected: FAIL — step modules don't exist.

- [ ] **Step 3: Write `step1_ingest.py`**

```python
# agent/program_steps/step1_ingest.py
from pathlib import Path

from agent._base import _call_with_retry, save_step
from models.program_analysis import ProgramAnalysisInput, ProgramResearch, CORE_DOMAINS

_PROMPT = (Path(__file__).parent / "prompts" / "step1_ingest.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    r = ProgramResearch.model_validate(data)
    errors = []
    if not r.statements:
        errors.append("statements is empty")
    domains = {s.domain for s in r.statements}
    missing = [d for d in CORE_DOMAINS if d not in domains]
    if missing:
        errors.append(f"no statement for domains: {missing}")
    for i, s in enumerate(r.statements):
        if not s.source.quote.strip():
            errors.append(f"statements[{i}].source.quote is empty (must be verbatim from the document)")
    return errors


async def run(input: ProgramAnalysisInput, steps_dir: Path, no_api: bool = False) -> dict:
    domains = "\n".join(f"- {d}" for d in CORE_DOMAINS)
    user_msg = (
        f"CANDIDAT·E : {input.candidate}\n\n"
        f"DOMAINES À COUVRIR (un ou plusieurs énoncés chacun) :\n{domains}\n\n"
        f"PROGRAMME (document fourni) :\n{input.program_text}\n\n---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ProgramResearch.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step1")
    data["statements"] = [
        {**s, "id": f"st_{i}"} for i, s in enumerate(data.get("statements", []))
    ]
    save_step(data, steps_dir, "step1_ingest.json")
    return data
```

- [ ] **Step 4: Write `agent/program_steps/prompts/step1_ingest.md`**

```markdown
Extrais du document de programme les positions du·de la candidat·e, réparties par domaine.

- Pour CHAQUE domaine listé, produis au moins un `statement` si le document en traite. Ne fabrique rien : si un domaine est absent du document, ne l'invente pas (l'énoncé peut alors manquer).
- `domain` doit être exactement l'un des libellés fournis.
- `quote` : une reformulation courte et neutre de la position.
- `source.quote` : un extrait VERBATIM du document appuyant l'énoncé (copié mot pour mot). Ne laisse jamais ce champ vide.
- Reste strictement descriptif à cette étape : aucune critique, aucune évaluation.
```

- [ ] **Step 5: Write `step2_vision.py`**

```python
# agent/program_steps/step2_vision.py
import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from models.program_analysis import ProgramAnalysisInput, VisionDiagnostic

_PROMPT = (Path(__file__).parent / "prompts" / "step2_vision.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    v = VisionDiagnostic.model_validate(data)
    errors = []
    if not v.vision.strip():
        errors.append("vision is empty")
    if not v.root_causes:
        errors.append("root_causes is empty")
    for i, c in enumerate(v.root_causes):
        if not any(s.quote.strip() for s in c.sources):
            errors.append(f"root_causes[{i}] has no sourced verbatim quote")
    return errors


async def run(input: ProgramAnalysisInput, research_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    user_msg = (
        f"CANDIDAT·E : {input.candidate}\n\n"
        f"ÉNONCÉS SOURCÉS (étape 1) :\n{json.dumps(research_data, ensure_ascii=False, indent=2)}\n\n"
        f"PROGRAMME (document fourni) :\n{input.program_text}\n\n---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, VisionDiagnostic.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step2")
    data["root_causes"] = [
        {**c, "id": f"rc_{i}"} for i, c in enumerate(data.get("root_causes", []))
    ]
    save_step(data, steps_dir, "step2_vision.json")
    return data
```

- [ ] **Step 6: Write `agent/program_steps/prompts/step2_vision.md`**

```markdown
Dégage la vision d'ensemble et le diagnostic du·de la candidat·e à partir du programme.

- `vision` : en 1–2 phrases, le fil conducteur — où le·la candidat·e veut mener le pays.
- `root_causes` : les causes profondes que le·la candidat·e affirme vouloir traiter (le problème tel qu'il·elle le pose). Chaque cause porte au moins un `source.quote` verbatim du document.
- `values` (optionnel) : les valeurs explicitement invoquées.
- Reste descriptif : tu restitues la lecture du·de la candidat·e, sans la juger (la contre-expertise vient ensuite).
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_program_steps_1_2.py -v`
Expected: PASS (2 tests).

- [ ] **Step 8: Commit**

```bash
git add agent/program_steps/step1_ingest.py agent/program_steps/step2_vision.py agent/program_steps/prompts/step1_ingest.md agent/program_steps/prompts/step2_vision.md tests/test_program_steps_1_2.py
git commit -m "feat(program): steps 1-2 (ingest & structure, vision & diagnostic)"
```

---

### Task 5: Step 3 (contre-expertise) — expert-grounded

**Files:**
- Create: `agent/program_steps/step3_contre_expertise.py`, `agent/program_steps/prompts/step3_contre_expertise.md`
- Test: `tests/test_program_step3.py`

**Interfaces:**
- Produces: `step3_contre_expertise.run(vision_data: dict, steps_dir, no_api=False) -> dict` (async) → validates as `ContreExpertise`; items get `ce_N` ids; saved to `step3_contre_expertise.json`. Gathers specialist corpus per root cause via `gather_corpus` (skipped when `no_api=True`).
- Consumes: `_gather.gather_corpus`, `_base._call_with_retry`, `PROGRAM_SYSTEM_PROMPT`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_program_step3.py
import pytest
from agent.program_steps import step3_contre_expertise as step3


@pytest.mark.asyncio
async def test_step3_assigns_ids_and_skips_gather_on_no_api(tmp_path, monkeypatch):
    called = {"gather": 0}
    async def fake_gather(queries, per_query=5):
        called["gather"] += 1
        return "", []
    monkeypatch.setattr(step3, "gather_corpus", fake_gather)

    fake = {"items": [
        {"id": "", "root_cause_id": "rc_0", "verdict": "Étayé.", "confidence": 70,
         "expert_sources": [{"name": "OFCE", "kind": "think_tank", "url": "https://x", "finding": "…"}]},
    ]}
    monkeypatch.setattr(step3, "_call_with_retry", lambda *a, **k: fake)

    vision = {"vision": "…", "root_causes": [{"id": "rc_0", "cause": "Inégalités.", "sources": []}]}
    data = await step3.run(vision, tmp_path, no_api=True)
    assert data["items"][0]["id"] == "ce_0"
    assert called["gather"] == 0  # no_api must not hit the network
    assert (tmp_path / "step3_contre_expertise.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_program_step3.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write `step3_contre_expertise.py`**

```python
# agent/program_steps/step3_contre_expertise.py
import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from agent.program_steps._gather import gather_corpus
from models.program_analysis import ContreExpertise, VisionDiagnostic

_PROMPT = (Path(__file__).parent / "prompts" / "step3_contre_expertise.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    ce = ContreExpertise.model_validate(data)
    valid_ids = None  # cross-check happens at assembly; here just require sources
    errors = []
    for i, it in enumerate(ce.items):
        if not it.expert_sources:
            errors.append(f"items[{i}] has no expert_sources (independent specialist required)")
        if not it.root_cause_id.strip():
            errors.append(f"items[{i}].root_cause_id is empty")
    return errors


async def run(vision_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    vision = VisionDiagnostic.model_validate(vision_data)
    corpus = ""
    if not no_api:
        queries = [f"{c.cause} analyse économiste OR rapport OR étude" for c in vision.root_causes]
        corpus, _ = await gather_corpus(queries, per_query=4)

    user_msg = (
        f"DIAGNOSTIC DU·DE LA CANDIDAT·E (étape 2) :\n{json.dumps(vision_data, ensure_ascii=False, indent=2)}\n\n"
        f"ANALYSES DE SPÉCIALISTES (recherche web) :\n{corpus or '(aucune — n\\'invente pas de source)'}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ContreExpertise.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step3")
    data["items"] = [{**it, "id": f"ce_{i}"} for i, it in enumerate(data.get("items", []))]
    save_step(data, steps_dir, "step3_contre_expertise.json")
    return data
```

- [ ] **Step 4: Write `agent/program_steps/prompts/step3_contre_expertise.md`**

```markdown
Soumets le DIAGNOSTIC du·de la candidat·e à la contre-expertise : chaque cause profonde est-elle réelle, exacte, partagée par les spécialistes ?

- Un `item` par cause profonde jugée. `root_cause_id` référence l'id exact fourni (rc_N).
- `verdict` : en une à deux phrases, ce que disent les spécialistes sur la réalité/l'exactitude de la cause.
- `confidence` : entier 0–100 estimant à quel point le diagnostic est corroboré par les sources.
- `expert_sources` : au moins une source INDÉPENDANTE (économiste, scientifique, ONG, rapport). Jamais le·la candidat·e. Chaque source porte `name`, `kind`, `url`, `finding`.
- Si les sources fournies ne permettent pas de trancher, dis-le dans `verdict` et baisse `confidence` — n'invente aucune source.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_program_step3.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/program_steps/step3_contre_expertise.py agent/program_steps/prompts/step3_contre_expertise.md tests/test_program_step3.py
git commit -m "feat(program): step 3 (contre-expertise, expert-grounded)"
```

---

### Task 6: Step 4 (per-topic analysis over 12 domains)

**Files:**
- Create: `agent/program_steps/step4_topics.py`, `agent/program_steps/prompts/step4_topics.md`
- Test: `tests/test_program_step4.py`

**Interfaces:**
- Produces: `step4_topics.run(input: ProgramAnalysisInput, research_data: dict, steps_dir, no_api=False) -> dict` (async) → validates as `ProgramTopics` with exactly `len(CORE_DOMAINS)` topics; measures across all topics get globally-unique `m_N` ids; saved to `step4_topics.json`. One LLM call per domain; failles gather a specialist corpus per domain (skipped when `no_api=True`).
- Consumes: `_gather.gather_corpus`, `_base._call_with_retry`, `TopicAnalysis`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_program_step4.py
import pytest
from agent.program_steps import step4_topics as step4
from models.program_analysis import ProgramAnalysisInput, ProgramTopics, CORE_DOMAINS


@pytest.mark.asyncio
async def test_step4_builds_all_domains_with_unique_measure_ids(tmp_path, monkeypatch):
    async def fake_gather(queries, per_query=5):
        return "", []
    monkeypatch.setattr(step4, "gather_corpus", fake_gather)

    def fake_topic_call(*a, **k):
        return {
            "domain": fake_topic_call.domain,
            "headline_measures": [{"id": "", "measure": "m", "detail": None,
                                   "sources": [{"quote": "verbatim"}]}],
            "faille": {"kind": "funding", "label": "Financement", "explanation": "…",
                       "expert_sources": [{"name": "OFCE", "kind": "think_tank", "url": "https://x", "finding": "…"}]},
        }
    # step4.run sets step4._current_domain before each call; emulate via closure list
    domains_iter = iter(CORE_DOMAINS)
    def call(user_msg, schema, validator, no_api, system, label):
        fake_topic_call.domain = next(domains_iter)
        return fake_topic_call()
    monkeypatch.setattr(step4, "_call_with_retry", call)

    inp = ProgramAnalysisInput(candidate="X", program_text="…")
    research = {"statements": [{"id": "st_0", "domain": CORE_DOMAINS[0], "quote": "q", "source": {"quote": "q"}}]}
    data = await step4.run(inp, research, tmp_path, no_api=True)
    t = ProgramTopics.model_validate(data)
    assert len(t.topics) == len(CORE_DOMAINS)
    all_ids = [m.id for topic in t.topics for m in topic.headline_measures]
    assert all_ids == [f"m_{i}" for i in range(len(all_ids))]  # globally unique, sequential
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_program_step4.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write `step4_topics.py`**

```python
# agent/program_steps/step4_topics.py
import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from agent.program_steps._gather import gather_corpus
from models.program_analysis import ProgramAnalysisInput, TopicAnalysis, CORE_DOMAINS

_PROMPT = (Path(__file__).parent / "prompts" / "step4_topics.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    t = TopicAnalysis.model_validate(data)
    errors = []
    if not t.headline_measures:
        errors.append("headline_measures is empty")
    for i, m in enumerate(t.headline_measures):
        if not any(s.quote.strip() for s in m.sources):
            errors.append(f"headline_measures[{i}] has no sourced verbatim quote")
    if not t.faille.expert_sources:
        errors.append("faille has no expert_sources (independent specialist required)")
    return errors


async def run(input: ProgramAnalysisInput, research_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    statements = research_data.get("statements", [])
    topics = []
    for domain in CORE_DOMAINS:
        domain_statements = [s for s in statements if s.get("domain") == domain]
        corpus = ""
        if not no_api:
            corpus, _ = await gather_corpus(
                [f"{input.candidate} {domain} mesure faisabilité coût analyse"], per_query=4
            )
        user_msg = (
            f"CANDIDAT·E : {input.candidate}\n"
            f"DOMAINE : {domain}\n\n"
            f"ÉNONCÉS DU PROGRAMME POUR CE DOMAINE :\n{json.dumps(domain_statements, ensure_ascii=False, indent=2)}\n\n"
            f"ANALYSES DE SPÉCIALISTES (recherche web) :\n{corpus or '(aucune — n\\'invente pas de source)'}\n\n"
            f"PROGRAMME (document fourni) :\n{input.program_text}\n\n---\n\n{_PROMPT}"
        )
        topic = _call_with_retry(user_msg, TopicAnalysis.model_json_schema(),
                                 validator=_validate, no_api=no_api, system=_SYSTEM, label=f"step4:{domain}")
        topic["domain"] = domain  # pin the domain deterministically
        topics.append(topic)

    # Assign globally-unique measure ids across all topics.
    counter = 0
    for topic in topics:
        for m in topic.get("headline_measures", []):
            m["id"] = f"m_{counter}"
            counter += 1

    data = {"topics": topics}
    save_step(data, steps_dir, "step4_topics.json")
    return data
```

- [ ] **Step 4: Write `agent/program_steps/prompts/step4_topics.md`**

```markdown
Analyse le programme du·de la candidat·e SUR CE DOMAINE précis.

- `headline_measures` : 1 à 3 mesures phares proposées sur ce domaine. Chaque mesure porte au moins un `source.quote` VERBATIM du document.
- `faille` : la principale faiblesse des mesures de ce domaine.
  - `kind` : efficacy | funding | feasibility | coherence | legal.
  - `label` : 1–3 mots.
  - `explanation` : une à deux phrases, appuyées sur les analyses de spécialistes fournies.
  - `expert_sources` : au moins une source INDÉPENDANTE (jamais le·la candidat·e), avec `name`, `kind`, `url`, `finding`.
- Ne juge que le fond, jamais la personne. Si aucune source ne soutient une critique, n'affirme pas cette critique.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_program_step4.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/program_steps/step4_topics.py agent/program_steps/prompts/step4_topics.md tests/test_program_step4.py
git commit -m "feat(program): step 4 (per-topic analysis over 12 domains)"
```

---

### Task 7: Steps 5–7 (incidence, review dimensions, distill + verdict)

**Files:**
- Create: `agent/program_steps/step5_incidence.py`, `prompts/step5_incidence.md`
- Create: `agent/program_steps/step6_review.py`, `prompts/step6_review.md`
- Create: `agent/program_steps/step7_distill.py`, `prompts/step7_distill.md`
- Test: `tests/test_program_steps_5_7.py`

**Interfaces:**
- Produces:
  - `step5_incidence.run(input, topics_data: dict, steps_dir, no_api=False) -> dict` (async) → `Incidence`; items get `inc_N` ids; gathers specialist corpus (skipped on `no_api`); file `step5_incidence.json`.
  - `step6_review.run(vision_data, topics_data, contre_data, steps_dir, no_api=False) -> dict` (async) → `ProgramReview` with exactly 4 dimensions; file `step6_review.json`.
  - `step7_distill.run(vision_data, topics_data, review_data, incidence_data, steps_dir, no_api=False) -> dict` (async) → `ProgramDistill` (3 points + verdict); file `step7_distill.json`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_program_steps_5_7.py
import pytest
from agent.program_steps import step5_incidence as s5, step6_review as s6, step7_distill as s7
from models.program_analysis import Incidence, ProgramReview, ProgramDistill


@pytest.mark.asyncio
async def test_step5_ids_and_no_api(tmp_path, monkeypatch):
    async def fake_gather(q, per_query=5): return "", []
    monkeypatch.setattr(s5, "gather_corpus", fake_gather)
    fake = {"items": [
        {"id": "", "group": "Ménages modestes", "effect": "benefits", "explanation": "…",
         "expert_sources": [{"name": "IPP", "kind": "think_tank", "url": "https://x", "finding": "…"}]},
        {"id": "", "group": "Grandes entreprises", "effect": "pays", "explanation": "…",
         "expert_sources": [{"name": "IPP", "kind": "think_tank", "url": "https://x", "finding": "…"}]},
    ]}
    monkeypatch.setattr(s5, "_call_with_retry", lambda *a, **k: fake)
    data = await s5.run(type("I", (), {"candidate": "X", "program_text": "…"})(), {"topics": []}, tmp_path, no_api=True)
    assert [i["id"] for i in data["items"]] == ["inc_0", "inc_1"]


@pytest.mark.asyncio
async def test_step6_four_dimensions(tmp_path, monkeypatch):
    dims = [{"dimension": k, "label": k, "score": 3, "rationale": "…"} for k in
            ("funding_clarity", "feasibility", "internal_coherence", "evidence_grounding")]
    monkeypatch.setattr(s6, "_call_with_retry", lambda *a, **k: {"dimensions": dims})
    data = await s6.run({}, {"topics": []}, {"items": []}, tmp_path, no_api=True)
    assert len(ProgramReview.model_validate(data).dimensions) == 4


@pytest.mark.asyncio
async def test_step7_distill_verdict(tmp_path, monkeypatch):
    fake = {"points": ["a", "b", "c"], "verdict": {"summary": "…", "open_question": "…"}}
    monkeypatch.setattr(s7, "_call_with_retry", lambda *a, **k: fake)
    data = await s7.run({}, {"topics": []}, {"dimensions": []}, {"items": []}, tmp_path, no_api=True)
    assert len(ProgramDistill.model_validate(data).points) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_program_steps_5_7.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 3: Write `step5_incidence.py`**

```python
# agent/program_steps/step5_incidence.py
import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from agent.program_steps._gather import gather_corpus
from models.program_analysis import Incidence

_PROMPT = (Path(__file__).parent / "prompts" / "step5_incidence.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    inc = Incidence.model_validate(data)
    errors = []
    if not inc.items:
        errors.append("items is empty")
    for i, it in enumerate(inc.items):
        if not it.expert_sources:
            errors.append(f"items[{i}] has no expert_sources")
    return errors


async def run(input, topics_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    corpus = ""
    if not no_api:
        corpus, _ = await gather_corpus(
            [f"{input.candidate} programme gagnants perdants redistribution incidence"], per_query=5
        )
    user_msg = (
        f"CANDIDAT·E : {input.candidate}\n\n"
        f"MESURES PAR DOMAINE (étape 4) :\n{json.dumps(topics_data, ensure_ascii=False, indent=2)}\n\n"
        f"ANALYSES DE SPÉCIALISTES (recherche web) :\n{corpus or '(aucune — n\\'invente pas de source)'}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, Incidence.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step5")
    data["items"] = [{**it, "id": f"inc_{i}"} for i, it in enumerate(data.get("items", []))]
    save_step(data, steps_dir, "step5_incidence.json")
    return data
```

- [ ] **Step 4: Write `agent/program_steps/prompts/step5_incidence.md`**

```markdown
Analyse l'INCIDENCE économique du programme dans son ensemble : qui y gagne, qui paie.

- `items` : les groupes concrets (ménages selon le revenu, catégories professionnelles, entreprises par taille, générations…) gagnants ou perdants.
- `effect` : "benefits" (bénéficie) ou "pays" (supporte le coût).
- `explanation` : le mécanisme économique, appuyé sur les analyses de spécialistes fournies — pas de spéculation sur les intentions.
- `expert_sources` : au moins une source INDÉPENDANTE par item.
- Équilibre : présente aussi bien les gagnants que les perdants.
```

- [ ] **Step 5: Write `step6_review.py`**

```python
# agent/program_steps/step6_review.py
import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from models.program_analysis import ProgramReview

_PROMPT = (Path(__file__).parent / "prompts" / "step6_review.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")

_DIMENSIONS = ("funding_clarity", "feasibility", "internal_coherence", "evidence_grounding")


def _validate(data: dict) -> list[str]:
    r = ProgramReview.model_validate(data)
    errors = []
    got = {d.dimension for d in r.dimensions}
    missing = [d for d in _DIMENSIONS if d not in got]
    if missing:
        errors.append(f"missing dimensions: {missing}")
    for i, d in enumerate(r.dimensions):
        if not (1 <= d.score <= 5):
            errors.append(f"dimensions[{i}].score={d.score} out of range 1–5")
    return errors


async def run(vision_data: dict, topics_data: dict, contre_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    user_msg = (
        f"VISION & DIAGNOSTIC (étape 2) :\n{json.dumps(vision_data, ensure_ascii=False, indent=2)}\n\n"
        f"CONTRE-EXPERTISE (étape 3) :\n{json.dumps(contre_data, ensure_ascii=False, indent=2)}\n\n"
        f"MESURES & FAILLES PAR DOMAINE (étape 4) :\n{json.dumps(topics_data, ensure_ascii=False, indent=2)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ProgramReview.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step6")
    save_step(data, steps_dir, "step6_review.json")
    return data
```

- [ ] **Step 6: Write `agent/program_steps/prompts/step6_review.md`**

```markdown
Évalue le programme sur EXACTEMENT ces quatre dimensions, chacune notée de 1 (très faible) à 5 (exemplaire) :

- `funding_clarity` — Clarté du financement : le coût est-il chiffré et une source de financement crédible est-elle donnée ?
- `feasibility` — Faisabilité : réalisme juridique, constitutionnel, budgétaire, politique dans un mandat.
- `internal_coherence` — Cohérence interne : les mesures se contredisent-elles, ou contredisent-elles les objectifs affichés ?
- `evidence_grounding` — Fondement factuel : le diagnostic et les mesures reposent-ils sur des données, ou sur des affirmations ?

Pour chaque dimension : `label` en français, `score` 1–5, `rationale` en une à deux phrases fondées sur les étapes précédentes.
```

- [ ] **Step 7: Write `step7_distill.py`**

```python
# agent/program_steps/step7_distill.py
import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from models.program_analysis import ProgramDistill

_PROMPT = (Path(__file__).parent / "prompts" / "step7_distill.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    d = ProgramDistill.model_validate(data)
    errors = []
    if len(d.points) != 3:
        errors.append(f"points: expected exactly 3, got {len(d.points)}")
    if not d.verdict.summary.strip():
        errors.append("verdict.summary is empty")
    if not d.verdict.open_question.strip():
        errors.append("verdict.open_question is empty")
    return errors


async def run(vision_data: dict, topics_data: dict, review_data: dict, incidence_data: dict,
              steps_dir: Path, no_api: bool = False) -> dict:
    user_msg = (
        f"VISION & DIAGNOSTIC :\n{json.dumps(vision_data, ensure_ascii=False, indent=2)}\n\n"
        f"MESURES & FAILLES :\n{json.dumps(topics_data, ensure_ascii=False, indent=2)}\n\n"
        f"INCIDENCE :\n{json.dumps(incidence_data, ensure_ascii=False, indent=2)}\n\n"
        f"NOTES PAR DIMENSION :\n{json.dumps(review_data, ensure_ascii=False, indent=2)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ProgramDistill.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step7")
    save_step(data, steps_dir, "step7_distill.json")
    return data
```

- [ ] **Step 8: Write `agent/program_steps/prompts/step7_distill.md`**

```markdown
Synthétise l'analyse du programme.

- `points` : EXACTEMENT 3 enseignements clés, les plus importants d'abord, une phrase chacun.
- `verdict.summary` : le verdict global en 1–2 phrases — une appréciation d'ensemble argumentée à partir des constats sourcés (financement, faisabilité, cohérence, fondement). Sans prendre parti pour ou contre la personne.
- `verdict.open_question` : une question ouverte que le programme laisse en suspens.
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `uv run pytest tests/test_program_steps_5_7.py -v`
Expected: PASS (3 tests).

- [ ] **Step 10: Commit**

```bash
git add agent/program_steps/step5_incidence.py agent/program_steps/step6_review.py agent/program_steps/step7_distill.py agent/program_steps/prompts/step5_incidence.md agent/program_steps/prompts/step6_review.md agent/program_steps/prompts/step7_distill.md tests/test_program_steps_5_7.py
git commit -m "feat(program): steps 5-7 (incidence, review, distill+verdict)"
```

---

### Task 8: Orchestrator + assembly audit + end-to-end `--no-api` test

**Files:**
- Create: `agent/program_analysis_agent.py`
- Modify: `agent/__init__.py` (export `analyze_program`)
- Test: `tests/test_program_audit.py`, `tests/test_program_pipeline.py`
- Test fixtures: `tests/fixtures/program_steps/step{1..7}_*.json`

**Interfaces:**
- Produces:
  - `analyze_program(input: ProgramAnalysisInput, no_api=False, steps_dir: Path | None = None) -> ProgramFullAnalysis` (async).
  - `_audit_program(data: dict) -> list[str]`.
  - `_assign_program_ids` is NOT needed — each step assigns its own ids; the orchestrator only assembles.
- Consumes: all 7 `step*.run` functions; `ProgramFullAnalysis` and sub-models.

- [ ] **Step 1: Write the failing audit test**

```python
# tests/test_program_audit.py
from agent.program_analysis_agent import _audit_program


def _clean() -> dict:
    src = {"quote": "verbatim", "url": None, "outlet": None}
    espec = [{"name": "OFCE", "kind": "think_tank", "url": "https://x", "finding": "…"}]
    return {
        "research": {"statements": []},
        "vision_diagnostic": {"vision": "v", "values": None,
                              "root_causes": [{"id": "rc_0", "cause": "c", "sources": [src]}]},
        "contre_expertise": {"items": [{"id": "ce_0", "root_cause_id": "rc_0", "verdict": "v",
                                        "confidence": 50, "expert_sources": espec}]},
        "topics": {"topics": [{"domain": "Retraites",
                               "headline_measures": [{"id": "m_0", "measure": "m", "detail": None, "sources": [src]}],
                               "faille": {"kind": "funding", "label": "F", "explanation": "e", "expert_sources": espec}}]},
        "incidence": {"items": [{"id": "inc_0", "group": "g", "effect": "pays", "explanation": "e", "expert_sources": espec}]},
    }


def test_audit_clean_passes():
    assert _audit_program(_clean()) == []


def test_audit_flags_unsourced_measure():
    d = _clean()
    d["topics"]["topics"][0]["headline_measures"][0]["sources"] = [{"quote": "  "}]
    issues = _audit_program(d)
    assert any("UNSOURCED_MEASURE" in i for i in issues)


def test_audit_flags_faille_without_expert():
    d = _clean()
    d["topics"]["topics"][0]["faille"]["expert_sources"] = []
    issues = _audit_program(d)
    assert any("UNSOURCED_JUDGMENT" in i for i in issues)


def test_audit_flags_dangling_root_cause_ref():
    d = _clean()
    d["contre_expertise"]["items"][0]["root_cause_id"] = "rc_99"
    issues = _audit_program(d)
    assert any("DANGLING_ROOT_CAUSE" in i for i in issues)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_program_audit.py -v`
Expected: FAIL — `agent.program_analysis_agent` does not exist.

- [ ] **Step 3: Write the orchestrator + audit**

```python
# agent/program_analysis_agent.py
"""Multi-step program analysis pipeline (hors-série track).

Steps:
  1. Ingest    — read the provided program document → domain-tagged statements
  2. Vision    — vision + diagnostic (root causes)
  3. Contre-expertise — specialists test the diagnostic
  4. Topics    — per-domain measures + faille (over the 12 CORE_DOMAINS)
  5. Incidence — program-level winners/payers
  6. Review    — 4 scored dimensions
  7. Distill   — 3 takeaways + verdict
"""
import json
import sys
import tempfile
from pathlib import Path

from models.program_analysis import (
    ProgramAnalysisInput, ProgramFullAnalysis, ProgramMetadata,
    ProgramResearch, VisionDiagnostic, ContreExpertise, ProgramTopics,
    Incidence, ProgramReview, ProgramDistill, CORE_DOMAINS,
)
from .program_steps import (
    step1_ingest, step2_vision, step3_contre_expertise, step4_topics,
    step5_incidence, step6_review, step7_distill,
)


async def _load_or_run(steps_dir: Path, filename: str, run_coro_fn):
    path = steps_dir / filename
    if path.exists():
        print(f"  (loaded from {path.name})", file=sys.stderr, flush=True)
        return json.loads(path.read_text(encoding="utf-8"))
    return await run_coro_fn()


def _audit_program(data: dict) -> list[str]:
    issues: list[str] = []

    def _has_quote(sources: list) -> bool:
        return any((s.get("quote") or "").strip() for s in (sources or []))

    vd = data.get("vision_diagnostic", {})
    root_ids = {c.get("id") for c in vd.get("root_causes", [])}
    for i, c in enumerate(vd.get("root_causes", [])):
        if not _has_quote(c.get("sources", [])):
            issues.append(f"UNSOURCED_ROOT_CAUSE root_causes[{i}]: '{c.get('cause','')[:60]}'")

    for ti, t in enumerate(data.get("topics", {}).get("topics", [])):
        for mi, m in enumerate(t.get("headline_measures", [])):
            if not _has_quote(m.get("sources", [])):
                issues.append(f"UNSOURCED_MEASURE topics[{ti}].headline_measures[{mi}]: '{m.get('measure','')[:60]}'")
        if not t.get("faille", {}).get("expert_sources"):
            issues.append(f"UNSOURCED_JUDGMENT topics[{ti}].faille: '{t.get('faille',{}).get('label','')}'")

    for i, it in enumerate(data.get("contre_expertise", {}).get("items", [])):
        if not it.get("expert_sources"):
            issues.append(f"UNSOURCED_JUDGMENT contre_expertise[{i}]")
        if it.get("root_cause_id") not in root_ids:
            issues.append(f"DANGLING_ROOT_CAUSE contre_expertise[{i}] → '{it.get('root_cause_id')}'")

    for i, it in enumerate(data.get("incidence", {}).get("items", [])):
        if not it.get("expert_sources"):
            issues.append(f"UNSOURCED_JUDGMENT incidence[{i}]")

    return issues


async def analyze_program(
    input: ProgramAnalysisInput,
    no_api: bool = False,
    steps_dir: Path | None = None,
) -> ProgramFullAnalysis:
    if steps_dir is None:
        steps_dir = Path(tempfile.mkdtemp(prefix="sing-sing-program-steps-"))
    steps_dir.mkdir(parents=True, exist_ok=True)

    print("[1/7] Ingest…", file=sys.stderr, flush=True)
    research = await _load_or_run(steps_dir, "step1_ingest.json",
        lambda: step1_ingest.run(input, steps_dir, no_api=no_api))

    print("[2/7] Vision & diagnostic…", file=sys.stderr, flush=True)
    vision = await _load_or_run(steps_dir, "step2_vision.json",
        lambda: step2_vision.run(input, research, steps_dir, no_api=no_api))

    print("[3/7] Contre-expertise…", file=sys.stderr, flush=True)
    contre = await _load_or_run(steps_dir, "step3_contre_expertise.json",
        lambda: step3_contre_expertise.run(vision, steps_dir, no_api=no_api))

    print("[4/7] Topics…", file=sys.stderr, flush=True)
    topics = await _load_or_run(steps_dir, "step4_topics.json",
        lambda: step4_topics.run(input, research, steps_dir, no_api=no_api))

    print("[5/7] Incidence…", file=sys.stderr, flush=True)
    incidence = await _load_or_run(steps_dir, "step5_incidence.json",
        lambda: step5_incidence.run(input, topics, steps_dir, no_api=no_api))

    print("[6/7] Review…", file=sys.stderr, flush=True)
    review = await _load_or_run(steps_dir, "step6_review.json",
        lambda: step6_review.run(vision, topics, contre, steps_dir, no_api=no_api))

    print("[7/7] Distill…", file=sys.stderr, flush=True)
    distill = await _load_or_run(steps_dir, "step7_distill.json",
        lambda: step7_distill.run(vision, topics, review, incidence, steps_dir, no_api=no_api))

    assembled = ProgramFullAnalysis(
        metadata=ProgramMetadata(candidate=input.candidate, domains=list(CORE_DOMAINS)),
        research=ProgramResearch.model_validate(research),
        vision_diagnostic=VisionDiagnostic.model_validate(vision),
        contre_expertise=ContreExpertise.model_validate(contre),
        topics=ProgramTopics.model_validate(topics),
        incidence=Incidence.model_validate(incidence),
        review=ProgramReview.model_validate(review),
        distill=ProgramDistill.model_validate(distill),
    )

    issues = _audit_program(json.loads(assembled.model_dump_json()))
    if issues:
        print(f"  ⚠  {len(issues)} sourcing gap(s):", file=sys.stderr)
        for i in issues:
            print(f"     • {i}", file=sys.stderr)
    else:
        print("  ✓ Sourcing audit: all measures and judgments sourced.", file=sys.stderr, flush=True)

    return assembled
```

- [ ] **Step 4: Export from the agent package**

In `agent/__init__.py`, add the import and `__all__` entry:

```python
from .program_analysis_agent import analyze_program
```
Add `"analyze_program"` to `__all__`.

- [ ] **Step 5: Run the audit test to verify it passes**

Run: `uv run pytest tests/test_program_audit.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Create the end-to-end fixtures**

Create `tests/fixtures/program_steps/` with 7 files matching each step's saved shape. Reuse the shapes from the step tests above. Each `stepN_*.json` filename must match the orchestrator's `_load_or_run` filename exactly:
`step1_ingest.json`, `step2_vision.json`, `step3_contre_expertise.json`, `step4_topics.json` (must contain **12** topics, one per `CORE_DOMAINS` entry, each with a sourced measure + expert-sourced faille), `step5_incidence.json`, `step6_review.json` (4 dimensions), `step7_distill.json` (3 points + verdict). Root-cause ids referenced by `contre_expertise` must exist in `step2_vision.json`.

- [ ] **Step 7: Write the end-to-end test**

```python
# tests/test_program_pipeline.py
import shutil
from pathlib import Path

import pytest

from agent.program_analysis_agent import analyze_program, _audit_program
from models.program_analysis import ProgramAnalysisInput, ProgramFullAnalysis, CORE_DOMAINS

FIXTURES = Path(__file__).parent / "fixtures" / "program_steps"


@pytest.mark.asyncio
async def test_pipeline_assembles_from_cached_steps(tmp_path):
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    for f in FIXTURES.glob("*.json"):
        shutil.copy(f, steps_dir / f.name)

    inp = ProgramAnalysisInput(candidate="Candidat X", program_text="… programme court …")
    result = await analyze_program(inp, no_api=True, steps_dir=steps_dir)

    assert isinstance(result, ProgramFullAnalysis)
    assert len(result.topics.topics) == len(CORE_DOMAINS)
    assert len(result.review.dimensions) == 4
    assert len(result.distill.points) == 3
    assert _audit_program(result.model_dump()) == []
```

- [ ] **Step 8: Run the end-to-end test to verify it passes**

Run: `uv run pytest tests/test_program_pipeline.py -v`
Expected: PASS. (If it fails on a missing domain/source, fix the fixture — the cached steps must satisfy the audit.)

- [ ] **Step 9: Run the whole suite**

Run: `uv run pytest tests/ -q`
Expected: PASS — all program tests + untouched article/newsletter tests.

- [ ] **Step 10: Commit**

```bash
git add agent/program_analysis_agent.py agent/__init__.py tests/test_program_audit.py tests/test_program_pipeline.py tests/fixtures/program_steps/
git commit -m "feat(program): analyze_program orchestrator + sourcing audit + e2e test"
```

---

### Task 9: CLI `program` subcommand

**Files:**
- Modify: `main.py` (add `cmd_program` + subparser)

**Interfaces:**
- Consumes: `analyze_program`, `ProgramAnalysisInput`, `_layout`.
- Produces: `python main.py program <program.txt> [--candidate NAME] [--no-api]` writing `samples/outputs/<stem>/analysis.json` + `steps/`.

- [ ] **Step 1: Add `cmd_program` to `main.py`**

Add near the other command handlers (after `cmd_produce`):

```python
async def cmd_program(args: argparse.Namespace) -> None:
    from agent import analyze_program
    from models.program_analysis import ProgramAnalysisInput

    input_path = args.program
    text = Path(input_path).read_text(encoding="utf-8").strip()
    if not text:
        print("Empty program file.", file=sys.stderr)
        sys.exit(1)

    stem = Path(input_path).stem
    candidate = args.candidate or stem
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    lay = _layout(stem)
    lay["base"].mkdir(parents=True, exist_ok=True)

    result = await analyze_program(
        ProgramAnalysisInput(candidate=candidate, program_text=text),
        no_api=args.no_api,
        steps_dir=lay["steps"],
    )
    lay["analysis"].write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"Analysis written to {lay['analysis']}", file=sys.stderr)
    print(f"Step outputs → {lay['steps']}/", file=sys.stderr)
```

- [ ] **Step 2: Register the subparser**

In `_build_parser()`, add alongside the other `sub.add_parser(...)` blocks:

```python
    p = sub.add_parser("program", help="analyze a candidate's program (hors-série)")
    p.add_argument("program", help="candidate program .txt file")
    p.add_argument("--candidate", help="candidate display name (default: file stem)")
    p.add_argument("--no-api", action="store_true", help="use cached steps / local claude CLI")
    p.set_defaults(func=cmd_program)
```

- [ ] **Step 3: Smoke-test the CLI wiring (no API)**

`_layout(stem)` derives the steps dir from the input file's stem, so seed the
cached fixtures under `samples/outputs/<stem>/steps/` for the stem you'll pass.
Use a program file named `_smoke.txt` → stem `_smoke`:

```bash
printf 'Programme de test.\n' > /tmp/_smoke.txt
rm -rf samples/outputs/_smoke
mkdir -p samples/outputs/_smoke/steps
cp tests/fixtures/program_steps/*.json samples/outputs/_smoke/steps/
uv run python main.py program /tmp/_smoke.txt --candidate "Candidat X" --no-api
```

Expected: the run loads all 7 steps from cache (`(loaded from stepN_*.json)` for
each), prints the sourcing-audit line (`✓ Sourcing audit: …`), and writes
`samples/outputs/_smoke/analysis.json`.

- [ ] **Step 4: Verify the output validates**

Run:
```bash
uv run python -c "
import json; from models.program_analysis import ProgramFullAnalysis
ProgramFullAnalysis.model_validate(json.load(open('samples/outputs/_smoke/analysis.json')))
print('OK: analysis.json validates')
"
```
Expected: `OK: analysis.json validates`.

- [ ] **Step 5: Clean up the smoke artifacts**

```bash
rm -rf samples/outputs/_smoke /tmp/_smoke.txt
```

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat(program): add 'program' CLI subcommand"
```

---

## Self-Review

**Spec coverage:**
- Schema (`ProgramFullAnalysis`, `CORE_DOMAINS`, 12 domains) → Task 1. ✓
- Program system prompt + `system=` override → Tasks 2, 3. ✓
- Gather infra (expert steps only) → Task 3. ✓
- 7 steps (ingest, vision, contre-expertise, topics×12, incidence, review×4, distill+verdict) → Tasks 4–7. ✓
- Orchestrator + `_load_or_run` cache + assembly + sourcing audit → Task 8. ✓
- Strict-sourcing audit (measure/root-cause verbatim quote; contre-expertise/faille/incidence specialist source; dangling root-cause ref) → Task 8 audit + tests. ✓
- Neutral tone in every prompt + program system prompt → Tasks 3–7. ✓
- `--no-api` end-to-end test on cached fixtures → Task 8. ✓
- CLI `program <program.txt>` → Task 9. ✓
- Article pipeline untouched (only additive `system=` param) → Task 2 (Step 5 verifies suite still green). ✓

**Placeholder scan:** no TBD/TODO; every step ships real code, real French prompts, and exact commands. ✓

**Type consistency:** step `run` signatures match the orchestrator's calls in Task 8 (`step1_ingest.run(input, steps_dir, no_api)`, `step2_vision.run(input, research, steps_dir, no_api)`, `step3.run(vision, steps_dir, no_api)`, `step4.run(input, research, steps_dir, no_api)`, `step5.run(input, topics, steps_dir, no_api)`, `step6.run(vision, topics, contre, steps_dir, no_api)`, `step7.run(vision, topics, review, incidence, steps_dir, no_api)`). Id prefixes (`st_`, `rc_`, `ce_`, `m_`, `inc_`) are consistent between the step that assigns them and the audit/tests that read them. `_call_with_retry(..., system=...)` matches the Task 2 signature. ✓

## Notes for the implementer
- The `_gather` queries in steps 3/4/5 are first drafts — tune the query wording against the configured `SEARCH_API_PROVIDER` once you can run live.
- Prompts are functional drafts; expect to iterate on wording after seeing real `--no-api`-off output. The *structure* (fields, sourcing, neutrality) is what the tests lock down, not the phrasing.
- Running live (`--no-api` off) needs `ANTHROPIC_API_KEY` and a `SEARCH_API_PROVIDER` in `.env` (see `.env.example`).
