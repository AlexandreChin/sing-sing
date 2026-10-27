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


def test_report_none_distinguishes(tmp_path, capsys):
    steps = tmp_path / "fmt" / "adapt_steps"
    main._report_stop(steps, None, True)
    err = capsys.readouterr().err
    assert "Awaiting a choice: python main.py choose" in err and "--guided" in err
    main._report_stop(steps, "socle", False)
    assert "Stopped after socle" in capsys.readouterr().err
