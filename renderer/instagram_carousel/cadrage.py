"""Renderer for the CADRAGE & LOGIQUE carousel: seven slides, in the optimized deck's
visual language, screenshotted by `renderer.shoot`. Slides 1 and 7 are the optimized
deck's own hook and sign-off (photo included); slides 2–6 are the
`article_carousel_cadrage_v1` templates. Registered as the `cadrage_logique` format."""
import json
import re
from pathlib import Path

from models.cadrage_presentation import CadrageDocument
from ._shared import (
    _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL, background_image, cover_dims, cover_layers,
    cover_thumb, duration_label, hook_metrics, medium_labels, pill_parts,
)

TPL = "article_carousel_cadrage_v1"
OPT = "article_carousel_optimized_v0"
_HYPHEN = re.compile(r"(?<=\w)-(?=\w)")


def _nobreak(value):
    """A hyphen inside a word is no line-break opportunity (« aide-t-il » must not
    end a line on « aide- »): word joiners on both sides, invisible and zero-width.
    Applied to every string of a slide's context, however nested."""
    if isinstance(value, str):
        return _HYPHEN.sub("⁠-⁠", value)
    if isinstance(value, list):
        return [_nobreak(v) for v in value]
    if isinstance(value, dict):
        return {k: _nobreak(v) for k, v in value.items()}
    return value


def generate_html(doc: CadrageDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta, pres = doc.analysis.article_metadata, doc.presentation
    # out_dir is <base>/<format>/html — the photo and capture sit in <base>
    base = Path(out_dir).resolve().parent.parent
    background = background_image(base)
    # the pill names the medium, the source and the date: the length is left out of this deck
    length = duration_label(meta, short=True)
    hook = {"pill": [part for part in pill_parts(meta) if part != length], "sub_topic": pres.hook.title, "subtitle": pres.hook.promise,
            "headline": pres.hook.title, "background": background, "thumb": cover_thumb(base),
            **hook_metrics(cover_dims(base), pres.hook.title), **cover_layers(meta, pres.hook.title)}
    notes = lambda items: [n.model_dump() for n in items]          # noqa: E731
    specs = [
        ("hook", f"{OPT}/01_hook.html", hook),
        ("constat", f"{TPL}/02_constat.html", _nobreak(pres.constat.model_dump())),
        ("these", f"{TPL}/03_these.html",
         _nobreak(pres.these.model_dump(exclude={"notes"}) | {"sources": notes(pres.these.notes)})),
        ("angle_mort", f"{TPL}/04_angle_mort.html",
         _nobreak(pres.angle_mort.model_dump(exclude={"notes", "second_notes"})
                  | {"sources": notes(pres.angle_mort.notes), "second_sources": notes(pres.angle_mort.second_notes)})),
        ("depassement", f"{TPL}/05_depassement.html", _nobreak(pres.depassement.model_dump())),
        ("boussole", f"{TPL}/06_boussole.html", _nobreak(pres.boussole.model_dump())),
        ("cta", f"{OPT}/10_cta.html", {**cover_layers(meta, pres.hook.title), "background": background}),
    ]
    env = _env()
    paths = []
    total = len(specs)
    for i, (name, tpl, ctx) in enumerate(specs, 1):
        html = env.get_template(tpl).render(
            bird=_LOGO_TIGHT_DATA_URL, logo=_LOGO_DATA_URL, L=medium_labels(meta.medium),
            slide_n=i, slide_total=total, progress=round(i / total * 100), **ctx)
        path = out_dir / f"{i:02d}_{name}.html"
        path.write_text(html, encoding="utf-8")
        paths.append(path)
        print(f"  ✓ {path.name}")
    return paths


def generate_html_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    doc = CadrageDocument.model_validate(json.loads(Path(json_path).read_text(encoding="utf-8")))
    return generate_html(doc, out_dir)


def render_from_json(json_path: Path, out_dir: Path, pdf: bool = False) -> list[Path]:
    """Generate HTML then screenshot it, into out_dir/html and out_dir/slides.
    `pdf` is accepted for a uniform renderer interface but unused."""
    from renderer.shoot import shoot_dir
    out_dir = Path(out_dir)
    generate_html_from_json(json_path, out_dir / "html")
    return shoot_dir(out_dir / "html", out_dir / "slides")
