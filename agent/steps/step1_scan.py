from pathlib import Path
from agent._base import _call_with_retry, save_step
from models.full_analysis_steps import ExtractionResult

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step1_scan.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    result = ExtractionResult.model_validate(data)
    errors = []
    if not result.context.contexts:
        errors.append("context.contexts is empty")
    if not result.context.important_facts:
        errors.append("context.important_facts is empty")
    if not result.context.who_is_speaking:
        errors.append("context.who_is_speaking is empty")
    return errors


def run(article: str, steps_dir: Path, no_api: bool = False) -> dict:
    data = _call_with_retry(
        f"{article}\n\n---\n\n{_PROMPT}",
        ExtractionResult.model_json_schema(),
        validator=_validate,
        no_api=no_api,
    )
    save_step(data, steps_dir, "step1_scan.json")
    return data
