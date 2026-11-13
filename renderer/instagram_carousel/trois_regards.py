"""Renderer for the TROIS REGARDS carousel: seven slides, in the optimized deck's visual
language, screenshotted by `renderer.shoot`. Slides 1 and 7 are the optimized deck's own
hook and sign-off (photo included); slide 2 is the `temps_long` position slide, drawn as
it is; slides 3–5 (one prism each) and 6 (the matrix) are the
`article_carousel_trois_regards_v1` templates. Registered as the `trois_regards` format."""
import json
from pathlib import Path

from agent.trois_regards_prisms import PRISMS
from models.trois_regards_presentation import TroisRegardsDocument
from .cadrage import _nobreak
from ._shared import (
    _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL, background_image, cover_dims, cover_layers,
    cover_thumb, duration_label, hook_metrics, medium_labels, pill_parts,
)

TPL = "article_carousel_trois_regards_v1"
OPT = "article_carousel_optimized_v0"
POSITION = "article_carousel_temps_long_v1/02_position.html"
POSITION_KICKER = "Ce que dit l'article"
POSITION_ICONS = ("book", "link", "eye", "widen")   # one fixed icon per card, in order
MEDIA_BADGE = "Le regard du média"


def _relance(question: str) -> str:
    """The sign-off's « Commentez — … » line: the deck's closing question, lowercased to follow the dash."""
    return question[:1].lower() + question[1:]


def _prism(pid: str) -> dict:
    p = PRISMS.get(pid)
    return {"name": p.name if p else pid, "icon": p.icon_svg if p else ""}


def generate_html(doc: TroisRegardsDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta, pres = doc.analysis.article_metadata, doc.presentation
    # out_dir is <base>/<format>/html — the photo and capture sit in <base>
    base = Path(out_dir).resolve().parent.parent
    background = background_image(base, or_cover=True)
    # the pill names the medium, the source and the date: the length is left out of this deck
    length = duration_label(meta, short=True)
    hook = {"pill": [part for part in pill_parts(meta) if part != length], "sub_topic": pres.hook.title, "subtitle": pres.hook.promise,
            "headline": pres.hook.title, "background": background, "thumb": cover_thumb(base),
            **hook_metrics(cover_dims(base), pres.hook.title), **cover_layers(meta, pres.hook.title)}
    media = pres.axe.media if pres.axe else ""
    question = pres.axe.question if pres.axe else ""
    position = {"kicker": pres.position.kicker or POSITION_KICKER, "title": pres.position.title, "lead": pres.position.lead,
                "cards": [{"label": c.label, "text": c.text, "icon": POSITION_ICONS[i % len(POSITION_ICONS)]}
                          for i, c in enumerate(pres.position.cards)]}
    # only the media's prism carries a media_note (a hard rule of the adapt agent): it draws the badge
    prisms = [("prisme", f"{TPL}/02_prisme.html",
               _nobreak({"question": s.question, "lines": s.lines, "sources": s.sources,
                         "media_note": s.media_note, "badge": MEDIA_BADGE}) | {"prism": _prism(s.prism)})
              for s in pres.prisms]
    columns = [_nobreak({"variable": c.variable, "indicator": c.indicator}) | _prism(c.prism) | {"media": bool(media) and c.prism == media}
               for c in pres.matrix.columns]
    specs = [
        ("hook", f"{OPT}/01_hook.html", hook),
        ("position", POSITION, _nobreak(position)),
        *prisms,
        ("matrice", f"{TPL}/03_matrice.html",
         _nobreak({"title": pres.matrix.title, "lead": question, "badge": MEDIA_BADGE}) | {"columns": columns}),
        ("cta", f"{OPT}/10_cta.html", {**cover_layers(meta, pres.hook.title), "background": background,
                                       "L": medium_labels(meta.medium)
                                       | ({"cta_comment": _relance(pres.axe.closing)} if pres.axe and pres.axe.closing else {})}),
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
    doc = TroisRegardsDocument.model_validate(json.loads(Path(json_path).read_text(encoding="utf-8")))
    return generate_html(doc, out_dir)


def render_from_json(json_path: Path, out_dir: Path, pdf: bool = False) -> list[Path]:
    """Generate HTML then screenshot it, into out_dir/html and out_dir/slides.
    `pdf` is accepted for a uniform renderer interface but unused."""
    from renderer.shoot import shoot_dir
    out_dir = Path(out_dir)
    generate_html_from_json(json_path, out_dir / "html")
    return shoot_dir(out_dir / "html", out_dir / "slides")
