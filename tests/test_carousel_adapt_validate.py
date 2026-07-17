from agent.instagram_carousel_adapt_agent import _lens_layer_errors
from models.instagram_carousel_presentation import (
    CarouselDisplay, Lens, ReadingBeat, GlobalAnalysis, SteelMan,
)

_BASE = dict(
    payoff="p", framing="f", why_selected="w", selection_headline="s", ethics="e",
    pre_reading=["a", "b"], watch_out=[], strengths=[],
    distill_points=["a", "b", "c"], after_reading=["a", "b", "c"],
    blind_spots=["x"], balance=["y"],
)


def _display(**over):
    good = dict(
        lenses=[
            Lens(id="chiffres", name="Chiffres sans base", question="Rapporté à quoi ?"),
            Lens(id="causalite", name="Causalité", question="Cause ou corrélation ?"),
        ],
        reading_beats=[
            ReadingBeat(moment="Accroche", quote="+4400 %", lens_ref="chiffres", note="pas de base"),
            ReadingBeat(moment="Milieu", quote="donc la cause", lens_ref="causalite", note="glissement"),
        ],
        global_analysis=GlobalAnalysis(headline="Une méthode", solid=["un constat réel"], mechanism=["a", "b"], signature="marque"),
        root_issue="L'enjeu est surtout symbolique : une élite qui affiche son indifférence.",
        steel_man=SteelMan(argument="Un tourisme encadré crée des ambassadeurs", alternative="le bilan net pourrait s'inverser"),
    )
    good.update(over)
    return CarouselDisplay(**_BASE, **good)


def test_valid_lens_layer_has_no_errors():
    assert _lens_layer_errors(_display()) == []


def test_rejects_noncanonical_lens_id():
    errs = _lens_layer_errors(_display(lenses=[
        Lens(id="vibes", name="Vibes", question="Bon feeling ?"),
        Lens(id="causalite", name="Causalité", question="Cause ?"),
    ]))
    assert any("vibes" in e for e in errs)


def test_rejects_beat_referencing_unselected_lens():
    errs = _lens_layer_errors(_display(reading_beats=[
        ReadingBeat(moment="A", quote="q", lens_ref="cadrage", note="n"),
        ReadingBeat(moment="B", quote="q", lens_ref="causalite", note="n"),
    ]))
    assert any("cadrage" in e for e in errs)


def test_rejects_missing_global_analysis_and_empty_root_issue():
    errs = _lens_layer_errors(_display(global_analysis=None, root_issue="  "))
    assert any("global_analysis" in e for e in errs)
    assert any("root_issue" in e for e in errs)


def test_rejects_wrong_lens_count():
    one = [Lens(id="chiffres", name="Chiffres sans base", question="?")]
    assert any("lenses" in e for e in _lens_layer_errors(_display(lenses=one)))
