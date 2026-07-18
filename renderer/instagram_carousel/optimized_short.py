"""Short (6-slide) variant of the `article_carousel_optimized_v0` carousel.

Same InstagramCarouselDocument, same adapt() presentation and templates as the
optimized format — only a reduced slide selection. Registered as
`instagram_carousel_optimized_short`.

Arc: Hook → Curation → Avant de lire → Décryptage (failles) → Prise de recul (radar) → CTA.
Slides are named 01–06 for output; some reuse the full deck's templates (verdict,
cta), so the spec carries (output_name, template_name, ctx) triples.
"""
import json
from pathlib import Path

from models.instagram_carousel_presentation import InstagramCarouselDocument
from renderer.categories import carousel_theme
from ._shared import _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL, TYPE_FR, cover_layers

TPL = "article_carousel_optimized_v0"

# 3-step tracker highlight, keyed by output slide name.
PHASE_OF = {"03_reperes": "avant", "04_decryptage": "analyse"}


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

    contexts = full.context.contexts[:1]

    # Le décryptage: both failles condensed to a scannable list (no evidence quotes).
    failles = [{"label": w.label, "body": w.text} for w in list(disp.watch_out)[:2]]

    specs = [
        ("01_hook", "01_hook", {"article_title": (meta.title or "").strip(),
                                "source_meta": source_meta,
                                "kicker_logo": _LOGO_TIGHT_DATA_URL,
                                "headline": pres.hook.headline, **cover_layers(meta, pres.hook.headline)}),
        ("02_selection", "02_selection", {"headline": disp.selection_headline, "items": [
            {"label": "L'intérêt", "body": disp.why_selected},
            {"label": "Ce que vous allez apprendre", "body": disp.payoff},
        ]}),
        ("03_reperes", "03_reperes", {"reperes_headline": disp.reperes_headline,
                                      "context": contexts[0].text if contexts else "",
                                      "clues": list(disp.pre_reading)[:2]}),
        ("04_decryptage", "decryptage", {"failles": failles}),
        ("05_bilan", "09_bilan", {"bilan_headline": disp.bilan_headline,
                                  "takeaways": list(disp.key_takeaways) or list(disp.distill_points)[:2],
                                  "critical": list(disp.after_reading)[:2]}),
        ("06_cta", "10_cta", {}),
    ]

    env = _env()
    theme = carousel_theme(meta.category)  # deck background tint by category ({} = default black)
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
