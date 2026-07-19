from renderer.newsletter.md_render import parse_source, segment


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


def test_segment_splits_container_blocks():
    body = "para one\n\n::: salmon\n- forced\n:::\n\npara two\n"
    segs = segment(body)
    assert segs[0] == (None, "para one\n")
    assert segs[1] == ("salmon", "- forced")
    assert segs[-1][0] is None and "para two" in segs[-1][1]


def test_segment_no_container_is_single_chunk():
    segs = segment("just text\nmore\n")
    assert segs == [(None, "just text\nmore")]
