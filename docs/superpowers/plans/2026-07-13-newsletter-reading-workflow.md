# Newsletter 4-phase reading workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the `newsletter` format so its analysis half becomes one chronological "détaillé pass" (fact-checks + failles interleaved in article order) followed by a "vue d'ensemble" synthesis, matching the intended reading workflow.

**Architecture:** Swap the presentation model's separate `fact_check` + `failles` fields for a single ordered `decryptage` list of typed items (`kind: "fait" | "faille"`). The adapt LLM emits the list pre-sorted in article order. The renderer attaches a fact-check verdict pill to `fait` items only; templates render one badged stream, then group strengths/angles/verdict under "La vue d'ensemble". No new analysis step, no new API cost.

**Tech Stack:** Python 3.14, Pydantic v2, Jinja2, pytest. Package management via `uv` (never `pip`).

## Global Constraints

- Python 3.14; manage deps with `uv add` only — never `pip install`.
- French copy throughout the newsletter, existing editorial voice.
- Email templates stay email-client-safe: table layout, inline styles, no SVG/flexbox. Only "chrome" colours are themed (`EMAIL_THEMES`); semantic verdict/gauge colours are fixed.
- Do NOT touch: the analysis pipeline (`agent/full_analysis_agent.py`, `agent/steps/`), either carousel format or their templates/renderers, `extractors/newsletter.py`, the radar/gauge logic, or `renderer/instagram_carousel/**` (its `failles` references are unrelated).
- `decryptage`: 4–6 items total = 2–4 `fait` + 2–4 `faille`, with at least 2 of each, already ordered by article appearance.

---

### Task 1: Presentation model — `DecryptageItem` + field swap

**Files:**
- Modify: `models/newsletter_presentation.py`
- Test: `tests/test_newsletter_model.py` (create)

**Interfaces:**
- Produces: `DecryptageItem(kind: Literal["fait","faille"], quote: str, presentation: str, reading: str, clue: str | None = None)`; `NewsletterPresentation.decryptage: list[DecryptageItem]` replacing `.fact_check` and `.failles`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_newsletter_model.py`:

```python
import pytest
from pydantic import ValidationError
from models.newsletter_presentation import NewsletterPresentation, DecryptageItem


