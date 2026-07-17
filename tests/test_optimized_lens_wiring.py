import json
from pathlib import Path

from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import (
    InstagramCarouselDocument, InstagramCarouselPresentation,
    Lens, ReadingBeat, GlobalAnalysis,
)
from extractors.instagram_carousel import extract
import renderer.instagram_carousel.optimized as opt


def _doc():
    full = ArticleFullAnalysis.model_validate(
        json.loads(Path("samples/outputs/article_3/analysis.json").read_text(encoding="utf-8")))
    pres = InstagramCarouselPresentation.model_validate(
        json.loads(Path("samples/outputs/article_3/instagram_carousel_optimized/adapt.json").read_text(encoding="utf-8")))
    pres = pres.model_copy(update={"display": pres.display.model_copy(update={
        "lenses": [
            Lens(id="chiffres", name="Chiffres sans base", question="Rapporté à quoi ?"),
            Lens(id="causalite", name="Causalité", question="Cause ou corrélation ?"),
        ],
        "reading_beats": [
            ReadingBeat(moment="Accroche", quote="+4400 %", lens_ref="chiffres", note="**pas de base**"),
            ReadingBeat(moment="Milieu", quote="donc la cause", lens_ref="causalite", note="glissement"),
        ],
        "global_analysis": GlobalAnalysis(headline="Une méthode", core_recap=["a", "b"], note="n"),
        "open_question": "Ignore-t-il ou omet-il ?",
    })})
    return extract(full, pres)


def test_deck_follows_merged_four_act_order(tmp_path):
    # 2 reading beats in the fixture → 2 moment slides; repères merges the lenses,
    # so there is no standalone lens slide.
    paths = opt.generate_html(_doc(), tmp_path)
    names = [p.stem for p in paths]
    assert names == [
        "01_hook", "02_selection", "03_reperes",
        "04_moment", "05_moment",
        "07_vue_ensemble", "08_prise_de_recul", "09_bilan", "10_cta",
    ]


def test_reperes_carries_the_lenses(tmp_path):
    opt.generate_html(_doc(), tmp_path)
    html = (tmp_path / "03_reperes.html").read_text(encoding="utf-8")
    assert "Chiffres sans base" in html and "Causalité" in html


def test_moment_slide_carries_lens_name(tmp_path):
    opt.generate_html(_doc(), tmp_path)
    html = (tmp_path / "04_moment.html").read_text(encoding="utf-8")
    assert "Chiffres sans base" in html and "+4400 %" in html


def test_no_lentille_point_fort_or_verif_faits_slide(tmp_path):
    paths = opt.generate_html(_doc(), tmp_path)
    names = [p.stem for p in paths]
    assert "04_lentille" not in names
    assert "07_point_fort" not in names
    assert "04_verif_faits" not in names
