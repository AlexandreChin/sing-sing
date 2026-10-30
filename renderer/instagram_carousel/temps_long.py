"""Renderer for the TEMPS LONG carousel: six slides, in the optimized deck's visual
language, screenshotted by `renderer.shoot`. Slides 1 and 6 are the optimized deck's
own hook and sign-off (photo included); slides 2–5 are the
`article_carousel_temps_long_v1` templates. Registered as the `temps_long` format."""
import json
from pathlib import Path

from models.temps_long_presentation import TempsLongDocument
from ._shared import (
    _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL, background_image, cover_dims, cover_layers,
    cover_thumb, duration_label, hook_metrics, medium_labels, pill_parts,
)
from .cadrage import _nobreak

TPL = "article_carousel_temps_long_v1"
OPT = "article_carousel_optimized_v0"
_READING_LABELS = {"rupture": "Rupture", "continuite": "Continuité", "cycle": "Cycle"}


def _relance(question: str) -> str:
    """The sign-off's « Commentez — … » line: the deck's closing question, lowercased to follow the dash."""
    return question[:1].lower() + question[1:]


def generate_html(doc: TempsLongDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta, pres = doc.analysis.article_metadata, doc.presentation
    # out_dir is <base>/<format>/html — the photo and capture sit in <base>
    base = Path(out_dir).resolve().parent.parent
    background = background_image(base, or_cover=True)   # the one picture opens and closes the deck
    # the pill names the medium, the source and the date: the length is left out of this deck
    length = duration_label(meta, short=True)
    hook = {"pill": [part for part in pill_parts(meta) if part != length], "sub_topic": pres.hook.title, "subtitle": pres.hook.promise,
            "headline": pres.hook.title, "background": background, "thumb": cover_thumb(base),
            **hook_metrics(cover_dims(base), pres.hook.title), **cover_layers(meta, pres.hook.title)}
    specs = [
        ("hook", f"{OPT}/01_hook.html", hook),
        ("episodes", f"{TPL}/02_frise.html",
         _nobreak(pres.episodes.model_dump()) | {"kick": "Les épisodes qu'on retient", "icon": "flame"}),
        ("tournants", f"{TPL}/02_frise.html",
         _nobreak(pres.tournants.model_dump()) | {"kick": "Les tournants", "icon": "anchor"}),
        ("lecture", f"{TPL}/04_lecture.html",
         _nobreak(pres.lecture.model_dump()) | {"labels": _READING_LABELS}),
        ("pieges", f"{TPL}/05_pieges.html", _nobreak(pres.pieges.model_dump())),
        ("cta", f"{OPT}/10_cta.html", {**cover_layers(meta, pres.hook.title), "background": background,
                                       "L": medium_labels(meta.medium) | {"cta_comment": _relance(pres.lecture.question)}}),
    ]
    env = _env()
    paths = []
    total = len(specs)
    for i, (name, tpl, ctx) in enumerate(specs, 1):
        ctx = {"L": medium_labels(meta.medium)} | ctx
        html = env.get_template(tpl).render(
            bird=_LOGO_TIGHT_DATA_URL, logo=_LOGO_DATA_URL,
            slide_n=i, slide_total=total, progress=round(i / total * 100), **ctx)
        path = out_dir / f"{i:02d}_{name}.html"
        path.write_text(html, encoding="utf-8")
        paths.append(path)
        print(f"  ✓ {path.name}")
    return paths


def generate_html_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    doc = TempsLongDocument.model_validate(json.loads(Path(json_path).read_text(encoding="utf-8")))
    return generate_html(doc, out_dir)


def render_from_json(json_path: Path, out_dir: Path, pdf: bool = False) -> list[Path]:
    """Generate HTML then screenshot it, into out_dir/html and out_dir/slides.
    `pdf` is accepted for a uniform renderer interface but unused."""
    from renderer.shoot import shoot_dir
    out_dir = Path(out_dir)
    generate_html_from_json(json_path, out_dir / "html")
    return shoot_dir(out_dir / "html", out_dir / "slides")
