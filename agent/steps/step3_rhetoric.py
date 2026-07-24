from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis import AnalyseForme

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step3_rhetoric.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    forme = AnalyseForme.model_validate(data)
    errors = []
    n_er = len(forme.emotional_register)
    if not (1 <= n_er <= 2):
        errors.append(f"emotional_register: expected 1–2, got {n_er}")
    for i, er in enumerate(forme.emotional_register):
        if not er.seeds.excerpt:
            errors.append(f"emotional_register[{i}].seeds.excerpt is empty")
    n_cb = len(forme.cui_bono)
    if not (1 <= n_cb <= 2):
        errors.append(f"cui_bono: expected 1–2, got {n_cb}")
    for i, cb in enumerate(forme.cui_bono):
        if not cb.seeds.excerpt:
            errors.append(f"cui_bono[{i}].seeds.excerpt is empty")
    if not forme.cadrage.title_analysis:
        errors.append("cadrage.title_analysis is empty")
    if not forme.cadrage.body.strip():
        errors.append("cadrage.body is empty")
    return errors


def run(
    article: str,
    ext_data: dict,
    fond_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"{article}\n\n---\n\n"
        f"SCAN (step 1):\n{_j(ext_data)}\n\n"
        f"LOGIC (step 2):\n{_j(fond_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, AnalyseForme.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step3_rhetoric.json")
    return data
