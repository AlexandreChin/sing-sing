import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from models.program_analysis import ProgramDistill

_PROMPT = (Path(__file__).parent / "prompts" / "step7_distill.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    d = ProgramDistill.model_validate(data)
    errors = []
    if len(d.points) != 3:
        errors.append(f"points: expected exactly 3, got {len(d.points)}")
    if not d.verdict.summary.strip():
        errors.append("verdict.summary is empty")
    if not d.verdict.open_question.strip():
        errors.append("verdict.open_question is empty")
    return errors


async def run(vision_data: dict, topics_data: dict, review_data: dict, incidence_data: dict,
              steps_dir: Path, no_api: bool = False) -> dict:
    user_msg = (
        f"VISION & DIAGNOSTIC :\n{json.dumps(vision_data, ensure_ascii=False, indent=2)}\n\n"
        f"MESURES & FAILLES :\n{json.dumps(topics_data, ensure_ascii=False, indent=2)}\n\n"
        f"INCIDENCE :\n{json.dumps(incidence_data, ensure_ascii=False, indent=2)}\n\n"
        f"NOTES PAR DIMENSION :\n{json.dumps(review_data, ensure_ascii=False, indent=2)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ProgramDistill.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step7")
    save_step(data, steps_dir, "step7_distill.json")
    return data
