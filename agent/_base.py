"""Shared infrastructure for all step agents."""
import json
import re
import subprocess
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from config import MODEL
from models.full_analysis import (
    AnalysisFond,
    AnalyseForme,
    ArticleFullAnalysis,
    BiasRhetoric,
    ClaimAndSource,
    DistillPoint,
    FullAnalysisInput,
    GlobalAnalysisItem,
    ProvenByRef,
)

client = anthropic.Anthropic()

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text(
    encoding="utf-8"
)

MAX_RETRIES = 2


# ── Core API calls ────────────────────────────────────────────────────────────

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
    # `claude -p` intermittently returns empty stdout; retry before giving up so a
    # single transient blank doesn't abort the whole pipeline.
    last_err = ""
    for _ in range(MAX_RETRIES + 1):
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            last_err = f"claude CLI failed:\n{result.stderr}"
            continue
        text = result.stdout.strip()
        if not text:
            last_err = "claude CLI returned empty output"
            continue
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            text = match.group(1).strip()
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            last_err = f"invalid JSON from claude CLI: {e}"
    raise RuntimeError(last_err or "claude CLI call failed")


def _call(user_message: str, schema: dict, no_api: bool = False, system: str | None = None) -> dict:
    if no_api:
        return _call_no_api(user_message, schema, system=system)
    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=system or _SYSTEM_PROMPT,
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
    label: str = "",
    system: str | None = None,
) -> dict:
    tag = f" [{label}]" if label else ""
    print(f"  → calling API{tag}…", file=sys.stderr, flush=True)
    data = _call(user_message, schema, no_api=no_api, system=system)
    print(f"  ✓ response received{tag}", file=sys.stderr, flush=True)

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
        data = _call(correction_msg, schema, no_api=no_api, system=system)

    errors = validator(data)
    for e in errors:
        print(f"  ⚠  {e}", file=sys.stderr)

    return data


# ── Helpers ───────────────────────────────────────────────────────────────────

