"""Data-driven renderer for the 4-act `article_carousel_optimized_v0` carousel.

Builds the slide list conditionally (absent sections drop out; numbering adapts)
and screenshots via `renderer.shoot`. Shared helpers come from `._shared`.
Registered as the `instagram_carousel_optimized` format.
"""
import json
from pathlib import Path

from models.instagram_carousel_presentation import InstagramCarouselDocument
from ._shared import (
    _env, _LOGO_DATA_URL,
    TYPE_FR, cover_layers,
)

TPL = "article_carousel_optimized_v0"

# Which act each output slide belongs to — drives the 3-pip tracker highlight.
# Keys stay avant/analyse/verdict (shared _tracker.html + short format); only
# the tracker's visible labels changed to the 4-act names.
# (01_hook, 02_selection, 11_cta sit outside the tracked journey.)
PHASE_OF = {
    "03_reperes": "avant",
    "04_moment": "analyse", "05_moment": "analyse", "06_moment": "analyse",
    "07_vue_ensemble": "verdict", "08_prise_de_recul": "verdict", "09_bilan": "verdict",
}

# French number words for the réflexes section label on the merged repères slide.
_COUNT_WORD = {1: "Un", 2: "Deux", 3: "Trois", 4: "Quatre"}

# Fact-check verdict → (reader label, css class) for the moment-slide pill.
_READING = {
    "consensual":   ("Largement admis", "consensual"),
    "true":         ("Solide",          "true"),
    "likely true":  ("Plutôt solide",   "likely_true"),
    "disputed":     ("Disputé",         "disputed"),
    "likely false": ("Fragile",         "false"),
    "false":        ("Fragile",         "false"),
    "unverifiable": ("Invérifiable",    "neutral"),
}


def generate_html(doc: InstagramCarouselDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    full, pres = doc.analysis, doc.presentation
    meta, disp = full.article_metadata, pres.display

    source_meta = " · ".join(x for x in [
        meta.source,
        TYPE_FR.get(meta.type) if meta.type else None,
        f"{meta.reading_time_minutes} min" if meta.reading_time_minutes else None,
    ] if x)

    d = disp
    contexts = full.context.contexts[:1]
    lens_by_id = {lens.id: lens for lens in d.lenses}

    # (output_name, template_name, ctx) triples — same pattern as the short deck.
    # Act 2 "Avant de lire" is a single merged slide: context + the lenses shown
    # as réflexes (the standalone lens slide was folded into 03_reperes).
    specs = [
        ("01_hook", "01_hook", {"article_title": (meta.title or "").strip(), "source_meta": source_meta,
                                "topic": pres.hook.topic, "sub_topic": pres.hook.sub_topic,
                                "headline": pres.hook.headline, **cover_layers(meta, pres.hook.headline)}),
        ("02_selection", "02_selection", {"headline": d.selection_headline, "items": [
            {"label": "Pourquoi on l'a retenu",
             "body": d.global_analysis.signature if d.global_analysis else d.why_selected},
            {"label": "Ce que vous allez apprendre", "body": d.payoff},
        ]}),
        ("03_reperes", "03_reperes", {
            "context": contexts[0].text if contexts else "",
            "lens_count_word": _COUNT_WORD.get(len(d.lenses), "Les"),
            "lenses": [{"name": l.name, "question": l.question} for l in d.lenses],
        }),
    ]

    for idx, b in enumerate(d.reading_beats[:3]):
        lens = lens_by_id[b.lens_ref]  # extractor guarantees lens_ref resolves
        fc = _READING.get(b.factcheck)  # fact-check pill only when the beat is a checkable fact
        specs.append((f"0{4 + idx}_moment", "moment", {
            "moment": b.moment, "quote": b.quote, "note": b.note,
            "lens_name": lens.name,
            "factcheck": {"label": fc[0], "cls": fc[1]} if fc else None,
        }))

    if d.global_analysis:
        ga = d.global_analysis
        specs.append(("07_vue_ensemble", "08_vue_ensemble",
                      {"headline": ga.headline, "solid": list(ga.solid),
                       "mechanism": list(ga.mechanism), "signature": ga.signature}))

    if d.steel_man or d.root_issue:
        specs.append(("08_prise_de_recul", "08_prise_de_recul", {
            "steel_man": {"argument": d.steel_man.argument, "alternative": d.steel_man.alternative} if d.steel_man else None,
            "root_issue": d.root_issue,
        }))

    specs.append(("09_bilan", "10_bilan", {
        "takeaways": list(d.key_takeaways),
        "reflexes": [{"name": l.name, "question": l.question} for l in d.lenses],
        "engagement": pres.cta.engagement_sentence,
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
