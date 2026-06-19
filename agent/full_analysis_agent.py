"""Multi-step full article analysis pipeline.

Steps:
  1. Extraction   — raw facts, claims, actors, omissions (no interpretation)
  2. Avant de lire — cadrage + context + watch_out
  3. Analyse fond  — main_claim, assumptions, blind_spots, observations
  4. Analyse forme — emotional_register, cui_bono
  5. Annotations  — facts_vs_opinions + biases_and_focus
  6. Finale        — hook + interest + synthesis + cta
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from models.full_analysis import (
    AnalysisFond,
    AnalyseForme,
    ArticleExtraction,
    ArticleFullAnalysis,
    ArticleMetadata,
    BiasRhetoric,
    ClaimAndSource,
    FullAnalysisInput,
    GlobalAnalysisItem,
    ProvenByRef,
    SynthesisPoint,
    TextItem,
)
from models.full_analysis_steps import ExtractionResult, Step2Output, Step5Output, Step6Output

client = anthropic.Anthropic()

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "analyze_article.md").read_text(
    encoding="utf-8"
)

MAX_RETRIES = 2


# ── Validators ───────────────────────────────────────────────────────────────

def _validate_avant_de_lire(data: dict) -> list[str]:
    step2 = Step2Output.model_validate(data)
    errors = []
    n = len(step2.watch_out.items)
    if not (2 <= n <= 8):
        errors.append(f"watch_out.items: expected 2–8, got {n}")
    if not step2.context.contexts:
        errors.append("context.contexts is empty")
    if not step2.context.important_facts:
        errors.append("context.important_facts is empty")
    if not step2.cadrage.title_bullets:
        errors.append("cadrage.title_bullets is empty (required for slide 3)")
    return errors


def _validate_fond(data: dict) -> list[str]:
    fond = AnalysisFond.model_validate(data)
    errors = []
    if not fond.main_claim:
        errors.append("analysis_fond.main_claim is empty")
    n = len(fond.observations)
    if not (1 <= n <= 5):
        errors.append(f"observations: expected 1–5, got {n}")
    for i, obs in enumerate(fond.observations):
        if not obs.seeds.excerpt:
            errors.append(f"observations[{i}].seeds.excerpt is empty")
    if not fond.premisses:
        errors.append("analysis_fond.premisses is empty")
    for i, p in enumerate(fond.premisses):
        if not p.statement:
            errors.append(f"premisses[{i}].statement is empty")
    if not fond.implicit_assumptions:
        errors.append("analysis_fond.implicit_assumptions is empty")
    if not fond.blind_spots:
        errors.append("analysis_fond.blind_spots is empty")
    if not fond.emphasis:
        errors.append("analysis_fond.emphasis is empty")
    if not fond.logical_reasoning:
        errors.append("analysis_fond.logical_reasoning is empty")
    for i, lr in enumerate(fond.logical_reasoning):
        if not lr.step:
            errors.append(f"logical_reasoning[{i}].step is empty")
    if not fond.steel_man:
        errors.append("analysis_fond.steel_man is empty")
    return errors


def _validate_forme(data: dict) -> list[str]:
    forme = AnalyseForme.model_validate(data)
    errors = []
    n_er = len(forme.emotional_register)
    if not (1 <= n_er <= 2):
        errors.append(f"emotional_register: expected 1–2, got {n_er}")
    for i, er in enumerate(forme.emotional_register):
        if not er.seeds.excerpt:
            errors.append(f"emotional_register[{i}].seeds.excerpt is empty")
    n_cb = len(forme.cui_bono)
    if not (1 <= n_cb <= 2):
        errors.append(f"cui_bono: expected 1–2, got {n_cb}")
    for i, cb in enumerate(forme.cui_bono):
        if not cb.seeds.excerpt:
            errors.append(f"cui_bono[{i}].seeds.excerpt is empty")
    return errors


def _validate_annotations(data: dict, fond_data: dict, forme_data: dict) -> list[str]:
    step5 = Step5Output.model_validate(data)
    fond = AnalysisFond.model_validate(fond_data)
    forme = AnalyseForme.model_validate(forme_data)
    errors = []

    valid_by_type = {
        "observation": {obs.aspect for obs in fond.observations},
        "emotional_register": {e.emotion for e in forme.emotional_register},
        "cui_bono": {c.beneficiary for c in forme.cui_bono},
    }

    def _check_proves(ref, path: str) -> str | None:
        valid = valid_by_type.get(ref.type, set())
        if ref.label not in valid:
            return (
                f"{path}.proves has type='{ref.type}' label='{ref.label}' but "
                f"'{ref.label}' not found in {ref.type}. Valid: {sorted(valid)}"
            )
        return None

    fvo = step5.facts_vs_opinions
    n_claims = len(fvo.claims_and_sources)
    if not (1 <= n_claims <= 6):
        errors.append(f"claims_and_sources: expected 1–6, got {n_claims}")
    for i, claim in enumerate(fvo.claims_and_sources):
        err = _check_proves(claim.proves, f"claims_and_sources[{i}]")
        if err:
            errors.append(err)

    bf = step5.biases_and_focus
    n_biases = len(bf.biases_and_rhetoric)
    if not (1 <= n_biases <= 4):
        errors.append(f"biases_and_rhetoric: expected 1–4, got {n_biases}")
    for i, bias in enumerate(bf.biases_and_rhetoric):
        err = _check_proves(bias.proves, f"biases_and_rhetoric[{i}]")
        if err:
            errors.append(err)

    # focus.proves must point to an observation specifically
    if bf.focus.proves.type != "observation":
        errors.append(f"focus.proves.type must be 'observation', got '{bf.focus.proves.type}'")
    else:
        err = _check_proves(bf.focus.proves, "focus")
        if err:
            errors.append(err)

    return errors


def _validate_finale(data: dict) -> list[str]:
    step6 = Step6Output.model_validate(data)
    errors = []
    n_points = len(step6.synthesis.points)
    if not (1 <= n_points <= 5):
        errors.append(f"synthesis.points must contain 1–5 items, got {n_points}")
    if not step6.synthesis.open_question.strip():
        errors.append("synthesis.open_question is empty")
    if not step6.synthesis.engagement_question.strip():
        errors.append("synthesis.engagement_question is empty")
    n_go = len(step6.go_further.items)
    if not (1 <= n_go <= 6):
        errors.append(f"go_further.items must contain 1–6 items, got {n_go}")
    n_cta_q = len(step6.cta.post_reading_questions)
    if not (1 <= n_cta_q <= 4):
        errors.append(f"cta.post_reading_questions must contain 1–4 items, got {n_cta_q}")
    blind_spots = [q for q in step6.cta.post_reading_questions if q.type == "blind_spot"]
    if not blind_spots:
        errors.append("cta.post_reading_questions: at least one question must be of type 'blind_spot'")
    for i, item in enumerate(step6.go_further.items):
        if item.cta_question_index is not None and not (0 <= item.cta_question_index < n_cta_q):
            errors.append(
                f"go_further[{i}].cta_question_index={item.cta_question_index} out of range (0–{n_cta_q - 1})"
            )
    return errors


# ── Core call + retry ────────────────────────────────────────────────────────

def _call_no_api(user_message: str, schema: dict) -> dict:
    """Invoke the Claude Code CLI (claude -p) instead of the Anthropic SDK."""
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        "---\n\n"
        f"{user_message}\n\n"
        "---\n\n"
        "Réponds UNIQUEMENT avec un objet JSON valide correspondant exactement à ce schéma :\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        "N'ajoute aucun texte avant ni après le JSON. Pas de balises markdown. Pas d'explication."
    )
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed:\n{result.stderr}")
    text = result.stdout.strip()
    # Strip markdown code block if Claude wraps its response
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        text = match.group(1).strip()
    # Remove trailing commas before } or ] (invalid JSON produced by CLI)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(text)


def _call(user_message: str, schema: dict, no_api: bool = False) -> dict:
    if no_api:
        return _call_no_api(user_message, schema)
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": schema,
            }
        },
    ) as stream:
        response = stream.get_final_message()
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def _call_with_retry(
    user_message: str,
    schema: dict,
    validator,  # (data: dict) -> list[str]
    no_api: bool = False,
) -> dict:
    data = _call(user_message, schema, no_api=no_api)

    for attempt in range(MAX_RETRIES):
        errors = validator(data)
        if not errors:
            return data

        error_text = "\n".join(f"- {e}" for e in errors)
        print(
            f"  ↻ {len(errors)} incohérence(s) détectée(s), correction ({attempt + 1}/{MAX_RETRIES})…",
            file=sys.stderr,
            flush=True,
        )

        correction_msg = (
            f"{user_message}\n\n"
            "---\n\n"
            f"CORRECTION REQUISE — Ta réponse précédente contenait {len(errors)} incohérence(s) :\n\n"
            f"{error_text}\n\n"
            "Ta réponse précédente (à corriger) :\n"
            f"{json.dumps(data, ensure_ascii=False, indent=2)}\n\n"
            "Produis une version corrigée qui adresse chacun de ces points précisément. "
            "Ne change que ce qui est incohérent — conserve le reste."
        )
        data = _call(correction_msg, schema, no_api=no_api)

    # After max retries: warn about remaining issues but continue
    errors = validator(data)
    for e in errors:
        print(f"  ⚠  {e}", file=sys.stderr)

    return data


class RepairPatch(BaseModel):
    additional_observations: list[GlobalAnalysisItem] = Field(default_factory=list)
    additional_claims: list[ClaimAndSource] = Field(default_factory=list)
    additional_biases: list[BiasRhetoric] = Field(default_factory=list)
    fixed_synthesis_points: list[SynthesisPoint] = Field(default_factory=list)


def _audit_connections(data: dict) -> list[str]:
    """Return a list of connection gaps in the assembled analysis."""
    issues = []

    watch_out_items = data.get("watch_out", {}).get("items", [])
    contexts        = data.get("context", {}).get("contexts", [])
    facts           = data.get("context", {}).get("important_facts", [])
    observations    = data.get("analysis_fond", {}).get("observations", [])
    emotional_reg   = data.get("analysis_forme", {}).get("emotional_register", [])
    cui_bono        = data.get("analysis_forme", {}).get("cui_bono", [])
    claims          = data.get("facts_vs_opinions", {}).get("claims_and_sources", [])
    biases          = data.get("biases_and_focus", {}).get("biases_and_rhetoric", [])
    focus           = data.get("biases_and_focus", {}).get("focus") or {}
    synthesis_pts   = data.get("synthesis", {}).get("points", [])

    referenced_wo  = set()
    referenced_ctx = set()
    referenced_fct = set()

    def _walk_seeds(item: dict) -> None:
        s = item.get("seeds") or {}
        src, idx = s.get("source"), s.get("index")
        if src == "watch_out" and idx is not None:      referenced_wo.add(idx)
        elif src == "context" and idx is not None:      referenced_ctx.add(idx)
        elif src == "important_fact" and idx is not None: referenced_fct.add(idx)

    for obs in observations: _walk_seeds(obs)
    for er  in emotional_reg: _walk_seeds(er)
    for cb  in cui_bono:     _walk_seeds(cb)

    referenced_obs = set()
    referenced_er  = set()
    referenced_cb  = set()

    def _walk_proves(item: dict) -> None:
        p = item.get("proves") or {}
        t, lbl = p.get("type"), p.get("label")
        if t == "observation":          referenced_obs.add(lbl)
        elif t == "emotional_register": referenced_er.add(lbl)
        elif t == "cui_bono":           referenced_cb.add(lbl)

    for c in claims: _walk_proves(c)
    for b in biases: _walk_proves(b)
    if focus:        _walk_proves(focus)

    all_ids = (
        {o.get("id") for o in observations} | {e.get("id") for e in emotional_reg} |
        {c.get("id") for c in cui_bono}     | {c.get("id") for c in claims}        |
        {b.get("id") for b in biases}
    )
    all_ids.discard("")

    for i, w in enumerate(watch_out_items):
        if i not in referenced_wo:
            issues.append(f"UNREFERENCED_SEED watch_out[{i}]: '{w.get('text','')[:80]}'")
    for i, c in enumerate(contexts):
        if i not in referenced_ctx:
            issues.append(f"UNREFERENCED_SEED context[{i}]: '{c.get('text','')[:80]}'")
    for i, f in enumerate(facts):
        if i not in referenced_fct:
            issues.append(f"UNREFERENCED_SEED important_fact[{i}]: '{f.get('text','')[:80]}'")

    for obs in observations:
        if obs.get("aspect") not in referenced_obs:
            issues.append(f"UNPROVEN_OBS '{obs.get('aspect')}': '{obs.get('summary','')[:80]}'")
    for er in emotional_reg:
        if er.get("emotion") not in referenced_er:
            issues.append(f"UNPROVEN_ER '{er.get('emotion')}'")
    for cb in cui_bono:
        if cb.get("beneficiary") not in referenced_cb:
            issues.append(f"UNPROVEN_CB '{cb.get('beneficiary')}'")

    for pt in synthesis_pts:
        for ref in pt.get("references", []):
            if ref and ref not in all_ids:
                issues.append(f"BROKEN_SYNTHESIS_REF '{ref}'")

    return issues


def _repair_connections(
    assembled: ArticleFullAnalysis,
    issues: list[str],
    article: str,
    fond_data: dict,
    forme_data: dict,
    step5_data: dict,
    no_api: bool,
) -> ArticleFullAnalysis:
    issue_text = "\n".join(f"  • {issue}" for issue in issues)

    # Build valid node IDs to show the model what exists
    all_ids = []
    for i, obs in enumerate(assembled.analysis_fond.observations):
        all_ids.append(f"  obs_{i} → '{obs.aspect}'")
    for i, er in enumerate(assembled.analysis_forme.emotional_register):
        all_ids.append(f"  er_{i} → '{er.emotion}'")
    for i, cb in enumerate(assembled.analysis_forme.cui_bono):
        all_ids.append(f"  cb_{i} → '{cb.beneficiary}'")
    for i, c in enumerate(assembled.facts_vs_opinions.claims_and_sources):
        all_ids.append(f"  claim_{i} → '{c.quote[:40]}…'")
    for i, b in enumerate(assembled.biases_and_focus.biases_and_rhetoric):
        all_ids.append(f"  bias_{i} → '{b.label}'")

    repair_data = _call(
        f"""{article}

