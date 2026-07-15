import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from models.program_analysis import ProgramAnalysisInput, VisionDiagnostic

_PROMPT = (Path(__file__).parent / "prompts" / "step2_vision.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    v = VisionDiagnostic.model_validate(data)
    errors = []
    if not v.vision.strip():
        errors.append("vision is empty")
    if not v.root_causes:
        errors.append("root_causes is empty")
    for i, c in enumerate(v.root_causes):
        if not any(s.quote.strip() for s in c.sources):
            errors.append(f"root_causes[{i}] has no sourced verbatim quote")
    return errors


async def run(input: ProgramAnalysisInput, research_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    user_msg = (
        f"CANDIDAT·E : {input.candidate}\n\n"
        f"ÉNONCÉS SOURCÉS (étape 1) :\n{json.dumps(research_data, ensure_ascii=False, indent=2)}\n\n"
        f"PROGRAMME (document fourni) :\n{input.program_text}\n\n---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, VisionDiagnostic.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step2")
    data["root_causes"] = [
        {**c, "id": f"rc_{i}"} for i, c in enumerate(data.get("root_causes", []))
    ]
    save_step(data, steps_dir, "step2_vision.json")
    return data
