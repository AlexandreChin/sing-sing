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
