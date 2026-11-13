import asyncio

import pytest

import main
from main import _build_parser as build_parser
from agent.carousel_steps import run


def test_stop_after_takes_step_names():
    args = build_parser().parse_args(["adapt", "a.json", "--stop-after", "socle", "--guided"])
    assert args.stop_after == "socle" and args.guided


def test_stop_after_rejects_old_stage_names():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["adapt", "a.json", "--stop-after", "axis"])


def test_choose_parses_picks_and_edits():
    args = build_parser().parse_args(["choose", "d", "idees", "--pick", "1a,2b,3a",
                                      "--edit", "2b=Un **texte** : détail", "--reason", "plus clair"])
    assert args.pick == "1a,2b,3a" and args.edit == ["2b=Un **texte** : détail"]


def test_edit_text_keeps_equals_signs_and_quotes():
    assert main._parse_edits(["a=« x = y »"]) == {"a": "« x = y »"}


def _fmt_dir(tmp_path):
    fmt = tmp_path / "stem" / "instagram_carousel_optimized"
    fmt.mkdir(parents=True)
    (fmt.parent / "analysis.json").write_text("{}", encoding="utf-8")
    return fmt


@pytest.fixture
def stub_full(monkeypatch):
    import models.full_analysis as fa
    monkeypatch.setattr(fa.ArticleFullAnalysis, "model_validate", classmethod(lambda cls, d: "FULL"))


def test_choose_error_exits_1(monkeypatch, tmp_path, capsys, stub_full):
    fmt = _fmt_dir(tmp_path)

    def boom(*a, **k):
        raise run.ChoiceError("nope")
    monkeypatch.setattr(run, "choose", boom)
    args = build_parser().parse_args(["choose", str(fmt), "idees", "--pick", "1a"])
    with pytest.raises(SystemExit) as e:
        asyncio.run(main.cmd_choose(args))
    assert e.value.code == 1
    assert "nope" in capsys.readouterr().err


def test_choose_prints_warnings_and_passes_args(monkeypatch, tmp_path, capsys, stub_full):
    fmt = _fmt_dir(tmp_path)
    (fmt.parent / "stem.txt").write_text("the article", encoding="utf-8")
    seen = {}

    def fake(full, steps_dir, step, picks, edits, reason, article_text):
        seen.update(steps_dir=steps_dir, step=step, picks=picks, edits=edits, reason=reason, article=article_text)
        return ["too long"]
    monkeypatch.setattr(run, "choose", fake)
    args = build_parser().parse_args(["choose", str(fmt), "idees", "--pick", "1a, 2b", "--edit", "2b=x=y",
                                      "--reason", "r"])
    asyncio.run(main.cmd_choose(args))
    assert seen == {"steps_dir": fmt / "adapt_steps", "step": "idees", "picks": ["1a", "2b"],
                    "edits": {"2b": "x=y"}, "reason": "r", "article": "the article"}
    assert "⚠" in capsys.readouterr().err


def test_choose_more_prints_options_on_stdout(monkeypatch, tmp_path, capsys, stub_full):
    fmt = _fmt_dir(tmp_path)
    from agent.carousel_steps.steps import Option
    from agent.carousel_steps.store import StepFile
    new = StepFile(step="question", recommended=["c"],
                   options=[Option(id="c", slot="question", reason="plus large", fields={"text": "Une autre ?"})])
    monkeypatch.setattr(run, "more", lambda *a, **k: new)
    args = build_parser().parse_args(["choose", str(fmt), "question", "--more", "--remark", "r"])
    asyncio.run(main.cmd_choose(args))                             # the real format_options
    out = capsys.readouterr().out
    assert "c — Une autre ? ★" in out and "↳ plus large" in out


def test_choose_without_pick_or_more_is_usage_error(tmp_path, capsys):
    fmt = _fmt_dir(tmp_path)
    args = build_parser().parse_args(["choose", str(fmt), "question"])
    with pytest.raises(SystemExit) as e:
        asyncio.run(main.cmd_choose(args))
    assert e.value.code == 2


def test_fix_calls_run_fix(monkeypatch, tmp_path, capsys, stub_full):
    fmt = _fmt_dir(tmp_path)
    monkeypatch.setattr(run, "fix", lambda full, steps_dir, field, text, article_text: "hook")
    args = build_parser().parse_args(["fix", str(fmt), "hook.title", "Hi"])
    asyncio.run(main.cmd_fix(args))
    assert "hook" in capsys.readouterr().err


