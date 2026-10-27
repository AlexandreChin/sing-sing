"""The eight adapt steps: slot rules, fragments, error routing, assembly."""
import json
from pathlib import Path

import pytest

from agent.carousel_steps.steps import STEP_BY_NAME, STEPS, Option, assemble, check_picks, default_picks, step_of, to_fragment
from models.instagram_carousel_presentation import InstagramCarouselPresentation

DECK = Path("samples/articles/article_15/article/instagram_carousel_optimized/adapt.json")


def test_steps_in_order():
    assert [s.name for s in STEPS] == ["question", "enjeu", "idees", "moments", "contexte", "socle", "hook", "writing"]


def fragments_from(deck: dict) -> dict:
    """A finished deck cut back into step fragments: one Option per displayed
    value, all picked (the unselected beats of the pool stay unpicked)."""
    d, cta, ga = deck["display"], deck["cta"], deck["display"]["global_analysis"]
    frags: dict = {"question_frame": d["thesis_frame"]}

    def run(name, opts, picked=None):
        frags[name] = to_fragment(STEP_BY_NAME[name], opts, [o.id for o in opts] if picked is None else picked, frags)

    run("question", [Option(id="a", slot="question", reason="r", fields={"text": cta["engagement_sentence"]})])
    run("enjeu", [Option(id="a", slot="enjeu", reason="r", fields={"text": d["root_issue"]})])
    run("idees", [Option(id=f"{i + 1}a", slot=str(i + 1), reason="r", fields={"text": t}) for i, t in enumerate(d["essentiel"])])
    cand = ("moment", "quote", "quote_original", "lens_ref", "factcheck", "theme", "centrality", "kind", "role", "rationale")
    moments = [Option(id=f"{b['spine_ref']}{chr(97 + i)}", slot=str(b["spine_ref"]), reason=b["axis_link"],
                      fields={k: b[k] for k in cand}) for i, b in enumerate(d["reading_beats"])]
    run("moments", moments, [o.id for o, b in zip(moments, d["reading_beats"]) if b["selected"]])
    run("contexte", [Option(id=chr(97 + i), slot="fact", reason="r", fields=f) for i, f in enumerate(d["reperes_facts"])])
    # the sample's recap is one prose line: split it back into the three présupposés
    sel = [b for b in d["reading_beats"] if b["selected"]]
    texts = ga["core_recap"][0].split(" : ", 1)[1].split(" ; ")
    socle = [Option(id="headlinea", slot="headline", reason="r", fields={"text": ga["headline"]})]
    socle += [Option(id=f"p{b['spine_ref']}a", slot=f"p{b['spine_ref']}", reason="r", fields={"text": t}) for b, t in zip(sel, texts)]
    sm = d["steel_man"]
    socle.append(Option(id="objectiona", slot="objection", reason="r", fields={
        "argument": sm["argument"], "alternative": sm["alternative"], "targets_slot": f"p{sel[sm['targets'] - 1]['spine_ref']}"}))
    run("socle", socle)
    run("hook", [Option(id="a", slot="hook", reason="r", fields={k: deck["hook"][k] for k in ("topic", "sub_topic", "subtitle", "headline")})])
    copy = ("lens_question", "note", "answer", "figure", "figure_label", "figure_caption", "pictogram")
    writing = {"beats": [{"index": i, **{k: b[k] for k in copy}} for i, b in enumerate(d["reading_beats"]) if b["selected"]],
               "why_selected": d["why_selected"], "selection_headline": d["selection_headline"],
               "key_takeaways": d["key_takeaways"], "go_further": deck["go_further"],
               "where_to_look": cta["where_to_look"], "caption": deck["caption"]}
    run("writing", [Option(id="a", slot="writing", reason="r", fields=writing)])
    return frags


def test_assemble_rebuilds_every_rendered_field():
    deck = json.loads(DECK.read_text(encoding="utf-8"))
    out = InstagramCarouselPresentation.model_validate(assemble(fragments_from(deck)))
    ref = InstagramCarouselPresentation.model_validate(deck)
    skip = {"context_line", "sub_topic_alt"}
    assert out.hook.model_dump(exclude=skip) == ref.hook.model_dump(exclude=skip)
    assert out.caption == ref.caption
    assert out.go_further == ref.go_further
    assert (out.cta.engagement_sentence, out.cta.where_to_look) == (ref.cta.engagement_sentence, ref.cta.where_to_look)
    od, rd = out.display, ref.display
    for field in ("thesis_frame", "essentiel", "why_selected", "selection_headline", "reperes_facts",
                  "key_takeaways", "root_issue", "steel_man"):
        assert getattr(od, field) == getattr(rd, field), field
    assert od.global_analysis.headline == rd.global_analysis.headline
    assert od.global_analysis.core_recap[0].split(" : ", 1)[1] == rd.global_analysis.core_recap[0].split(" : ", 1)[1]
    for ob, rb in zip(od.reading_beats, rd.reading_beats):
        if rb.selected:
            assert ob.model_dump(exclude={"axis_link"}) == rb.model_dump(exclude={"axis_link"})
        else:  # the pool keeps its choice, not copy no step writes for it
            assert (ob.moment, ob.quote, ob.selected) == (rb.moment, rb.quote, rb.selected)


