"""The adapt stages: axis → selection → writing, assembled into one deck."""
import json
from pathlib import Path

import pytest

from agent import instagram_carousel_adapt_agent as agent
from agent.instagram_carousel_adapt_agent import _assemble, _stage_errors, _stage_of
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselPresentation

DECK = Path("samples/articles/article_15/article/instagram_carousel_optimized/adapt.json")
ANALYSIS = Path("samples/articles/article_15/article/analysis.json")


def _split(deck: dict) -> dict[str, dict]:
    """A finished deck cut back into the three stage outputs."""
    d, cta = deck["display"], deck["cta"]
    ga = d["global_analysis"]
    axis = {"thesis_frame": d["thesis_frame"], "root_issue": d["root_issue"],
            "engagement_sentence": cta["engagement_sentence"],
            "engagement_sentence_alt": cta.get("engagement_sentence_alt", []),
            "essentiel": d["essentiel"], "headline": ga["headline"],
            "headline_alt": ga.get("headline_alt", [])}
    cand = ("moment", "quote", "quote_original", "lens_ref", "factcheck", "selected", "theme",
            "centrality", "kind", "role", "spine_ref", "axis_link", "rationale")
    copy = ("lens_question", "note", "answer", "figure", "figure_label", "figure_caption", "pictogram")
    selection = {"reading_beats": [{k: b[k] for k in cand} for b in d["reading_beats"]],
                 "core_recap": ga["core_recap"], "steel_man": d["steel_man"]}
    writing = {"beats": [{"index": i, **{k: b[k] for k in copy}}
                         for i, b in enumerate(d["reading_beats"]) if b["selected"]],
               "reperes_facts": d["reperes_facts"], "why_selected": d["why_selected"],
               "selection_headline": d["selection_headline"], "key_takeaways": d["key_takeaways"],
               "go_further": deck["go_further"], "where_to_look": cta["where_to_look"],
               "hook": {k: deck["hook"][k] for k in ("topic", "sub_topic", "subtitle", "headline", "sub_topic_alt")},
               "caption": deck["caption"]}
    return {"axis": axis, "selection": selection, "writing": writing}


@pytest.fixture
def deck() -> dict:
    return json.loads(DECK.read_text(encoding="utf-8"))


def test_assemble_rebuilds_every_rendered_field(deck):
    out = InstagramCarouselPresentation.model_validate(_assemble(_split(deck)))
    ref = InstagramCarouselPresentation.model_validate(deck)
    assert out.hook.model_dump(exclude={"context_line"}) == ref.hook.model_dump(exclude={"context_line"})
    assert out.caption == ref.caption
    assert out.go_further == ref.go_further
    assert (out.cta.engagement_sentence, out.cta.where_to_look) == (ref.cta.engagement_sentence, ref.cta.where_to_look)
    od, rd = out.display, ref.display
    for field in ("thesis_frame", "essentiel", "why_selected", "selection_headline", "reperes_facts",
                  "key_takeaways", "root_issue", "steel_man", "global_analysis"):
        assert getattr(od, field) == getattr(rd, field), field
    for ob, rb in zip(od.reading_beats, rd.reading_beats):
        if rb.selected:
            assert ob == rb
        else:  # the pool keeps its choice, not copy no stage writes for it
            assert (ob.moment, ob.quote, ob.selected) == (rb.moment, rb.quote, rb.selected)


@pytest.mark.parametrize("error, stage", [
    ("display.root_issue is empty", 1),
    ("cta.engagement_sentence is a yes/no question — …", 1),
    ("display.essentiel[1] shares no key word with slide 8 …", 1),
    ("display.global_analysis.headline is 60 characters (max 54) …", 1),
    ("display.thesis_frame.main_claim is empty (…)", 1),
    ("display.global_analysis.core_recap[0] holds 2 presupposé(s) for 3 selected beats …", 2),
    ("display.steel_man.targets is 4 — …", 2),
    ("display.reading_beats[2].quote is 22 words (max 18) …", 2),
    ("display.reading_beats[2].moment is 60 characters …", 2),
    ("display.reading_beats: 2 selected beat(s) carry spine_ref=1 …", 2),
    ("display.reading_beats must have 2–3 selected, got 4", 2),
    ("display.reading_beats[0].answer is 160 characters …", 3),
    ("display.reading_beats[0].lens_question opens like beats[1]'s …", 3),
    ("display.reading_beats[0] — neither lens_question nor answer shares a key word …", 3),
    ("display.reading_beats[0] has both a figure and a pictogram — keep one", 3),
    ("display.essentiel[0] restates the lede printed two lines above it …", 3),
    ("hook.sub_topic shares no key word with slide 8 …", 3),
    ("cta.where_to_look[0] is 70 characters …", 3),
    ("caption contains hashtag(s) …", 3),
])
def test_errors_go_to_the_stage_that_owns_the_field(error, stage):
    assert _stage_of(error) == stage


