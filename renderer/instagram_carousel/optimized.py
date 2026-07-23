"""Data-driven renderer for the 4-act `article_carousel_optimized_v0` carousel.

Builds the slide list conditionally (absent sections drop out; numbering adapts)
and screenshots via `renderer.shoot`. Shared helpers come from `._shared`.
Registered as the `instagram_carousel_optimized` format.
"""
import json
from pathlib import Path

from agent.lenses import CANONICAL_LENSES
from models.instagram_carousel_presentation import InstagramCarouselDocument
from ._shared import (
    _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL,
    TYPE_FR, cover_layers,
)

TPL = "article_carousel_optimized_v0"

# Which act each output slide belongs to — drives the 3-pip tracker highlight.
# Keys stay avant/analyse/verdict (shared _tracker.html + short format); only
# the tracker's visible labels changed to the 4-act names.
# (01_hook, 02_essentiel, 03_selection, 10_cta sit outside the tracked journey.)
PHASE_OF = {
    "04_reperes": "avant",
    "05_moment": "analyse", "06_moment": "analyse", "07_moment": "analyse",
    "08_socle": "verdict", "09_prise_de_recul": "verdict",
}

# French number words for the réflexes section label on the merged repères slide.
_COUNT_WORD = {1: "Un", 2: "Deux", 3: "Trois", 4: "Quatre"}


def generate_html(doc: InstagramCarouselDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    full, pres = doc.analysis, doc.presentation
    meta, disp = full.article_metadata, pres.display

    source_meta = " · ".join(x for x in [
        meta.source,
        meta.published_at,
        TYPE_FR.get(meta.type) if meta.type else None,
        f"{meta.reading_time_minutes} min" if meta.reading_time_minutes else None,
    ] if x)

    d = disp
    contexts = full.context.contexts[:1]

    # Candidate-pool cherry-picking: render the `selected` reading beats (max 3
    # moment slides), and derive the réflexe lenses (slides 3 & 9) from them via
    # the canonical vocabulary — so picking a beat updates the lenses too.
    selected_beats = [b for b in d.reading_beats if b.selected]
    if len(selected_beats) > 3:
        import sys
        print(f"[optimized] {len(selected_beats)} beats selected; rendering the first 3.", file=sys.stderr)
    selected_beats = selected_beats[:3]
    display_lenses = []
    for b in selected_beats:
        canon = CANONICAL_LENSES.get(b.lens_ref)
        if canon and b.lens_ref not in {x["id"] for x in display_lenses}:
            display_lenses.append({"id": b.lens_ref, "name": canon["name"], "question": canon["question"],
                                   "icon_svg": canon.get("icon_svg", "")})

    # (output_name, template_name, ctx) triples — same pattern as the short deck.
    # Act 2 "Avant de lire" is a single merged slide: context + the lenses shown
    # as réflexes (the standalone lens slide was folded into 03_reperes).
    specs = [
        ("01_hook", "01_hook", {"article_title": (meta.title or "").strip(), "source_meta": source_meta,
                                "topic": pres.hook.topic, "sub_topic": pres.hook.sub_topic,
                                "kicker_logo": _LOGO_TIGHT_DATA_URL,
                                "headline": pres.hook.headline, **cover_layers(meta, pres.hook.headline)}),
        # Slide 2 — L'essentiel: neutral prose summary of the article, right after the hook
        # (the 3 `essentiel` bullets are kept in the model but not rendered)
        ("02_essentiel", "02_essentiel", {"essentiel_summary": d.essentiel_summary}),
        ("03_selection", "02_selection", {"headline": d.selection_headline, "why_selected": d.why_selected}),
        ("04_reperes", "03_reperes", {
            "reperes_headline": d.reperes_headline,
            "context": contexts[0].text if contexts else "",
            "lens_count_word": _COUNT_WORD.get(len(display_lenses), "Les"),
            "lenses": [{"name": l["name"], "question": l["question"], "icon_svg": l["icon_svg"]} for l in display_lenses],
        }),
    ]

    number_done = False
    for idx, b in enumerate(selected_beats):
        canon = CANONICAL_LENSES.get(b.lens_ref, {})
        common = {
            "note": b.note,      # the challenge (lens + imperative line)
            "answer": b.answer,  # the reveal (gold-arrow payoff)
            "lens_name": canon.get("name", b.lens_ref),
            "lens_icon_svg": canon.get("icon_svg", ""),
        }
        if b.figure and not number_done:
            # #1 — number-forward slide: only when the beat carries a figure
            # (filled by the adapt agent for a figure-centric chiffres beat).
            number_done = True
            specs.append((f"0{5 + idx}_moment", "moment_number", {
                "moment": b.moment, "figure": b.figure,
                "figure_label": b.figure_label, "figure_caption": b.figure_caption,
                **common,
            }))
        else:
            specs.append((f"0{5 + idx}_moment", "moment", {
                "moment": b.moment, "quote": b.quote, **common,
            }))

    if d.global_analysis:
        ga = d.global_analysis
        # Slide 8 pairs the argument's unstated supports with the reader-facing
        # question. `core_recap` carries only "Ses présupposés : body"; "La question"
        # is the engagement question, shown here (moved up from slide 9).
        recap_icons = {"Ses présupposés": "anchor"}
        recap_items = []
        for c in ga.core_recap:
            label, sep, body = c.partition(":")
            label, body = (label.strip(), body.strip()) if sep else ("", c.strip())
            if label == "À questionner":
                continue  # legacy label — superseded by "La question" (engagement) below
            recap_items.append({"label": label, "body": body,
                                "icon": recap_icons.get(label, "hierarchy")})
        if pres.cta.engagement_sentence:
            recap_items.append({"label": "La question", "body": pres.cta.engagement_sentence,
                                "icon": "speech_bubble"})
        specs.append(("08_socle", "08_socle",
                      {"headline": ga.headline, "recap_items": recap_items}))

    # Slide 9 — Prise de recul: the deep stake + the strongest objection
    # (the closing question moved to slide 8's "La question").
    if d.steel_man or d.root_issue:
        specs.append(("09_prise_de_recul", "08_prise_de_recul", {
            "steel_man": {"argument": d.steel_man.argument, "alternative": d.steel_man.alternative} if d.steel_man else None,
            "root_issue": d.root_issue,
        }))
    specs.append(("10_cta", "10_cta", cover_layers(meta, pres.hook.headline)))

    env = _env()
    theme = {}  # backgrounds stay black; category identity lives only in the hook pill/glyph
    paths = []
    total = len(specs)
    for i, (out_name, tpl_name, ctx) in enumerate(specs, 1):
        html = env.get_template(f"{TPL}/{tpl_name}.html").render(
            logo=_LOGO_DATA_URL, phase=PHASE_OF.get(out_name),
            slide_n=i, slide_total=total, progress=round(i / total * 100), **theme, **ctx)
        path = out_dir / f"{out_name}.html"
        path.write_text(html, encoding="utf-8")
        paths.append(path)
        print(f"  ✓ {path.name}")
    return paths


def generate_html_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return generate_html(InstagramCarouselDocument.model_validate(data), out_dir)


def render_from_json(json_path: Path, out_dir: Path, pdf: bool = False) -> list[Path]:
    """Generate HTML then screenshot it, into out_dir/html and out_dir/slides.
    `pdf` is accepted for a uniform renderer interface but unused (carousels are PNG)."""
    from renderer.shoot import shoot_dir
    out_dir = Path(out_dir)
    generate_html_from_json(json_path, out_dir / "html")
    return shoot_dir(out_dir / "html", out_dir / "slides")
