import pytest
from agent.program_steps import step4_topics as step4
from models.program_analysis import ProgramAnalysisInput, ProgramTopics, CORE_DOMAINS


@pytest.mark.asyncio
async def test_step4_builds_all_domains_with_unique_measure_ids(tmp_path, monkeypatch):
    async def fake_gather(queries, per_query=5):
        return "", []
    monkeypatch.setattr(step4, "gather_corpus", fake_gather)

    def fake_topic_call(*a, **k):
        return {
            "domain": fake_topic_call.domain,
            "headline_measures": [{"id": "", "measure": "m", "detail": None,
                                   "sources": [{"quote": "verbatim"}]}],
            "faille": {"kind": "funding", "label": "Financement", "explanation": "…",
                       "expert_sources": [{"name": "OFCE", "kind": "think_tank", "url": "https://x", "finding": "…"}]},
        }
    # step4.run sets step4._current_domain before each call; emulate via closure list
    domains_iter = iter(CORE_DOMAINS)
    def call(user_msg, schema, validator, no_api, system, label):
        fake_topic_call.domain = next(domains_iter)
        return fake_topic_call()
    monkeypatch.setattr(step4, "_call_with_retry", call)

    inp = ProgramAnalysisInput(candidate="X", program_text="…")
    research = {"statements": [{"id": "st_0", "domain": CORE_DOMAINS[0], "quote": "q", "source": {"quote": "q"}}]}
    data = await step4.run(inp, research, tmp_path, no_api=True)
    t = ProgramTopics.model_validate(data)
    assert len(t.topics) == len(CORE_DOMAINS)
    all_ids = [m.id for topic in t.topics for m in topic.headline_measures]
    assert all_ids == [f"m_{i}" for i in range(len(all_ids))]  # globally unique, sequential
