from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis_steps import Step8Output

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step8_consistency.md").read_text(encoding="utf-8")

_DIMENSIONS = [
    "source_rigor",
    "reasoning_structure",
    "approach_transparency",
    "treatment_fairness",
    "clarity",
    "angle_originality",
]


def _validate(data: dict) -> list[str]:
    step8 = Step8Output.model_validate(data)
    errors = []
    dims = [d.dimension for d in step8.masterclass.dimensions]
    missing = [d for d in _DIMENSIONS if d not in dims]
    if missing:
        errors.append(f"masterclass.dimensions: missing {missing}")
    if len(step8.masterclass.dimensions) != 6:
        errors.append(f"masterclass.dimensions: expected exactly 6, got {len(step8.masterclass.dimensions)}")
    return errors


def run(full_analysis: dict, steps_dir: Path, no_api: bool = False) -> dict:
    user_msg = f"FULL ANALYSIS:\n{_j(full_analysis)}\n\n---\n\n{_PROMPT}"
    data = _call_with_retry(user_msg, Step8Output.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step8_consistency.json")
    return data
