from models.instagram_carousel_presentation import (
    CarouselDisplay, Lens, ReadingBeat, GlobalAnalysis,
)

_BASE = dict(
    payoff="p", framing="f", why_selected="w", selection_headline="s", ethics="e",
    pre_reading=["a", "b"], watch_out=[], strengths=[],
    distill_points=["a", "b", "c"], after_reading=["a", "b", "c"],
    blind_spots=["x"], balance=["y"],
)


def test_new_lens_fields_default_empty_so_old_extracts_load():
    d = CarouselDisplay(**_BASE)
    assert d.lenses == []
    assert d.reading_beats == []
    assert d.global_analysis is None
    assert d.open_question == ""


def test_lens_beat_and_global_analysis_roundtrip():
    d = CarouselDisplay(
        **_BASE,
        lenses=[Lens(id="chiffres", name="Chiffres sans base", question="Rapporté à quoi ?")],
        reading_beats=[ReadingBeat(moment="L'accroche", quote="+4400 %", lens_ref="chiffres", note="pas de base")],
        global_analysis=GlobalAnalysis(headline="Une méthode", core_recap=["a", "b"], note="une remarque"),
        open_question="Ignore-t-il ou omet-il ?",
    )
    assert d.reading_beats[0].lens_ref == "chiffres"
    assert d.global_analysis.core_recap == ["a", "b"]
