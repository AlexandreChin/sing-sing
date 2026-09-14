"""Data-driven renderer for the 4-act `article_carousel_optimized_v0` carousel.

Builds the slide list conditionally (absent sections drop out; numbering adapts)
and screenshots via `renderer.shoot`. Shared helpers come from `._shared`.
Registered as the `instagram_carousel_optimized` format.
"""
import json
import sys
from pathlib import Path

from agent.lenses import CANONICAL_LENSES
from models.instagram_carousel_presentation import InstagramCarouselDocument
from ._shared import (
    _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL, inner_quotes,
    source_type_label, duration_label, cover_layers, cover_thumb, cover_dims,
    hook_metrics, medium_labels,
)

TPL = "article_carousel_optimized_v0"

# Which act each slide belongs to — drives the 3-pip tracker highlight. Keyed on
# the slide's base name, not its number: the number is assigned from the spec's
# position, so merging or dropping a slide renumbers the deck on its own.
# (hook, essentiel and cta sit outside the tracked journey.)
PHASE_OF = {
    "reperes": "avant",
    "moment": "analyse",
    "socle": "verdict", "prise_de_recul": "verdict",
}

# French number words for the réflexes section label on the merged repères slide.
_COUNT_WORD = {1: "Un", 2: "Deux", 3: "Trois", 4: "Quatre"}


