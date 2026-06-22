from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis_steps import Step2Output

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step2_avant_de_lire.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    step2 = Step2Output.model_validate(data)
    errors = []
    n = len(step2.watch_out.items)
    if not (2 <= n <= 8):
        errors.append(f"watch_out.items: expected 2–8, got {n}")
    if not step2.context.contexts:
        errors.append("context.contexts is empty")
    if not step2.context.important_facts:
        errors.append("context.important_facts is empty")
    if not step2.cadrage.title_analysis:
        errors.append("cadrage.title_analysis is empty")
    return errors


def run(
    article: str,
    ext_data: dict,
    title_line: str,
    chapo_line: str,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"{article}\n\n---\n\n"
        f"EXTRACTION (étape 1) :\n{_j(ext_data)}\n\n"
        f"TITRE DE L'ARTICLE : {title_line}\n"
        f"CHAPEAU : {chapo_line}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, Step2Output.model_json_schema(), validator=_validate, no_api=no_api)
    save_step(data, steps_dir, "step2_avant_de_lire.json")
    return data
