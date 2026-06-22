"""Extractor for the 9-slide long Instagram carousel format."""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselDocument, InstagramCarouselPresentation
from extractors._base import (
    filter_distill_refs,
    rebuild_proven_by,
    remap_seeds,
    score_nodes,
    select,
    select_with_must,
)

CAPS = {
    "distill": 3,
    "observations": 3,
    "claims": 2,
    "biases": 2,
    "watch_out": 4,
    "who_is_speaking": 1,
    "contexts": 2,
    "important_facts": 1,
    "ia": 2,
    "blind_spots": 2,
    "title_analysis": 1,
    "emotional_register": 3,
    "go_further": 3,
    "cta_questions": 2,
}


def extract(full: ArticleFullAnalysis, presentation: InstagramCarouselPresentation) -> InstagramCarouselDocument:
    """Select the top-scored analysis nodes and trim the presentation layer to match."""
    scores = score_nodes(full)

    def node_score(item) -> float:
        return scores.get(getattr(item, "id", ""), 0.0)

    fond = full.analysis.fond
    forme = full.analysis.forme

    # ── Distill ───────────────────────────────────────────────────────────────
    sel_distill = full.distill.points[: CAPS["distill"]] if full.distill else []

    # ── Observations ──────────────────────────────────────────────────────────
    sel_obs, _ = select(
        fond.observations, CAPS["observations"], lambda i: node_score(fond.observations[i])
    )

    # ── Propagate scores to seeds sources ─────────────────────────────────────
    seed_scores: dict[str, dict[int, float]] = {}
    for item in list(sel_obs) + list(forme.emotional_register) + list(forme.cui_bono):
        if not hasattr(item, "seeds"):
            continue
        s = node_score(item)
        src, idx = item.seeds.source, item.seeds.index
        seed_scores.setdefault(src, {})[idx] = seed_scores.get(src, {}).get(idx, 0.0) + s

    def src_score(source: str, idx: int) -> float:
        return seed_scores.get(source, {}).get(idx, 0.0)

    # ── Select source items ───────────────────────────────────────────────────
    must_ctx: set[int] = set()
    must_fact: set[int] = set()
    for item in list(sel_obs) + list(forme.emotional_register) + list(forme.cui_bono):
        if not hasattr(item, "seeds"):
            continue
        src, idx = item.seeds.source, item.seeds.index
        if src == "context":
            must_ctx.add(idx)
        elif src == "important_fact":
            must_fact.add(idx)

    sel_ctx, ctx_old_to_new = select_with_must(
        full.context.contexts, CAPS["contexts"], must_ctx,
        lambda i: src_score("context", i),
    )
    sel_fact, fact_old_to_new = select_with_must(
        full.context.important_facts, CAPS["important_facts"], must_fact,
        lambda i: src_score("important_fact", i),
    )
    source_remap = {
        "context": ctx_old_to_new,
        "important_fact": fact_old_to_new,
    }

    # ── Simple slices ─────────────────────────────────────────────────────────
    sel_who = full.context.who_is_speaking[: CAPS["who_is_speaking"]]
    sel_title_analysis = forme.cadrage.title_analysis[: CAPS["title_analysis"]]
    sel_ia = fond.implicit_assumptions[: CAPS["ia"]]
    sel_bs = fond.blind_spots[: CAPS["blind_spots"]]

    # ── Watch_out: top N from guide (already curated) ─────────────────────────
    guide_wo_items = full.guide.watch_out.items if full.guide else []
    sel_wo = guide_wo_items[: CAPS["watch_out"]]

    # ── Claims and biases: only those proving selected targets ────────────────
    sel_obs_aspects = {obs.aspect for obs in sel_obs}
    all_er_emotions = {er.emotion for er in forme.emotional_register}
    all_cb_beneficiaries = {cb.beneficiary for cb in forme.cui_bono}

    def proves_selected(item) -> bool:
        t, label = item.proves.type, item.proves.label
        if t == "observation":
            return label in sel_obs_aspects
        if t == "emotional_register":
            return label in all_er_emotions
        if t == "cui_bono":
            return label in all_cb_beneficiaries
        return False

    all_claims = full.annotations.facts_vs_opinions.claims_and_sources
    claims_pool = [c for c in all_claims if proves_selected(c)]
    sel_claims, _ = select(claims_pool, CAPS["claims"], lambda i: node_score(claims_pool[i]))
    claim_id_to_orig = {c.id: i for i, c in enumerate(all_claims)}
    claim_orig_to_new = {claim_id_to_orig[c.id]: new_i for new_i, c in enumerate(sel_claims)}

    all_biases = full.annotations.biases_and_focus.biases_and_rhetoric
    biases_pool = [b for b in all_biases if proves_selected(b)]
    sel_biases, _ = select(biases_pool, CAPS["biases"], lambda i: node_score(biases_pool[i]))
    bias_id_to_orig = {b.id: i for i, b in enumerate(all_biases)}
    bias_orig_to_new = {bias_id_to_orig[b.id]: new_i for new_i, b in enumerate(sel_biases)}

    # ── CTA: always include at least one blind_spot question ──────────────────
    must_cta: set[int] = set()
    for i, q in enumerate(presentation.cta.post_reading_questions):
        if q.type == "blind_spot":
            must_cta.add(i)
            break
    sel_cta_q, cta_old_to_new = select_with_must(
        presentation.cta.post_reading_questions,
        CAPS["cta_questions"],
        must_cta,
        lambda i: -i,
    )

    # ── Remap seeds + rebuild proven_by ───────────────────────────────────────
    remapped_er = [
        er.model_copy(update={"seeds": remap_seeds(er.seeds, source_remap)})
        for er in forme.emotional_register
    ][: CAPS["emotional_register"]]

    remapped_cb = [
        cb.model_copy(update={"seeds": remap_seeds(cb.seeds, source_remap)})
        for cb in forme.cui_bono
    ]
    final_obs = [
        obs.model_copy(update={
            "seeds": remap_seeds(obs.seeds, source_remap),
            "proven_by": rebuild_proven_by(obs, claim_orig_to_new, bias_orig_to_new),
        })
        for obs in sel_obs
    ]

    # ── Filter distill references to kept node IDs ────────────────────────────
    kept_ids = {
        item.id
        for item in final_obs + remapped_er + remapped_cb + sel_claims + sel_biases
        if getattr(item, "id", "")
    }
    final_distill = filter_distill_refs(sel_distill, kept_ids)

    # ── Trim go_further + remap CTA indices ───────────────────────────────────
    sel_go_raw = presentation.go_further[: CAPS["go_further"]]
    final_go = []
    for item in sel_go_raw:
        if item.cta_question_index is not None:
            item = item.model_copy(update={
                "cta_question_index": cta_old_to_new.get(item.cta_question_index)
            })
        final_go.append(item)

    # ── Assemble ──────────────────────────────────────────────────────────────
    trimmed_full = full.model_copy(update={
        "context": full.context.model_copy(update={
            "who_is_speaking": sel_who,
            "contexts": sel_ctx,
            "important_facts": sel_fact,
        }),
        "analysis": full.analysis.model_copy(update={
            "fond": fond.model_copy(update={
                "implicit_assumptions": sel_ia,
                "blind_spots": sel_bs,
                "observations": final_obs,
            }),
            "forme": forme.model_copy(update={
                "cadrage": forme.cadrage.model_copy(update={"title_analysis": sel_title_analysis}),
                "emotional_register": remapped_er,
                "cui_bono": remapped_cb,
            }),
        }),
        "annotations": full.annotations.model_copy(update={
            "facts_vs_opinions": full.annotations.facts_vs_opinions.model_copy(update={
                "claims_and_sources": sel_claims,
            }),
            "biases_and_focus": full.annotations.biases_and_focus.model_copy(update={
                "biases_and_rhetoric": sel_biases,
            }),
        }),
        "distill": full.distill.model_copy(update={"points": final_distill}) if full.distill else None,
        "guide": full.guide.model_copy(update={
            "watch_out": full.guide.watch_out.model_copy(update={"items": sel_wo}),
        }) if full.guide else None,
    })

    trimmed_presentation = presentation.model_copy(update={
        "go_further": final_go,
        "cta": presentation.cta.model_copy(update={"post_reading_questions": sel_cta_q}),
    })

    return InstagramCarouselDocument(analysis=trimmed_full, presentation=trimmed_presentation)
