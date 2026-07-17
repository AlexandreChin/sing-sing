import json
from pathlib import Path

from extractors.instagram_carousel import extract
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import (
    InstagramCarouselPresentation, Lens, ReadingBeat,
)

_ANALYSIS = ArticleFullAnalysis.model_validate(
    json.loads(Path("samples/outputs/article_3/analysis.json").read_text(encoding="utf-8"))
)
_PRES = InstagramCarouselPresentation.model_validate(
    json.loads(Path("samples/outputs/article_3/instagram_carousel_optimized/adapt.json").read_text(encoding="utf-8"))
)


def _pres_with_beats(lenses, beats):
    return _PRES.model_copy(update={"display": _PRES.display.model_copy(update={
        "lenses": lenses, "reading_beats": beats,
    })})


def test_dangling_lens_ref_beats_are_dropped_order_preserved():
    lenses = [Lens(id="chiffres", name="Chiffres sans base", question="?")]
    beats = [
        ReadingBeat(moment="A", quote="q1", lens_ref="chiffres", note="n"),
        ReadingBeat(moment="B", quote="q2", lens_ref="cadrage", note="n"),   # not selected → drop
        ReadingBeat(moment="C", quote="q3", lens_ref="chiffres", note="n"),
    ]
    doc = extract(_ANALYSIS, _pres_with_beats(lenses, beats))
    kept = doc.presentation.display.reading_beats
    assert [b.moment for b in kept] == ["A", "C"]


def test_lens_name_and_question_are_canonicalized():
    lenses = [Lens(id="chiffres", name="Les chiffres", question="wrong?")]
    doc = extract(_ANALYSIS, _pres_with_beats(lenses, []))
    lens = doc.presentation.display.lenses[0]
    assert lens.name == "Chiffres sans base"
    assert lens.question == "Ce chiffre, rapporté à quoi ?"
