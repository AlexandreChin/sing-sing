from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis_steps import EthicsOutput

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step5_ethics.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    out = EthicsOutput.model_validate(data)
    errors = []
    for v in out.deontology.violations:
        if not v.evidence.strip():
            errors.append(f"violation '{v.category}': evidence is empty — must quote the article")
    overall = out.deontology.verdict.overall
    has_violation = any(v.status == "violation" for v in out.deontology.violations)
    has_critical = any(v.severity == "critical" for v in out.deontology.violations)
    if has_critical and overall != "violation":
        errors.append(f"verdict.overall must be 'violation' when a critical severity item is present (got '{overall}')")
    if has_violation and overall == "clean":
        errors.append("verdict.overall is 'clean' but violations list is non-empty")
    if overall == "violation" and not has_violation:
        errors.append("verdict.overall is 'violation' but no entry has status='violation'")
    if overall != "clean" and not out.deontology.verdict.editorial_note:
        errors.append("verdict.editorial_note must be set when overall is not 'clean'")
    return errors


def run(
    article: str,
    ext_data: dict,
    fond_data: dict,
    forme_data: dict,
    probe_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"{article}\n\n---\n\n"
        f"SCAN (step 1):\n{_j(ext_data)}\n\n"
        f"LOGIC (step 2):\n{_j(fond_data)}\n\n"
        f"RHETORIC (step 3):\n{_j(forme_data)}\n\n"
        f"PROBE (step 4):\n{_j(probe_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, EthicsOutput.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step5_ethics.json")
    return data
