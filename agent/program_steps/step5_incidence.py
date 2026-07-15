import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from agent.program_steps._gather import gather_corpus
from models.program_analysis import Incidence

_PROMPT = (Path(__file__).parent / "prompts" / "step5_incidence.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    inc = Incidence.model_validate(data)
    errors = []
    if not inc.items:
        errors.append("items is empty")
    for i, it in enumerate(inc.items):
        if not it.expert_sources:
            errors.append(f"items[{i}] has no expert_sources")
    return errors


async def run(input, topics_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    corpus = ""
    if not no_api:
        corpus, _ = await gather_corpus(
            [f"{input.candidate} programme gagnants perdants redistribution incidence"], per_query=5
        )
    no_corpus_msg = "(aucune — n'invente pas de source)"
    user_msg = (
        f"CANDIDAT·E : {input.candidate}\n\n"
        f"MESURES PAR DOMAINE (étape 4) :\n{json.dumps(topics_data, ensure_ascii=False, indent=2)}\n\n"
        f"ANALYSES DE SPÉCIALISTES (recherche web) :\n{corpus or no_corpus_msg}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(user_msg, Incidence.model_json_schema(),
                            validator=_validate, no_api=no_api, system=_SYSTEM, label="step5")
    data["items"] = [{**it, "id": f"inc_{i}"} for i, it in enumerate(data.get("items", []))]
    save_step(data, steps_dir, "step5_incidence.json")
    return data
