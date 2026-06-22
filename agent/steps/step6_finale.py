from pathlib import Path
from agent._base import _call_with_retry, _j, save_step, _build_node_index
from models.full_analysis import AnalysisFond, AnalyseForme
from models.full_analysis_steps import Step6Output

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step6_finale.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    step6 = Step6Output.model_validate(data)
    errors = []
    n_points = len(step6.synthesis.points)
    if not (1 <= n_points <= 5):
        errors.append(f"synthesis.points must contain 1–5 items, got {n_points}")
    if not step6.synthesis.open_question.strip():
        errors.append("synthesis.open_question is empty")
    return errors


def run(
    article: str,
    step2_data: dict,
    fond_data: dict,
    forme_data: dict,
    step5_data: dict,
    fond: AnalysisFond,
    forme: AnalyseForme,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    node_index = _build_node_index(fond, forme, step5_data)
    user_msg = (
        f"{article}\n\n---\n\n"
        f"AVANT DE LIRE (étape 2) :\n{_j(step2_data)}\n\n"
        f"ANALYSE — LE FOND (étape 3) :\n{_j(fond_data)}\n\n"
        f"ANALYSE — LA FORME (étape 4) :\n{_j(forme_data)}\n\n"
        f"ANNOTATIONS (étape 5) :\n{_j(step5_data)}\n\n"
        f"{node_index}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, Step6Output.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step6_finale.json")
    return data
