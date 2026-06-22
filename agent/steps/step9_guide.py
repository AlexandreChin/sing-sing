from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis_steps import GuideOutput

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step9_guide.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    out = GuideOutput.model_validate(data)
    errors = []
    guide = out.guide
    if not guide.pre_reading:
        errors.append("guide.pre_reading is empty")
    if not guide.watch_out.items:
        errors.append("guide.watch_out.items is empty")
    if not guide.after_reading:
        errors.append("guide.after_reading is empty")
    for i, item in enumerate(guide.watch_out.items):
        if not item.references:
            errors.append(f"guide.watch_out.items[{i}]: references is empty — must cite analysis node IDs")
        if not item.text.strip():
            errors.append(f"guide.watch_out.items[{i}]: text is empty")
    return errors


def run(
    article: str,
    fond_data: dict,
    forme_data: dict,
    probe_data: dict,
    ethics_data: dict,
    review_data: dict,
    blend_data: dict,
    distill_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"{article}\n\n---\n\n"
        f"LOGIC (step 2):\n{_j(fond_data)}\n\n"
        f"RHETORIC (step 3):\n{_j(forme_data)}\n\n"
        f"PROBE (step 4):\n{_j(probe_data)}\n\n"
        f"ETHICS (step 5):\n{_j(ethics_data)}\n\n"
        f"REVIEW (step 6):\n{_j(review_data)}\n\n"
        f"BLEND (step 7):\n{_j(blend_data)}\n\n"
        f"DISTILL (step 8):\n{_j(distill_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, GuideOutput.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step9_guide.json")
    return data
