from pathlib import Path
from agent._base import _call_with_retry, _j, save_step, _build_node_index
from models.full_analysis import AnalysisFond, AnalyseForme  # needed for node index
from models.full_analysis_steps import BlendOutput

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step7_blend.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    out = BlendOutput.model_validate(data)
    errors = []
    n = len(out.blend.patterns)
    if not (1 <= n <= 8):
        errors.append(f"blend.patterns: expected 1–8, got {n}")
    for i, p in enumerate(out.blend.patterns):
        if len(p.layers) < 2:
            errors.append(f"blend.patterns[{i}]: must span ≥2 layers, got {p.layers}")
        if not p.references:
            errors.append(f"blend.patterns[{i}]: references is empty — must cite node IDs")
        if not p.text.strip():
            errors.append(f"blend.patterns[{i}]: text is empty")
    return errors


def run(
    fond_data: dict,
    forme_data: dict,
    probe_data: dict,
    ethics_data: dict,
    review_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    fond = AnalysisFond.model_validate(fond_data)
    forme = AnalyseForme.model_validate(forme_data)
    node_index = _build_node_index(fond, forme, probe_data)
    user_msg = (
        f"LOGIC (step 2):\n{_j(fond_data)}\n\n"
        f"RHETORIC (step 3):\n{_j(forme_data)}\n\n"
        f"PROBE (step 4):\n{_j(probe_data)}\n\n"
        f"ETHICS (step 5):\n{_j(ethics_data)}\n\n"
        f"REVIEW (step 6):\n{_j(review_data)}\n\n"
        f"{node_index}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, BlendOutput.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step7_blend.json")
    return data
