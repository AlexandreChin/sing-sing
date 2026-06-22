from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis_steps import DistillOutput

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step8_distill.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    out = DistillOutput.model_validate(data)
    errors = []
    n = len(out.distill.points)
    if not (3 <= n <= 5):
        errors.append(f"distill.points: expected 3–5, got {n}")
    if not out.distill.open_question.strip():
        errors.append("distill.open_question is empty")
    for i, pt in enumerate(out.distill.points):
        if not pt.references:
            errors.append(f"distill.points[{i}]: references is empty")
    return errors


def run(
    blend_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"BLEND (step 7):\n{_j(blend_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, DistillOutput.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step8_distill.json")
    return data