def test_axis_stage_checks_the_socle_against_slide_8(deck):
    stages = _split(deck)
    stages["axis"]["essentiel"][0] = "Un **sujet** sans rapport avec la dernière slide"
    errs = _stage_errors(1, {"axis": stages["axis"]}, None)
    assert any(e.startswith("display.essentiel[0] shares no key word") for e in errs)


def test_axis_stage_ignores_fields_written_later(deck):
    # with only the axis, the empty hook, beats and copy are not stage 1's errors
    errs = _stage_errors(1, {"axis": _split(deck)["axis"]}, None)
    assert all(_stage_of(e) == 1 for e in errs)
    assert not any(e.startswith(("hook.", "display.reading_beats", "go_further")) for e in errs)


def test_writing_stage_flags_copy_for_an_unselected_beat(deck):
    stages = _split(deck)
    unselected = next(i for i, b in enumerate(stages["selection"]["reading_beats"]) if not b["selected"])
    stages["writing"]["beats"][0]["index"] = unselected
    errs = _stage_errors(3, stages, None)
    assert any(f"index {unselected} is not a selected beat" in e for e in errs)


@pytest.fixture
def fake_calls(deck, monkeypatch):
    """Stage calls answered from the sample deck, recorded by label."""
    stages, calls = _split(deck), []

    def call(user_message, schema, validator, no_api=False, label="", system=None):
        calls.append(label)
        return json.loads(json.dumps(stages[label]))
    monkeypatch.setattr(agent, "_call_with_retry", call)
    return calls


def _full():
    return ArticleFullAnalysis.model_validate_json(ANALYSIS.read_text(encoding="utf-8"))


def test_adapt_runs_the_stages_in_order_and_caches_them(fake_calls, tmp_path, deck):
    pres = agent.adapt(_full(), steps_dir=tmp_path)
    assert fake_calls == ["axis", "selection", "writing"]
    assert pres.display.root_issue == deck["display"]["root_issue"]
    assert {p.name for p in tmp_path.glob("*.json")} == {"1_axis.json", "2_selection.json", "3_writing.json"}
    agent.adapt(_full(), steps_dir=tmp_path)
    assert fake_calls == ["axis", "selection", "writing"]  # all reused


def test_a_hand_edited_axis_reruns_only_what_follows(fake_calls, tmp_path):
    agent.adapt(_full(), steps_dir=tmp_path)
    axis_file = tmp_path / "1_axis.json"
    axis = json.loads(axis_file.read_text(encoding="utf-8"))
    axis["root_issue"] = "Un enjeu réécrit à la main"
    axis_file.write_text(json.dumps(axis, ensure_ascii=False), encoding="utf-8")
    pres = agent.adapt(_full(), steps_dir=tmp_path)
    assert fake_calls == ["axis", "selection", "writing", "selection", "writing"]
    assert pres.display.root_issue == "Un enjeu réécrit à la main"
    assert (tmp_path.glob("stale_*/2_selection.json")).__next__()


def test_changed_analysis_reruns_everything(fake_calls, tmp_path):
    agent.adapt(_full(), steps_dir=tmp_path)
    full = _full()
    full.analysis.fond.main_claim += " (révisé)"
    agent.adapt(full, steps_dir=tmp_path)
    assert fake_calls == ["axis", "selection", "writing"] * 2


def test_stop_after_axis_writes_the_axis_only(fake_calls, tmp_path):
    assert agent.adapt(_full(), steps_dir=tmp_path, stop_after="axis") is None
    assert fake_calls == ["axis"]
    assert [p.name for p in tmp_path.glob("*.json")] == ["1_axis.json"]
    agent.adapt(_full(), steps_dir=tmp_path)
    assert fake_calls == ["axis", "selection", "writing"]  # the reviewed axis is reused


def test_each_stage_sees_only_its_slice_of_the_analysis():
    full = _full()
    ctx = {n: agent._full_analysis_context(full, n) for n in (1, 2, 3)}
    for n in (1, 2, 3):
        assert '"fond"' in ctx[n]
        assert '"review"' not in ctx[n] and '"guide"' not in ctx[n] and '"deontology"' not in ctx[n]
    assert '"key_quotes"' in ctx[2] and '"key_quotes"' not in ctx[1]
    assert '"contexts"' in ctx[1] and '"contexts"' in ctx[3]
