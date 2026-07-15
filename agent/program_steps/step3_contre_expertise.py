import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from agent.program_steps._gather import gather_corpus
from models.program_analysis import ContreExpertise, VisionDiagnostic

_PROMPT = (Path(__file__).parent / "prompts" / "step3_contre_expertise.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    ce = ContreExpertise.model_validate(data)
    valid_ids = None  # cross-check happens at assembly; here just require sources
    errors = []
    for i, it in enumerate(ce.items):
        if not it.expert_sources:
            errors.append(f"items[{i}] has no expert_sources (independent specialist required)")
        if not it.root_cause_id.strip():
            errors.append(f"items[{i}].root_cause_id is empty")
    return errors


async def run(vision_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    vision = VisionDiagnostic.model_validate(vision_data)
    corpus = ""
    if not no_api:
        queries = [f"{c.cause} analyse économiste OR rapport OR étude" for c in vision.root_causes]
        corpus, _ = await gather_corpus(queries, per_query=4)

    no_corpus_msg = "(aucune — n'invente pas de source)"
    user_msg = (
        f"DIAGNOSTIC DU·DE LA CANDIDAT·E (étape 2) :\n{json.dumps(vision_data, ensure_ascii=False, indent=2)}\n\n"
        f"ANALYSES DE SPÉCIALISTES (recherche web) :\n{corpus or no_corpus_msg}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, ContreExpertise.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step3")
    data["items"] = [{**it, "id": f"ce_{i}"} for i, it in enumerate(data.get("items", []))]
    save_step(data, steps_dir, "step3_contre_expertise.json")
    return data