def test_socle_orders_presupposes_by_the_pool_and_targets_follow():
    moments = {"display": {"reading_beats": [
        {"moment": "m", "quote": "q", "lens_ref": "source", "selected": True, "spine_ref": 3},
        {"moment": "m", "quote": "q", "lens_ref": "source", "selected": False, "spine_ref": 1},
        {"moment": "m", "quote": "q", "lens_ref": "source", "selected": True, "spine_ref": 1},
        {"moment": "m", "quote": "q", "lens_ref": "source", "selected": True, "spine_ref": 2}]}}
    opts = [Option(id="headlinea", slot="headline", reason="r", fields={"text": "Thèse"}),
            Option(id="p1a", slot="p1", reason="r", fields={"text": "un"}),
            Option(id="p2a", slot="p2", reason="r", fields={"text": "deux"}),
            Option(id="p3a", slot="p3", reason="r", fields={"text": "trois"}),
            Option(id="objectiona", slot="objection", reason="r",
                   fields={"argument": "a", "alternative": "b", "targets_slot": "p1"})]
    frag = to_fragment(STEP_BY_NAME["socle"], opts, [o.id for o in opts], {"moments": moments})
    assert frag["display"]["global_analysis"]["core_recap"] == ["Ses présupposés : trois ; un ; deux"]
    assert frag["display"]["steel_man"]["targets"] == 2


@pytest.mark.parametrize("picked, ok", [(["1a", "2a", "3a"], True), (["1a", "1b", "3a"], False), (["1a", "2a"], False)])
def test_picks_keep_one_per_slot(picked, ok):
    opts = [Option(id=i, slot=i[0], reason="r", fields={"text": i}) for i in ("1a", "1b", "2a", "3a")]
    assert (check_picks(STEP_BY_NAME["idees"], opts, picked) == []) is ok


def test_contexte_keeps_two_or_three():
    opts = [Option(id=c, slot="fact", reason="r", fields={"label": "L", "text": c}) for c in "abcde"]
    s = STEP_BY_NAME["contexte"]
    assert check_picks(s, opts, ["a"]) and not check_picks(s, opts, ["a", "b"]) and check_picks(s, opts, list("abcd"))


def test_default_picks_take_first_per_slot():
    opts = [Option(id=i, slot=i[0], reason="r", fields={"text": i}) for i in ("1a", "1b", "2a", "3a")]
    assert default_picks(STEP_BY_NAME["idees"], opts) == ["1a", "2a", "3a"]


@pytest.mark.parametrize("error, step", [
    ("display.thesis_frame.main_claim is empty (…)", "question"),
    ("cta.engagement_sentence is a yes/no question — …", "question"),
    ("cta.engagement_sentence shares no **gilded** word with display.root_issue — …", "enjeu"),
    ("display.root_issue is 140 characters …", "enjeu"),
    ("slide prise de recul has no **gilded** phrase — …", "enjeu"),
    ("display.essentiel[1] shares no key word with slide 8 …", "idees"),
    ("display.essentiel[0] restates the lede printed two lines above it …", "writing"),
    ("display.reading_beats[2].quote is 22 words (max 18) …", "moments"),
    ("display.reading_beats: 2 selected beat(s) carry spine_ref=1 …", "moments"),
    ("display.reading_beats[0].answer is 160 characters …", "writing"),
    ("display.reading_beats[0] has both a figure and a pictogram — keep one", "writing"),
    ("display.reperes_facts must have 2–3 items, got 4", "contexte"),
    ("display.global_analysis.headline is 60 characters (max 54) …", "socle"),
    ("display.steel_man.targets is 4 — …", "socle"),
    ("hook.sub_topic is 90 characters …", "hook"),
    ("cta.where_to_look[0] is 70 characters …", "writing"),
    ("caption contains hashtag(s) …", "writing"),
])
def test_errors_go_to_the_step_that_owns_the_field(error, step):
    assert step_of(error) == step


def test_assemble_leaves_the_fragments_untouched():
    import copy
    frags = fragments_from(json.loads(DECK.read_text(encoding="utf-8")))
    before = copy.deepcopy(frags)
    first = assemble(frags)
    assert frags == before
    assert assemble(frags) == first


def test_writing_without_beat_copy_keeps_the_pool():
    frags = fragments_from(json.loads(DECK.read_text(encoding="utf-8")))
    opt = Option(id="a", slot="writing", reason="r", fields={
        "beats": [], "why_selected": "", "selection_headline": "", "key_takeaways": [],
        "go_further": [], "where_to_look": [], "caption": ""})
    frags["writing"] = to_fragment(STEP_BY_NAME["writing"], [opt], ["a"], frags)
    assert len(assemble(frags)["display"]["reading_beats"]) == len(frags["moments"]["display"]["reading_beats"])


def test_picks_reject_duplicates():
    opts = [Option(id=i, slot=i[0], reason="r", fields={"text": i}) for i in ("1a", "2a", "3a")]
    assert check_picks(STEP_BY_NAME["idees"], opts, ["1a", "1a", "2a", "3a"])
