"""Multi-step carousel analysis pipeline with per-step consistency validation.

Steps:
  1. Extraction  — raw facts, claims, actors, omissions (no interpretation)
  2. Before You Read — seeds the consistency chain
  3. Global Analysis — observations, emotional register, cui bono (anchored to step 2)
  4. Local Annotations — quote-level proof of every global item (anchored to step 3)
  5. Hook + Synthesis + Finale — written last, when the full analysis exists

Each step is validated after generation. If inconsistencies are found, the step is
retried with a correction prompt listing the specific gaps (max MAX_RETRIES attempts).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import anthropic

from models.carousel import (
    ArticleMetadata,
    BeforeYouRead,
    CarouselInput,
    CarouselOutput,
    GlobalAnalysis,
    LocalAnnotationsSlide,
)
from models.carousel_steps import ExtractionResult, HookSynthesisFinale

client = anthropic.Anthropic()

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "analyze_carousel.md").read_text(
    encoding="utf-8"
)

MAX_RETRIES = 2


# ── Validators ───────────────────────────────────────────────────────────────

def _validate_ga(ga_data: dict, byr_data: dict) -> list[str]:
    """Step 3: all three GA sections must be non-empty."""
    ga = GlobalAnalysis.model_validate(ga_data)
    errors = []
    if not ga.observations:
        errors.append("global_analysis.observations est vide")
    if not ga.emotional_register:
        errors.append("global_analysis.emotional_register est vide")
    if not ga.cui_bono:
        errors.append("global_analysis.cui_bono est vide")
    return errors


def _confidence_label_expected(confidence: int | None) -> str:
    if confidence is None:
        return "unverifiable"
    if confidence <= 20:
        return "false"
    if confidence <= 40:
        return "opinion stated as fact"
    if confidence <= 60:
        return "disputed"
    if confidence <= 80:
        return "likely true"
    if confidence <= 90:
        return "true"
    return "consensual"


def _validate_la(la_data: dict, ga_data: dict) -> list[str]:
    """Step 4: every proves field must match a real GA item; confidence labels must be correct."""
    la = LocalAnnotationsSlide.model_validate(la_data)
    ga = GlobalAnalysis.model_validate(ga_data)
    errors = []

    valid_proves = (
        {obs.aspect for obs in ga.observations}
        | {e.emotion for e in ga.emotional_register}
        | {c.beneficiary for c in ga.cui_bono}
    )

    for i, claim in enumerate(la.claims_and_sources):
        if claim.proves not in valid_proves:
            errors.append(
                f"claims_and_sources[{i}].proves = '{claim.proves}' ne correspond à aucun item "
                f"de global_analysis. Valeurs valides : {sorted(valid_proves)}"
            )
        expected = _confidence_label_expected(claim.confidence)
        if claim.confidence_label != expected:
            errors.append(
                f"claims_and_sources[{i}].confidence_label = '{claim.confidence_label}' incorrect "
                f"pour le score {claim.confidence}. Attendu : '{expected}'"
            )

    for i, bias in enumerate(la.biases_and_rhetoric):
        if bias.proves not in valid_proves:
            errors.append(
                f"biases_and_rhetoric[{i}].proves = '{bias.proves}' ne correspond à aucun item "
                f"de global_analysis. Valeurs valides : {sorted(valid_proves)}"
            )

    if la.quote_deep_dive.proves not in valid_proves:
        errors.append(
            f"quote_deep_dive.proves = '{la.quote_deep_dive.proves}' ne correspond à aucune "
            f"observation de global_analysis. Valeurs valides : {sorted(valid_proves)}"
        )

    return errors


def _validate_finale(finale_data: dict) -> list[str]:
    """Step 5: synthesis has 3 points; blind_spot question present; each blind_spot answered."""
    finale = HookSynthesisFinale.model_validate(finale_data)
    errors = []

    if len(finale.synthesis.points) != 3:
        errors.append(
            f"synthesis.points doit contenir exactement 3 items, {len(finale.synthesis.points)} produit(s)"
        )

    blind_spots = [q for q in finale.post_reading_questions if q.type == "blind_spot"]
    if not blind_spots:
        errors.append(
            "post_reading_questions : au moins une question doit être de type 'blind_spot'"
        )

    answered = {item.answers_question for item in finale.go_further if item.answers_question}
    for q in blind_spots:
        if q.question not in answered:
            errors.append(
                f"La question blind_spot '{q.question[:70]}…' n'a pas de ressource "
                f"go_further avec answers_question correspondant"
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


def _j(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _article_header(input: CarouselInput) -> str:
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


# ── Pipeline ─────────────────────────────────────────────────────────────────

async def analyze_for_carousel(input: CarouselInput, no_api: bool = False) -> CarouselOutput:
    article = _article_header(input)

    # ── Step 1 — Extraction (no cross-step validation) ───────────────────────
    print("[1/5] Extraction…", file=sys.stderr, flush=True)
    ext_data = _call(
        f"""{article}

---

ÉTAPE 1 SUR 5 — EXTRACTION BRUTE

Lis l'article et extrais sans interpréter :
- article_type : type d'article
- key_claims : affirmations centrales avec citation verbatim et source éventuelle
- key_quotes : citations verbatim les plus importantes ou révélatrices
- key_actors : acteurs mentionnés et leur rôle dans l'article
- notable_omissions : éléments attendus dans ce type d'article qui sont absents
- rhetorical_patterns : patterns dans la structure, le vocabulaire, la mise en scène