def _j(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _article_header(input: FullAnalysisInput) -> str:
    parts = []
    if input.extra_instructions:
        parts.append(f"<extra_instructions>\n{input.extra_instructions.strip()}\n</extra_instructions>")
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


def save_step(data: dict, steps_dir: Path, filename: str) -> None:
    steps_dir.mkdir(parents=True, exist_ok=True)
    (steps_dir / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── ID assignment ─────────────────────────────────────────────────────────────

def _assign_ids(output: ArticleFullAnalysis) -> ArticleFullAnalysis:
    def _ids(items: list, prefix: str) -> list:
        return [item.model_copy(update={"id": f"{prefix}_{i}"}) for i, item in enumerate(items)]

    ctx = output.context
    new_ctx = ctx.model_copy(update={
        "contexts": _ids(ctx.contexts, "ctx"),
        "important_facts": _ids(ctx.important_facts, "fact"),
    })

    fond = output.analysis.fond
    new_fond = fond.model_copy(update={
        "premisses": _ids(fond.premisses, "pr"),
        "implicit_assumptions": _ids(fond.implicit_assumptions, "ia"),
        "blind_spots": _ids(fond.blind_spots, "bs"),
        "logical_reasoning": _ids(fond.logical_reasoning, "lr"),
        "observations": _ids(fond.observations, "obs"),
    })

    forme = output.analysis.forme
    new_forme = forme.model_copy(update={
        "emotional_register": _ids(forme.emotional_register, "er"),
        "cui_bono": _ids(forme.cui_bono, "cb"),
    })

    new_fvo = output.annotations.facts_vs_opinions.model_copy(update={
        "claims_and_sources": _ids(output.annotations.facts_vs_opinions.claims_and_sources, "claim"),
    })

    new_bf = output.annotations.biases_and_focus.model_copy(update={
        "biases_and_rhetoric": _ids(output.annotations.biases_and_focus.biases_and_rhetoric, "bias"),
    })

    return output.model_copy(update={
        "context": new_ctx,
        "analysis": output.analysis.model_copy(update={"fond": new_fond, "forme": new_forme}),
        "annotations": output.annotations.model_copy(update={
            "facts_vs_opinions": new_fvo,
            "biases_and_focus": new_bf,
        }),
    })


# ── Connection audit + repair ─────────────────────────────────────────────────

def _audit_connections(data: dict) -> list[str]:
    issues = []

    _analysis    = data.get("analysis", {})
    _annotations = data.get("annotations", {})
    contexts        = data.get("context", {}).get("contexts", [])
    facts           = data.get("context", {}).get("important_facts", [])
    observations    = _analysis.get("fond", {}).get("observations", [])
    emotional_reg   = _analysis.get("forme", {}).get("emotional_register", [])
    cui_bono        = _analysis.get("forme", {}).get("cui_bono", [])
    claims          = _annotations.get("facts_vs_opinions", {}).get("claims_and_sources", [])
    biases          = _annotations.get("biases_and_focus", {}).get("biases_and_rhetoric", [])
    focus           = _annotations.get("biases_and_focus", {}).get("focus") or {}
    distill_pts     = data.get("distill", {}).get("points", []) if data.get("distill") else []

    referenced_ctx = set()
    referenced_fct = set()

    def _walk_seeds(item: dict) -> None:
        s = item.get("seeds") or {}
        src, idx = s.get("source"), s.get("index")
        if src == "context" and idx is not None:        referenced_ctx.add(idx)
        elif src == "important_fact" and idx is not None: referenced_fct.add(idx)

    for obs in observations: _walk_seeds(obs)
    for er  in emotional_reg: _walk_seeds(er)
    for cb  in cui_bono:      _walk_seeds(cb)

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

    for pt in distill_pts:
        for ref in pt.get("references", []):
            if ref and ref not in all_ids:
                issues.append(f"BROKEN_DISTILL_REF '{ref}'")

    return issues


class RepairPatch(BaseModel):
    additional_observations: list[GlobalAnalysisItem] = Field(default_factory=list)
    additional_claims: list[ClaimAndSource] = Field(default_factory=list)
    additional_biases: list[BiasRhetoric] = Field(default_factory=list)
    fixed_distill_points: list[DistillPoint] = Field(default_factory=list)


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

    all_ids = []
    for i, obs in enumerate(assembled.analysis.fond.observations):
        all_ids.append(f"  obs_{i} → '{obs.aspect}'")
    for i, er in enumerate(assembled.analysis.forme.emotional_register):
        all_ids.append(f"  er_{i} → '{er.emotion}'")
    for i, cb in enumerate(assembled.analysis.forme.cui_bono):
        all_ids.append(f"  cb_{i} → '{cb.beneficiary}'")
    for i, c in enumerate(assembled.annotations.facts_vs_opinions.claims_and_sources):
        all_ids.append(f"  claim_{i} → '{c.quote[:40]}…'")
    for i, b in enumerate(assembled.annotations.biases_and_focus.biases_and_rhetoric):
        all_ids.append(f"  bias_{i} → '{b.label}'")

    if no_api:
        return assembled
    print("  → calling API [connection repair]…", file=sys.stderr, flush=True)
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
- BROKEN_DISTILL_REF 'X' : dans `fixed_distill_points`, remplace les références invalides par des IDs valides uniquement (liste ci-dessus). Reproduis tous les distill points, en corrigeant uniquement les références invalides.""",
        RepairPatch.model_json_schema(),
        no_api=no_api,
    )

    patch = RepairPatch.model_validate(repair_data)

    fond  = assembled.analysis.fond
    fvo   = assembled.annotations.facts_vs_opinions
    bf    = assembled.annotations.biases_and_focus
    dist  = assembled.distill

    if patch.additional_observations:
        fond = fond.model_copy(update={"observations": list(fond.observations) + patch.additional_observations})
    if patch.additional_claims:
        fvo = fvo.model_copy(update={"claims_and_sources": list(fvo.claims_and_sources) + patch.additional_claims})
    if patch.additional_biases:
        bf = bf.model_copy(update={"biases_and_rhetoric": list(bf.biases_and_rhetoric) + patch.additional_biases})
    if patch.fixed_distill_points and dist:
        dist = dist.model_copy(update={"points": patch.fixed_distill_points})

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
        "analysis": assembled.analysis.model_copy(update={"fond": fond}),
        "annotations": assembled.annotations.model_copy(update={
            "facts_vs_opinions": fvo,
            "biases_and_focus": bf,
        }),
        "distill": dist,
    })
    return _assign_ids(patched)


# ── Node index for step 6 synthesis references ────────────────────────────────

def _build_node_index(fond: AnalysisFond, forme: AnalyseForme, step5_data: dict) -> str:
    lines = ["NŒUDS DISPONIBLES POUR LES RÉFÉRENCES DE SYNTHÈSE :"]
    # Logic layer
    for i, pr in enumerate(fond.premisses):
        lines.append(f"  pr_{i} → prémisse « {pr.statement[:50].replace(chr(10), ' ')}… »")
    for i, ia in enumerate(fond.implicit_assumptions):
        lines.append(f"  ia_{i} → hypothèse implicite « {ia.statement[:50].replace(chr(10), ' ')}… »")
    for i, bs in enumerate(fond.blind_spots):
        lines.append(f"  bs_{i} → angle mort « {bs.topic[:50].replace(chr(10), ' ')}… »")
    for i, lr in enumerate(fond.logical_reasoning):
        lines.append(f"  lr_{i} → raisonnement « {lr.step[:50].replace(chr(10), ' ')}… »")
    for i, obs in enumerate(fond.observations):
        lines.append(f"  obs_{i} → observation « {obs.aspect} »")
    # Rhetoric layer
    for i, er in enumerate(forme.emotional_register):
        lines.append(f"  er_{i} → registre émotionnel « {er.emotion} »")
    for i, cb in enumerate(forme.cui_bono):
        lines.append(f"  cb_{i} → cui bono « {cb.beneficiary} »")
    # Probe layer
    for i, claim in enumerate(step5_data["facts_vs_opinions"]["claims_and_sources"]):
        q = claim["quote"][:50].replace("\n", " ")
        lines.append(f"  claim_{i} → affirmation « {q}… »")
    for i, bias in enumerate(step5_data["biases_and_focus"]["biases_and_rhetoric"]):
        lines.append(f"  bias_{i} → biais « {bias['label']} »")
    focus_quote = step5_data["biases_and_focus"]["focus"]["quote"][:50].replace("\n", " ")
    lines.append(f"  focus → focus éditorial « {focus_quote}… »")
    return "\n".join(lines)
