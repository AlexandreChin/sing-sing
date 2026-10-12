"""Slide 7 draws one pillar per presupposé, not one semicolon-separated run."""
from renderer.instagram_carousel._shared import _env, medium_labels

TPL = "article_carousel_optimized_v0/08_socle.html"


def _render(items, target=0):
    return _env().get_template(TPL).render(
        slide_n=8, slide_total=10, progress=80, logo="", L=medium_labels("article"),
        phase="verdict", headline="Sur quoi cet argument repose-t-il ?", recap_items=items,
        target=target)


def test_each_presuppose_gets_its_own_line():
    html = _render([{"label": "Ses présupposés", "icon": "anchor",
                     "clauses": ["un coût chiffré dit l'essentiel",
                                 "un bénéfice sans indice existe",
                                 "une étude fragile représente le camp adverse"]}])
    assert html.count('<div class="pillar"') == 3
    assert "un coût chiffré dit l" in html and "une étude fragile" in html


def test_objection_points_at_the_pillar_it_targets():
    items = [{"label": "Ce qu'il tient pour acquis", "icon": "anchor", "clauses": ["a", "b", "c"]},
             {"label": "L'objection la plus solide", "icon": "shield", "clauses": ["une **objection**"]}]
    body = _render(items, target=2).split("<body>")[-1]
    assert body.count('class="pillar target"') == 1 and body.count('class="pillar dim"') == 2
    assert body.index('class="pillar dim"') < body.index('class="pillar target"')  # the second one
    assert body.count("<i></i>") == 1                                             # one arrow
    plain = _render(items).split("<body>")[-1]                                    # older decks
    assert "target" not in plain and "dim" not in plain and "<i></i>" not in plain
    assert "La thèse" not in body and 'class="head"' in body                     # thesis as the title


def test_bold_is_rendered_inside_a_clause():
    html = _render([{"label": "Ses présupposés", "icon": "anchor",
                     "clauses": ["un **coût chiffré** dit l'essentiel"]}])
    assert "<strong>coût chiffré</strong>" in html
