import pytest
from pathlib import Path
from agent.program_steps import step1_ingest, step2_vision
from models.program_analysis import ProgramAnalysisInput, ProgramResearch, VisionDiagnostic, CORE_DOMAINS


@pytest.mark.asyncio
async def test_step1_assigns_ids_and_validates(tmp_path, monkeypatch):
    fake = {"statements": [
        {"id": "", "domain": CORE_DOMAINS[0], "quote": "SMIC à 1600€", "source": {"quote": "SMIC à 1600€"}},
        {"id": "", "domain": CORE_DOMAINS[1], "quote": "Bloquer les prix", "source": {"quote": "Bloquer les prix"}},
    ]}
    monkeypatch.setattr(step1_ingest, "_call_with_retry", lambda *a, **k: fake)
    inp = ProgramAnalysisInput(candidate="X", program_text="… programme …")
    data = await step1_ingest.run(inp, tmp_path, no_api=True)
    r = ProgramResearch.model_validate(data)
    assert [s.id for s in r.statements] == ["st_0", "st_1"]
    assert (tmp_path / "step1_ingest.json").exists()


@pytest.mark.asyncio
async def test_step2_assigns_rootcause_ids(tmp_path, monkeypatch):
    fake = {"vision": "Une France plus juste.", "values": None, "root_causes": [
        {"id": "", "cause": "Inégalités.", "sources": [{"quote": "…"}]},
        {"id": "", "cause": "Désindustrialisation.", "sources": [{"quote": "…"}]},
    ]}
    monkeypatch.setattr(step2_vision, "_call_with_retry", lambda *a, **k: fake)
    inp = ProgramAnalysisInput(candidate="X", program_text="…")
    data = await step2_vision.run(inp, {"statements": []}, tmp_path, no_api=True)
    v = VisionDiagnostic.model_validate(data)
    assert [c.id for c in v.root_causes] == ["rc_0", "rc_1"]