def test_fix_prints_the_warnings_a_fix_returns(monkeypatch, tmp_path, capsys, stub_full):
    fmt = _fmt_dir(tmp_path)
    monkeypatch.setattr(run, "fix", lambda full, steps_dir, field, text, article_text: ("hook", ["hook.title is 65 chars (max 64)"]))
    asyncio.run(main.cmd_fix(build_parser().parse_args(["fix", str(fmt), "hook.title", "Hi"])))
    err = capsys.readouterr().err
    assert "⚠ hook.title is 65" in err and "Fixed hook.title in hook" in err


def test_fix_error_exits_1(monkeypatch, tmp_path, stub_full):
    fmt = _fmt_dir(tmp_path)

    def boom(*a, **k):
        raise run.ChoiceError("bad")
    monkeypatch.setattr(run, "fix", boom)
    with pytest.raises(SystemExit) as e:
        asyncio.run(main.cmd_fix(build_parser().parse_args(["fix", str(fmt), "f", "t"])))
    assert e.value.code == 1


def test_stage_kwargs_guided_only_when_accepted(tmp_path):
    k = {}
    assert main._adapt_stage_kwargs({"steps_dir", "guided"}, k, tmp_path, None, True)
    assert k == {"steps_dir": tmp_path, "guided": True}
    k = {}
    assert main._adapt_stage_kwargs({"x"}, k, tmp_path, None, True)
    assert k == {}


def _write_step(steps, n, name, picked):
    from agent.carousel_steps.store import StepFile
    steps.mkdir(parents=True, exist_ok=True)
    (steps / f"{n}_{name}.json").write_text(StepFile(step=name, picked=picked).model_dump_json(), encoding="utf-8")


def test_report_none_names_the_pending_step(tmp_path, capsys):
    steps = tmp_path / "fmt" / "adapt_steps"
    _write_step(steps, 1, "question", ["a"])
    _write_step(steps, 2, "enjeu", [])
    main._report_stop(steps, None, True)
    err = capsys.readouterr().err
    assert f"Awaiting a choice: python main.py choose {steps.parent} enjeu --pick <ids>" in err
    assert "--guided" in err and "<step>" not in err


def test_report_none_stopped_after(tmp_path, capsys):
    steps = tmp_path / "fmt" / "adapt_steps"
    _write_step(steps, 1, "question", ["a"])
    main._report_stop(steps, "question", False)
    assert "Stopped after question" in capsys.readouterr().err


def test_report_none_guided_and_stop_after_both(tmp_path, capsys):
    steps = tmp_path / "fmt" / "adapt_steps"
    _write_step(steps, 1, "question", ["a"])
    main._report_stop(steps, "question", True)
    assert "Stopped after question" in capsys.readouterr().err
    _write_step(steps, 2, "enjeu", [])
    main._report_stop(steps, "question", True)
    assert "Awaiting a choice" in capsys.readouterr().err


def test_edit_without_equals_is_usage_error(capsys):
    with pytest.raises(SystemExit) as e:
        main._parse_edits(["oops"])
    assert e.value.code == 2 and "ID=TEXT" in capsys.readouterr().err


def test_missing_analysis_exits_1(tmp_path, capsys):
    fmt = tmp_path / "stem" / "instagram_carousel_optimized"
    fmt.mkdir(parents=True)
    args = build_parser().parse_args(["fix", str(fmt), "f", "t"])
    with pytest.raises(SystemExit) as e:
        asyncio.run(main.cmd_fix(args))
    assert e.value.code == 1 and "analysis.json" in capsys.readouterr().err


# ── trois_regards ───────────────────────────────────────────────────────────

def _trois_dir(tmp_path):
    from tests._carousel_steps_fixtures import full
    fmt = tmp_path / "stem" / "trois_regards"
    fmt.mkdir(parents=True)
    (fmt.parent / "analysis.json").write_text(full().model_dump_json(), encoding="utf-8")
    return fmt


def _trois_adapted(tmp_path, fake):
    from agent import trois_regards_adapt_agent as tra
    from tests._carousel_steps_fixtures import full
    fmt = _trois_dir(tmp_path)
    tra.adapt(full(), steps_dir=fmt / "adapt_steps")
    return fmt


