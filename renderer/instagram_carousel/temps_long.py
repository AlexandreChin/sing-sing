"""Renderer for the TEMPS LONG carousel: six slides, seven when the author's position is
written, in the optimized deck's visual language, screenshotted by `renderer.shoot`.
The first and the last are the optimized deck's own hook and sign-off (photo included);
the ones between are the `article_carousel_temps_long_v1` templates, the position
(when there is one) right after the hook. Registered as the `temps_long` format."""
import json
import re
from pathlib import Path

from models.temps_long_presentation import TempsLongDocument
from markupsafe import escape

from ._shared import (
    ICONS, _env, _LOGO_DATA_URL, _LOGO_TIGHT_DATA_URL, background_image, cover_dims, cover_layers,
    cover_thumb, duration_label, hook_metrics, medium_labels, pill_parts,
)
from .cadrage import _nobreak

TPL = "article_carousel_temps_long_v1"
OPT = "article_carousel_optimized_v0"
# the second paragraph of the promise, the same on every deck of this archetype
_HOOK_TAGLINE = "Des épisodes, des textes, trois lectures pour **en juger**."
_READING_LABELS = {"rupture": "Rupture", "continuite": "Continuité", "cycle": "Cycle",
                   "experts": "Les experts", "amnesty": "Amnesty", "tests": "Trois tests",
                   "cible": "Cible", "proportion": "Proportion", "effet": "Effet"}
