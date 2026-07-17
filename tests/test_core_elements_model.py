from models.full_analysis import ArticleFullAnalysis, CoreElement, CoreElements


def test_core_element_fields_and_defaults():
    e = CoreElement(statement="Le tourisme polaire concurrence la faune", kind="enjeu", centrality=5)
    assert e.centrality == 5 and e.kind == "enjeu" and e.seeds is None


def test_core_elements_list():
    ce = CoreElements(elements=[
        CoreElement(statement="a", kind="fait", centrality=5),
        CoreElement(statement="b", kind="biais", centrality=3),
    ])
    assert len(ce.elements) == 2


def test_article_full_analysis_core_elements_defaults_none():
    # a minimal existing analysis.json still loads without core_elements
    import json
    from pathlib import Path
    d = json.loads(Path("samples/outputs/article_2/analysis.json").read_text(encoding="utf-8"))
    a = ArticleFullAnalysis.model_validate(d)
    assert a.core_elements is None or isinstance(a.core_elements, CoreElements)
