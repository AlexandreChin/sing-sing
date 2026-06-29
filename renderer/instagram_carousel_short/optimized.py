"""Data-driven renderer for the `article_carousel_optimized_v0` carousel.

Same InstagramCarouselDocument as the short format — only the slide selection and
templates differ. Reuses the short renderer's Jinja env, screenshot helpers, and
gauge logic. Registered as the `instagram_carousel_optimized` format.
"""
import json
import re
from pathlib import Path

from models.instagram_carousel_presentation import InstagramCarouselDocument
from .renderer import (
    _env, _LOGO_DATA_URL,
    _weighted_quality, DIM_FR, DIMENSION_WEIGHTS, TYPE_FR,
)

TPL = "article_carousel_optimized_v0"

# Which section each slide belongs to — drives the 3-step tracker highlight.
PHASE_OF = {
    "02_reperes": "avant",
    "03_verif_faits": "analyse", "04_faille_1": "analyse", "05_faille_2": "analyse",
    "06_point_fort": "analyse", "07_angles_morts": "analyse", "08_nuance": "analyse",
    "09_verdict": "verdict",
}
RECO = {
    "recommended": "Recommandé",
    "with_reservations": "À lire — avec réserves",
    "not_recommended": "À éviter",
}


def _fr_num(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def _truncate(text: str, limit: int) -> str:
    """Trim to `limit` chars on a word boundary, adding an ellipsis if cut."""
    s = (text or "").strip()
    if len(s) <= limit:
        return s
    return s[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"


def _lead_clause(text: str) -> str:
    """First positive clause of a review rationale — drop everything from the
    first sentence break or contrastive 'mais' onward, so a strength reads as a
    strength rather than a caveat."""
    s = (text or "").strip()
    for sep in (". ", " mais ", " Mais ", ", mais ", ", Mais "):
        s = s.split(sep, 1)[0]
    s = s.strip(" .,")
    return s + "." if s else ""


# ── Fact-check slide (honest framing) ─────────────────────────────────────────
# How the article frames each claim — surfaced so readers see the gap between
# "presented as a fact" and how solid the claim actually is.
PRESENTATION_FR = {
    "presented_as_established_fact": "Présenté comme un fait",
    "attributed_to_source": "Attribué à une source",
    "opinion_stated_as_fact": "Opinion énoncée comme un fait",
}
# Our *critical reading* of how solid each claim is — deliberately a reading to
# recheck, NOT a certified fact-check verdict (confidence is the model's own
# estimate, not live source verification). (label, css class)
_READING = {
    "consensual":   ("Largement admis", "consensual"),
    "true":         ("Solide",          "true"),
    "likely true":  ("Plutôt solide",   "likely_true"),
    "disputed":     ("Disputé",         "disputed"),
    "likely false": ("Fragile",         "false"),
    "false":        ("Fragile",         "false"),
    "unverifiable": ("Invérifiable",    "neutral"),
}
# Surface the most telling claims first: opinions dressed as fact, then facts
# asserted on shaky ground (lowest confidence first).
_PRES_RANK = {"opinion_stated_as_fact": 0, "presented_as_established_fact": 1, "attributed_to_source": 2}


# Minimal French keyword set for scoring a claim's relevance to the hook + verdict.
_STOP = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "en", "dans", "que",
    "qui", "pour", "sur", "au", "aux", "ce", "cette", "ces", "est", "sont", "par",
    "plus", "ne", "pas", "se", "son", "sa", "ses", "leur", "leurs", "avec", "ou",
    "mais", "comme", "dont", "il", "elle", "ils", "elles", "on", "nous", "vous",
    "être", "avoir", "fait", "entre", "selon", "cas", "leurs",
}


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zàâäéèêëïîôöùûüç]{4,}", (text or "").lower()) if w not in _STOP}


def _factcheck_items(full, focus_text: str = "", limit: int = 2) -> list[dict]:
    claims = full.annotations.facts_vs_opinions.claims_and_sources
    focus = _keywords(focus_text)
    # Rank by relevance to the hook + verdict first (keyword overlap), then by how
    # telling the claim is (opinion-as-fact, then shakiest), then original order.
    def _key(ci):
        i, c = ci
        overlap = len(_keywords(c.quote) & focus)
        return (-overlap, _PRES_RANK.get(c.presentation, 3),
                c.confidence if c.confidence is not None else 50, i)
    ranked = [c for _, c in sorted(enumerate(claims), key=_key)]
    items = []
    for c in ranked[:limit]:
        label, cls = _READING.get(c.confidence_label, ("À vérifier", "neutral"))
        quote = _truncate(c.quote, 120)
        items.append({
            "quote": quote,
            "presentation": PRESENTATION_FR.get(c.presentation, ""),
            "reading": label,
            "cls": cls,
        })
    return items


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
    # Slide 6 frames the best dimension. Only call it a strength when it actually
    # scores well (≥4); otherwise it's just the least-weak point — say so honestly.
    strength = {
        "kicker": "Ce qui tient" if top and top.score >= 4 else "Ce qui tient le mieux",
        "label": DIM_FR.get(top.dimension, top.label) if top else "",
        "body": _lead_clause(top.rationale) if top else "",
    }

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
        # Clues = pre-reading tips (what to watch for), NOT the watch_out findings
        # (those are the proof, revealed in full on slides 4–5).
        ("02_reperes", {"context": contexts[0].text if contexts else "",
                        "clues": list(disp.pre_reading)[:2]}),
        ("03_verif_faits", {"items": _factcheck_items(
            full, f"{pres.hook.headline} {verdict.summary if verdict else ''}")}),
        ("04_faille_1", {"label": w0.label if w0 else "", "body": w0.text if w0 else ""}),
        ("05_faille_2", {"label": w1.label if w1 else "", "body": w1.text if w1 else ""}),
        ("06_point_fort", strength),
        ("07_angles_morts", {"points": list(disp.blind_spots)}),
        ("08_nuance", {"points": list(disp.balance)}),
        ("09_verdict", {"gauge": main_gauge,
                        "score": _fr_num(wq["score"]) if wq else "",
                        "body": verdict.main_blind_side if verdict else "",
                        "final": RECO.get(verdict.reading_recommendation, "") if verdict else ""}),
        ("10_cta", {"cta_title": pres.cta.title}),
    ]

    env = _env()
    paths = []
    for name, ctx in specs:
        html = env.get_template(f"{TPL}/{name}.html").render(logo=_LOGO_DATA_URL, phase=PHASE_OF.get(name), **ctx)
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
