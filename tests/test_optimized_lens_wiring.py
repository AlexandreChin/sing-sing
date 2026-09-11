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
        "essentiel": ["La thèse.", "L'appui chiffré.", "La conclusion."],
        "essentiel_summary": "L'article avance sa **thèse** et conclut.",
    })})
    return extract(full, pres)


def test_deck_follows_merged_four_act_order(tmp_path):
    # L'essentiel sits right after the hook and carries the dispute as its lede
    # (the standalone "Pourquoi cet article" slide was folded into it). 2 reading
    # beats → 2 moment slides; repères merges the lenses. Numbers come from the
    # spec's position, so the deck renumbers itself when a slide is added or
    # dropped.
    paths = opt.generate_html(_doc(), tmp_path)
    names = [p.stem for p in paths]
    assert names == [
        "01_hook", "02_essentiel", "03_reperes",
        "04_moment", "05_moment",
        "06_socle", "07_prise_de_recul", "08_cta",
    ]
    assert "08_a_emporter" not in names   # À emporter removed


def test_essentiel_slide_carries_the_summary(tmp_path):
    """Slide 2 renders the numbered `essentiel` claims, or the prose summary when
    a deck has no bullets."""
    opt.generate_html(_doc(), tmp_path)
    html = (tmp_path / "02_essentiel.html").read_text(encoding="utf-8")
    assert "essentiel de l" in html  # label; the apostrophes render escaped
    assert 'class="pts"' in html or "avance sa" in html


def test_reperes_carries_the_lenses(tmp_path):
    opt.generate_html(_doc(), tmp_path)
    html = (tmp_path / "03_reperes.html").read_text(encoding="utf-8")
    assert "Chiffres" in html and "Causalité" in html


def test_moment_slide_carries_lens_name(tmp_path):
    opt.generate_html(_doc(), tmp_path)
    html = (tmp_path / "04_moment.html").read_text(encoding="utf-8")
    assert "Chiffres" in html and "+4400 %" in html


def test_no_lentille_point_fort_or_verif_faits_slide(tmp_path):
    paths = opt.generate_html(_doc(), tmp_path)
    names = [p.stem for p in paths]
    assert "04_lentille" not in names
    assert "07_point_fort" not in names
    assert "04_verif_faits" not in names


def test_beats_repeat_slide_4s_numbered_reflexes(tmp_path):
    """Slide 4 promises N numbered réflexes; each beat carries the same number,
    the same lens name and the same question, so the reader can pair them."""
    import re
    opt.generate_html(_doc(), tmp_path)
    reperes = (tmp_path / "03_reperes.html").read_text(encoding="utf-8")
    listed = re.findall(r'<span class="rk">(\d\d)</span><span><strong>([^<]+)</strong> — ([^<]+)</span>',
                        reperes)
    assert listed, "slide 4 lists no numbered réflexe"
    for i, (number, name, question) in enumerate(listed):
        beat = (tmp_path / f"0{4 + i}_moment.html").read_text(encoding="utf-8")
        assert f"Réflexe {number}" in beat
        assert name in beat
        assert question.strip() in beat          # the same wording, not a paraphrase
