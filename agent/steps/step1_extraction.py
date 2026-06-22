from pathlib import Path
from agent._base import _call, save_step
from models.full_analysis_steps import ExtractionResult

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step1_extraction.md").read_text(encoding="utf-8")


def run(article: str, steps_dir: Path, no_api: bool = False) -> dict:
    data = _call(
        f"{article}\n\n---\n\n{_PROMPT}",
        ExtractionResult.model_json_schema(),
        no_api=no_api,
    )
    save_step(data, steps_dir, "step1_extraction.json")
    return data
