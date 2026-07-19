import asyncio
import argparse
import pytest

from main import cmd_render
from renderer.newsletter.md_render import (
    parse_source,
    render_body_html,
    render_email_body_html,
    render_email_html,
    render_html,
    segment,
)
from renderer.newsletter.renderer import generate_markdown, render_from_markdown
from tests._newsletter_fixtures import sample_doc


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


def test_loose_list_does_not_leak_p_tags():
    html = render_body_html("### Les réflexes\n\n- un\n\n- deux\n")
    assert 'class="mk gold"' in html and "›" in html
    assert "<p>" not in html and "</p>" not in html


def test_blockquote_claim_style_under_au_fil_de_la_lecture():
    html = render_body_html("### Au fil de la lecture\n\n> some quote\n")
    assert 'class="decrypt"' in html and 'class="claim"' in html


def test_blockquote_default_openq_style_without_quote_style_entry():
    html = render_body_html("### Le contexte\n\n> some quote\n")
    assert 'class="openq"' in html
    assert 'class="claim"' not in html


def test_forced_keystone_overrides_claim_default():
    html = render_body_html(
        "### Au fil de la lecture\n\n::: keystone\n> some quote\n:::\n"
    )
    assert 'class="openq"' in html
    assert 'class="claim"' not in html


def test_paragraph_starting_with_hook_char_is_clue():
    html = render_body_html("↩ back to something\n")
    assert 'class="clue"' in html
    assert 'class="ret">↩</span>' in html


def test_italic_only_paragraph_is_subtitle():
    html = render_body_html("*italic text*\n")
    assert 'class="subtitle"' in html


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_email_body_inline_styles_no_svg(theme):
    html = render_email_body_html("### Les réflexes\n\n- un\n- deux\n", theme)
    assert "style=" in html          # inline styles present
    assert "<svg" not in html        # no SVG in email body
    assert "class=" not in html      # email body carries no class hooks


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_email_salmon_and_bold(theme):
    html = render_email_body_html(
        "### Angles morts & nuances\n\n- un **gras**\n", theme)
    assert "~" in html
    assert "<strong" in html and "font-weight:700" in html


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_email_loose_list_does_not_leak_p_tags(theme):
    html = render_email_body_html("### Les réflexes\n\n- un\n\n- deux\n", theme)
    assert "<p>" not in html and "</p>" not in html


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_email_blockquote_claim_style_under_au_fil_de_la_lecture(theme):
    html = render_email_body_html("### Au fil de la lecture\n\n> some quote\n", theme)
    assert "border-left" in html
    assert "background:" not in html


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_email_blockquote_default_boxed_style_without_quote_style_entry(theme):
    html = render_email_body_html("### Le contexte\n\n> some quote\n", theme)
    assert "background:" in html


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_email_forced_keystone_overrides_claim_default(theme):
    html = render_email_body_html(
        "### Au fil de la lecture\n\n::: keystone\n> some quote\n:::\n", theme)
    assert "background:" in html


_MD = """---
subject: Objet test
preheader: Aperçu
hook_title: On décrypte
category: politique
article_title: Le titre original
article_url: https://example.com/a
meta_line: Source · 5 min
---

Intro para.

## L'intérêt

- point un
"""


def test_render_html_wraps_body_in_chrome():
    html = render_html(_MD)
    assert "<!DOCTYPE html>" in html or "<html" in html
    assert "On décrypte" in html          # hook_title in cover
    assert "Le titre original" in html    # article ref
    assert 'class="kicker"' in html       # body rendered
    assert "point un" in html


def test_render_email_html_wraps_body_and_cta():
    html = render_email_html(_MD, "light")
    assert "Le titre original" in html
    assert "https://example.com/a" in html   # CTA link
    assert "point un" in html
    assert "<svg" not in html                 # email body has no SVG


def test_generated_markdown_has_front_matter_and_parses():
    md = generate_markdown(sample_doc(), hook_title="Le hook")
    fm, body = parse_source(md)
    assert fm["hook_title"] == "Le hook"
    assert fm["subject"]
    assert "## L'intérêt" in body


def test_render_from_markdown_writes_three_html_files(tmp_path):
    md = generate_markdown(sample_doc(), hook_title="Le hook")
    (tmp_path / "newsletter.md").write_text(md, encoding="utf-8")
    paths = render_from_markdown(tmp_path / "newsletter.md", tmp_path)
    names = {p.name for p in paths}
    assert names == {"newsletter.html", "newsletter.email.html", "newsletter.email.dark.html"}
    assert (tmp_path / "newsletter.md").read_text(encoding="utf-8") == md  # md untouched


def test_cmd_render_dispatches_on_md(tmp_path):
    md = generate_markdown(sample_doc(), hook_title="Hook")
    md_path = tmp_path / "newsletter.md"
    md_path.write_text(md, encoding="utf-8")
    args = argparse.Namespace(document=str(md_path), output_dir=str(tmp_path), format="newsletter")
    asyncio.run(cmd_render(args))
    assert (tmp_path / "newsletter.html").exists()
    assert (tmp_path / "newsletter.email.html").exists()
