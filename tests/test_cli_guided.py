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
    monkeypatch.setattr(run, "more", lambda *a, **k: "NEWFILE")
    monkeypatch.setattr(run, "format_options", lambda step, sf: f"options {step} {sf}")
    args = build_parser().parse_args(["choose", str(fmt), "question", "--more", "--remark", "r"])
    asyncio.run(main.cmd_choose(args))
    assert capsys.readouterr().out.strip() == "options question NEWFILE"


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