---

FOND (étape 3) :
{_j(fond_data)}

FORME (étape 4) :
{_j(forme_data)}

ANNOTATIONS (étape 5) :
{_j(step5_data)}

IDS VALIDES :
{chr(10).join(all_ids)}

---

RÉPARATION DES CONNEXIONS

L'audit a détecté {len(issues)} lacune(s) :

{issue_text}

Produis uniquement les éléments manquants pour fermer ces lacunes — ne reproduis pas l'existant :

- UNREFERENCED_SEED watch_out[N] : ajoute dans `additional_observations` une observation dont seeds.source="watch_out" et seeds.index=N, ancrée dans l'article.
- UNREFERENCED_SEED context[N] / important_fact[N] : idem avec source="context"/"important_fact".
- UNPROVEN_OBS 'X' : ajoute dans `additional_claims` ou `additional_biases` un item avec proves.type="observation" et proves.label="X", citation verbatim depuis l'article.
- UNPROVEN_ER 'X' : ajoute un item avec proves.type="emotional_register" et proves.label="X".
- UNPROVEN_CB 'X' : ajoute un item avec proves.type="cui_bono" et proves.label="X".
- BROKEN_SYNTHESIS_REF 'X' : dans `fixed_synthesis_points`, remplace les références invalides par des IDs valides uniquement (liste ci-dessus). Reproduis tous les synthesis points, en corrigeant uniquement les références invalides.""",
        RepairPatch.model_json_schema(),
        no_api=no_api,
    )

    patch = RepairPatch.model_validate(repair_data)

    fond = assembled.analysis_fond
    fvo  = assembled.facts_vs_opinions
    bf   = assembled.biases_and_focus
    synth = assembled.synthesis

    if patch.additional_observations:
        fond = fond.model_copy(update={"observations": list(fond.observations) + patch.additional_observations})
    if patch.additional_claims:
        fvo = fvo.model_copy(update={"claims_and_sources": list(fvo.claims_and_sources) + patch.additional_claims})
    if patch.additional_biases:
        bf = bf.model_copy(update={"biases_and_rhetoric": list(bf.biases_and_rhetoric) + patch.additional_biases})
    if patch.fixed_synthesis_points:
        synth = synth.model_copy(update={"points": patch.fixed_synthesis_points})

    # Recompute proven_by with updated claims/biases
    obs_index = {obs.aspect: i for i, obs in enumerate(fond.observations)}
    obs_proven_by: dict[int, list[ProvenByRef]] = {i: [] for i in range(len(fond.observations))}
    for ci, claim in enumerate(fvo.claims_and_sources):
        if claim.proves.type == "observation" and claim.proves.label in obs_index:
            obs_proven_by[obs_index[claim.proves.label]].append(ProvenByRef(type="claim", index=ci))
    for bi, bias in enumerate(bf.biases_and_rhetoric):
        if bias.proves.type == "observation" and bias.proves.label in obs_index:
            obs_proven_by[obs_index[bias.proves.label]].append(ProvenByRef(type="bias", index=bi))
    if bf.focus.proves.type == "observation" and bf.focus.proves.label in obs_index:
        obs_proven_by[obs_index[bf.focus.proves.label]].append(ProvenByRef(type="focus", index=0))
    fond = fond.model_copy(update={
        "observations": [
            obs.model_copy(update={"proven_by": obs_proven_by[i]})
            for i, obs in enumerate(fond.observations)
        ]
    })

    patched = assembled.model_copy(update={
        "analysis_fond": fond,
        "facts_vs_opinions": fvo,
        "biases_and_focus": bf,
        "synthesis": synth,
    })
    return _assign_ids(patched)


def _extract_title_chapo(body: str) -> tuple[str | None, str | None]:
    lines = body.split('\n')
    title = None
    chapo = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('http') and '://' in s:
            for j in range(i + 1, min(i + 6, len(lines))):
                candidate = lines[j].strip()
                if candidate and not candidate.startswith('http') and len(candidate) > 10:
                    title = candidate
                    for k in range(j + 1, min(j + 12, len(lines))):
                        para = lines[k].strip()
                        if len(para) > 80:
                            for suffix in ['Publié le', 'Read in English', 'Lire plus tard', 'Temps de']:
                                if suffix in para:
                                    para = para.split(suffix)[0].strip()
                            if len(para) > 50:
                                chapo = para
                            break
                    break
            break
    return title, chapo


def _j(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _article_header(input: FullAnalysisInput) -> str:
    parts = []
    if input.title:
        parts.append(f"Titre : {input.title}")
    if input.source:
        parts.append(f"Source : {input.source}")
    if input.published_at:
        parts.append(f"Date : {input.published_at}")
    if input.url:
        parts.append(f"URL : {input.url}")
    parts.append(f"\nContenu de l'article :\n{input.body}")
    return "\n".join(parts)


# ── ID assignment ────────────────────────────────────────────────────────────

def _assign_ids(output: ArticleFullAnalysis) -> ArticleFullAnalysis:
    """Assign stable string IDs to all cross-referenceable nodes at assembly time."""

    def _ids(items: list, prefix: str) -> list:
        return [item.model_copy(update={"id": f"{prefix}_{i}"}) for i, item in enumerate(items)]

    ctx = output.context
    new_ctx = ctx.model_copy(update={
        "contexts": _ids(ctx.contexts, "ctx"),
        "important_facts": _ids(ctx.important_facts, "fact"),
    })

    new_wo = output.watch_out.model_copy(update={"items": _ids(output.watch_out.items, "wo")})

    fond = output.analysis_fond
    new_fond = fond.model_copy(update={
        "premisses": _ids(fond.premisses, "pr"),
        "implicit_assumptions": _ids(fond.implicit_assumptions, "ia"),
        "blind_spots": _ids(fond.blind_spots, "bs"),
        "logical_reasoning": _ids(fond.logical_reasoning, "lr"),
        "observations": _ids(fond.observations, "obs"),
    })

    forme = output.analysis_forme
    new_forme = forme.model_copy(update={
        "emotional_register": _ids(forme.emotional_register, "er"),
        "cui_bono": _ids(forme.cui_bono, "cb"),
    })

    new_fvo = output.facts_vs_opinions.model_copy(update={
        "claims_and_sources": _ids(output.facts_vs_opinions.claims_and_sources, "claim"),
    })

    new_bf = output.biases_and_focus.model_copy(update={
        "biases_and_rhetoric": _ids(output.biases_and_focus.biases_and_rhetoric, "bias"),
    })

    new_cta = output.cta.model_copy(update={
        "post_reading_questions": _ids(output.cta.post_reading_questions, "q"),
    })

    return output.model_copy(update={
        "context": new_ctx,
        "watch_out": new_wo,
        "analysis_fond": new_fond,
        "analysis_forme": new_forme,
        "facts_vs_opinions": new_fvo,
        "biases_and_focus": new_bf,
        "cta": new_cta,
    })


# ── Node index for synthesis references ──────────────────────────────────────

def _build_node_index(fond: AnalysisFond, forme: AnalyseForme, step5_data: dict) -> str:
    """Build a human-readable index of available node IDs for the LLM to reference."""
    lines = ["NŒUDS DISPONIBLES POUR LES RÉFÉRENCES DE SYNTHÈSE :"]
    for i, obs in enumerate(fond.observations):
        lines.append(f"  obs_{i} → observation « {obs.aspect} »")
    for i, er in enumerate(forme.emotional_register):
        lines.append(f"  er_{i} → registre émotionnel « {er.emotion} »")
    for i, cb in enumerate(forme.cui_bono):
        lines.append(f"  cb_{i} → cui bono « {cb.beneficiary} »")
    for i, claim in enumerate(step5_data["facts_vs_opinions"]["claims_and_sources"]):
        q = claim["quote"][:35].replace("\n", " ")
        lines.append(f"  claim_{i} → affirmation « {q}… »")
    for i, bias in enumerate(step5_data["biases_and_focus"]["biases_and_rhetoric"]):
        lines.append(f"  bias_{i} → biais « {bias['label']} »")
    focus_quote = step5_data["biases_and_focus"]["focus"]["quote"][:35].replace("\n", " ")
    lines.append(f"  focus → focus éditorial « {focus_quote}… »")
    return "\n".join(lines)


# ── Pipeline ─────────────────────────────────────────────────────────────────

async def analyze_for_full_analysis(input: FullAnalysisInput, no_api: bool = False) -> ArticleFullAnalysis:
    article = _article_header(input)
    article_title, article_chapo = _extract_title_chapo(input.body)

    # Step 1 — Extraction
    print("[1/6] Extraction…", file=sys.stderr, flush=True)
    ext_data = _call(
        f"""{article}

