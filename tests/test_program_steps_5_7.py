import pytest
from agent.program_steps import step5_incidence as s5, step6_review as s6, step7_distill as s7
from models.program_analysis import Incidence, ProgramReview, ProgramDistill


@pytest.mark.asyncio
async def test_step5_ids_and_no_api(tmp_path, monkeypatch):
    gather_called = []
    async def fake_gather(q, per_query=5):
        gather_called.append(True)
        return "", []
    monkeypatch.setattr(s5, "gather_corpus", fake_gather)
    fake = {"items": [
        {"id": "", "group": "Ménages modestes", "effect": "benefits", "explanation": "…",
         "expert_sources": [{"name": "IPP", "kind": "think_tank", "url": "https://x", "finding": "…"}]},
        {"id": "", "group": "Grandes entreprises", "effect": "pays", "explanation": "…",
         "expert_sources": [{"name": "IPP", "kind": "think_tank", "url": "https://x", "finding": "…"}]},
    ]}
    monkeypatch.setattr(s5, "_call_with_retry", lambda *a, **k: fake)
    data = await s5.run(type("I", (), {"candidate": "X", "program_text": "…"})(), {"topics": []}, tmp_path, no_api=True)
    assert [i["id"] for i in data["items"]] == ["inc_0", "inc_1"]
    assert not gather_called, "gather_corpus should not be called when no_api=True"


@pytest.mark.asyncio
async def test_step6_four_dimensions(tmp_path, monkeypatch):
    dims = [{"dimension": k, "label": k, "score": 3, "rationale": "…"} for k in
            ("funding_clarity", "feasibility", "internal_coherence", "evidence_grounding")]
    monkeypatch.setattr(s6, "_call_with_retry", lambda *a, **k: {"dimensions": dims})
    data = await s6.run({}, {"topics": []}, {"items": []}, tmp_path, no_api=True)
    assert len(ProgramReview.model_validate(data).dimensions) == 4


@pytest.mark.asyncio
async def test_step7_distill_verdict(tmp_path, monkeypatch):
    fake = {"points": ["a", "b", "c"], "verdict": {"summary": "…", "open_question": "…"}}
    monkeypatch.setattr(s7, "_call_with_retry", lambda *a, **k: fake)
    data = await s7.run({}, {"topics": []}, {"dimensions": []}, {"items": []}, tmp_path, no_api=True)
    assert len(ProgramDistill.model_validate(data).points) == 3
