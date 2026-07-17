from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis import CoreElements

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step10_core.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    out = CoreElements.model_validate(data)
    errors = []
    n = len(out.elements)
    if not (3 <= n <= 5):
        errors.append(f"core_elements.elements must have 3–5 items, got {n}")
    for i, e in enumerate(out.elements):
        if not (1 <= e.centrality <= 5):
            errors.append(f"elements[{i}].centrality={e.centrality} out of range 1–5")
        if not e.statement.strip():
            errors.append(f"elements[{i}].statement is empty")
    return errors


def run(article: str, ext_data: dict, fond_data: dict, probe_data: dict,
        steps_dir: Path, no_api: bool = False) -> dict:
    user_msg = (
        f"{article}\n\n---\n\n"
        f"EXTRACTION (étape 1) :\n{_j(ext_data)}\n\n"
        f"FOND (étape 2) :\n{_j(fond_data)}\n\n"
        f"PROBE (étape 4) :\n{_j(probe_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, CoreElements.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step10_core.json")
    return data