# the pictograms of the readings and of the sign cards, as the inside of a 24×24 svg
_SHAPES = {'rupture': '<path d="M3 18h7V6h11"/>', 'continuite': '<path d="M3 18L21 6"/><circle cx="12" cy="12" r="1.6"/>', 'cycle': '<path d="M2 12c2.5-8 5.5-8 8 0s5.500 8 8 0 3-5 4-4"/>', 'experts': '<path d="M12 4v16M6 20h12M4 8h16"/><path d="M4 8l-2 6h4zM20 8l-2 6h4z"/>', 'amnesty': '<path d="M3 20h5v-5h5v-5h5V5"/>', 'tests': '<path d="M4 6l2 2 3-3M4 14l2 2 3-3M12 7h8M12 15h8"/>', 'cible': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>', 'proportion': '<path d="M12 4v16M6 20h12M4 8h16"/><path d="M4 8l-2 6h4zM20 8l-2 6h4z"/>', 'effet': '<path d="M2 12h5l3-7 4 14 3-7h5"/>', 'sequence': '<circle cx="4" cy="12" r="2"/><circle cx="20" cy="12" r="2"/><path d="M6 12h12"/>', 'nouveaute': '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"/>', 'delai': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>', 'memoire': '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/>'}
_POSITION_CARDS = (("ecarte", "Ce qu'il écarte", "eye_off"), ("diagnostic", "Son diagnostic", "lightbulb"),
                   ("mecanisme", "Pourquoi ça a duré, et pourquoi ça casse", "roots"), ("issue", "Sa conclusion", "widen"))


def _pictograms() -> dict[str, str]:
    """Every pictogram a template may name: the readings' own, then the deck's general icons."""
    return {**{k: v for k, v in ICONS.items() if k not in _SHAPES}, **_SHAPES}


def _tag_meta(pres) -> dict[str, dict]:
    """What a tag on a timeline shows: the icon of the criterion it names and whose criterion it is — the left-hand voice's
    (a reading's name) or the second voice's (a sign's short name): every pill is drawn the same way."""
    pic = _pictograms()
    meta = {}
    for r in pres.lecture.readings:
        name = (r.label or r.kind).strip().lower()
        meta[name] = {"icon": pic.get(r.icon) or pic.get(r.kind) or pic.get(pres.move) or pic["tests"]}
    for c in pres.lecture.aside_cards:
        meta[c.label.strip().lower()] = {"icon": pic.get(c.icon) or pic["tests"]}
    return meta


def _frise_rows(frise: dict) -> dict:
    """What the `annees` and `axe` layouts need besides the rows: the date split into month / year / range end, and the
    gap in years to the previous row (written on the spine). Years are read from the dates; a row with no year has no gap."""
    rows, prev = [], None
    for r in frise["reperes"]:
        d = r["date"].strip()
        years = re.findall(r"\b\d{4}\b", d)
        year = years[0] if years else d
        month = d[:d.find(year)].strip() if years else ""
        rest = d[d.find(year) + len(year):].strip() if years else ""
        gap = ""
        if years and prev is not None and int(year) - prev > 0:
            n = int(year) - prev
            gap = f"{n}\u00a0an{'s' if n > 1 else ''}"
        if years:
            prev = int(year)
        rows.append(r | {"year": year, "month": month, "to": rest, "gap": gap})
    return frise | {"reperes": rows}


def _highlight(text: str, label: str) -> tuple[str, bool]:
    """A sign's phrase with its name in bold gold: the word of the phrase that starts with the name (« presse » in
    « attaquer la presse », « techno » in « technologies »). Returns the phrase and whether the name was found in it."""
    m = re.search(re.escape(label.strip()) + r"\w*", text, re.IGNORECASE) if label.strip() else None
    if not m:
        return text, False
    return f"{text[:m.start()]}**{m.group(0)}**{text[m.end():]}", True


def _lecture_ctx(pres) -> dict:
    ctx = _nobreak(pres.lecture.model_dump()) | {"labels": _READING_LABELS, "move": pres.move, "SHAPES": _pictograms()}
    for c in ctx.get("aside_cards", []):
        c["hl"], c["found"] = _highlight(c["text"], c["label"])
    return ctx


def _key_html(key: str) -> str:
    """The key under a timeline: its text escaped, and a word written [[like this]] drawn as a pill, as the ones on the rows."""
    return re.sub(r"\[\[(.+?)\]\]", r'<i class="pl">\1</i>', str(escape(key)))


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
            "tagline": pres.hook.tagline or _HOOK_TAGLINE, "center_head": True, "headline": pres.hook.title, "background": background, "thumb": cover_thumb(base),
            **hook_metrics(cover_dims(base), pres.hook.title), **cover_layers(meta, pres.hook.title)}
    specs = [
        ("hook", f"{OPT}/01_hook.html", hook),
        *([("position", f"{TPL}/02_position.html",
            _nobreak({"title": pres.position.title, "lead": pres.position.lead,
                      "kicker": pres.position.kicker or "Ce que dit l'auteur",
                      "cards": [{"label": getattr(pres.position, f"{key}_label") or label, "icon": icon,
                                 "text": getattr(pres.position, key)}
                                for key, label, icon in _POSITION_CARDS if getattr(pres.position, key)]}))] if pres.position else []),
        ("episodes", f"{TPL}/02_frise.html",
         _nobreak(_frise_rows(pres.episodes.model_dump())) | {"kick": "Les épisodes récents", "icon": "flame", "detail": "Les épisodes", "key_html": _key_html(pres.episodes.key),
                                                  "tag_meta": _tag_meta(pres)}),
        ("tournants", f"{TPL}/02_frise.html",
         _nobreak(_frise_rows(pres.tournants.model_dump())) | {"kick": "Les textes de loi", "icon": "anchor", "detail": "Les textes", "key_html": _key_html(pres.tournants.key),
                                                   "tag_meta": _tag_meta(pres)}),
        ("lecture", f"{TPL}/04_lecture.html",
         _lecture_ctx(pres)),
        ("pieges", f"{TPL}/05_pieges.html", _nobreak(pres.pieges.model_dump())),
        ("cta", f"{OPT}/10_cta.html", {**cover_layers(meta, pres.hook.title), "background": background, "plain_head": True,
                                       "L": medium_labels(meta.medium) | {"cta_comment": _relance(pres.lecture.question)}}),
    ]
    if pres.order:   # the slides between the hook and the sign-off follow the deck's own order
        rank = {name: i for i, name in enumerate(pres.order)}
        specs = [specs[0], *sorted(specs[1:-1], key=lambda s: rank.get(s[0], len(rank))), specs[-1]]
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
