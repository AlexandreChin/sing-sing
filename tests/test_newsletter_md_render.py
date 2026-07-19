from renderer.newsletter.md_render import parse_source


def test_parse_source_splits_front_matter_and_body():
    md = "---\nsubject: Hello\ncategory: politique\n---\n\n# Title\n\nBody.\n"
    fm, body = parse_source(md)
    assert fm == {"subject": "Hello", "category": "politique"}
    assert body.strip().startswith("# Title")


def test_parse_source_no_front_matter_returns_empty_dict():
    md = "# Title\n\nBody.\n"
    fm, body = parse_source(md)
    assert fm == {}
    assert body == md
