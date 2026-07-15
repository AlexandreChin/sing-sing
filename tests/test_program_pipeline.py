import shutil
from pathlib import Path

import pytest

from agent.program_analysis_agent import analyze_program, _audit_program
from models.program_analysis import ProgramAnalysisInput, ProgramFullAnalysis, CORE_DOMAINS

FIXTURES = Path(__file__).parent / "fixtures" / "program_steps"


@pytest.mark.asyncio
async def test_pipeline_assembles_from_cached_steps(tmp_path):
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    for f in FIXTURES.glob("*.json"):
        shutil.copy(f, steps_dir / f.name)

    inp = ProgramAnalysisInput(candidate="Candidat X", program_text="… programme court …")
    result = await analyze_program(inp, no_api=True, steps_dir=steps_dir)

    assert isinstance(result, ProgramFullAnalysis)
    assert len(result.topics.topics) == len(CORE_DOMAINS)
    assert len(result.review.dimensions) == 4
    assert len(result.distill.points) == 3
    assert _audit_program(result.model_dump()) == []
