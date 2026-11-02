"""Renderer for the ANATOMIE D'UN CHIFFRE carousel: six slides, in the optimized deck's
visual language, screenshotted by `renderer.shoot`. Slides 1 and 6 are the optimized
deck's own hook and sign-off (photo included); slides 2–5 are the
`article_carousel_anatomie_chiffre_v1` templates. Registered as the `anatomie_chiffre` format."""
import json
import re
from pathlib import Path

from models.anatomie_chiffre_presentation import AnatomieChiffreDocument
from ._shared import (
    _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL, background_image, cover_dims, cover_layers,
    cover_thumb, duration_label, hook_metrics, medium_labels, pill_parts,
)

TPL = "article_carousel_anatomie_chiffre_v1"
OPT = "article_carousel_optimized_v0"
_HYPHEN = re.compile(r"(?<=\w)-(?=\w)")


def _relance(question: str) -> str:
    """The sign-off's « Commentez — … » line: the variable's question, lowercased to follow the dash."""
    return question[:1].lower() + question[1:]


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


_RATIO = re.compile(r"^\s*[×x]\s*(\d+(?:[.,]\d+)?)\s*$")


def bar_widths(ratio_value: str) -> tuple[int, int] | None:
    """The two bars' widths (%), in the ratio the slide states (« × 15 » → 100 and 7), the
    longer one full. None when the ratio is not a plain multiple: the bars are then drawn equal
    and unfilled, so no proportion is suggested."""
    m = _RATIO.match(ratio_value or "")
    r = float(m.group(1).replace(",", ".")) if m else 0
    if r <= 0:
        return None
    return (100, max(1, round(100 / r))) if r >= 1 else (max(1, round(100 * r)), 100)


def generate_html(doc: AnatomieChiffreDocument, out_dir: Path) -> list[Path]:
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
    var = pres.variable
    if var is None:
        raise ValueError("the deck has no `variable`: slide 5 cannot be drawn")
    specs = [
        ("hook", f"{OPT}/01_hook.html", hook),
        ("boite_noire", f"{TPL}/02_boite_noire.html", _nobreak(pres.boite_noire.model_dump())),
        ("eclairage", f"{TPL}/03_eclairage.html",
         _nobreak(pres.eclairage.model_dump() | {"bars": bar_widths(pres.eclairage.ratio.value) if pres.eclairage.ratio else None})),
        ("perimetre", f"{TPL}/04_perimetre.html",
         _nobreak({"title": pres.perimetre.title,
                   "cards": [{**c.model_dump(exclude={"notes"}), "sources": notes(c.notes), "icon": icon}
                             for c, icon in ((pres.perimetre.statistique, "eye_off"), (pres.perimetre.periode, "frame"))]})),
        ("variable", f"{TPL}/05_variable.html",
         _nobreak(var.model_dump(exclude={"looks"}) | {"sources": notes(var.looks)})),
        ("cta", f"{OPT}/10_cta.html", {**cover_layers(meta, pres.hook.title), "background": background,
                                       "L": medium_labels(meta.medium) | {"cta_comment": _relance(var.question)}}),
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
    doc = AnatomieChiffreDocument.model_validate(json.loads(Path(json_path).read_text(encoding="utf-8")))
    return generate_html(doc, out_dir)


def render_from_json(json_path: Path, out_dir: Path, pdf: bool = False) -> list[Path]:
    """Generate HTML then screenshot it, into out_dir/html and out_dir/slides.
    `pdf` is accepted for a uniform renderer interface but unused."""
    from renderer.shoot import shoot_dir
    out_dir = Path(out_dir)
    generate_html_from_json(json_path, out_dir / "html")
    return shoot_dir(out_dir / "html", out_dir / "slides")
