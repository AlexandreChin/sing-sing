from models.instagram_carousel_presentation import ReadingBeat


def test_reading_beat_figure_fields_default_empty():
    b = ReadingBeat(moment="m", quote="q", lens_ref="chiffres", note="n")
    assert b.figure == "" and b.figure_label == "" and b.figure_caption == ""


def test_reading_beat_accepts_figure_fields():
    b = ReadingBeat(moment="m", quote="q", lens_ref="chiffres", note="n",
                    figure="4 400 %", figure_label="de voyageurs", figure_caption="230 → 10 000")
    assert b.figure == "4 400 %"
    assert b.figure_label == "de voyageurs"
    assert b.figure_caption == "230 → 10 000"


import json
from pathlib import Path

from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import (
    InstagramCarouselPresentation, Lens, ReadingBeat, GlobalAnalysis,
)
from extractors.instagram_carousel import extract
import renderer.instagram_carousel.optimized as opt


def _doc(beats, core_recap=("Le fil : a", "À questionner : b ?")):
    full = ArticleFullAnalysis.model_validate(
        json.loads(Path("samples/outputs/article_3/analysis.json").read_text(encoding="utf-8")))
    pres = InstagramCarouselPresentation.model_validate(
        json.loads(Path("samples/outputs/article_3/instagram_carousel_optimized/adapt.json").read_text(encoding="utf-8")))
    pres = pres.model_copy(update={"display": pres.display.model_copy(update={
        "lenses": [Lens(id="chiffres", name="Chiffres", question="Rapporté à quoi ?")],
        "reading_beats": beats,
        "global_analysis": GlobalAnalysis(headline="Une méthode", core_recap=list(core_recap), note="n"),
        "essentiel": ["a", "b", "c"], "essentiel_summary": "x",
    })})
    return extract(full, pres)


def test_beat_with_figure_renders_number_slide(tmp_path):
    beats = [ReadingBeat(moment="En chiffres", quote="q", lens_ref="chiffres", note="n",
                         figure="4 400 %", figure_label="de voyageurs en 20 ans",
                         figure_caption="230 → 10 000")]
    opt.generate_html(_doc(beats), tmp_path)
    html = (tmp_path / "05_moment.html").read_text(encoding="utf-8")
    assert "num-fig" in html                 # number layout
    assert "4 400 %" in html and "de voyageurs en 20 ans" in html
    assert "230 → 10 000" in html
    assert "Au fil de la lecture" in html and "En chiffres" in html  # normal beat header


def test_chiffres_beat_without_figure_uses_standard_moment(tmp_path):
    beats = [ReadingBeat(moment="En chiffres", quote="citation", lens_ref="chiffres", note="n")]
    opt.generate_html(_doc(beats), tmp_path)
    html = (tmp_path / "05_moment.html").read_text(encoding="utf-8")
    assert "num-fig" not in html             # NOT the number layout
    assert "evidence" in html and "citation" in html  # standard evidence box
