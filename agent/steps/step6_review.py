from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis_steps import ReviewOutput

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step6_review.md").read_text(encoding="utf-8")

_DIMENSIONS = [
    "source_rigor",
    "reasoning_structure",
    "approach_transparency",
    "treatment_fairness",
    "clarity",
    "angle_originality",
]


def _validate(data: dict) -> list[str]:
    out = ReviewOutput.model_validate(data)
    errors = []
    dims = [d.dimension for d in out.review.dimensions]
    missing = [d for d in _DIMENSIONS if d not in dims]
    if missing:
        errors.append(f"review.dimensions: missing {missing}")
    if len(out.review.dimensions) != 6:
        errors.append(f"review.dimensions: expected exactly 6, got {len(out.review.dimensions)}")
    for d in out.review.dimensions:
        if not (1 <= d.score <= 5):
            errors.append(f"dimension '{d.dimension}': score {d.score} out of range (1–5)")
        if not d.rationale.strip():
            errors.append(f"dimension '{d.dimension}': rationale is empty")
        if not d.lesson.strip():
            errors.append(f"dimension '{d.dimension}': lesson is empty")
    verdict = out.review.verdict
    if not verdict.for_whom.strip():
        errors.append("verdict.for_whom is empty")
    if not verdict.payoff.strip():
        errors.append("verdict.payoff is empty")
    if not verdict.summary.strip():
        errors.append("verdict.summary is empty")
    return errors


def run(
    fond_data: dict,
    forme_data: dict,
    probe_data: dict,
    ethics_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"LOGIC (step 2):\n{_j(fond_data)}\n\n"
        f"RHETORIC (step 3):\n{_j(forme_data)}\n\n"
        f"PROBE (step 4):\n{_j(probe_data)}\n\n"
        f"ETHICS (step 5):\n{_j(ethics_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ReviewOutput.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step6_review.json")
    return data
