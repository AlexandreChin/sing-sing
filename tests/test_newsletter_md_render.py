from renderer.newsletter.md_render import parse_source, render_body_html, segment


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


def test_inference_salmon_list_under_angles_morts():
    html = render_body_html("### Angles morts & nuances\n\n- un\n- deux\n")
    assert 'class="mk salmon"' in html and "~" in html


def test_inference_box_list_under_a_retenir():
    html = render_body_html("### À retenir\n\n- un\n- deux\n")
    assert 'class="box"' in html and "<li>" in html


def test_default_list_is_gold_chevron():
    html = render_body_html("### Les réflexes\n\n- un\n")
    assert 'class="mk gold"' in html and "›" in html


def test_ordered_list_is_spine():
    html = render_body_html("### L'architecture de l'argument\n\n1. a\n2. b\n")
    assert 'class="spine"' in html and 'class="n"' in html


def test_forced_style_overrides_section_default():
    # Under "Les réflexes" the default is gold; ::: salmon forces salmon.
    html = render_body_html("### Les réflexes\n\n::: salmon\n- x\n:::\n")
    assert 'class="mk salmon"' in html


def test_heading_icon_attribute_sets_icon_and_strips_braces():
    html = render_body_html("## Ma nouvelle section {icon=flame}\n")
    assert "Ma nouvelle section" in html
    assert "{icon=" not in html
    assert "<svg" in html  # flame icon emitted


def test_unknown_icon_key_falls_back_without_crash():
    html = render_body_html("## Section {icon=doesnotexist}\n")
    assert "Section" in html and "{icon=" not in html


def test_bold_becomes_strong_and_divider():
    html = render_body_html("para **gras**\n\n---\n")
    assert "<strong>gras</strong>" in html
    assert 'class="divider"' in html
