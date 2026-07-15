import pytest
from agent.program_steps import step3_contre_expertise as step3


@pytest.mark.asyncio
async def test_step3_assigns_ids_and_skips_gather_on_no_api(tmp_path, monkeypatch):
    called = {"gather": 0}
    async def fake_gather(queries, per_query=5):
        called["gather"] += 1
        return "", []
    monkeypatch.setattr(step3, "gather_corpus", fake_gather)

    fake = {"items": [
        {"id": "", "root_cause_id": "rc_0", "verdict": "Étayé.", "confidence": 70,
         "expert_sources": [{"name": "OFCE", "kind": "think_tank", "url": "https://x", "finding": "…"}]},
    ]}
    monkeypatch.setattr(step3, "_call_with_retry", lambda *a, **k: fake)

    vision = {"vision": "…", "root_causes": [{"id": "rc_0", "cause": "Inégalités.", "sources": []}]}
    data = await step3.run(vision, tmp_path, no_api=True)
    assert data["items"][0]["id"] == "ce_0"
    assert called["gather"] == 0  # no_api must not hit the network
    assert (tmp_path / "step3_contre_expertise.json").exists()
