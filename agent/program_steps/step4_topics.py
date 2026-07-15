import json
from pathlib import Path

from agent._base import _call_with_retry, save_step
from agent.program_steps._gather import gather_corpus
from models.program_analysis import ProgramAnalysisInput, TopicAnalysis, CORE_DOMAINS

_PROMPT = (Path(__file__).parent / "prompts" / "step4_topics.md").read_text(encoding="utf-8")
_SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


def _validate(data: dict) -> list[str]:
    t = TopicAnalysis.model_validate(data)
    errors = []
    if not t.headline_measures:
        errors.append("headline_measures is empty")
    for i, m in enumerate(t.headline_measures):
        if not any(s.quote.strip() for s in m.sources):
            errors.append(f"headline_measures[{i}] has no sourced verbatim quote")
    if not t.faille.expert_sources:
        errors.append("faille has no expert_sources (independent specialist required)")
    return errors


async def run(input: ProgramAnalysisInput, research_data: dict, steps_dir: Path, no_api: bool = False) -> dict:
    statements = research_data.get("statements", [])
    topics = []
    no_corpus_msg = "(aucune — n'invente pas de source)"
    for domain in CORE_DOMAINS:
        domain_statements = [s for s in statements if s.get("domain") == domain]
        corpus = ""
        if not no_api:
            corpus, _ = await gather_corpus(
                [f"{input.candidate} {domain} mesure faisabilité coût analyse"], per_query=4
            )
        user_msg = (
            f"CANDIDAT·E : {input.candidate}\n"
            f"DOMAINE : {domain}\n\n"
            f"ÉNONCÉS DU PROGRAMME POUR CE DOMAINE :\n{json.dumps(domain_statements, ensure_ascii=False, indent=2)}\n\n"
            f"ANALYSES DE SPÉCIALISTES (recherche web) :\n{corpus or no_corpus_msg}\n\n"
            f"PROGRAMME (document fourni) :\n{input.program_text}\n\n---\n\n{_PROMPT}"
        )
        topic = _call_with_retry(user_msg, TopicAnalysis.model_json_schema(),
                                 validator=_validate, no_api=no_api, system=_SYSTEM, label=f"step4:{domain}")
        topic["domain"] = domain  # pin the domain deterministically
        topics.append(topic)

    # Assign globally-unique measure ids across all topics.
    counter = 0
    for topic in topics:
        for m in topic.get("headline_measures", []):
            m["id"] = f"m_{counter}"
            counter += 1

    data = {"topics": topics}
    save_step(data, steps_dir, "step4_topics.json")
    return data
