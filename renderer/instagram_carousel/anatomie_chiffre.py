"""Renderer for the ANATOMIE D'UN CHIFFRE carousel: six slides, in the optimized deck's
visual language, screenshotted by `renderer.shoot`. Slides 1 and 6 are the optimized
deck's own hook and sign-off (photo included); slides 2–5 are the
`article_carousel_anatomie_chiffre_v1` templates. Registered as the `anatomie_chiffre` format."""
import json
import re
from pathlib import Path

from models.anatomie_chiffre_presentation import AnatomieChiffreDocument, AnatomieNote
from ._shared import (
    _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL, background_image, cover_dims, cover_layers,
    cover_thumb, duration_label, hook_metrics, medium_labels, pill_parts,
)

TPL = "article_carousel_anatomie_chiffre_v1"
OPT = "article_carousel_optimized_v0"
_HYPHEN = re.compile(r"(?<=\w)-(?=\w)")
# a number stays with its unit (« +37 % », « 505.000 $ », « 75 ans »), and « × » with its number:
# the shared French spacing does not cover them, and a line must not end on « 75 » or « + 37 »
_UNIT = re.compile(r"(?<=\d) (?=%|\$|ans\b|fois\b)|(?<=×) (?=\d)")


CTA_COMMENT = "quelle lecture les séries que vous trouverez soutiennent-elles ?"


def _nobreak(value):
    """A hyphen inside a word is no line-break opportunity (« aide-t-il » must not
    end a line on « aide- »): word joiners on both sides, invisible and zero-width;
    a number is bound to its unit the same way.
    Applied to every string of a slide's context, however nested."""
    if isinstance(value, str):
        return _UNIT.sub("\u00a0", _HYPHEN.sub("⁠-⁠", value))
    if isinstance(value, list):
        return [_nobreak(v) for v in value]
    if isinstance(value, dict):
        return {k: _nobreak(v) for k, v in value.items()}
    return value


_KIND_ICONS = {"donnee": "info", "explication": "link", "interpretation": "eye", "consequence": "widen", "prevision": "widen"}
_READING_ICONS = ["lightbulb"] * 3   # an alternative is a hypothesis: one icon for the three
_KIND_LABELS = {"donnee": "Donnée", "explication": "Explication", "interpretation": "Interprétation", "consequence": "Conséquence", "prevision": "Prévision"}


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
    if pres.axe is None or len(pres.axe.readings) != 3:
        raise ValueError("the deck has no `axe` with three readings: slides 4 and 5 cannot be drawn")
    specs = [
        ("hook", f"{OPT}/01_hook.html", hook),
        ("chiffres", f"{TPL}/02_chiffres.html",
         _nobreak(pres.chiffres.model_dump(exclude={"note"}) | {"sources": notes([pres.chiffres.note] if pres.chiffres.note else [])})),
        ("recit", f"{TPL}/03_recit.html", _nobreak({"title": pres.recit.title, "labels": _KIND_LABELS, "icons": _KIND_ICONS,
                                                      "rows": [{**r.model_dump(exclude={"remark", "basis"}),
                                                                "sources": notes([AnatomieNote(kind="remark", text=r.remark)] if r.remark else [])}
                                                               for r in pres.recit.rows]})),
        ("angle_mort", f"{TPL}/04_angle_mort.html",
         _nobreak({"title": pres.angle_mort.title,
                   "cards": [{**c.model_dump(exclude={"notes", "opens", "detail"}), "sources": notes(c.notes), "icon": icon}
                             for c, icon in zip(pres.angle_mort.cards, ("help",) * 4)]})),
        ("lectures", f"{TPL}/05_lectures.html", _nobreak(pres.lectures.model_dump() | {"icons": _READING_ICONS})),
        ("cta", f"{OPT}/10_cta.html", {**cover_layers(meta, pres.hook.title), "background": background,
                                       "L": medium_labels(meta.medium) | {"cta_comment": CTA_COMMENT}}),
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
