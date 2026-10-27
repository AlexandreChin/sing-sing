"""Choosing, asking for more options, fixing a field."""
import json

import pytest

from agent.carousel_steps import run
from agent.carousel_steps.steps import STEP_BY_NAME
from agent.carousel_steps.store import load
from tests._carousel_steps_fixtures import FakeCalls, full as _full, load_deck


@pytest.fixture
def fake(monkeypatch) -> FakeCalls:
    calls = FakeCalls(load_deck())
    monkeypatch.setattr(run, "_call_with_retry", calls)
    return calls


@pytest.fixture
def steps_dir(tmp_path):
    return tmp_path / "adapt_steps"


def _log(tmp_path) -> list[dict]:
    return [json.loads(line) for line in (tmp_path / "choices.jsonl").read_text().splitlines()]


def _beats(steps_dir) -> list[dict]:
    return load(steps_dir, STEP_BY_NAME["moments"])[0].fragment["display"]["reading_beats"]


def test_choose_records_pick_and_rewrite(fake, tmp_path, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    text = "Qui gagne à ce qu'une **révolte** se résume à ses casseurs ?"
    warnings = run.choose(_full(), steps_dir, "question", ["b"], {"b": text})
    sf, _ = load(steps_dir, STEP_BY_NAME["question"])
    assert sf.picked == ["b"] and next(o for o in sf.options if o.id == "b").edited
    assert sf.fragment["cta"]["engagement_sentence"].startswith("Qui gagne")
    assert isinstance(warnings, list)
    last = _log(tmp_path)[-1]
    assert last["event"] == "pick" and last["picked"] == ["b"] and last["edits"] == {"b": text}
    assert {"id", "text"} == set(last["offered"][0])


def test_rewrite_failing_a_hard_check_is_kept_with_a_warning(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    run.choose(_full(), steps_dir, "question", ["a"], {})
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    long = "La " + "très " * 40 + "longue **promesse**."
    warnings = run.choose(_full(), steps_dir, "enjeu", ["a"], {"a": long})
    assert load(steps_dir, STEP_BY_NAME["enjeu"])[0].fragment["display"]["root_issue"] == long
    assert any("root_issue is" in w and "characters" in w for w in warnings)


def _reach_idees(steps_dir):
    for name in ("question", "enjeu"):
        run.adapt(_full(), steps_dir=steps_dir, guided=True)
        run.choose(_full(), steps_dir, name, ["a"], {})
    run.adapt(_full(), steps_dir=steps_dir, guided=True)


def test_slot_rule_blocks_the_pick(fake, steps_dir):
    _reach_idees(steps_dir)
    with pytest.raises(run.ChoiceError):
        run.choose(_full(), steps_dir, "idees", ["1a", "1b", "3a"], {})
    assert load(steps_dir, STEP_BY_NAME["idees"])[0].picked == []


def test_choose_on_a_stale_step_is_refused(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    run.choose(_full(), steps_dir, "question", ["a"], {})
    run.adapt(_full(), steps_dir=steps_dir, guided=True)             # enjeu options
    run.choose(_full(), steps_dir, "question", ["b"], {})            # enjeu's stamp no longer matches
    with pytest.raises(run.ChoiceError, match="produce --guided"):
        run.choose(_full(), steps_dir, "enjeu", ["a"], {})


def test_choose_refuses_an_unchosen_earlier_step(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    with pytest.raises(run.ChoiceError, match="produce --guided"):
        run.choose(_full(), steps_dir, "enjeu", ["a"], {})


def test_more_twice_never_repeats(fake, tmp_path, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    _, stamp = load(steps_dir, STEP_BY_NAME["question"])
    run.more(_full(), steps_dir, "question", "plus large")
    sf = run.more(_full(), steps_dir, "question", "sans le mot école")
    ids = [o.id for o in sf.rejected]
    assert len(ids) == len(set(ids)) >= 6
    assert not {o.id for o in sf.options} & set(ids)
    assert sf.picked == [] and load(steps_dir, STEP_BY_NAME["question"])[1] == stamp
    assert "plus large" in fake.messages[-1] and "sans le mot école" in fake.messages[-1]
    assert "DÉJÀ PROPOSÉES ET ÉCARTÉES" in fake.messages[-1]
    assert _log(tmp_path)[-1] == {**_log(tmp_path)[-1], "event": "more", "remark": "sans le mot école"}


def test_fix_patches_the_owner_and_keeps_later_steps(fake, tmp_path, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir)
    n = len(fake.labels)
    assert run.fix(_full(), steps_dir, "cta.engagement_sentence", "Une question corrigée ?") == "question"
    run.adapt(_full(), steps_dir=steps_dir)
    assert len(fake.labels) == n                                     # nothing regenerated
    i = next(i for i, b in enumerate(_beats(steps_dir)) if b["selected"])
    assert run.fix(_full(), steps_dir, f"display.reading_beats[{i}].answer", "Une réponse.") == "writing"
    pres = run.adapt(_full(), steps_dir=steps_dir)
    assert len(fake.labels) == n
    assert pres.cta.engagement_sentence == "Une question corrigée ?"
    assert pres.display.reading_beats[i].answer == "Une réponse."
    last = _log(tmp_path)[-1]
    assert last["event"] == "fix" and last["after"] == "Une réponse."


def test_fix_on_a_bad_path_writes_nothing(fake, tmp_path, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir)
    before = {p: p.read_text() for p in steps_dir.glob("*")}
    with pytest.raises(run.ChoiceError):
        run.fix(_full(), steps_dir, "display.reading_beats[99].answer", "x")
    assert before == {p: p.read_text() for p in steps_dir.glob("*")}
    assert not (tmp_path / "choices.jsonl").exists()