def generate_html(doc: InstagramCarouselDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    full, pres = doc.analysis, doc.presentation
    meta, disp = full.article_metadata, pres.display

    # Slide 1 shows only what the source capture cannot: the article's own title
    # and chapô are inside the image, so the metadata line carries the rest.
    meta_parts = [x for x in [
        meta.source,
        meta.published_at,
        source_type_label(meta),
        duration_label(meta, short=True),
    ] if x]

    d = disp
    contexts = full.context.contexts[:1]

    # Candidate-pool cherry-picking: render the `selected` reading beats (max 3
    # moment slides), and derive the réflexe lenses (slides 3 & 9) from them via
    # the canonical vocabulary — so picking a beat updates the lenses too.
    selected_beats = [b for b in d.reading_beats if b.selected]
    if len(selected_beats) > 3:
        print(f"[optimized] {len(selected_beats)} beats selected; rendering the first 3.", file=sys.stderr)
    selected_beats = selected_beats[:3]
    # Slide 4 promises N numbered réflexes; slides 5–7 answer them in the same
    # order, under the same number and the same question. Without that pairing a
    # reader sees three unrelated lens names.
    lens_numbers: dict[str, int] = {}
    display_lenses = []
    for b in selected_beats:
        canon = CANONICAL_LENSES.get(b.lens_ref)
        if canon and b.lens_ref not in lens_numbers:
            lens_numbers[b.lens_ref] = len(display_lenses) + 1
            # The canonical question is a fallback: it is a constant, so every deck
            # using this lens would show the same line. `lens_question` specialises
            # it to this article without spoiling the moment.
            # The réflexe line is rendered raw (no md_bold filter), so strip any
            # `**…**` the model adds — it would show as literal asterisks.
            own_q = b.lens_question.strip().replace("**", "")
            display_lenses.append({"id": b.lens_ref, "name": canon["name"],
                                   "n": lens_numbers[b.lens_ref],
                                   "question": own_q or canon["question"],
                                   "icon_svg": canon.get("icon_svg", "")})

    # The capture and the headline share slide 1's vertical budget, so the
    # headline size is computed from the capture's aspect ratio (hook_metrics).
    _base = Path(out_dir).resolve().parent.parent
    hook_head = pres.hook.sub_topic or pres.hook.topic or pres.hook.headline

    # (output_name, template_name, ctx) triples — same pattern as the short deck.
    # Act 2 "Avant de lire" is a single merged slide: context + the lenses shown
    # as réflexes (the standalone lens slide was folded into 03_reperes).
    specs = [
        ("hook", "01_hook", {"meta_parts": meta_parts,
                                "topic": pres.hook.topic, "sub_topic": pres.hook.sub_topic,
                                "kicker_logo": _LOGO_TIGHT_DATA_URL,
                                # out_dir is <base>/<format>/html — the capture sits in <base>
                                "thumb": cover_thumb(_base), **hook_metrics(cover_dims(_base), hook_head),
                                "headline": pres.hook.headline, **cover_layers(meta, pres.hook.headline)}),
        # Slide 2 — L'essentiel: the 3 `essentiel` claims, numbered. The prose
        # `essentiel_summary` is the fallback for decks whose adapt produced no bullets.
        # Slide 2 — L'essentiel: the dispute (why_selected §1) as a lede, then the
        # 3 `essentiel` claims. The standalone "Pourquoi cet article" slide was
        # folded in here; §2 and `selection_headline` stay in the model for the
        # newsletter but are no longer shown.
        ("essentiel", "02_essentiel", {"essentiel": d.essentiel,
                                       "essentiel_summary": d.essentiel_summary,
                                       "lede": next((p.strip() for p in d.why_selected.split("\n")
                                                     if p.strip()), "")}),
        ("reperes", "03_reperes", {
            "reperes_headline": d.reperes_headline,
            "context": contexts[0].text if contexts else "",
            "lens_count_word": _COUNT_WORD.get(len(display_lenses), "Les"),
            "lenses": [{"n": l["n"], "name": l["name"], "question": l["question"]} for l in display_lenses],
        }),
    ]

    number_done = False
    for idx, b in enumerate(selected_beats):
        canon = CANONICAL_LENSES.get(b.lens_ref, {})
        common = {
            # The challenge line repeats slide 4's question verbatim — the reader
            # has to recognise it, so it cannot be a second phrasing of the same
            # idea (`note`, the imperative habit, is no longer rendered here).
            "lens_question": b.lens_question.strip().replace("**", "") or canon.get("question", ""),
            "answer": b.answer,  # the reveal (gold-arrow payoff)
            "lens_name": canon.get("name", b.lens_ref),
            "lens_n": lens_numbers.get(b.lens_ref, idx + 1),
            "lens_icon_svg": canon.get("icon_svg", ""),
        }
        # The template wraps the quote in « » itself — strip any the source JSON
        # carries so they don't render doubled, and turn an inner pair into “ ”.
        beat = {"moment": b.moment,
                "quote": inner_quotes(b.quote.strip().strip("«»").strip()), **common}
        if b.figure and not number_done:
            # The hero slot — at most one per deck, so the beats never all look
            # alike. A term swap sets smaller than a count and splits on its
            # arrow, which the renderer wraps (never raw HTML from the model).
            number_done = True
            figure = b.figure.strip()
            before, arrow, after = figure.partition("→")
            beat |= {
                "figure": figure, "figure_label": b.figure_label,
                "figure_caption": b.figure_caption,
                "figure_is_term": any(c.isalpha() for c in figure),
                "figure_arrow": bool(arrow),
                "figure_before": before.strip() + " ", "figure_after": " " + after.strip(),
            }
        specs.append(("moment", "moment", beat))

    if d.global_analysis:
        ga = d.global_analysis
        # Slide 8 pairs the argument's unstated supports with the reader-facing
        # question. `core_recap` carries only "Ses présupposés : body"; "La question"
        # is the engagement question, shown here (moved up from slide 9).
        recap_icons = {"Ce qu'il tient pour acquis": "anchor", "Ses présupposés": "anchor"}
        recap_items = []
        for c in ga.core_recap:
            label, sep, body = c.partition(":")
            label, body = (label.strip(), body.strip()) if sep else ("", c.strip())
            if label == "À questionner":
                continue  # legacy label — superseded by "La question" (engagement) below
            # One line per presupposé: crammed onto a single line they compress into
            # telegraphese (a "; les critiques valent Harrison" nobody can decode).
            clauses = [c.strip() for c in body.split(";") if c.strip()]
            recap_items.append({"label": label, "clauses": clauses,
                                "icon": recap_icons.get(label, "hierarchy")})
        # The objection closes the socle: it puts the assumptions just listed to the
        # test. The reader-facing question moved to the prise de recul, last.
        if d.steel_man and d.steel_man.argument.strip():
            recap_items.append({"label": "L'objection la plus solide",
                                "clauses": [d.steel_man.argument], "icon": "shield"})
        specs.append(("socle", "08_socle",
                      {"headline": ga.headline, "recap_items": recap_items}))

    # Slide 9 — Prise de recul: the deep stake + the strongest objection
    # (the closing question moved to slide 8's "La question").
    if d.root_issue or pres.cta.engagement_sentence:
        specs.append(("prise_de_recul", "08_prise_de_recul", {
            "question": pres.cta.engagement_sentence,
            "root_issue": d.root_issue,
        }))
    specs.append(("cta", "10_cta", cover_layers(meta, pres.hook.headline)))

    env = _env()
    theme = {}  # backgrounds stay black; category identity lives only in the hook pill/glyph
    paths = []
    total = len(specs)
    for i, (base, tpl_name, ctx) in enumerate(specs, 1):
        out_name = f"{i:02d}_{base}"
        html = env.get_template(f"{TPL}/{tpl_name}.html").render(
            logo=_LOGO_DATA_URL, phase=PHASE_OF.get(base), L=medium_labels(meta.medium),
            slide_n=i, slide_total=total, progress=round(i / total * 100), **theme, **ctx)
        path = out_dir / f"{out_name}.html"
        path.write_text(html, encoding="utf-8")
        paths.append(path)
        print(f"  ✓ {path.name}")
    return paths


def _warn_invalid(doc: InstagramCarouselDocument) -> None:
    """Print the adapt-time structural errors before rendering — never fail.

    `render` is run on hand-edited extracts, where the caps the adapt loop
    enforces (a quote over 24 words overflows its block) otherwise go unnoticed
    until someone looks at the slide. You still get the render: mid-edit, seeing
    the result is the point.
    """
    from agent.instagram_carousel_adapt_agent import _validate
    problems = [e for e in _validate(doc.presentation) if "go_further" not in e]
    for e in problems:
        print(f"  ⚠  {e}", file=sys.stderr)


def generate_html_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    doc = InstagramCarouselDocument.model_validate(data)
    _warn_invalid(doc)
    return generate_html(doc, out_dir)


def render_from_json(json_path: Path, out_dir: Path, pdf: bool = False) -> list[Path]:
    """Generate HTML then screenshot it, into out_dir/html and out_dir/slides.
    `pdf` is accepted for a uniform renderer interface but unused (carousels are PNG)."""
    from renderer.shoot import shoot_dir
    out_dir = Path(out_dir)
    generate_html_from_json(json_path, out_dir / "html")
    return shoot_dir(out_dir / "html", out_dir / "slides")
