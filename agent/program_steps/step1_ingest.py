from pathlib import Path

from agent._base import _call_with_retry, save_step
from models.program_analysis import ProgramAnalysisInput, ProgramResearch, CORE_DOMAINS

_PROMPT = (Path(__file__).parent / "prompts" / "step1_ingest.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    r = ProgramResearch.model_validate(data)
    errors = []
    if not r.statements:
        errors.append("statements is empty")
    domains = {s.domain for s in r.statements}
    missing = [d for d in CORE_DOMAINS if d not in domains]
    if missing:
        errors.append(f"no statement for domains: {missing}")
    for i, s in enumerate(r.statements):
        if not s.source.quote.strip():
            errors.append(f"statements[{i}].source.quote is empty (must be verbatim from the document)")
    return errors


async def run(input: ProgramAnalysisInput, steps_dir: Path, no_api: bool = False) -> dict:
    domains = "\n".join(f"- {d}" for d in CORE_DOMAINS)
    user_msg = (
        f"CANDIDAT·E : {input.candidate}\n\n"
        f"DOMAINES À COUVRIR (un ou plusieurs énoncés chacun) :\n{domains}\n\n"
        f"PROGRAMME (document fourni) :\n{input.program_text}\n\n---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ProgramResearch.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step1")
    data["statements"] = [
        {**s, "id": f"st_{i}"} for i, s in enumerate(data.get("statements", []))
    ]
    save_step(data, steps_dir, "step1_ingest.json")
    return data
