import json

from agent.carousel_steps.steps import STEP_BY_NAME
from agent.carousel_steps.store import (
    StepFile, load, log_choice, restamp_after, retire, retire_legacy, save, stamp_for,
)


def test_round_trip_and_stamp(tmp_path):
    s = STEP_BY_NAME["enjeu"]
    save(tmp_path, StepFile(step="enjeu", picked=["a"], fragment={"display": {"root_issue": "x"}}), "abc")
    sf, stamp = load(tmp_path, s)
    assert sf.picked == ["a"] and stamp == "abc" and (tmp_path / "2_enjeu.json").exists()
    assert load(tmp_path, STEP_BY_NAME["hook"]) == (None, "")


def test_stamp_ignores_options_but_follows_fragments():
    assert stamp_for("b", [{"x": 1}]) == stamp_for("b", [{"x": 1}]) != stamp_for("b", [{"x": 2}])


def test_retire_and_legacy(tmp_path):
    for n in ("1_axis", "2_selection", "3_writing"):
        (tmp_path / f"{n}.json").write_text("{}")
        (tmp_path / f"{n}.sha256").write_text("h")
    retire_legacy(tmp_path)
    assert sorted(p.name for p in (tmp_path / "stale_legacy").iterdir())[:1] == ["1_axis.json"]
    assert not list(tmp_path.glob("*.json"))
    save(tmp_path, StepFile(step="hook"), "deadbeef99")
    retire(tmp_path, STEP_BY_NAME["hook"], "deadbeef99")
    assert (tmp_path / "stale_deadbeef" / "7_hook.json").exists()
    assert (tmp_path / "stale_deadbeef" / "7_hook.sha256").exists()


def test_restamp_after_rewrites_later_stamps_only(tmp_path):
    for name, frag in (("question", {"a": 1}), ("enjeu", {"b": 2}), ("idees", {"c": 3})):
        save(tmp_path, StepFile(step=name, fragment=frag), "old")
    restamp_after(tmp_path, STEP_BY_NAME["question"], "base")
    assert load(tmp_path, STEP_BY_NAME["question"])[1] == "old"
    assert load(tmp_path, STEP_BY_NAME["enjeu"])[1] == stamp_for("base", [{"a": 1}])
    assert load(tmp_path, STEP_BY_NAME["idees"])[1] == stamp_for("base", [{"a": 1}, {"b": 2}])


def test_restamp_stops_at_a_gap(tmp_path):
    for name, frag in (("question", {"a": 1}), ("idees", {"c": 3})):
        save(tmp_path, StepFile(step=name, fragment=frag), "old")
    restamp_after(tmp_path, STEP_BY_NAME["question"], "base")
    assert load(tmp_path, STEP_BY_NAME["idees"])[1] == "old"


def test_log_appends_lines(tmp_path):
    log_choice(tmp_path, {"step": "enjeu", "event": "pick", "picked": ["b"]})
    log_choice(tmp_path, {"step": "enjeu", "event": "more", "remark": "plus large"})
    lines = [json.loads(l) for l in (tmp_path / "choices.jsonl").read_text().splitlines()]
    assert [l["event"] for l in lines] == ["pick", "more"] and all("ts" in l for l in lines)
