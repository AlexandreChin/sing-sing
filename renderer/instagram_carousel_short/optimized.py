"""Data-driven renderer for the `article_carousel_optimized_v0` carousel.

Same InstagramCarouselDocument as the short format — only the slide selection and
templates differ. Reuses the short renderer's Jinja env, screenshot helpers, and
gauge logic. Registered as the `instagram_carousel_optimized` format.
"""
import json
from pathlib import Path

from models.instagram_carousel_presentation import InstagramCarouselDocument
from .renderer import (
    _env, _LOGO_DATA_URL,
    _weighted_quality, DIM_FR, DIMENSION_WEIGHTS, TYPE_FR,
)

TPL = "article_carousel_optimized_v0"
RECO = {
    "recommended": "Recommandé",
    "with_reservations": "À lire — avec réserves",
    "not_recommended": "À éviter",
}


def _fr_num(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def _verdict_body(summary: str) -> str:
    """Core explanatory clause of the verdict summary (drop the recommendation
    prefix before ' : ' and the trailing advice sentence)."""
    s = (summary or "").split(" : ", 1)[-1].split(". ", 1)[0].strip()
    return s[:1].upper() + s[1:] if s else ""


def generate_html(doc: InstagramCarouselDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    full, pres = doc.analysis, doc.presentation
    meta, disp = full.article_metadata, pres.display

    source_meta = " · ".join(x for x in [
        meta.source,
        TYPE_FR.get(meta.type) if meta.type else None,
        f"{meta.reading_time_minutes} min" if meta.reading_time_minutes else None,
    ] if x)

    watch = list(disp.watch_out)
    w0 = watch[0] if len(watch) > 0 else None
    w1 = watch[1] if len(watch) > 1 else None

    dims = full.review.dimensions if full.review else []
    top = max(dims, key=lambda d: (d.score, DIMENSION_WEIGHTS.get(d.dimension, 1.0))) if dims else None

    wq = _weighted_quality(full)
    verdict = full.review.verdict if full.review else None
    contexts = full.context.contexts[:1]

    main_gauge = (
        {"name": "Qualité de l'article", "val": wq["label"], "pos": wq["pos"], "level": wq["level"]}
        if wq else {"name": "Qualité de l'article", "val": "—", "pos": 50, "level": "mid"}
    )

    specs = [
        ("01_hook", {"article_title": meta.title, "source_meta": source_meta,
                     "headline": pres.hook.headline}),
        ("02_reperes", {"context": contexts[0].text if contexts else "",
                        "clues": [w.label for w in watch]}),
        ("03_faille_source", {"label": w0.label if w0 else "", "body": w0.text if w0 else ""}),
        ("04_faille_methode", {"label": w1.label if w1 else "", "body": w1.text if w1 else ""}),
        ("05_force_clarte", {"label": DIM_FR.get(top.dimension, top.label) if top else "",
                             "body": top.lesson if top else ""}),
        ("06_angles_morts", {"points": list(disp.blind_spots)}),
        ("07_nuance", {"points": list(disp.balance)}),
        ("08_verdict", {"gauge": main_gauge,
                        "score": _fr_num(wq["score"]) if wq else "",
                        "body": _verdict_body(verdict.summary) if verdict else "",
                        "final": RECO.get(verdict.reading_recommendation, "") if verdict else ""}),
        ("09_cta", {"cta_title": pres.cta.title}),
    ]

    env = _env()
    paths = []
    for name, ctx in specs:
        html = env.get_template(f"{TPL}/{name}.html").render(logo=_LOGO_DATA_URL, **ctx)
        path = out_dir / f"{name}.html"
        path.write_text(html, encoding="utf-8")
        paths.append(path)
        print(f"  ✓ {path.name}")
    return paths


def generate_html_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return generate_html(InstagramCarouselDocument.model_validate(data), out_dir)


def render_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    """Convenience: generate HTML then screenshot it (both steps)."""
    from renderer.shoot import shoot_dir
    generate_html_from_json(json_path, out_dir)
    return shoot_dir(out_dir)
