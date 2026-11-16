"""Renderer for the TROIS REGARDS carousel, in the optimized deck's visual language, screenshotted
by `renderer.shoot`. The first and last slides are the optimized deck's own hook and sign-off (photo
included); slide 2 is the `temps_long` position slide, drawn as it is; slides 3–5 (one prism each)
are the `article_carousel_trois_regards_v1` templates. A deck with prism `cards` draws four cards per
prism, then the tensions (slide 6) and « Les angles morts » (`limites`, slide 7): eight slides (a revision-2
deck, whose arbitrage is not read, has seven). Slides 3–7 never repeat the deck's question: each
draws its own lead (the media's prism its `media_note`), and the bird perches on the first card. An
older deck (prism `lines`, `matrix`) keeps its seven slides and its old templates.
Registered as the `trois_regards` format."""
import json
import re
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
POSITION_V4 = f"{TPL}/02_position.html"   # revision 4: the same slide, with room for three-line facts
POSITION_ICONS = ("book", "link", "eye", "widen")   # one fixed icon per card, in order
MEDIA_BADGE = "Le regard du média"
CARD_ICON = "lightbulb"                  # a prism card answers: the cause and how it acts
QUESTION_ICON = "help"                   # a revision-2 prism card ends on a question, as the anatomie blind spots
TENSIONS_KICKER, TENSIONS_ICON, TENSION_CARD_ICON = "Les tensions", "flame", "link"
LIMITES_KICKER, LIMITES_ICON = "Les angles morts", "eye_off"   # the anatomie « angles morts » slide's own icon
# revision 4: each prism card wears its role, by position, with an icon of its own
PRISM_KICKER = "Le prisme"
ROLES = (("Origine", "roots"), ("Mécanisme", "hierarchy"), ("Amplificateur", "flame"), ("Ce qu'on en voit", "eye"))


def _typeset(text: str) -> str:
    """French typography at draw time: a no-break space before « ; : ? ! » (the prompts ask for a plain
    space), so the sign never starts a line; then word joiners around in-word hyphens (`_nobreak`)."""
    return _nobreak(re.sub(r"[ \u202f\u00a0]+([;:?!])", "\u00a0\\1", text))


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
    title, promise = _typeset(pres.hook.title), _typeset(pres.hook.promise)
    hook = {"pill": [part for part in pill_parts(meta) if part != length], "sub_topic": title, "subtitle": promise,
            "headline": title, "background": background, "thumb": cover_thumb(base),
            **hook_metrics(cover_dims(base), pres.hook.title), **cover_layers(meta, pres.hook.title)}
    media = pres.axe.media if pres.axe else ""
    position = {"kicker": pres.position.kicker or POSITION_KICKER, "title": pres.position.title, "lead": pres.position.lead,
                "cards": [{"label": c.label, "text": c.text, "icon": POSITION_ICONS[i % len(POSITION_ICONS)]}
                          for i, c in enumerate(pres.position.cards)]}
    # a revision-4 deck: its tension cards carry the three regards' views
    if pres.tensions and any(c.views for c in pres.tensions.cards):
        return _write(_specs_v4(pres, meta, hook, _nobreak(position), background), meta, out_dir)
    # only the media's prism carries a media_note (a hard rule of the adapt agent): it draws the badge;
    # a prism with cards is a revision-2 slide, one with lines the older one
    prisms = [("prisme", f"{TPL}/02_prisme_cartes.html",
               _nobreak({"title": s.title, "lead": s.lead, "media_note": s.media_note, "badge": MEDIA_BADGE,
                         "cards": [c.model_dump() | {"icon": CARD_ICON if c.answer else QUESTION_ICON} for c in s.cards]})
               | {"prism": _prism(s.prism)})
              if s.cards else
              ("prisme", f"{TPL}/02_prisme.html",
               _nobreak({"question": s.question, "lines": s.lines, "sources": s.sources,
                         "media_note": s.media_note, "badge": MEDIA_BADGE}) | {"prism": _prism(s.prism)})
              for s in pres.prisms]
    # the tags name the prisms by their place in the axe (the prism slides' order when the deck has no axe)
    order = [_prism(p) for p in (pres.axe.prisms if pres.axe else [s.prism for s in pres.prisms])]
    name = lambda k: order[k - 1]["name"] if 0 < k <= len(order) else ""   # noqa: E731
    later = []
    if pres.tensions:
        later.append(("tensions", f"{TPL}/03_tensions.html", _nobreak(
            {"kicker": TENSIONS_KICKER, "kicker_icon": TENSIONS_ICON, "icon": TENSION_CARD_ICON,
             "title": pres.tensions.title, "lead": pres.tensions.lead,
             "cards": [c.model_dump() | {"tag": " × ".join(name(k) for k in c.pair)} for c in pres.tensions.cards]})))
    elif pres.matrix:
        columns = [_nobreak({"variable": c.variable, "indicator": c.indicator}) | _prism(c.prism)
                   | {"media": bool(media) and c.prism == media} for c in pres.matrix.columns]
        later.append(("matrice", f"{TPL}/03_matrice.html",
                      _nobreak({"title": pres.matrix.title, "lead": pres.axe.question if pres.axe else "",
                                "badge": MEDIA_BADGE}) | {"columns": columns}))
    # the prism icons are svg markup: added after `_nobreak`, which would put word joiners in their path data
    if pres.limites:
        later.append(("limites", f"{TPL}/04_limites.html", _nobreak(
            {"kicker": LIMITES_KICKER, "kicker_icon": LIMITES_ICON, "title": pres.limites.title, "lead": pres.limites.lead,
             "cards": [c.model_dump() | {"tag": name(k)} for k, c in enumerate(pres.limites.cards, 1)]})
            | {"icons": [p["icon"] for p in order]}))
    specs = [
        ("hook", f"{OPT}/01_hook.html", hook),
        ("position", POSITION, _nobreak(position)),
        *prisms,
        *later,
        _cta(pres, meta, background),
    ]
    return _write(specs, meta, out_dir)


