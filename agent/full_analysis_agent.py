"""Multi-step full article analysis pipeline.

Steps:
  1. Scan     — raw extraction + context (no interpretation)
  2. Logic    — main_claim, assumptions, blind_spots, observations
  3. Rhetoric — emotional_register, cui_bono, cadrage
  4. Probe    — facts_vs_opinions + biases_and_focus
  5. Ethics   — hard red line audit (violations list)
  6. Review   — journalistic quality evaluation across 6 dimensions
  7. Blend    — cross-layer pattern integration (up to 8 patterns)
  8. Distill  — select top 3–5 patterns + open_questions
  9. Guide    — reader companion: pre_reading, watch_out, after_reading
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
    CoreElements,
    FullAnalysisInput,
    ProvenByRef,
)
from models.full_analysis_steps import (
    ExtractionResult,
    ProbeOutput,
    EthicsOutput,
    ReviewOutput,
    BlendOutput,
    DistillOutput,
    GuideOutput,
)

from ._base import _article_header, _assign_ids, _audit_connections, _repair_connections
from .steps import (
    step1_scan,
    step2_logic,
    step3_rhetoric,
    step4_probe,
    step5_ethics,
    step6_review,
    step7_blend,
    step8_distill,
    step9_guide,
    step10_core,
)


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
    # Fallback for pasted / title-first articles (no URL header): take the first
    # substantial line as the title, skipping HTML-tagged duplicate lines.
    if title is None:
        for line in lines:
            s = line.strip()
            if len(s) > 15 and not s.startswith('http') and '<' not in s:
                # A headline is short; a long first "line" is body text — e.g. a
                # single-line transcript with no title. Don't mistake it for one.
                if len(s) <= 160:
                    title = s
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

    # Step 1 — Scan + Context
    print("[1/9] Scan…", file=sys.stderr, flush=True)
    ext_data = _load_or_run(steps_dir, "step1_scan.json",
        lambda: step1_scan.run(article, steps_dir, no_api=no_api))
    extraction = ExtractionResult.model_validate(ext_data)

    # Step 2 — Logic
    print("[2/9] Logic…", file=sys.stderr, flush=True)
    fond_data = _load_or_run(steps_dir, "step2_logic.json",
        lambda: step2_logic.run(article, ext_data, steps_dir, no_api=no_api))
    fond = AnalysisFond.model_validate(fond_data)

    # Step 3 — Rhetoric
    print("[3/9] Rhetoric…", file=sys.stderr, flush=True)
    forme_data = _load_or_run(steps_dir, "step3_rhetoric.json",
        lambda: step3_rhetoric.run(article, ext_data, fond_data, steps_dir, no_api=no_api))
    forme = AnalyseForme.model_validate(forme_data)

    # Step 4 — Probe
    print("[4/9] Probe…", file=sys.stderr, flush=True)
    probe_data = _load_or_run(steps_dir, "step4_probe.json",
        lambda: step4_probe.run(article, fond_data, forme_data, steps_dir, no_api=no_api))
    probe = ProbeOutput.model_validate(probe_data)

    # Step 5 — Ethics
    print("[5/9] Ethics…", file=sys.stderr, flush=True)
    ethics_data = _load_or_run(steps_dir, "step5_ethics.json",
        lambda: step5_ethics.run(article, ext_data, probe_data, steps_dir, no_api=no_api))
    ethics = EthicsOutput.model_validate(ethics_data)

    # Step 6 — Review
    print("[6/9] Review…", file=sys.stderr, flush=True)
    review_data = _load_or_run(steps_dir, "step6_review.json",
        lambda: step6_review.run(fond_data, forme_data, probe_data, ethics_data, steps_dir, no_api=no_api))
    review_out = ReviewOutput.model_validate(review_data)

    # Compute proven_by back-references on each observation
    obs_index = {obs.aspect: i for i, obs in enumerate(fond.observations)}
    obs_proven_by: dict[int, list[ProvenByRef]] = {i: [] for i in range(len(fond.observations))}
    for claim_idx, claim in enumerate(probe.facts_vs_opinions.claims_and_sources):
        if claim.proves.type == "observation" and claim.proves.label in obs_index:
            obs_proven_by[obs_index[claim.proves.label]].append(ProvenByRef(type="claim", index=claim_idx))
    for bias_idx, bias in enumerate(probe.biases_and_focus.biases_and_rhetoric):
        if bias.proves.type == "observation" and bias.proves.label in obs_index:
            obs_proven_by[obs_index[bias.proves.label]].append(ProvenByRef(type="bias", index=bias_idx))
    if probe.biases_and_focus.focus.proves.type == "observation":
        focus_label = probe.biases_and_focus.focus.proves.label
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
            # `_extract_title_chapo` only finds a title in scraped bodies (URL
            # line before the title); step1_scan backfills the first non-empty
            # line for title-first files, so fall through to it.
            title=input.title or article_title or (ext_data.get("article_metadata") or {}).get("title"),
            # Topical rubrique classified in step 1; default to "Autre" so older
            # caches (pre-category) and misses stay valid and just render pill-less.
            category=(ext_data.get("article_metadata") or {}).get("category") or "Autre",
            source=input.source,
            published_at=input.published_at,
            type=extraction.article_type,
            medium=input.medium,
            reading_time_minutes=max(1, len(input.body.split()) // 200),
            chapo=article_chapo,
        ),
        extraction=ArticleExtraction(
            authority_anchors=extraction.authority_anchors,
            key_quotes=extraction.key_quotes,
            notable_omissions=extraction.notable_omissions,
            rhetorical_patterns=extraction.rhetorical_patterns,
        ),
        context=extraction.context,
        analysis=Analysis(fond=fond, forme=forme),
        annotations=Annotations(
            facts_vs_opinions=probe.facts_vs_opinions,
            biases_and_focus=probe.biases_and_focus,
        ),
        deontology=ethics.deontology,
        review=review_out.review,
    )
    assembled = _assign_ids(assembled)

    # Connection audit + repair
    conn_issues = _audit_connections(json.loads(assembled.model_dump_json()))
    if conn_issues:
        print(
            f"  ↻ {len(conn_issues)} connection gap(s) detected, repairing…",
            file=sys.stderr, flush=True,
        )
        assembled = _repair_connections(assembled, conn_issues, article, fond_data, forme_data, probe_data, no_api)
        remaining = _audit_connections(json.loads(assembled.model_dump_json()))
        for issue in remaining:
            print(f"  ⚠  {issue}", file=sys.stderr)
    else:
        print("  ✓ Connection audit: all nodes connected.", file=sys.stderr, flush=True)

    # Step 7 — Blend
    print("[7/9] Blend…", file=sys.stderr, flush=True)
    blend_data = _load_or_run(steps_dir, "step7_blend.json",
        lambda: step7_blend.run(fond_data, forme_data, probe_data, ethics_data, review_data, steps_dir, no_api=no_api))
    blend_out = BlendOutput.model_validate(blend_data)
    assembled = assembled.model_copy(update={"blend": blend_out.blend})

    # Step 8 — Distill
    print("[8/9] Distill…", file=sys.stderr, flush=True)
    distill_data = _load_or_run(steps_dir, "step8_distill.json",
        lambda: step8_distill.run(blend_data, steps_dir, no_api=no_api))
    distill_out = DistillOutput.model_validate(distill_data)
    assembled = assembled.model_copy(update={"distill": distill_out.distill})

    # Step 9 — Guide
    print("[9/9] Guide…", file=sys.stderr, flush=True)
    guide_data = _load_or_run(steps_dir, "step9_guide.json",
        lambda: step9_guide.run(review_data, blend_data, distill_data, steps_dir, no_api=no_api))
    guide_out = GuideOutput.model_validate(guide_data)
    assembled = assembled.model_copy(update={"guide": guide_out.guide})

    # Step 10 — Core elements (title-independent; drives the carousel)
    print("[10] Core…", file=sys.stderr, flush=True)
    core_data = _load_or_run(steps_dir, "step10_core.json",
        lambda: step10_core.run(article, ext_data, fond_data, probe_data, steps_dir, no_api=no_api))
    assembled = assembled.model_copy(update={"core_elements": CoreElements.model_validate(core_data)})

    return assembled
