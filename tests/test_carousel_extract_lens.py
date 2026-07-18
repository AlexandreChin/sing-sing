import json
from pathlib import Path

from extractors.instagram_carousel import extract
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import (
    InstagramCarouselPresentation, ReadingBeat,
)

_ANALYSIS = ArticleFullAnalysis.model_validate(
    json.loads(Path("samples/outputs/article_3/analysis.json").read_text(encoding="utf-8"))
)
_PRES = InstagramCarouselPresentation.model_validate(
    json.loads(Path("samples/outputs/article_3/instagram_carousel_optimized/adapt.json").read_text(encoding="utf-8"))
)


def _pres_with_beats(beats):
    return _PRES.model_copy(update={"display": _PRES.display.model_copy(update={
        "reading_beats": beats,
    })})


def test_extract_keeps_full_beat_pool_untouched():
    # extract must NOT trim the candidate pool — cherry-picking happens later
    beats = [
        ReadingBeat(moment="A", quote="q1", lens_ref="chiffres", note="n", selected=True),
        ReadingBeat(moment="B", quote="q2", lens_ref="cadrage", note="n", selected=False),
        ReadingBeat(moment="C", quote="q3", lens_ref="sources", note="n", selected=True),
    ]
    doc = extract(_ANALYSIS, _pres_with_beats(beats))
    kept = doc.presentation.display.reading_beats
    assert [b.moment for b in kept] == ["A", "B", "C"]          # nothing dropped, order preserved
    assert [b.selected for b in kept] == [True, False, True]    # selected flags preserved
