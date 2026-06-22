from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis_steps import Step7Output

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step7_masterclass.md").read_text(encoding="utf-8")

_DIMENSIONS = [
    "source_rigor",
    "reasoning_structure",
    "approach_transparency",
    "treatment_fairness",
    "clarity",
    "angle_originality",
]


def _validate(data: dict) -> list[str]:
    step7 = Step7Output.model_validate(data)
    errors = []
    dims = [d.dimension for d in step7.masterclass.dimensions]
    missing = [d for d in _DIMENSIONS if d not in dims]
    if missing:
        errors.append(f"masterclass.dimensions: missing {missing}")
    if len(step7.masterclass.dimensions) != 6:
        errors.append(f"masterclass.dimensions: expected exactly 6, got {len(step7.masterclass.dimensions)}")
    for d in step7.masterclass.dimensions:
        if not (1 <= d.score <= 5):
            errors.append(f"dimension '{d.dimension}': score {d.score} out of range (1–5)")
        if not d.rationale.strip():
            errors.append(f"dimension '{d.dimension}': rationale is empty")
        if not d.lesson.strip():
            errors.append(f"dimension '{d.dimension}': lesson is empty")
    return errors


def run(
    article: str,
    fond_data: dict,
    forme_data: dict,
    step5_data: dict,
    step6_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"{article}\n\n---\n\n"
        f"ANALYSE — LE FOND (step 3):\n{_j(fond_data)}\n\n"
        f"ANALYSE — LA FORME (step 4):\n{_j(forme_data)}\n\n"
        f"ANNOTATIONS (step 5):\n{_j(step5_data)}\n\n"
        f"SYNTHESIS (step 6):\n{_j(step6_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, Step7Output.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step7_masterclass.json")
    return data
