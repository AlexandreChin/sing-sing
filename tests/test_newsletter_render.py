from renderer.newsletter.renderer import (
    _decryptage_ctx, _unwrap_quote, generate_markdown, generate_html, generate_email_html,
)
from models.newsletter_presentation import DecryptageItem
from tests._newsletter_fixtures import sample_doc


def test_quote_stripped_of_surrounding_guillemets():
    # The model often returns the quote already wrapped in « … »; templates wrap it
    # again, so the render layer must unwrap to avoid « « … » ».
    assert _unwrap_quote("« 27,5 % des enfants »") == "27,5 % des enfants"
    assert _unwrap_quote("  «  déjà espacé  »  ") == "déjà espacé"
    assert _unwrap_quote("sans guillemets") == "sans guillemets"


def test_render_does_not_double_wrap_wrapped_quotes():
    doc = sample_doc()
    doc.presentation.decryptage[0] = DecryptageItem(
        kind="faille", quote="« 27,5 % des enfants »",
        presentation="", reading="Lecture.",
    )
    for html in (generate_markdown(doc), generate_html(doc), generate_email_html(doc, "light")):
        assert "« « " not in html and "«&nbsp;«" not in html


def test_decryptage_ctx_preserves_order_and_shape():
    items = _decryptage_ctx(sample_doc())
    assert [i["quote"] for i in items] == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    assert all("kind" not in i and "verdict" not in i and "color" not in i for i in items)


def test_decryptage_ctx_carries_quote_prompt_reading():
    # each beat is a three-part exercise: quote → prompt (instruction) → reading (answer)
    items = _decryptage_ctx(sample_doc())
    assert all(i.get("quote") and i.get("prompt") and i.get("reading") for i in items)


def test_markdown_structure_and_order():
    md = generate_markdown(sample_doc())
    acts = ["## Pourquoi cet article", "## Avant de vous lancer",
            "## Au fil de la lecture", "## Après la lecture"]
    positions = [md.index(a) for a in acts]
    assert positions == sorted(positions), "acts out of order"
    # subsections live under "Après la lecture"
    assert md.index("## Après la lecture") < md.index("### L'architecture de l'argument")
    assert md.index("### Angles morts") < md.index("### Nuances")
    # go_further is structured (front-matter) + a body marker at its position
    assert md.index("### Nuances") < md.index("::: gofurther") < md.index("### Avant de partir")
    assert "### Pour aller plus loin" not in md  # rendered from structured data, not a md heading


def test_rich_html_has_no_grade_badge():
    html = generate_html(sample_doc())
    assert "Au fil de la lecture" in html
    # the fait/faille grade badge is gone — no more badge markup or verdict pill
    assert "⚖️ Fait" not in html
    assert 'class="badge' not in html
    assert "Vérification des faits" not in html


def test_email_both_themes():
    for theme in ("light", "dark"):
        html = generate_email_html(sample_doc(), theme)
        assert "Au fil de la lecture" in html
        assert "L'architecture de l'argument" in html
        assert "À retenir" not in html          # "À retenir" section removed
        assert "Comment le lire" in html         # réflexes now live under "Comment le lire"
        assert "À qui profite ce cadrage ?" in html
        assert "Pour aller plus loin" in html


def test_category_pill_renders_with_theme_colours():
    doc = sample_doc()
    doc.analysis.article_metadata.category = "Société"
    # rich newsletter uses the dark palette
    assert "Société" in generate_html(doc) and "#c59cf0" in generate_html(doc)
    # email pill re-resolves per theme
    assert "#7a3fc0" in generate_email_html(doc, "light")   # light text colour
    assert "#c59cf0" in generate_email_html(doc, "dark")    # dark text colour


def test_essentiel_is_titleless_lead():
    md = generate_markdown(sample_doc())
    # the summary opens the newsletter, title-less, before "## Pourquoi cet article"
    assert "### L'essentiel de l'article" not in md
    assert md.index("L'article avance sa thèse et conclut.") < md.index("## Pourquoi cet article")


def test_markdown_has_all_new_subsections():
    md = generate_markdown(sample_doc())
    for sub in ("### Le lexique", "### Comment le lire",
                "### Les enjeux de fond", "### Les objections les plus solides",
                "### Les questions à se poser", "### Avant de partir"):
        assert sub in md
    assert "### À retenir" not in md                # "À retenir" removed
    assert "### Les réflexes critiques" not in md   # merged into "Comment le lire"
    assert "### À vous de repérer" not in md   # exercises removed (redundant with beats)
    assert "tient" not in md.lower() or "ce qui tient" not in md.lower()


def test_markdown_reordered_after_reading():
    # machinery (architecture → cui bono) → judge (enjeux → objections → angles
    # morts → nuances → questions) → extend (pour aller plus loin → avant de partir).
    md = generate_markdown(sample_doc())
    order = ["### L'architecture de l'argument", "### À qui profite ce cadrage ?",
             "### Les enjeux de fond", "### Les objections les plus solides",
             "### Angles morts", "### Nuances",
             "### Les questions à se poser", "::: gofurther", "### Avant de partir"]
    positions = [md.index(s) for s in order]
    assert positions == sorted(positions), "Après la lecture subsections out of order"


def test_named_reflexes_and_source_link_render():
    md = generate_markdown(sample_doc())
    # lens-anchored critical reflex: icon + canonical name from agent/lenses.py
    assert "📊 **Chiffres** : De combien à combien ?" in md   # colon separator, under "Comment le lire"
    assert "*(réutilisable" not in md                          # reusable tag removed


def test_go_further_renders_pill_cards():
    from renderer.newsletter.renderer import generate_html, generate_email_html
    doc = sample_doc()
    for html in (generate_html(doc), generate_email_html(doc, "light")):
        assert "Pour aller plus loin" in html
        assert "étude" in html            # resource type rendered (as a pill)
        assert "https://ademe.fr" in html  # linked title
        assert "R1" in html


def test_beats_carry_lens_tag():
    md = generate_markdown(sample_doc())
    # a beat with a clue shows its lens icon + name before the clue
    assert "🔎 **Sources** :" in md   # Q2, lens_ref="sources", has a clue
    assert "📊 **Chiffres** :" in md   # Q5, lens_ref="chiffres", has a clue


def test_no_pill_for_autre():
    # "Autre" must render exactly like no category at all — pill-less.
    base = sample_doc()
    base.analysis.article_metadata.category = None
    autre = sample_doc()
    autre.analysis.article_metadata.category = "Autre"
    assert generate_html(autre) == generate_html(base)
    assert generate_email_html(autre, "dark") == generate_email_html(base, "dark")
