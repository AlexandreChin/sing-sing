from agent.full_analysis_agent import _sync_instructions_stamp


def _seed(steps):
    steps.mkdir()
    (steps / "step1_scan.json").write_text("{}")


def test_unstamped_cache_kept_without_instructions(tmp_path):
    steps = tmp_path / "steps"; _seed(steps)
    _sync_instructions_stamp(steps, None)
    assert (steps / "step1_scan.json").exists()


def test_new_instructions_move_cache_aside(tmp_path):
    steps = tmp_path / "steps"; _seed(steps)
    _sync_instructions_stamp(steps, "angle : le cadrage")
    assert not (steps / "step1_scan.json").exists()
    assert len(list(steps.glob("stale_*/step1_scan.json"))) == 1


def test_same_instructions_keep_cache(tmp_path):
    steps = tmp_path / "steps"; steps.mkdir()
    _sync_instructions_stamp(steps, "angle")
    (steps / "step1_scan.json").write_text("{}")
    _sync_instructions_stamp(steps, "angle")
    assert (steps / "step1_scan.json").exists()


def test_adapt_context_leads_with_instructions():
    import json
    from pathlib import Path
    from agent.instagram_carousel_adapt_agent import _full_analysis_context
    from models.full_analysis import ArticleFullAnalysis
    data = json.loads(Path("samples/podcasts/podcast_1/analysis.json").read_text())
    full = ArticleFullAnalysis.model_validate(data)
    assert "CONSIGNES ÉDITORIALES" not in _full_analysis_context(full)
    full.article_metadata.extra_instructions = "Angle : le cadrage « casseurs »."
    ctx = _full_analysis_context(full)
    assert ctx.startswith("CONSIGNES ÉDITORIALES") and "cadrage « casseurs »" in ctx
