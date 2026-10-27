"""Regressions from the whole-branch review of the guided carousel adapt: each test
drives the real code path that was broken; only the model call is faked."""
import asyncio
import json
import shutil
from pathlib import Path

import pytest

import agent._base as base
import main
from main import _build_parser as build_parser
from agent.carousel_steps import run
from agent.carousel_steps.steps import STEP_BY_NAME
from agent.carousel_steps.store import load
from tests._carousel_steps_fixtures import FakeCalls, full as _full, load_deck, responses

ARTICLE = Path("samples/articles/article_15/article.txt")


@pytest.fixture
def fake(monkeypatch) -> FakeCalls:
    calls = FakeCalls(load_deck())
    monkeypatch.setattr(run, "_call_with_retry", calls)
    return calls


@pytest.fixture
def steps_dir(tmp_path):
    return tmp_path / "adapt_steps"


# ── 1. Inputs with leading/trailing whitespace stamp the same on every path ──

@pytest.fixture
def produced(tmp_path, monkeypatch, fake):
    """A scratch input ending in a newline, its analysis, and `produce --guided` on it."""
    txt = tmp_path / "piece.txt"
    txt.write_text("\n" + ARTICLE.read_text(encoding="utf-8").strip() + "\n\n", encoding="utf-8")

    async def analysed(*a, **k):
        return _full()
    monkeypatch.setattr(main, "analyze_for_full_analysis", analysed)

    def produce():
        asyncio.run(main.cmd_produce(build_parser().parse_args(["produce", str(txt), "--guided"])))
    produce()
    return tmp_path / "piece" / "instagram_carousel_optimized", produce


def test_choose_after_produce_accepts_the_pick_on_a_padded_input(produced, fake, capsys):
    fmt, produce = produced
    assert fake.labels == ["question"]
    asyncio.run(main.cmd_choose(build_parser().parse_args(["choose", str(fmt), "question", "--pick", "b"])))
    assert load(fmt / "adapt_steps", STEP_BY_NAME["question"])[0].picked == ["b"]
    produce()
    assert fake.labels == ["question", "enjeu"]                      # question reused, not regenerated


def test_fix_after_produce_keeps_later_steps_on_a_padded_input(produced, fake):
    fmt, produce = produced
    asyncio.run(main.cmd_choose(build_parser().parse_args(["choose", str(fmt), "question", "--pick", "a"])))
    produce()                                                        # enjeu offered
    asyncio.run(main.cmd_fix(build_parser().parse_args(
        ["fix", str(fmt), "cta.engagement_sentence", "Une question corrigée ?"])))
    produce()
    assert fake.labels == ["question", "enjeu"]                      # enjeu still current
    asyncio.run(main.cmd_choose(build_parser().parse_args(["choose", str(fmt), "enjeu", "--pick", "a"])))


def test_base_inputs_ignores_surrounding_whitespace():
    assert run.base_inputs(_full(), "texte\n") == run.base_inputs(_full(), "  texte")


def test_article_beside_is_stripped(tmp_path):
    (tmp_path / "s").mkdir()
    (tmp_path / "s.txt").write_text("\ncorps\n", encoding="utf-8")
    assert main._article_beside(tmp_path / "s" / "analysis.json") == "corps"


# ── 3. An answer still invalid after the retries fails loudly ────────────────

def _real_call(monkeypatch, label, edit):
    """The real `_call_with_retry`, its API call answering `label`'s fixture after `edit`."""
    monkeypatch.setattr(run, "_call_with_retry", base._call_with_retry)
    answer = edit(responses(load_deck())[label])
    monkeypatch.setattr(base, "_call", lambda *a, **k: json.loads(json.dumps(answer)))


def test_schema_invalid_answer_raises_naming_the_step(monkeypatch, steps_dir):
    def no_text(data):
        for o in data["options"]:
            del o["text"]
        return data
    _real_call(monkeypatch, "question", no_text)
    with pytest.raises(RuntimeError, match=r"step 1 \(question\)") as e:
        run.adapt(_full(), steps_dir=steps_dir)
    assert "text" in str(e.value)
    saved = json.loads((steps_dir / "1_question.failed.json").read_text(encoding="utf-8"))
    assert "text" not in saved["options"][0]


def test_missing_slot_raises_naming_the_step(fake, monkeypatch, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, stop_after="contexte")

    def no_headline(data):
        keep = [i for i, o in enumerate(data["options"]) if o["slot"] != "headline"]
        data["options"] = [data["options"][i] for i in keep]
        data["recommended"] = [keep.index(i) for i in data["recommended"] if i in keep]
        return data
    _real_call(monkeypatch, "socle", no_headline)
    with pytest.raises(RuntimeError, match=r"step 6 \(socle\)") as e:
        run.adapt(_full(), steps_dir=steps_dir)
    assert "slot 'headline' has 0 option(s)" in str(e.value)
    assert (steps_dir / "6_socle.failed.json").exists()
    assert load(steps_dir, STEP_BY_NAME["socle"])[0] is None          # nothing half-built saved


