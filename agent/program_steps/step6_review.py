import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from models.program_analysis import ProgramReview

_PROMPT = (Path(__file__).parent / "prompts" / "step6_review.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")

_DIMENSIONS = ("funding_clarity", "feasibility", "internal_coherence", "evidence_grounding")


def _validate(data: dict) -> list[str]:
    r = ProgramReview.model_validate(data)
    errors = []
    if len(r.dimensions) != 4:
        errors.append(f"expected exactly 4 dimensions, got {len(r.dimensions)}")
    got = {d.dimension for d in r.dimensions}
    missing = [d for d in _DIMENSIONS if d not in got]
    if missing:
        errors.append(f"missing dimensions: {missing}")
    for i, d in enumerate(r.dimensions):
        if not (1 <= d.score <= 5):
            errors.append(f"dimensions[{i}].score={d.score} out of range 1–5")
    return errors


async def run(vision_data: dict, topics_data: dict, contre_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    user_msg = (
        f"VISION & DIAGNOSTIC (étape 2) :\n{json.dumps(vision_data, ensure_ascii=False, indent=2)}\n\n"
        f"CONTRE-EXPERTISE (étape 3) :\n{json.dumps(contre_data, ensure_ascii=False, indent=2)}\n\n"
        f"MESURES & FAILLES PAR DOMAINE (étape 4) :\n{json.dumps(topics_data, ensure_ascii=False, indent=2)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ProgramReview.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step6")
    save_step(data, steps_dir, "step6_review.json")
    return data
