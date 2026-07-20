from agent.instagram_carousel_adapt_agent import _lens_layer_errors
from models.instagram_carousel_presentation import (
    CarouselDisplay, ReadingBeat, GlobalAnalysis, SteelMan,
)

_BASE = dict(
    payoff="p", framing="f", why_selected="w", selection_headline="s", ethics="e",
    pre_reading=["a", "b"], watch_out=[], strengths=[],
    distill_points=["a", "b", "c"], after_reading=["a", "b", "c"],
    blind_spots=["x"], balance=["y"],
)


def _display(**over):
    good = dict(
        # candidate pool: ≥3 beats, canonical lens_refs; default selected=True → 3 selected
        reading_beats=[
            ReadingBeat(moment="A", quote="+4400 %", lens_ref="chiffres", note="n"),
            ReadingBeat(moment="B", quote="donc la cause", lens_ref="causalite", note="n"),
            ReadingBeat(moment="C", quote="qui l'affirme", lens_ref="sources", note="n"),
        ],
        global_analysis=GlobalAnalysis(headline="Une méthode", core_recap=["a", "b"]),
        root_issue="L'enjeu est surtout symbolique : une élite qui affiche son indifférence.",
        steel_man=SteelMan(argument="Un tourisme encadré crée des ambassadeurs", alternative="le bilan net pourrait s'inverser"),
        key_takeaways=["a", "b"],
        essentiel=["La thèse de l'article.", "Son appui chiffré.", "Sa conclusion."],
        essentiel_summary="L'article avance sa thèse, l'appuie sur un chiffre, et conclut.",
    )
    good.update(over)
    return CarouselDisplay(**_BASE, **good)


def test_valid_lens_layer_has_no_errors():
    assert _lens_layer_errors(_display()) == []


def test_rejects_noncanonical_beat_lens_ref():
    errs = _lens_layer_errors(_display(reading_beats=[
        ReadingBeat(moment="A", quote="q", lens_ref="vibes", note="n"),
        ReadingBeat(moment="B", quote="q", lens_ref="causalite", note="n"),
        ReadingBeat(moment="C", quote="q", lens_ref="sources", note="n"),
    ]))
    assert any("vibes" in e for e in errs)


def test_rejects_wrong_selected_count():
    # only 1 of the 3 candidates selected → out of the 2–3 range
    errs = _lens_layer_errors(_display(reading_beats=[
        ReadingBeat(moment="A", quote="q", lens_ref="chiffres", note="n", selected=True),
        ReadingBeat(moment="B", quote="q", lens_ref="causalite", note="n", selected=False),
        ReadingBeat(moment="C", quote="q", lens_ref="sources", note="n", selected=False),
    ]))
    assert any("selected" in e for e in errs)


def test_rejects_pool_too_small():
    errs = _lens_layer_errors(_display(reading_beats=[
        ReadingBeat(moment="A", quote="q", lens_ref="chiffres", note="n"),
        ReadingBeat(moment="B", quote="q", lens_ref="causalite", note="n"),
    ]))
    assert any("reading_beats" in e for e in errs)


def test_rejects_missing_global_analysis_and_empty_root_issue():
    errs = _lens_layer_errors(_display(global_analysis=None, root_issue="  "))
    assert any("global_analysis" in e for e in errs)
    assert any("root_issue" in e for e in errs)


def test_key_takeaways_allows_two_or_three():
    d2 = _display(key_takeaways=["a", "b"])
    d3 = _display(key_takeaways=["a", "b", "c"])
    assert _lens_layer_errors(d2) == []
    assert _lens_layer_errors(d3) == []


def test_context_includes_core_elements():
    import json
    from pathlib import Path
    from agent.instagram_carousel_adapt_agent import _full_analysis_context
    from models.full_analysis import ArticleFullAnalysis, CoreElements, CoreElement
    a = ArticleFullAnalysis.model_validate(
        json.loads(Path("samples/outputs/article_3/analysis.json").read_text(encoding="utf-8")))
    a = a.model_copy(update={"core_elements": CoreElements(elements=[
        CoreElement(statement="La faune est concurrencée par les touristes", kind="enjeu", centrality=5),
        CoreElement(statement="Le bilan carbone par passager est élevé", kind="fait", centrality=4),
        CoreElement(statement="La régulation repose sur l'autorégulation", kind="enjeu", centrality=4),
    ])})
    ctx = _full_analysis_context(a)
    assert "éléments centraux" in ctx.lower()
    assert "La faune est concurrencée par les touristes" in ctx
