"""Multi-step carousel analysis pipeline.

Steps:
  1. Extraction   — raw facts, claims, actors, omissions (no interpretation)
  2. Avant de lire — cadrage + context + watch_out (slides 3–5)
  3. Analyse fond  — main_claim, assumptions, blind_spots, observations (slide 6)
  4. Analyse forme — emotional_register, cui_bono (slide 7)
  5. Annotations  — facts_vs_opinions + biases_and_focus (slides 8–9)
  6. Finale        — hook + interest + synthesis + cta (slides 1–2, 10–11)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import anthropic

from models.carousel import (
    AnalysisFond,
    AnalyseForme,
    ArticleMetadata,
    CarouselInput,
    CarouselOutput,
)
from models.carousel_steps import ExtractionResult, Step2Output, Step5Output, Step6Output

client = anthropic.Anthropic()

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "analyze_carousel.md").read_text(
    encoding="utf-8"
)

MAX_RETRIES = 2


# ── Validators ───────────────────────────────────────────────────────────────

def _validate_fond(data: dict) -> list[str]:
    fond = AnalysisFond.model_validate(data)
    errors = []
    if not fond.main_claim:
        errors.append("analysis_fond.main_claim est vide")
    if not fond.observations:
        errors.append("analysis_fond.observations est vide")
    if not fond.implicit_assumptions:
        errors.append("analysis_fond.implicit_assumptions est vide")
    if not fond.blind_spots:
        errors.append("analysis_fond.blind_spots est vide")
    return errors


def _validate_forme(data: dict) -> list[str]:
    forme = AnalyseForme.model_validate(data)
    errors = []
    if not forme.emotional_register:
        errors.append("analysis_forme.emotional_register est vide")
    if not forme.cui_bono:
        errors.append("analysis_forme.cui_bono est vide")
    return errors


def _confidence_label_expected(confidence: int | None) -> str:
    if confidence is None:
        return "unverifiable"
    if confidence <= 20: return "false"
    if confidence <= 40: return "opinion stated as fact"
    if confidence <= 60: return "disputed"
    if confidence <= 80: return "likely true"
    if confidence <= 90: return "true"
    return "consensual"


def _validate_annotations(data: dict, fond_data: dict, forme_data: dict) -> list[str]:
    step5 = Step5Output.model_validate(data)
    fond = AnalysisFond.model_validate(fond_data)
    forme = AnalyseForme.model_validate(forme_data)
    errors = []

    valid_proves = (
        {obs.aspect for obs in fond.observations}
        | {e.emotion for e in forme.emotional_register}
        | {c.beneficiary for c in forme.cui_bono}
    )

    fvo = step5.facts_vs_opinions
    for i, claim in enumerate(fvo.claims_and_sources):
        if claim.proves not in valid_proves:
            errors.append(
                f"claims_and_sources[{i}].proves='{claim.proves}' invalide. "
                f"Valeurs valides: {sorted(valid_proves)}"
            )
        expected = _confidence_label_expected(claim.confidence)
        if claim.confidence_label != expected:
            errors.append(
                f"claims_and_sources[{i}].confidence_label='{claim.confidence_label}' incorrect "
                f"pour score {claim.confidence}. Attendu: '{expected}'"
            )

    bf = step5.biases_and_focus
    for i, bias in enumerate(bf.biases_and_rhetoric):
        if bias.proves not in valid_proves:
            errors.append(
                f"biases_and_rhetoric[{i}].proves='{bias.proves}' invalide. "
                f"Valeurs valides: {sorted(valid_proves)}"
            )

    obs_aspects = {obs.aspect for obs in fond.observations}
    if bf.focus.proves not in obs_aspects:
        errors.append(
            f"focus.proves='{bf.focus.proves}' invalide. "
            f"Doit correspondre à un aspect de observations: {sorted(obs_aspects)}"
        )
    return errors


def _validate_finale(data: dict) -> list[str]:
    step6 = Step6Output.model_validate(data)
    errors = []
    if len(step6.synthesis.points) != 3:
        errors.append(f"synthesis.points doit contenir exactement 3 items, {len(step6.synthesis.points)} produit(s)")
    if not (3 <= len(step6.go_further.items) <= 4):
        errors.append(f"go_further.items doit contenir 4 à 6 items, {len(step6.go_further.items)} produit(s)")
    if len(step6.cta.post_reading_questions) != 2:
        errors.append(f"cta.post_reading_questions doit contenir exactement 2 items")
    blind_spots = [q for q in step6.cta.post_reading_questions if q.type == "blind_spot"]
    if not blind_spots:
        errors.append("cta.post_reading_questions: au moins une question doit être de type 'blind_spot'")
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
    step2_data = _call(
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
- watch_out : 4–5 items (text + refers_to: fond/forme/faits/biais), triés fond→forme→faits→biais, next_slide_hook""",
        Step2Output.model_json_schema(),
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

Produis analysis_fond : main_claim, implicit_assumptions (1–2), blind_spots (1–2), observations (2–3).
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

Produis facts_vs_opinions (2–4 items) et biases_and_focus (1–2 biais + 1 focus).
Contrainte : chaque proves doit correspondre exactement à un aspect/emotion/beneficiary de l'analyse globale.
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

---

ÉTAPE 6/6 — FINALE (slides 1, 2, 10, 11, 12)

L'analyse complète est disponible ci-dessus. Produis :
- hook : topic, sub_topic, headline (≤12 mots), context_line (≤20 mots)
- interest : why_read (1 phrase), pull_quote (optionnel), next_slide_hook
- synthesis : exactement 3 points courts issus de l'analyse — chaque point s'arrête juste avant la conclusion
- go_further : 3 à 4 ressources (articles, livres, documentaires, podcasts…) pour aller plus loin. Pour chaque item : title, source, media_type, category (deep_dive ou question_answer), url (si disponible), duration_minutes, why_explore (1 phrase), answers_question (si question_answer : copier verbatim la question de cta.post_reading_questions à laquelle cette ressource répond)
- cta : engagement_sentence (1 phrase invitant à commenter), post_reading_questions (exactement 2, dont au moins 1 blind_spot)""",
        Step6Output.model_json_schema(),
        validator=_validate_finale,
        no_api=no_api,
    )
    step6 = Step6Output.model_validate(step6_data)

    return CarouselOutput(
        article_metadata=ArticleMetadata(
            url=input.url,
            title=input.title or article_title,
            source=input.source,
            published_at=input.published_at,
            article_type=extraction.article_type,
            reading_time_minutes=max(1, len(input.body.split()) // 200),
            article_title=article_title,
            article_chapo=article_chapo,
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