---

ÉTAPE 1/6 — EXTRACTION BRUTE

Lis l'article et extrais sans interpréter :
- article_type : type d'article
- key_claims : affirmations centrales avec citation verbatim et source éventuelle
- key_quotes : citations verbatim les plus importantes ou révélatrices
- key_actors : acteurs mentionnés et leur rôle
- authority_anchors : entités (personnes, organisations, institutions) citées pour conférer de la crédibilité à une affirmation spécifique — pour chacune : entity (nom) + used_for (quelle affirmation elle est invoquée à légitimer)
- notable_omissions : éléments attendus absents
- rhetorical_patterns : patterns dans la structure, le vocabulaire, la mise en scène

Ne conclus pas. Capture uniquement ce que le texte contient et ce qu'il ne contient pas.""",
        ExtractionResult.model_json_schema(),
        no_api=no_api,
    )
    extraction = ExtractionResult.model_validate(ext_data)

    # Step 2 — Avant de lire (slides 3–5)
    title_line = article_title or "(non extrait)"
    chapo_line = article_chapo or "(non extrait)"
    print("[2/6] Avant de lire…", file=sys.stderr, flush=True)
    step2_data = _call_with_retry(
        f"""{article}

---

EXTRACTION (étape 1) :
{_j(ext_data)}

TITRE DE L'ARTICLE : {title_line}
CHAPEAU : {chapo_line}

---

ÉTAPE 2/6 — AVANT DE LIRE (slides 3, 4, 5)

Produis cadrage, context et watch_out selon le prompt système.
- cadrage : analyse du titre et du chapeau de l'article (title_bullets + chapo_bullets)
- context : contexts, who_is_speaking, important_facts, key_terms (1–2 items chacun), next_slide_hook
- watch_out : 2–8 items (text + refers_to: analysis_fond/analysis_forme/facts_vs_opinions/biases_and_focus), triés analysis_fond→analysis_forme→facts_vs_opinions→biases_and_focus, next_slide_hook""",
        Step2Output.model_json_schema(),
        validator=_validate_avant_de_lire,
        no_api=no_api,
    )
    step2 = Step2Output.model_validate(step2_data)

    # Step 3 — Analyse globale — Le fond (slide 6)
    print("[3/6] Analyse — Le fond…", file=sys.stderr, flush=True)
    fond_data = _call_with_retry(
        f"""{article}

---

EXTRACTION (étape 1) :
{_j(ext_data)}

AVANT DE LIRE (étape 2) :
{_j(step2_data)}

---

ÉTAPE 3/6 — ANALYSE GLOBALE — LE FOND (slide 6)

Produis analysis_fond :
- main_claim (1 phrase, ≤ 15 mots)
- premisses (1–4) : prémisses explicites ou implicites mais évidentes que l'auteur accepte — objet {{statement, quality}}
- implicit_assumptions (1–4) : hypothèses implicites et discutables que l'argument suppose vraies sans le dire — objet {{statement (la supposition en 1 phrase), impact (ce qui s'effondre si elle est fausse)}}
- blind_spots (1–4) : angles absents OU minimisés — objet {{topic (ce qui manque), significance (pourquoi ça change la conclusion)}}
- emphasis (1–3) : ce que l'auteur met en avant de façon disproportionnée — ce sur quoi le texte revient, ce qui occupe le plus d'espace
- logical_reasoning (1–4) : étapes inférentielles qui conduisent des prémisses à la conclusion
- observations (1–5) : aspect (1 mot), summary (1–2 phrases), seeds (objet {{source, index, excerpt}} — source ∈ "watch_out"/"context"/"important_fact", index = position 0-based dans la liste, excerpt = extrait court)
- steel_man (1–3) : contre-arguments les plus solides — counterargument, seeds (objet {{source, index, excerpt}} — source ∈ "premisse"/"implicit_assumption"/"blind_spot"/"logical_reasoning"), alternative_conclusion

Contrainte : chaque observation doit être ancrée dans un context, important_fact ou watch_out de l'étape 2.
Chaque context, important_fact et watch_out doit être adressé par au moins une observation.""",
        AnalysisFond.model_json_schema(),
        validator=_validate_fond,
        no_api=no_api,
    )
    fond = AnalysisFond.model_validate(fond_data)

    # Step 4 — Analyse globale — La forme (slide 7)
    print("[4/6] Analyse — La forme…", file=sys.stderr, flush=True)
    forme_data = _call_with_retry(
        f"""{article}

---

EXTRACTION (étape 1) :
{_j(ext_data)}

AVANT DE LIRE (étape 2) :
{_j(step2_data)}

ANALYSE — LE FOND (étape 3) :
{_j(fond_data)}

---

ÉTAPE 4/6 — ANALYSE GLOBALE — LA FORME (slide 7)

Produis analysis_forme : emotional_register (1–2 items), cui_bono (1–2 items), next_slide_hook.
Ces items doivent être ancrés dans les observations et seeds de l'étape 3.
Pour seeds de chaque item : objet {{source, index, excerpt}} — source ∈ "watch_out"/"context"/"important_fact", index = position 0-based, excerpt = extrait court.
Ils devront être prouvés dans le texte à l'étape suivante — anticipe.""",
        AnalyseForme.model_json_schema(),
        validator=_validate_forme,
        no_api=no_api,
    )
    forme = AnalyseForme.model_validate(forme_data)

    # Step 5 — Annotations (slides 8–9)
    print("[5/6] Annotations…", file=sys.stderr, flush=True)
    step5_data = _call_with_retry(
        f"""{article}

---

ANALYSE — LE FOND (étape 3) :
{_j(fond_data)}

ANALYSE — LA FORME (étape 4) :
{_j(forme_data)}

---

ÉTAPE 5/6 — ANNOTATIONS (slides 8 et 9)

Produis facts_vs_opinions (exactement 4 items) et biases_and_focus (exactement 3 biais + 1 focus).
Contrainte proves : chaque proves est un objet {{type, label}}. type est "observation", "emotional_register", ou "cui_bono". label doit correspondre exactement à un aspect/emotion/beneficiary de l'analyse globale. Pour focus, type doit être "observation".
Citations verbatim : mot pour mot depuis l'article — jamais paraphrasées.
Scores confidence : applique la méthodologie du prompt système.
next_slide_hook pour biases_and_focus.""",
        Step5Output.model_json_schema(),
        validator=lambda d: _validate_annotations(d, fond_data, forme_data),
        no_api=no_api,
    )
    step5 = Step5Output.model_validate(step5_data)

    # Step 6 — Finale (slides 1–2, 10–11)
    print("[6/6] Finale…", file=sys.stderr, flush=True)
    node_index = _build_node_index(fond, forme, step5_data)
    step6_data = _call_with_retry(
        f"""{article}

---

AVANT DE LIRE (étape 2) :
{_j(step2_data)}

ANALYSE — LE FOND (étape 3) :
{_j(fond_data)}

ANALYSE — LA FORME (étape 4) :
{_j(forme_data)}

ANNOTATIONS (étape 5) :
{_j(step5_data)}

{node_index}

---

ÉTAPE 6/6 — FINALE (slides 1, 2, 10, 11, 12)

L'analyse complète est disponible ci-dessus. Produis :
- hook : topic, sub_topic, headline (≤12 mots), context_line (≤20 mots)
- interest : why_read (1 phrase), pull_quote (optionnel), next_slide_hook
- synthesis : 1 à 5 points courts issus de l'analyse, triés du plus important au moins important — chaque point s'arrête juste avant la conclusion. Pour chaque point, indique dans `references` la liste des IDs de nœuds (issus de la liste ci-dessus) qui le supportent — ex. ["obs_0", "claim_1", "bias_2"]. open_question (1 phrase rétrospective ou de fond ancrée dans les biais identifiés en slide 7 — "Aviez-vous repéré…" ou question que l'analyse soulève sans trancher). engagement_question (1 question ouverte invitant à commenter, ancrée dans la tension principale de la synthèse).
- go_further : 1 à 6 ressources (articles, livres, documentaires, podcasts…) pour aller plus loin. Pour chaque item : title, source, media_type, category (deep_dive ou question_answer), url (si disponible), duration_minutes, why_explore (1 phrase), cta_question_index (si question_answer : index entier 0-based de la question dans cta.post_reading_questions à laquelle cette ressource répond — null sinon)
- cta : engagement_sentence (1 phrase invitant à commenter), post_reading_questions (1 à 4, dont au moins 1 blind_spot)""",
        Step6Output.model_json_schema(),
        validator=_validate_finale,
        no_api=no_api,
    )
    step6 = Step6Output.model_validate(step6_data)

    # Compute proven_by back-references on each observation
    obs_index = {obs.aspect: i for i, obs in enumerate(fond.observations)}
    obs_proven_by: dict[int, list[ProvenByRef]] = {i: [] for i in range(len(fond.observations))}
    for claim_idx, claim in enumerate(step5.facts_vs_opinions.claims_and_sources):
        if claim.proves.type == "observation" and claim.proves.label in obs_index:
            obs_proven_by[obs_index[claim.proves.label]].append(ProvenByRef(type="claim", index=claim_idx))
    for bias_idx, bias in enumerate(step5.biases_and_focus.biases_and_rhetoric):
        if bias.proves.type == "observation" and bias.proves.label in obs_index:
            obs_proven_by[obs_index[bias.proves.label]].append(ProvenByRef(type="bias", index=bias_idx))
    if step5.biases_and_focus.focus.proves.type == "observation":
        focus_label = step5.biases_and_focus.focus.proves.label
        if focus_label in obs_index:
            obs_proven_by[obs_index[focus_label]].append(ProvenByRef(type="focus", index=0))
    updated_obs = [
        obs.model_copy(update={"proven_by": obs_proven_by[i]})
        for i, obs in enumerate(fond.observations)
    ]
    fond = fond.model_copy(update={"observations": updated_obs})

    assembled = ArticleFullAnalysis(
        article_metadata=ArticleMetadata(
            url=input.url,
            title=input.title or article_title,
            source=input.source,
            published_at=input.published_at,
            type=extraction.article_type,
            reading_time_minutes=max(1, len(input.body.split()) // 200),
            chapo=article_chapo,
        ),
        extraction=ArticleExtraction(
            authority_anchors=extraction.authority_anchors,
            key_quotes=extraction.key_quotes,
            notable_omissions=extraction.notable_omissions,
            rhetorical_patterns=extraction.rhetorical_patterns,
        ),
        hook=step6.hook,
        interest=step6.interest,
        cadrage=step2.cadrage,
        context=step2.context,
        watch_out=step2.watch_out,
        analysis_fond=fond,
        analysis_forme=forme,
        facts_vs_opinions=step5.facts_vs_opinions,
        biases_and_focus=step5.biases_and_focus,
        synthesis=step6.synthesis,
        go_further=step6.go_further,
        cta=step6.cta,
    )
    assembled = _assign_ids(assembled)

    # Connection audit + repair
    conn_issues = _audit_connections(json.loads(assembled.model_dump_json()))
    if conn_issues:
        print(
            f"  ↻ {len(conn_issues)} connection gap(s) detected, repairing…",
            file=sys.stderr, flush=True,
        )
        assembled = _repair_connections(assembled, conn_issues, article, fond_data, forme_data, step5_data, no_api)
        remaining = _audit_connections(json.loads(assembled.model_dump_json()))
        for issue in remaining:
            print(f"  ⚠  {issue}", file=sys.stderr)
    else:
        print("  ✓ Connection audit: all nodes connected.", file=sys.stderr, flush=True)

    return assembled
