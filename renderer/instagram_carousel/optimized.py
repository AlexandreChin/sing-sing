"""Data-driven renderer for the 10-slide `article_carousel_optimized_v0` carousel.

Builds the slide list conditionally (absent sections drop out; numbering adapts)
and screenshots via `renderer.shoot`. Shared helpers come from `._shared`.
Registered as the `instagram_carousel_optimized` format.
"""
import json
import re
from pathlib import Path

from models.instagram_carousel_presentation import InstagramCarouselDocument
from renderer.categories import pill, carousel_theme
from ._shared import (
    _env, _LOGO_DATA_URL,
    _weighted_quality, TYPE_FR,
)

TPL = "article_carousel_optimized_v0"

# Which section each slide belongs to — drives the 3-step tracker highlight.
# (01_hook, 02_selection and 11_cta sit outside the tracked journey.)
PHASE_OF = {
    "03_reperes": "avant",
    "04_verif_faits": "analyse", "05_faille_1": "analyse", "06_faille_2": "analyse",
    "07_point_fort": "analyse", "08_prise_de_recul": "analyse",
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


# ── Fact-check slide (honest framing) ─────────────────────────────────────────
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
            "reading": label,
            "cls": cls,
        })
    return items


def _quote_lookup(full) -> dict:
    """Map claim_N / bias_N node ids → their verbatim article quote."""
    q = {}
    for i, c in enumerate(full.annotations.facts_vs_opinions.claims_and_sources):
        q[f"claim_{i}"] = c.quote
    for i, b in enumerate(full.annotations.biases_and_focus.biases_and_rhetoric):
        q[f"bias_{i}"] = b.quote
    return q


def _faille_evidence(full, faille_text: str, qlookup: dict) -> str:
    """The article's own sentence that exhibits a faille — turns an assertion into
    proof. Match the faille to its analysis watch_out item (keyword overlap), then
    resolve that item's first claim/bias reference to its verbatim quote."""
    items = full.guide.watch_out.items if full.guide else []
    ft = _keywords(faille_text)
    if not items or not ft:
        return ""
    best = max(items, key=lambda it: len(_keywords(it.text) & ft))
    if not (_keywords(best.text) & ft):
        return ""
    for ref in best.references:
        if ref in qlookup:
            return _truncate(qlookup[ref], 160)
    return ""


def generate_html(doc: InstagramCarouselDocument, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    full, pres = doc.analysis, doc.presentation
    meta, disp = full.article_metadata, pres.display

    source_meta = " · ".join(x for x in [
        meta.source,
        TYPE_FR.get(meta.type) if meta.type else None,
        f"{meta.reading_time_minutes} min" if meta.reading_time_minutes else None,
    ] if x)

    watch = list(disp.watch_out)[:2]
    qlookup = _quote_lookup(full)

    def _faille(w):
        return {"label": w.label, "body": w.text,
                "quote": _faille_evidence(full, f"{w.label} {w.text}", qlookup)}

    dims = full.review.dimensions if full.review else []
    top_score = max((d.score for d in dims), default=0)
    # Slide 7 frames the article's best dimensions, curated by the adapt step
    # (disp.strengths — reader-facing, no rationale firehose). Only call them
    # strengths when the best one actually scores well (≥4); else say so honestly.
    strength = {
        "kicker": "Ce qui tient" if top_score >= 4 else "Ce qui tient le mieux",
        "items": [{"label": s.label, "body": s.text} for s in disp.strengths],
    }

    wq = _weighted_quality(full)
    verdict = full.review.verdict if full.review else None
    contexts = full.context.contexts[:1]

    main_gauge = (
        {"name": "Qualité de l'article", "val": wq["label"], "pos": wq["pos"], "level": wq["level"]}
        if wq else {"name": "Qualité de l'article", "val": "—", "pos": 50, "level": "mid"}
    )

    # Build the slide list conditionally: sections with no content are dropped
    # rather than rendered hollow, and dynamic numbering adapts to the result.
    specs = [
        ("01_hook", {"article_title": (meta.title or "").strip(), "source_meta": source_meta,
                     "cat_pill": pill(meta.category), "headline": pres.hook.headline}),
        # Curation beat (pillar ①) — a one-line "why we chose it" headline, then
        # two reasons in the slide-7 layout. No verdict spoiler, no topic restatement.
        ("02_selection", {"headline": disp.selection_headline, "items": [
            {"label": "Pourquoi on l'a retenu", "body": disp.why_selected},
            {"label": "Ce que vous allez apprendre", "body": disp.payoff},
        ]}),
        # Clues = pre-reading tips (what to watch for), NOT the watch_out findings
        # (those are the proof, revealed in full on the faille slides).
        ("03_reperes", {"context": contexts[0].text if contexts else "",
                        "clues": list(disp.pre_reading)[:2]}),
    ]

    fc_items = _factcheck_items(full, f"{pres.hook.headline} {verdict.summary if verdict else ''}")
    if fc_items:
        specs.append(("04_verif_faits", {"items": fc_items}))

    # One faille slide per available watch_out item (1–2). next_hook is computed
    # from what actually follows, so transitions stay correct with a single faille.
    for idx, w in enumerate(watch):
        name = "05_faille_1" if idx == 0 else "06_faille_2"
        last = idx == len(watch) - 1
        next_hook = ("Et ce qui marche ? ›" if strength["items"] else "Prendre du recul ›") \
            if last else "La faille suivante ›"
        specs.append((name, {**_faille(w), "next_hook": next_hook}))

    if strength["items"]:
        specs.append(("07_point_fort", strength))
    if disp.blind_spots or disp.balance:
        specs.append(("08_prise_de_recul",
                      {"blind_spots": list(disp.blind_spots), "balance": list(disp.balance)}))

    specs.append(("09_verdict", {"gauge": main_gauge,
                                 "score": _fr_num(wq["score"]) if wq else "",
                                 "body": verdict.main_blind_side if verdict else "",
                                 "final": RECO.get(verdict.reading_recommendation, "") if verdict else ""}))
    specs.append(("10_cta", {}))

    env = _env()
    theme = carousel_theme(meta.category)  # deck background tint by category ({} = default black)
    paths = []
    total = len(specs)
    for i, (name, ctx) in enumerate(specs, 1):
        html = env.get_template(f"{TPL}/{name}.html").render(
            logo=_LOGO_DATA_URL, phase=PHASE_OF.get(name),
            slide_n=i, slide_total=total, progress=round(i / total * 100), **theme, **ctx)
        path = out_dir / f"{name}.html"
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
