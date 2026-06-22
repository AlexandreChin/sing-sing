from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis import AnalysisFond

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step2_logic.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    fond = AnalysisFond.model_validate(data)
    errors = []
    if not fond.main_claim:
        errors.append("analysis_fond.main_claim is empty")
    n = len(fond.observations)
    if not (1 <= n <= 5):
        errors.append(f"observations: expected 1–5, got {n}")
    for i, obs in enumerate(fond.observations):
        if not obs.seeds.excerpt:
            errors.append(f"observations[{i}].seeds.excerpt is empty")
    if not fond.premisses:
        errors.append("analysis_fond.premisses is empty")
    for i, p in enumerate(fond.premisses):
        if not p.statement:
            errors.append(f"premisses[{i}].statement is empty")
    if not fond.implicit_assumptions:
        errors.append("analysis_fond.implicit_assumptions is empty")
    if not fond.blind_spots:
        errors.append("analysis_fond.blind_spots is empty")
    if not fond.emphasis:
        errors.append("analysis_fond.emphasis is empty")
    if not fond.logical_reasoning:
        errors.append("analysis_fond.logical_reasoning is empty")
    for i, lr in enumerate(fond.logical_reasoning):
        if not lr.step:
            errors.append(f"logical_reasoning[{i}].step is empty")
    if not fond.steel_man:
        errors.append("analysis_fond.steel_man is empty")
    return errors


def run(
    article: str,
    ext_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"{article}\n\n---\n\n"
        f"SCAN (step 1):\n{_j(ext_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, AnalysisFond.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step2_logic.json")
    return data