def _cta(pres, meta, background) -> tuple:
    return ("cta", f"{OPT}/10_cta.html", {**cover_layers(meta, pres.hook.title), "background": background,
                                          "L": medium_labels(meta.medium)
                                          | ({"cta_comment": _relance(pres.axe.closing)} if pres.axe and pres.axe.closing else {})})


def _specs_v4(pres, meta, hook, position, background) -> list[tuple]:
    """A revision-4 deck (tension cards with `views`): hook, position, the three prism slides (kicker « Le prisme
    <nom> », role-tagged cards, no lead, no media badge, no media_note), the tensions (a topic and the three regards), sign-off — seven
    slides, no limites."""
    order = [_prism(p) for p in (pres.axe.prisms if pres.axe else [s.prism for s in pres.prisms])]
    prisms = [("prisme", f"{TPL}/02_prisme_cartes.html",
               # no media badge; the kicker reads « Le prisme économique »; the title and the lead centred (`centered`)
               _nobreak({"title": s.title, "lead": s.lead, "centered": True,
                         "cards": [c.model_dump() | {"role": ROLES[k][0], "icon": ROLES[k][1]}
                                   for k, c in enumerate(s.cards[:len(ROLES)])]})
               | {"prism": _prism(s.prism), "kicker": f"{PRISM_KICKER} {_prism(s.prism)['name'].lower()}"})
              for s in pres.prisms]
    names = [p["name"] for p in order]
    # the three regards are named once, in a header row over three columns; each card's views sit in those columns
    tensions = ("tensions", f"{TPL}/03_tensions.html", _nobreak(
        {"kicker": TENSIONS_KICKER, "kicker_icon": TENSIONS_ICON, "icon": TENSION_CARD_ICON,
         "title": pres.tensions.title, "lead": pres.tensions.lead, "centered": True,
         "cards": [c.model_dump() for c in pres.tensions.cards]})
        | {"columns": order})
    return [("hook", f"{OPT}/01_hook.html", hook), ("position", POSITION_V4, position), *prisms, tensions,
            _cta(pres, meta, background)]


def _write(specs: list[tuple], meta, out_dir: Path) -> list[Path]:
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
