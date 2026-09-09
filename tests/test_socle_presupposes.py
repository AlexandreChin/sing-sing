"""Slide 8 renders one presupposé per line, not one semicolon-separated run."""
from renderer.instagram_carousel._shared import _env, medium_labels

TPL = "article_carousel_optimized_v0/08_socle.html"


def _render(items):
    return _env().get_template(TPL).render(
        slide_n=8, slide_total=10, progress=80, logo="", L=medium_labels("article"),
        phase="verdict", headline="Sur quoi cet argument repose-t-il ?", recap_items=items)


def test_each_presuppose_gets_its_own_line():
    html = _render([{"label": "Ses présupposés", "icon": "anchor",
                     "clauses": ["un coût chiffré dit l'essentiel",
                                 "un bénéfice sans indice existe",
                                 "une étude fragile représente le camp adverse"]}])
    assert html.count('class="r-item"') == 3
    assert "un coût chiffré dit l" in html and "une étude fragile" in html


def test_single_clause_item_renders_one_line():
    html = _render([{"label": "La question", "icon": "speech_bubble",
                     "clauses": ["Faut-il juger un outil sur ce qu'on sait mesurer ?"]}])
    assert html.count('class="r-item"') == 1


def test_bold_is_rendered_inside_a_clause():
    html = _render([{"label": "Ses présupposés", "icon": "anchor",
                     "clauses": ["un **coût chiffré** dit l'essentiel"]}])
    assert "<strong>coût chiffré</strong>" in html
