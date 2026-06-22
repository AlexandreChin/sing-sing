"""Multi-step full article analysis pipeline.

Steps:
  1. Extraction          — raw facts, claims, actors, omissions (no interpretation)
  2. Avant de lire       — cadrage + context + watch_out
  3. Analyse fond        — main_claim, assumptions, blind_spots, observations
  4. Analyse forme       — emotional_register, cui_bono
  5. Annotations         — facts_vs_opinions + biases_and_focus
  6. Finale              — synthesis
  7. Masterclass         — journalistic quality evaluation across 6 dimensions
  8. Consistency audit   — score grounding, verdict non-redundancy, quality enum coherence
"""
import json
import sys
import tempfile
from pathlib import Path

from models.full_analysis import (
    Analysis,
    Annotations,
    AnalysisFond,
    AnalyseForme,
    ArticleExtraction,
    ArticleFullAnalysis,
    ArticleMetadata,
    FullAnalysisInput,
    ProvenByRef,
)
from models.full_analysis_steps import ExtractionResult, Step2Output, Step5Output, Step6Output, Step7Output, Step8Output  # noqa: F401

from ._base import _article_header, _assign_ids, _audit_connections, _repair_connections
from .steps import step1_extraction, step2_avant_de_lire, step3_fond, step4_forme, step5_annotations, step6_finale, step7_masterclass, step8_consistency


def _load_or_run(steps_dir: Path, filename: str, run_fn):
    """Return cached JSON if the step file exists, otherwise call run_fn() and save."""
    path = steps_dir / filename
    if path.exists():
        print(f"  (loaded from {path.name})", file=sys.stderr, flush=True)
        return json.loads(path.read_text(encoding="utf-8"))
    return run_fn()


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


async def analyze_for_full_analysis(
    input: FullAnalysisInput,
    no_api: bool = False,
    steps_dir: Path | None = None,
) -> ArticleFullAnalysis:
    if steps_dir is None:
        steps_dir = Path(tempfile.mkdtemp(prefix="sing-sing-steps-"))
    steps_dir.mkdir(parents=True, exist_ok=True)

    article = _article_header(input)
    article_title, article_chapo = _extract_title_chapo(input.body)

    # Step 1 — Extraction
    print("[1/8] Extraction…", file=sys.stderr, flush=True)
    ext_data = _load_or_run(steps_dir, "step1_extraction.json",
        lambda: step1_extraction.run(article, steps_dir, no_api=no_api))
    extraction = ExtractionResult.model_validate(ext_data)

    # Step 2 — Avant de lire
    title_line = article_title or "(non extrait)"
    chapo_line = article_chapo or "(non extrait)"
    print("[2/8] Avant de lire…", file=sys.stderr, flush=True)
    step2_data = _load_or_run(steps_dir, "step2_avant_de_lire.json",
        lambda: step2_avant_de_lire.run(article, ext_data, title_line, chapo_line, steps_dir, no_api=no_api))
    step2 = Step2Output.model_validate(step2_data)

    # Step 3 — Le fond
    print("[3/8] Analyse — Le fond…", file=sys.stderr, flush=True)
    fond_data = _load_or_run(steps_dir, "step3_fond.json",
        lambda: step3_fond.run(article, ext_data, step2_data, steps_dir, no_api=no_api))
    fond = AnalysisFond.model_validate(fond_data)

    # Step 4 — La forme
    print("[4/8] Analyse — La forme…", file=sys.stderr, flush=True)
    forme_data = _load_or_run(steps_dir, "step4_forme.json",
        lambda: step4_forme.run(article, ext_data, step2_data, fond_data, steps_dir, no_api=no_api))
    forme = AnalyseForme.model_validate(forme_data)

    # Step 5 — Annotations
    print("[5/8] Annotations…", file=sys.stderr, flush=True)
    step5_data = _load_or_run(steps_dir, "step5_annotations.json",
        lambda: step5_annotations.run(article, fond_data, forme_data, steps_dir, no_api=no_api))
    step5 = Step5Output.model_validate(step5_data)

    # Step 6 — Finale
    print("[6/8] Finale…", file=sys.stderr, flush=True)
    step6_data = _load_or_run(steps_dir, "step6_finale.json",
        lambda: step6_finale.run(article, step2_data, fond_data, forme_data, step5_data, fond, forme, steps_dir, no_api=no_api))
    step6 = Step6Output.model_validate(step6_data)

    # Step 7 — Masterclass
    print("[7/8] Masterclass…", file=sys.stderr, flush=True)
    step7_data = _load_or_run(steps_dir, "step7_masterclass.json",
        lambda: step7_masterclass.run(article, fond_data, forme_data, step5_data, step6_data, steps_dir, no_api=no_api))
    step7 = Step7Output.model_validate(step7_data)

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
        cadrage=step2.cadrage,
        context=step2.context,
        watch_out=step2.watch_out,
        analysis=Analysis(fond=fond, forme=forme),
        annotations=Annotations(
            facts_vs_opinions=step5.facts_vs_opinions,
            biases_and_focus=step5.biases_and_focus,
        ),
        synthesis=step6.synthesis,
        masterclass=step7.masterclass,
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

    # Step 8 — Consistency audit
    print("[8/8] Consistency audit…", file=sys.stderr, flush=True)
    step8_data = _load_or_run(steps_dir, "step8_consistency.json",
        lambda: step8_consistency.run(json.loads(assembled.model_dump_json()), steps_dir, no_api=no_api))
    step8 = Step8Output.model_validate(step8_data)
    if step8.changes:
        for change in step8.changes:
            print(f"  ↻ {change}", file=sys.stderr, flush=True)
        assembled = assembled.model_copy(update={"masterclass": step8.masterclass})
    else:
        print("  ✓ Consistency audit: no corrections needed.", file=sys.stderr, flush=True)

    return assembled