def test_choose_more_accepts_a_prism_slot_for_trois_regards(tmp_path, capsys):
    from tests.test_trois_regards import FakeCalls
    import agent.trois_regards_adapt_agent as tra
    calls = FakeCalls()
    mp = pytest.MonkeyPatch()
    mp.setattr(tra, "_call_with_retry", calls)
    try:
        fmt = _trois_adapted(tmp_path, calls)
        args = build_parser().parse_args(["choose", str(fmt), "prismes", "--more", "--prism", "p2", "--remark", "plus concret"])
        asyncio.run(main.cmd_choose(args))
        assert calls.slots[-1] == ["p2"]
        assert "[p2]" in capsys.readouterr().out
        args = build_parser().parse_args(["choose", str(fmt), "prismes", "--more", "--prism", "economique"])
        asyncio.run(main.cmd_choose(args))
        assert calls.slots[-1] == ["p2"]
    finally:
        mp.undo()


def test_prism_flag_without_more_is_refused(tmp_path, capsys):
    fmt = _trois_dir(tmp_path)
    args = build_parser().parse_args(["choose", str(fmt), "prismes", "--pick", "p1a,p2a,p3a", "--prism", "p2"])
    with pytest.raises(SystemExit) as e:
        asyncio.run(main.cmd_choose(args))
    assert e.value.code == 2 and "--prism" in capsys.readouterr().err


def test_prism_flag_is_refused_by_a_format_without_prisms(tmp_path, capsys, stub_full):
    fmt = _fmt_dir(tmp_path)
    args = build_parser().parse_args(["choose", str(fmt), "idees", "--more", "--prism", "p2"])
    with pytest.raises(SystemExit) as e:
        asyncio.run(main.cmd_choose(args))
    assert e.value.code == 2 and "--prism" in capsys.readouterr().err


def test_fix_a_prism_field_by_slot(tmp_path, capsys):
    from tests.test_trois_regards import FakeCalls
    import agent.trois_regards_adapt_agent as tra
    mp = pytest.MonkeyPatch()
    mp.setattr(tra, "_call_with_retry", FakeCalls())
    try:
        fmt = _trois_adapted(tmp_path, None)
        new = "Les loyers montent plus vite que les salaires."
        asyncio.run(main.cmd_fix(build_parser().parse_args(["fix", str(fmt), "prismes.p2.line1", new])))
        assert "Fixed prismes.p2.line1 in prismes" in capsys.readouterr().err
        sf = tra._load(fmt / "adapt_steps", tra.STEP_BY_NAME["prismes"])[0]
        assert sf.fragment["prisms"][1]["lines"][0] == new
    finally:
        mp.undo()


def test_stop_after_accepts_prismes_and_matrice():
    for step in ("prismes", "matrice"):
        args = build_parser().parse_args(["adapt", "a.json", "--format", "trois_regards", "--stop-after", step, "--guided"])
        assert args.stop_after == step
        assert build_parser().parse_args(["choose", "d", step, "--pick", "x"]).step == step


def test_choose_pick_runs_the_prismes_pick_and_the_web_check(tmp_path, capsys):
    from tests.test_trois_regards import FakeCalls
    from types import SimpleNamespace
    import agent.trois_regards_adapt_agent as tra
    import agent.trois_regards_verify as tv
    mp = pytest.MonkeyPatch()
    mp.setattr(tra, "_call_with_retry", FakeCalls())
    try:
        fmt = _trois_adapted(tmp_path, None)

        async def search(text):
            return SimpleNamespace(confirming=[], contradicting=[])
        mp.setattr(tv, "_search", search)
        args = build_parser().parse_args(["choose", str(fmt), "prismes", "--pick", "p1a,p2a,p3a"])
        asyncio.run(main.cmd_choose(args))
        err = capsys.readouterr().err
        assert "Kept p1a, p2a, p3a" in err
        assert "⚠" in err and "news" in err      # the web check ran and found nothing
        assert (fmt / "adapt_steps" / "3_prismes.verification.json").exists()
        asyncio.run(main.cmd_choose(build_parser().parse_args(["choose", str(fmt), "prismes", "--pick", "p1b,p2a,p3a", "--no-api"])))
        assert "news" not in capsys.readouterr().err   # --no-api skips the check
    finally:
        mp.undo()