Ne conclus pas encore. Capture uniquement ce que le texte contient et ce qu'il ne contient pas.""",
        ExtractionResult.model_json_schema(),
        no_api=no_api,
    )
    extraction = ExtractionResult.model_validate(ext_data)

    # ── Step 2 — Before You Read (no cross-step validation) ──────────────────
    print("[2/5] Before You Read…", file=sys.stderr, flush=True)
    byr_data = _call(
        f"""{article}

---

EXTRACTION (étape 1) :
{_j(ext_data)}

---

ÉTAPE 2 SUR 5 — AVANT DE LIRE

Produis uniquement `before_you_read` selon le prompt système.
Appuie-toi sur l'extraction pour identifier les faits clés, acteurs, et points d'attention.
`watch_out` : consignes de lecture précises pointant vers des éléments identifiés en extraction — pas des consignes génériques.""",
        BeforeYouRead.model_json_schema(),
        no_api=no_api,
    )
    byr = BeforeYouRead.model_validate(byr_data)

    # ── Step 3 — Global Analysis (validated: all sections non-empty) ──────────
    print("[3/5] Global Analysis…", file=sys.stderr, flush=True)
    ga_data = _call_with_retry(
        f"""{article}

---

EXTRACTION (étape 1) :
{_j(ext_data)}

AVANT DE LIRE (étape 2) :
{_j(byr_data)}

---

ÉTAPE 3 SUR 5 — ANALYSE GLOBALE

Produis uniquement `global_analysis` (observations, emotional_register, cui_bono).
Contrainte : chaque item doit être ancré dans un `context`, `important_fact`, ou `watch_out` de `before_you_read`.
Chaque `context`, `important_fact` et `watch_out` doit être adressé par au moins une observation.
Les items de `emotional_register` et `cui_bono` devront être prouvés en étape 4 — anticipe.""",
        GlobalAnalysis.model_json_schema(),
        validator=lambda d: _validate_ga(d, byr_data),
        no_api=no_api,
    )
    ga = GlobalAnalysis.model_validate(ga_data)

    # ── Step 4 — Local Annotations (validated: proves refs + confidence labels) ─
    print("[4/5] Local Annotations…", file=sys.stderr, flush=True)
    la_data = _call_with_retry(
        f"""{article}

---

EXTRACTION (étape 1) :
{_j(ext_data)}

AVANT DE LIRE (étape 2) :
{_j(byr_data)}

ANALYSE GLOBALE (étape 3) :
{_j(ga_data)}

---

ÉTAPE 4 SUR 5 — ANNOTATIONS LOCALES

Produis uniquement `local_annotations` (claims_and_sources, biases_and_rhetoric, quote_deep_dive).
Contrainte : chaque annotation doit prouver un item précis de `global_analysis`.
Le champ `proves` doit reprendre l'`aspect`, l'`emotion`, ou le `beneficiary` exact de `global_analysis`.
Citations verbatim : extraites mot pour mot de l'article — jamais paraphrasées.
Scores de confiance : applique la méthodologie du prompt système (tangibilité, témoignages, crédibilité, asymétrie, convergence).""",
        LocalAnnotationsSlide.model_json_schema(),
        validator=lambda d: _validate_la(d, ga_data),
        no_api=no_api,
    )
    la = LocalAnnotationsSlide.model_validate(la_data)

    # ── Step 5 — Hook, Synthesis, Finale (validated: synthesis count, blind_spot coverage) ─
    print("[5/5] Hook, Synthesis, Go Further…", file=sys.stderr, flush=True)
    finale_data = _call_with_retry(
        f"""{article}

---

AVANT DE LIRE (étape 2) :
{_j(byr_data)}

ANALYSE GLOBALE (étape 3) :
{_j(ga_data)}

ANNOTATIONS LOCALES (étape 4) :
{_j(la_data)}

---

ÉTAPE 5 SUR 5 — ACCROCHE, SYNTHÈSE, QUESTIONS, POUR ALLER PLUS LOIN

L'analyse complète est disponible ci-dessus. Produis les quatre champs :
- `hook` : maintenant que l'analyse existe, écris l'accroche la plus précise et percutante — headline ≤ 12 mots, context_line ≤ 20 mots
- `synthesis` : exactement 3 points issus directement de l'analyse — chaque point s'arrête juste avant la conclusion
- `post_reading_questions` : 3 à 5 questions ancrées dans l'analyse, au moins une `blind_spot` pointant vers un angle absent du carrousel
- `go_further` : 4 à 6 ressources (tout format), dont au moins une `question_answer` pour chaque question `blind_spot`""",
        HookSynthesisFinale.model_json_schema(),
        validator=_validate_finale,
        no_api=no_api,
    )
    finale = HookSynthesisFinale.model_validate(finale_data)

    return CarouselOutput(
        article_metadata=ArticleMetadata(
            url=input.url,
            title=input.title,
            source=input.source,
            published_at=input.published_at,
            article_type=extraction.article_type,
        ),
        hook=finale.hook,
        before_you_read=byr,
        global_analysis=ga,
        local_annotations=la,
        synthesis=finale.synthesis,
        go_further=finale.go_further,
        post_reading_questions=finale.post_reading_questions,
    )