def _base_kwargs(**overrides):
    kwargs = dict(
        subject="Objet", preheader="Aperçu", intro="Intro.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["R1", "R2"],
        decryptage=[
            DecryptageItem(kind="fait", quote="Q1", presentation="fait", reading="L1."),
            DecryptageItem(kind="faille", quote="Q2", presentation="Source unique", reading="M.", clue="une seule source ?"),
            DecryptageItem(kind="fait", quote="Q3", presentation="attribué", reading="L2."),
            DecryptageItem(kind="faille", quote="Q4", presentation="Glissement", reading="M2.", clue="mot neutre ?"),
        ],
        strengths=[{"heading": "Force", "body": "Corps."}],
        angles_morts=["A1", "A2"],
        verdict_line="Verdict.",
        go_further=[{"title": "R1", "source": "S1", "why": "W.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "W.", "type": "rapport"}],
        signoff="Bye.",
    )
    kwargs.update(overrides)
    return kwargs


def test_presentation_accepts_decryptage_list():
    pres = NewsletterPresentation(**_base_kwargs())
    assert [d.kind for d in pres.decryptage] == ["fait", "faille", "fait", "faille"]
    assert pres.decryptage[1].clue == "une seule source ?"


def test_fact_check_and_failles_fields_removed():
    assert "fact_check" not in NewsletterPresentation.model_fields
    assert "failles" not in NewsletterPresentation.model_fields
    assert "decryptage" in NewsletterPresentation.model_fields


def test_decryptage_kind_is_constrained():
    with pytest.raises(ValidationError):
        DecryptageItem(kind="autre", quote="Q", presentation="p", reading="r")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_newsletter_model.py -v`
Expected: FAIL — `ImportError` / `AttributeError` for `DecryptageItem` (not yet defined).

- [ ] **Step 3: Edit the model**

In `models/newsletter_presentation.py`:

Add `Literal` to the imports line:

```python
from pydantic import BaseModel
from typing import Literal
```

Add the new class (place it just above `class FactCheckItem`):

```python
class DecryptageItem(BaseModel):
    """One annotation in the chronological détaillé pass, in article order."""
    kind: Literal["fait", "faille"]   # drives the badge + which extras render
    quote: str          # the article sentence examined (verbatim, « … »)
    presentation: str   # fait: how the article frames it; faille: short mechanism title
    reading: str        # our critical reading / the mechanism (2–4 sentences)
    clue: str | None = None   # failles only — ≤12 words echoing the paired pre-reading reflex
```

Delete the `FactCheckItem` class entirely (lines defining `class FactCheckItem(BaseModel): …`).

Remove the now-unused `clue` field from `NewsletterSection` (it moved to `DecryptageItem`; `strengths` never used it):

```python
class NewsletterSection(BaseModel):
    heading: str   # short French section title
    body: str      # a detailed paragraph — the finding explained, with the article's own words
```

In `NewsletterPresentation`, replace these two lines:

```python
    fact_check: list[FactCheckItem]     # 2–3 — Vérification des faits
    failles: list[NewsletterSection]    # exactly 2 — Les failles (detailed, with article words)
```

with:

```python
    decryptage: list[DecryptageItem]    # 4–6, article-ordered — Le décryptage, pas à pas (faits + failles)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_newsletter_model.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add models/newsletter_presentation.py tests/test_newsletter_model.py
git commit -m "feat(newsletter): DecryptageItem model, replace fact_check/failles"
```

---

### Task 2: Adapt validator

**Files:**
- Modify: `agent/newsletter_adapt_agent.py:16-40` (the `_validate` function)
- Test: `tests/test_newsletter_validate.py` (create)

**Interfaces:**
- Consumes: `NewsletterPresentation.decryptage` (Task 1).
- Produces: `_validate(data: dict) -> list[str]` — empty list = valid.

- [ ] **Step 1: Write the failing test**

Create `tests/test_newsletter_validate.py`:

```python
from agent.newsletter_adapt_agent import _validate


def _valid_data():
    return dict(
        subject="Objet", preheader="Aperçu", intro="Intro.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["R1", "R2"],
        decryptage=[
            {"kind": "fait", "quote": "Q1", "presentation": "fait", "reading": "L1."},
            {"kind": "faille", "quote": "Q2", "presentation": "Source unique", "reading": "M.", "clue": "une source ?"},
            {"kind": "fait", "quote": "Q3", "presentation": "attribué", "reading": "L2."},
            {"kind": "faille", "quote": "Q4", "presentation": "Glissement", "reading": "M2.", "clue": "mot neutre ?"},
        ],
        strengths=[{"heading": "Force", "body": "Corps."}],
        angles_morts=["A1", "A2"],
        verdict_line="Verdict.",
        go_further=[{"title": "R1", "source": "S1", "why": "W.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "W.", "type": "rapport"}],
        signoff="Bye.",
    )


def test_valid_passes():
    assert _validate(_valid_data()) == []


def test_too_few_decryptage_fails():
    d = _valid_data()
    d["decryptage"] = d["decryptage"][:3]  # only 1 faille left → both count + faille-min fail
    assert any("decryptage" in e for e in _validate(d))


def test_faille_without_clue_fails():
    d = _valid_data()
    d["decryptage"][1].pop("clue")
    assert any("clue" in e for e in _validate(d))


def test_needs_at_least_two_of_each_kind():
    d = _valid_data()
    d["decryptage"][3]["kind"] = "fait"  # 3 faits, 1 faille
    assert any("faille" in e for e in _validate(d))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_newsletter_validate.py -v`
Expected: FAIL — `test_valid_passes` errors because `_validate` still references `pres.fact_check`/`pres.failles` (AttributeError).

- [ ] **Step 3: Edit the validator**

In `agent/newsletter_adapt_agent.py`, replace the fact_check + failles blocks. Delete these lines:

```python
    if not (2 <= len(pres.fact_check) <= 3):
        errors.append(f"fact_check must have 2–3 items, got {len(pres.fact_check)}")
    if len(pres.failles) != 2:
        errors.append(f"failles must have exactly 2 items, got {len(pres.failles)}")
```

and delete the failles loop:

```python
    for i, s in enumerate(pres.failles):
        if not s.heading.strip() or not s.body.strip():
            errors.append(f"failles[{i}] has an empty heading/body")
```

Insert this in their place (keep the `strengths` count check and its loop as-is):

```python
    n = len(pres.decryptage)
    faits = [d for d in pres.decryptage if d.kind == "fait"]
    failles = [d for d in pres.decryptage if d.kind == "faille"]
    if not (4 <= n <= 6):
        errors.append(f"decryptage must have 4–6 items, got {n}")
    if len(faits) < 2:
        errors.append(f"decryptage needs at least 2 'fait' items, got {len(faits)}")
    if len(failles) < 2:
        errors.append(f"decryptage needs at least 2 'faille' items, got {len(failles)}")
    for i, d in enumerate(pres.decryptage):
        if not d.quote.strip() or not d.reading.strip():
            errors.append(f"decryptage[{i}] has an empty quote/reading")
        if d.kind == "faille" and not (d.clue or "").strip():
            errors.append(f"decryptage[{i}] (faille) is missing its clue")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_newsletter_validate.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add agent/newsletter_adapt_agent.py tests/test_newsletter_validate.py
git commit -m "feat(newsletter): validate decryptage counts + faille clue"
```

---

### Task 3: Adapt prompt

**Files:**
- Modify: `agent/prompts/newsletter.md`

**Interfaces:**
- Produces: instructions that make the LLM emit `decryptage` (article-ordered). No code, no automated test — verified live in Task 6.

- [ ] **Step 1: Rewrite the fact_check + failles instruction lines**

Replace these two bullets (the `fact_check` block on line ~22 and the `failles` block on line ~26, through its sub-bullets):

```markdown
- `fact_check` : 2 à 3 items — **Vérification des faits**, chacun `{claim, presentation, reading}` :
  - `claim` : l'affirmation, citée ou paraphrasée fidèlement
  - `presentation` : comment l'article la présente (« présenté comme un fait », « attribué à une source », « opinion présentée comme un fait »)
  - `reading` : 2–3 phrases — notre lecture critique : ce qui tient, ce qu'il faut recouper. (depuis `annotations.facts_vs_opinions`)
- `failles` : exactement 2 items `{heading, body, clue}` — **Les failles** (les 2 faiblesses décisives), appariées aux `reflexes` (même ordre) :
  - `heading` : titre court (ex. « Une source unique, sans contradiction »)
  - `body` : 3–5 phrases — explique le mécanisme de la faille ET pourquoi elle compte, en t'appuyant sur les mots de l'article (guillemets). (depuis `guide.watch_out` / `review.dimensions` les plus faibles)
  - `clue` : ≤12 mots — un rappel du réflexe apparié (`reflexes[i]`), formulé comme la question que le lecteur devait garder en tête (ex. « le constat tient-il à une seule institution ? »). Sans gras.
```

with:

```markdown
- `decryptage` : 4 à 6 items — **Le décryptage, pas à pas** : le cœur de l'analyse, une lecture critique de l'article DANS L'ORDRE OÙ IL SE DÉROULE. Mélange 2–4 vérifications de faits et 2–4 failles (au moins 2 de chaque), **triés selon leur ordre d'apparition dans l'article** — suis l'ordre de `annotations.facts_vs_opinions.claims_and_sources`, et insère chaque faille à la position du passage qu'elle concerne. Chaque item `{kind, quote, presentation, reading, clue}` :
  - `kind` : « fait » (vérification d'une affirmation) ou « faille » (faiblesse de raisonnement ou de traitement)
  - `quote` : la phrase de l'article examinée, citée FIDÈLEMENT entre guillemets « … »
  - `presentation` : pour un `fait`, comment l'article la présente (« présenté comme un fait », « attribué à une source », « opinion présentée comme un fait ») ; pour une `faille`, un titre court du mécanisme (ex. « Une source unique, sans contradiction »)
  - `reading` : 2–4 phrases — pour un `fait`, notre lecture critique (ce qui tient, ce qu'il faut recouper, depuis `annotations.facts_vs_opinions`) ; pour une `faille`, le mécanisme ET pourquoi il compte, appuyé sur les mots de l'article (depuis `guide.watch_out` / `review.dimensions` les plus faibles)
  - `clue` : **failles uniquement** — ≤12 mots, un rappel du réflexe apparié (`reflexes`), formulé comme la question que le lecteur devait garder en tête (ex. « le constat tient-il à une seule institution ? »). Les failles restent appariées aux `reflexes` dans le même ordre relatif. Sans gras. (Laisse `clue` vide pour les items `fait`.)
```

- [ ] **Step 2: Update the bold-emphasis field list**

On line ~11, in the parenthesised field list, replace `` `fact_check.reading`, `failles.body` `` with `` `decryptage.reading` ``, and in the "N'en mets PAS dans" clause replace `` `claim` `` with `` `quote` `` (so it reads `… les « heading » / « title » / « quote » / « presentation » / « source »`).

- [ ] **Step 3: Update the voice line**

On line ~9, change "dans les failles" to "dans le décryptage" so the quoting guidance points at the new field:

```markdown
**Voix.** Ton éditorial, direct, un peu incisif — celui d'un décryptage qui aide à mieux lire. Développé mais sans remplissage. JAMAIS de score de confiance, d'identifiant de nœud (`claim_3`, `cui_bono`…). Tu PEUX citer les mots de l'article entre guillemets « … » dans le décryptage.
```

- [ ] **Step 4: Update the reflexes pairing note**

On line ~21, the `reflexes` bullet references "les 2 `failles`". Change it to point at the failles inside `decryptage`:

```markdown
- `reflexes` : exactement 2 items, 1 phrase chacun — les réflexes à garder en tête avant de lire. (depuis `guide.pre_reading`). Les 2 `reflexes` et les 2 failles du `decryptage` forment des PAIRES indice → révélation : le réflexe amorce ce qu'une faille démontrera ; garde le même ordre relatif entre les réflexes et les failles.
```

- [ ] **Step 5: Verify no stale references remain**

Run: `grep -nE "fact_check|failles" agent/prompts/newsletter.md`
Expected: no output (empty).

- [ ] **Step 6: Commit**

```bash
git add agent/prompts/newsletter.md
git commit -m "feat(newsletter): prompt emits article-ordered decryptage"
```

---

### Task 4: Renderer context — `_decryptage_ctx` + wire into `_ctx`

**Files:**
- Modify: `renderer/newsletter/renderer.py` (`_ctx` ~line 200, `_email_ctx` ~line 279)
- Create: `tests/_newsletter_fixtures.py`
- Test: `tests/test_newsletter_render.py` (create)

**Interfaces:**
- Consumes: `NewsletterDocument`, `NewsletterPresentation.decryptage` (Task 1); existing `_fc_verdict(quote, claims) -> (label, colour)`.
- Produces: `_decryptage_ctx(doc) -> list[dict]` where each dict has `kind, quote, presentation, reading, clue`; `fait` items additionally carry `verdict` and `color`. `_ctx` now emits `"decryptage"` and no longer emits `"fact_check"`/`"failles"`. `sample_doc()` test fixture in `tests/_newsletter_fixtures.py`.

- [ ] **Step 1: Create the shared test fixture**

Create `tests/_newsletter_fixtures.py`:

```python
import json
from pathlib import Path

from models.full_analysis import ArticleFullAnalysis
from models.newsletter_presentation import (
    NewsletterPresentation, NewsletterDocument, DecryptageItem,
)

_ANALYSIS = Path(__file__).resolve().parent.parent / "samples/outputs/article_1/analysis.json"


def sample_doc() -> NewsletterDocument:
    """A NewsletterDocument built from a real sample analysis + a hand-authored
    presentation on the new schema (no API)."""
    full = ArticleFullAnalysis.model_validate(json.loads(_ANALYSIS.read_text(encoding="utf-8")))
    pres = NewsletterPresentation(
        subject="Objet test", preheader="Aperçu test", intro="Intro.",
        why_selected="Pourquoi.", payoff="Gain.", context="Contexte.",
        reflexes=["Réflexe 1", "Réflexe 2"],
        decryptage=[
            DecryptageItem(kind="fait", quote="Q1", presentation="présenté comme un fait", reading="Lecture 1."),
            DecryptageItem(kind="faille", quote="Q2", presentation="Source unique", reading="Mécanisme.", clue="une seule source ?"),
            DecryptageItem(kind="fait", quote="Q3", presentation="attribué à une source", reading="Lecture 2."),
            DecryptageItem(kind="faille", quote="Q4", presentation="Glissement sémantique", reading="Mécanisme 2.", clue="le mot est-il neutre ?"),
        ],
        strengths=[{"heading": "Une force", "body": "Corps."}],
        angles_morts=["Angle 1", "Angle 2"],
        verdict_line="Verdict.",
        go_further=[{"title": "R1", "source": "S1", "why": "Pourquoi.", "type": "étude"},
                    {"title": "R2", "source": "S2", "why": "Pourquoi.", "type": "rapport"}],
        signoff="À bientôt.",
    )
    return NewsletterDocument(analysis=full, presentation=pres)
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_newsletter_render.py`:

```python
from renderer.newsletter.renderer import _decryptage_ctx
from tests._newsletter_fixtures import sample_doc


def test_decryptage_ctx_preserves_order_and_kinds():
    items = _decryptage_ctx(sample_doc())
    assert [i["kind"] for i in items] == ["fait", "faille", "fait", "faille"]


def test_fait_carries_verdict_faille_carries_clue():
    items = _decryptage_ctx(sample_doc())
    faits = [i for i in items if i["kind"] == "fait"]
    failles = [i for i in items if i["kind"] == "faille"]
    assert faits and all("verdict" in i and "color" in i for i in faits)
    assert failles and all(i.get("clue") for i in failles)
    assert all("verdict" not in i for i in failles)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_newsletter_render.py -v`
Expected: FAIL — `ImportError: cannot import name '_decryptage_ctx'`.

- [ ] **Step 4: Add `_decryptage_ctx` and wire it in**

In `renderer/newsletter/renderer.py`, add this function just below `_fc_verdict` (~line 143):

```python
def _decryptage_ctx(doc: NewsletterDocument) -> list[dict]:
    """The chronological détaillé pass as render-ready dicts (article order kept).
    `fait` items get a verdict pill (label + colour) matched to the analysis claim;
    `faille` items keep their clue and no pill."""
    ann = getattr(doc.analysis, "annotations", None)
    claims = ann.facts_vs_opinions.claims_and_sources if ann else []
    items = []
    for d in doc.presentation.decryptage:
        item = {"kind": d.kind, "quote": d.quote, "presentation": d.presentation,
                "reading": d.reading, "clue": d.clue}
        if d.kind == "fait":
            item["verdict"], item["color"] = _fc_verdict(d.quote, claims)
        items.append(item)
    return items
```

In `_ctx`, replace these two lines:

```python
        "fact_check": list(pres.fact_check),
        "failles": list(pres.failles),
```

with:

```python
        "decryptage": _decryptage_ctx(doc),
```

In `_email_ctx`, delete the whole fact_check re-derivation block (from `ann = getattr(doc.analysis, "annotations", None)` through `ctx["fact_check"] = fact_check`), leaving `dims_bars` and `gauge_color`. The function should end:

```python
    ctx["gauge_color"] = _LEVEL_COLOR.get(ctx["gauge_level"], "#e8a07a")
    return ctx
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_newsletter_render.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add renderer/newsletter/renderer.py tests/_newsletter_fixtures.py tests/test_newsletter_render.py
git commit -m "feat(newsletter): _decryptage_ctx, verdict pill on fait items"
```

---

### Task 5: Templates + CSS

**Files:**
- Modify: `renderer/newsletter/templates/newsletter.md`
- Modify: `renderer/newsletter/templates/newsletter.html`
- Modify: `renderer/newsletter/templates/newsletter.css`
- Modify: `renderer/newsletter/templates/newsletter.email.html`
- Test: `tests/test_newsletter_render.py` (extend)

**Interfaces:**
- Consumes: `decryptage` context list (Task 4), each item `{kind, quote, presentation, reading, clue, [verdict, color]}`.

- [ ] **Step 1: Extend the failing test**

Append to `tests/test_newsletter_render.py`:

```python
from renderer.newsletter.renderer import (
    generate_markdown, generate_html, generate_email_html,
)


def test_markdown_structure_and_order():
    md = generate_markdown(sample_doc())
    assert "Le décryptage, pas à pas" in md
    assert "La vue d'ensemble" in md
    assert "Vérification des faits" not in md
    assert "## Les failles" not in md
    assert md.index("Le décryptage") < md.index("La vue d'ensemble") < md.index("Notre verdict")


def test_rich_html_has_badges():
    html = generate_html(sample_doc())
    assert "Le décryptage, pas à pas" in html
    assert "Fait" in html and "Faille" in html
    assert "Vérification des faits" not in html


def test_email_both_themes():
    for theme in ("light", "dark"):
        html = generate_email_html(sample_doc(), theme)
        assert "Le décryptage, pas à pas" in html
        assert "La vue d'ensemble" in html
        assert "Vérification des faits" not in html
        assert "Les failles" not in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_newsletter_render.py -v`
Expected: FAIL — templates still reference `fact_check`/`failles` (UndefinedError) or missing strings.

- [ ] **Step 3: Edit `newsletter.md`**

Replace the block from `## Vérification des faits` through the end of the `## Notre verdict` section (lines ~20–51) with:

```jinja
## Le décryptage, pas à pas
{% for d in decryptage %}
> « {{ d.quote }} »
> *{% if d.kind == "fait" %}⚖️ Fait — {{ d.verdict }}{% else %}⚠️ Faille{% endif %} · {{ d.presentation }}*

{{ d.reading }}
{% if d.clue %}
↩ *« {{ d.clue }} »*
{% endif %}{% endfor %}
## La vue d'ensemble

### Ce qui tient
{% for s in strengths %}
#### ✓ {{ s.heading }}

{{ s.body }}
{% endfor %}
### Angles morts & nuances
{% for a in angles_morts %}
- {{ a }}
{%- endfor %}

### Notre verdict

{% if score %}**{{ score }} / 5**{% if band %} — {{ band }}{% endif %}

{% endif %}{{ verdict_line }}
{% if for_whom %}
*Pour qui : {{ for_whom }}*
{% endif %}
```

(Leave the `## Pour aller plus loin` section and everything after it unchanged.)

- [ ] **Step 4: Edit `newsletter.html`**

Replace the two kicker blocks — "Vérification des faits" (lines ~23–28) and "Les failles" (lines ~30–34) — with one décryptage block:

```jinja
  <div class="kicker"><svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>Le décryptage, pas à pas</div>
  {% for d in decryptage %}<div class="decrypt {{ d.kind }}">
    <div class="dtop">
      <span class="badge {{ d.kind }}">{% if d.kind == 'fait' %}⚖️ Fait{% else %}⚠️ Faille{% endif %}</span>
      {% if d.kind == 'fait' %}<span class="pill" style="color:{{ d.color }};border-color:{{ d.color }};">{{ d.verdict }}</span>{% endif %}
    </div>
    <div class="claim">« {{ d.quote }} »</div>
    <div class="pres">{{ d.presentation }}</div>
    <p>{{ d.reading | md_bold }}</p>
    {% if d.clue %}<div class="clue"><span class="ret">↩</span> «&nbsp;{{ d.clue }}&nbsp;»</div>{% endif %}
  </div>{% endfor %}

  <div class="kicker vue"><svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/></svg>La vue d'ensemble</div>
```

Immediately after that, the existing "Ce qui tient" kicker block follows. Delete the standalone "Ce qui tient" kicker `<div class="kicker">…Ce qui tient</div>` line (line ~36) since the strengths cards now sit directly under "La vue d'ensemble"; keep the `{% for s in strengths %}` loop. (The "Angles morts" and "Notre verdict" kickers/blocks stay as-is.)

- [ ] **Step 5: Edit `newsletter.css`**

Delete the now-unused `/* fact check */` rule block (the `.fact`, `.fact .claim`, `.fact .pres`, `.fact p` rules, lines ~31–35). Add, just below where they were:

```css
/* décryptage (chronological pass) */
.decrypt { border-left: 3px solid #d4aa00; padding: 2px 0 2px 22px; margin: 22px 0; break-inside: avoid; }
.decrypt.faille { border-left-color: #e8a07a; }
.decrypt .dtop { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.decrypt .badge { font-size: 12px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: #d4aa00; }
.decrypt .badge.faille { color: #e8a07a; }
.decrypt .pill { font-size: 11px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; border: 1.5px solid; border-radius: 999px; padding: 3px 12px; }
.decrypt .claim { font-size: 17px; font-style: italic; line-height: 1.4; color: #f0f0f0; }
.decrypt .pres { font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #8a8a8a; margin: 6px 0 8px; }
.decrypt p { font-size: 16px; color: #dedede; margin: 0; }
.decrypt .clue { font-size: 15px; font-style: italic; color: #9a9a9a; margin-top: 10px; }
.decrypt .clue .ret { color: #d4aa00; font-style: normal; font-weight: 700; }
.kicker.vue { margin-top: 48px; }
```

- [ ] **Step 6: Edit `newsletter.email.html`**

Replace the "Vérification des faits" card (lines ~169–183) and the "Les failles" card (lines ~185–193) with one décryptage card:

```jinja
    <!-- Le décryptage, pas à pas -->
    {% call card("🔍", "Le décryptage, pas à pas") %}
      {% for d in decryptage %}
      {% if not loop.first %}<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:20px 0;"><tr><td height="1" bgcolor="{{ t.border }}" style="height:1px;font-size:0;line-height:0;background-color:{{ t.border }};">&nbsp;</td></tr></table>{% endif %}
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
        <td width="3" bgcolor="{% if d.kind == 'fait' %}{{ t.accent }}{% else %}#cf8a5a{% endif %}" style="width:3px;font-size:0;line-height:0;background-color:{% if d.kind == 'fait' %}{{ t.accent }}{% else %}#cf8a5a{% endif %};">&nbsp;</td>
        <td style="padding-left:18px;">
          <div style="padding-bottom:9px;">
            <span style="display:inline-block;font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:{% if d.kind == 'fait' %}{{ t.accent_text }}{% else %}#cf8a5a{% endif %};">{% if d.kind == 'fait' %}&#9878;&#65039; Fait{% else %}&#9888;&#65039; Faille{% endif %}</span>
            {% if d.kind == 'fait' %}<span style="display:inline-block;margin-left:8px;font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:{{ d.color }};border:1.5px solid {{ d.color }};border-radius:999px;padding:3px 12px;">{{ d.verdict }}</span>{% endif %}
          </div>
          <div style="font-size:17px;font-style:italic;line-height:1.45;color:{{ t.heading }};">&laquo;&nbsp;{{ d.quote }}&nbsp;&raquo;</div>
          <div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{{ t.muted }};padding:7px 0 9px;">{{ d.presentation }}</div>
          <div style="font-size:16px;line-height:1.58;color:{{ t.text_soft }};">{{ d.reading | md_bold_email(t.accent_text) }}</div>
          {% if d.clue %}<div style="font-size:15px;font-style:italic;line-height:1.4;color:{{ t.muted }};padding-top:11px;"><span style="color:{{ t.accent_text }};font-style:normal;font-weight:700;">&#8617;</span>&nbsp; &laquo;&nbsp;{{ d.clue }}&nbsp;&raquo;</div>{% endif %}
        </td>
      </tr></table>
      {% endfor %}
    {% endcall %}

    {{ kicker("🧠", "La vue d'ensemble") }}
```

(The "Ce qui tient", "Angles morts", "Notre verdict", "Pour aller plus loin" cards below stay unchanged — they now render under the "La vue d'ensemble" kicker.)

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/test_newsletter_render.py -v`
Expected: PASS (5 tests).

- [ ] **Step 8: Commit**

```bash
git add renderer/newsletter/templates/
git commit -m "feat(newsletter): render one décryptage stream + La vue d'ensemble"
```

---

### Task 6: Full-suite check + live integration

**Files:** none (verification only).

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest tests/ -v`
Expected: all tests pass (existing `test_search.py` + the 4 new files).

- [ ] **Step 2: Live adapt + render on a sample**

The existing `samples/outputs/article_1/newsletter/adapt.json` is on the old schema; regenerate it:

Run:
```bash
python main.py adapt samples/outputs/article_1/analysis.json --format newsletter
python main.py extract samples/outputs/article_1/analysis.json samples/outputs/article_1/newsletter/adapt.json --format newsletter --render
```
Expected: adapt validates (no validator errors), and render writes `newsletter.md`, `.html`, `.email.html`, `.email.dark.html`.

- [ ] **Step 3: Eyeball the output**

Run: `grep -nE "décryptage|vue d'ensemble|Fait|Faille|Vérification des faits" samples/outputs/article_1/newsletter/newsletter.md`
Expected: "Le décryptage, pas à pas" and "La vue d'ensemble" present; "Vérification des faits" absent. Confirm the décryptage items read in article order and each faille shows a `↩` clue.

Open `samples/outputs/article_1/newsletter/newsletter.email.html` and `.email.dark.html` in a browser; confirm section order reads Phase 1 → 2 → décryptage → vue d'ensemble → Pour aller plus loin, in both themes, with Fait/Faille badges and fait verdict pills visible.

- [ ] **Step 4: Commit regenerated sample (optional)**

```bash
git add samples/outputs/article_1/newsletter/
git commit -m "chore(newsletter): regenerate article_1 sample on new schema"
```

---

## Self-Review

**Spec coverage:**
- Model swap (spec §1) → Task 1. ✓
- Validator (spec §2) → Task 2. ✓
- Adapt prompt, article-ordered (spec §3) → Task 3. ✓
- Renderer `_fc_verdict` per fait, single context list (spec §4) → Task 4. ✓
- Templates md/html/email + "La vue d'ensemble" grouping (spec §5) → Task 5. ✓
- Both email themes verified (spec Verification) → Tasks 5 & 6. ✓
- Out-of-scope items (carousels, extractor, analysis pipeline) untouched — asserted in Global Constraints. ✓

**Placeholder scan:** No TBD/TODO; every code and template step shows full content. ✓

**Type consistency:** `DecryptageItem(kind, quote, presentation, reading, clue)` defined in Task 1 is consumed identically in Tasks 2 (`d.kind`, `d.quote`, `d.reading`, `d.clue`), 4 (`_decryptage_ctx` builds `{kind, quote, presentation, reading, clue, [verdict, color]}`), and 5 (templates read those exact keys). `_fc_verdict(quote, claims)` signature matches its existing definition. ✓
