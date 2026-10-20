import json
from pathlib import Path

from agent.instagram_carousel_light_agent import LIGHT_FORMAT, merge
from extractors.registry import FORMATS
from renderer.instagram_carousel._shared import _env

FULL = json.loads(Path("tests/fixtures/carousel_axis_adapt.json").read_text())


def test_light_format_is_registered():
    agent, extractor, renderer = FORMATS[LIGHT_FORMAT]
    assert agent.endswith("light_agent") and renderer.endswith(".light")
    assert extractor == FORMATS["instagram_carousel_optimized"][1]


def _copy():
    beats = FULL["display"]["reading_beats"]
    picked = [i for i, b in enumerate(beats) if b.get("selected", True)]
    return {
        "hook_sub_topic": "Ce que le mot « **casseurs** » cache",
        "hook_subtitle": "Comprendre ce qu'on ne voit plus.",
        "essentiel": ["Un.", "Deux.", "Trois."],
        "reperes_fact": {"label": "Le journal", "text": "The Nation : hebdomadaire progressiste."},
        "moments": [{"index": i, "moment": f"M{i}", "quote": "q", "quote_original": "o",
                     "lens_question": "Q ?", "answer": "A."} for i in picked],
        "headline": "Thèse", "presupposes": ["que a", "que b", "que c"], "objection": "Objection.",
        "root_issue": "Enjeu.", "question": "Question ?", "where_to_look": ["Acrimed"],
    }


def test_merge_keeps_the_full_decks_choices():
    out = merge(FULL, _copy())
    d, fd = out["display"], FULL["display"]
    assert [b.get("selected") for b in d["reading_beats"]] == [b.get("selected") for b in fd["reading_beats"]]
    assert [b["lens_ref"] for b in d["reading_beats"]] == [b["lens_ref"] for b in fd["reading_beats"]]
    assert d["why_selected"] == fd["why_selected"]          # the newsletter still has its lede
    assert d["reperes_facts"] == [{"label": "Le journal", "text": "The Nation : hebdomadaire progressiste."}]
    assert d["global_analysis"]["core_recap"] == ["Ce qu'il tient pour acquis : que a ; que b ; que c"]
    picked = [b for b in d["reading_beats"] if b.get("selected", True)]
    assert all(b["moment"].startswith("M") for b in picked)


def test_moment_template_moves_the_perch_to_the_question_in_light():
    tpl = _env().get_template("article_carousel_optimized_v0/moment.html")
    ctx = dict(bird="data:image/png;base64,x", lens_question="Q ?", answer="A.", quote="q",
               moment="m", slide_n=4, slide_total=9, progress=40, L={}, ICONS={})
    full, light = tpl.render(**ctx), tpl.render(light=True, **ctx)
    assert 'class="reveal" data-perch' in full and 'class="watch" data-perch' not in full
    assert 'class="watch" data-perch' in light and 'class="reveal" data-perch' not in light