def test_too_many_options_is_kept_with_a_warning(monkeypatch, steps_dir, capsys):
    def five(data):
        data["options"].append({**data["options"][-1], "text": "Une cinquième question ?"})
        return data
    _real_call(monkeypatch, "question", five)
    run.adapt(_full(), steps_dir=steps_dir, stop_after="question")
    sf, _ = load(steps_dir, STEP_BY_NAME["question"])
    assert len(sf.options) == 5 and sf.picked == ["a"]
    assert "slot 'question' has 5 option(s), must have 3–4" in capsys.readouterr().err
    assert not (steps_dir / "1_question.failed.json").exists()


def test_schema_invalid_writing_raises(fake, monkeypatch, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, stop_after="hook")
    _real_call(monkeypatch, "writing", lambda d: {k: v for k, v in d.items() if k != "caption"})
    with pytest.raises(RuntimeError, match=r"step 8 \(writing\)"):
        run.adapt(_full(), steps_dir=steps_dir)
    assert (steps_dir / "8_writing.failed.json").exists()


# ── 4. --edit on an unknown field is refused ─────────────────────────────────

def test_edit_of_an_unknown_field_is_refused(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    with pytest.raises(run.ChoiceError, match="text"):
        run.choose(_full(), steps_dir, "question", ["a"], {"a.txet": "Une question ?"})
    sf, _ = load(steps_dir, STEP_BY_NAME["question"])
    assert sf.picked == [] and "txet" not in sf.options[0].fields


# ── choose at the question step keeps its thesis frame ───────────────────────

def test_choose_at_question_keeps_the_thesis_frame(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    run.choose(_full(), steps_dir, "question", ["a"], {})
    sf, _ = load(steps_dir, STEP_BY_NAME["question"])
    assert sf.fragment["display"]["thesis_frame"] == sf.thesis_frame.model_dump()


# ── 6. The pause line names the command that ran ─────────────────────────────

def test_pause_line_names_adapt_when_adapt_ran(tmp_path, capsys):
    from agent.carousel_steps.store import StepFile, save
    steps = tmp_path / "fmt" / "adapt_steps"
    save(steps, StepFile(step="question"), "x")
    main._report_stop(steps, None, True, command="adapt")
    err = capsys.readouterr().err
    assert "rerun adapt with --guided" in err and "produce" not in err


# ── 7. Retiring the legacy stage files says so ───────────────────────────────

def test_legacy_move_is_announced_once(fake, steps_dir, capsys):
    run.adapt(_full(), steps_dir=steps_dir)
    assert "stale_legacy" not in capsys.readouterr().err
    (steps_dir / "2_selection.json").write_text("{}")
    run.adapt(_full(), steps_dir=steps_dir)
    assert "old 3-stage adapt files moved to stale_legacy/" in capsys.readouterr().err


# ── 8. fix on an option step reaches the picked option ───────────────────────

def test_fix_question_survives_a_later_choose(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    run.choose(_full(), steps_dir, "question", ["b"], {})
    run.fix(_full(), steps_dir, "cta.engagement_sentence", "Une question corrigée ?")
    b = next(o for o in load(steps_dir, STEP_BY_NAME["question"])[0].options if o.id == "b")
    assert b.fields["text"] == "Une question corrigée ?" and b.edited
    run.choose(_full(), steps_dir, "question", ["b"], {})
    sf, _ = load(steps_dir, STEP_BY_NAME["question"])
    assert sf.fragment["cta"]["engagement_sentence"] == "Une question corrigée ?"


def test_fix_enjeu_survives_a_later_choose(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    run.choose(_full(), steps_dir, "question", ["a"], {})
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    run.choose(_full(), steps_dir, "enjeu", ["c"], {})
    run.fix(_full(), steps_dir, "display.root_issue", "Un **enjeu** corrigé.")
    run.choose(_full(), steps_dir, "enjeu", ["c"], {})
    sf, _ = load(steps_dir, STEP_BY_NAME["enjeu"])
    assert sf.fragment["display"]["root_issue"] == "Un **enjeu** corrigé."
    assert next(o for o in sf.options if o.id == "c").edited


def test_fix_idees_reaches_the_option_of_its_position(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir)
    run.fix(_full(), steps_dir, "display.essentiel[1]", "Une **idée** corrigée.")
    sf, _ = load(steps_dir, STEP_BY_NAME["idees"])
    assert next(o for o in sf.options if o.id == "2a").fields["text"] == "Une **idée** corrigée."


# ── 5. The headline/why_selected word overlap is advisory ────────────────────

def test_headline_overlap_is_advisory(tmp_path):
    from tools.check_deck import check
    src = Path("samples/articles/article_15/article/instagram_carousel_optimized/extract.json")
    doc = json.loads(src.read_text(encoding="utf-8"))
    doc["presentation"]["display"]["selection_headline"] = "Les **girafes** du désert"
    deck = tmp_path / "a" / "fmt" / "extract.json"
    deck.parent.mkdir(parents=True)
    deck.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    report = check(deck)
    hits = [(fam, p) for fam, ps in report.items() for p in ps if "absent from why_selected" in p]
    assert hits and all("advisory" in fam for fam, _ in hits)
