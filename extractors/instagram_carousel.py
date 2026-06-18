"""Extractor for 9-slide Instagram carousel format."""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from extractors._base import (
    filter_synthesis_refs,
    rebuild_proven_by,
    remap_seeds,
    score_nodes,
    select,
    select_with_must,
)

CAPS = {
    "synthesis": 3,
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


def extract(output: ArticleFullAnalysis) -> ArticleFullAnalysis:
    """Return a carousel-sized ArticleFullAnalysis with graph connections intact."""
    scores = score_nodes(output)

    def node_score(item) -> float:
        return scores.get(getattr(item, "id", ""), 0.0)

    fond = output.analysis_fond
    forme = output.analysis_forme

    # ── Synthesis ─────────────────────────────────────────────────────────────
    sel_synthesis = output.synthesis.points[: CAPS["synthesis"]]

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

    # ── Mandatory watch_out: seeds sources + at least 1 per category ──────────
    must_wo: set[int] = set()
    must_ctx: set[int] = set()
    must_fact: set[int] = set()
    for item in list(sel_obs) + list(forme.emotional_register) + list(forme.cui_bono):
        if not hasattr(item, "seeds"):
            continue
        src, idx = item.seeds.source, item.seeds.index
        if src == "watch_out":
            must_wo.add(idx)
        elif src == "context":
            must_ctx.add(idx)
        elif src == "important_fact":
            must_fact.add(idx)

    # Guarantee at least 1 watch_out item per category
    seen_cats: dict[str, int] = {}
    for i, item in enumerate(output.watch_out.items):
        if item.refers_to not in seen_cats:
            seen_cats[item.refers_to] = i
    for idx in seen_cats.values():
        must_wo.add(idx)

    # ── Select source items ───────────────────────────────────────────────────
    sel_wo, wo_old_to_new = select_with_must(
        output.watch_out.items, CAPS["watch_out"], must_wo,
        lambda i: src_score("watch_out", i),
    )
    sel_ctx, ctx_old_to_new = select_with_must(
        output.context.contexts, CAPS["contexts"], must_ctx,
        lambda i: src_score("context", i),
    )
    sel_fact, fact_old_to_new = select_with_must(
        output.context.important_facts, CAPS["important_facts"], must_fact,
        lambda i: src_score("important_fact", i),
    )
    source_remap = {
        "watch_out": wo_old_to_new,
        "context": ctx_old_to_new,
        "important_fact": fact_old_to_new,
    }

    # ── Simple slices ─────────────────────────────────────────────────────────
    sel_who = output.context.who_is_speaking[: CAPS["who_is_speaking"]]
    sel_title_analysis = output.cadrage.title_analysis[: CAPS["title_analysis"]]
    sel_ia = fond.implicit_assumptions[: CAPS["ia"]]
    sel_bs = fond.blind_spots[: CAPS["blind_spots"]]
    sel_go_raw = output.go_further.items[: CAPS["go_further"]]

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

    all_claims = output.facts_vs_opinions.claims_and_sources
    claims_pool = [c for c in all_claims if proves_selected(c)]
    sel_claims, _ = select(claims_pool, CAPS["claims"], lambda i: node_score(claims_pool[i]))
    claim_id_to_orig = {c.id: i for i, c in enumerate(all_claims)}
    claim_orig_to_new = {claim_id_to_orig[c.id]: new_i for new_i, c in enumerate(sel_claims)}

    all_biases = output.biases_and_focus.biases_and_rhetoric
    biases_pool = [b for b in all_biases if proves_selected(b)]
    sel_biases, _ = select(biases_pool, CAPS["biases"], lambda i: node_score(biases_pool[i]))
    bias_id_to_orig = {b.id: i for i, b in enumerate(all_biases)}
    bias_orig_to_new = {bias_id_to_orig[b.id]: new_i for new_i, b in enumerate(sel_biases)}

    # ── CTA: always include at least one blind_spot question ──────────────────
    must_cta: set[int] = set()
    for i, q in enumerate(output.cta.post_reading_questions):
        if q.type == "blind_spot":
            must_cta.add(i)
            break
    sel_cta_q, cta_old_to_new = select_with_must(
        output.cta.post_reading_questions,
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

    # ── Filter synthesis references to kept node IDs ──────────────────────────
    kept_ids = {
        item.id
        for item in final_obs + remapped_er + remapped_cb + sel_claims + sel_biases
        if getattr(item, "id", "")
    }
    final_synthesis = filter_synthesis_refs(sel_synthesis, kept_ids)

    # ── Remap go_further cta_question_index ───────────────────────────────────
    final_go = []
    for item in sel_go_raw:
        if item.cta_question_index is not None:
            item = item.model_copy(update={
                "cta_question_index": cta_old_to_new.get(item.cta_question_index)
            })
        final_go.append(item)

    # ── Assemble ──────────────────────────────────────────────────────────────
    return output.model_copy(update={
        "watch_out": output.watch_out.model_copy(update={"items": sel_wo}),
        "context": output.context.model_copy(update={
            "who_is_speaking": sel_who,
            "contexts": sel_ctx,
            "important_facts": sel_fact,
        }),
        "cadrage": output.cadrage.model_copy(update={
            "title_analysis": sel_title_analysis,
        }),
        "analysis_fond": fond.model_copy(update={
            "implicit_assumptions": sel_ia,
            "blind_spots": sel_bs,
            "observations": final_obs,
        }),
        "analysis_forme": forme.model_copy(update={
            "emotional_register": remapped_er,
            "cui_bono": remapped_cb,
        }),
        "facts_vs_opinions": output.facts_vs_opinions.model_copy(update={
            "claims_and_sources": sel_claims,
        }),
        "biases_and_focus": output.biases_and_focus.model_copy(update={
            "biases_and_rhetoric": sel_biases,
        }),
        "synthesis": output.synthesis.model_copy(update={"points": final_synthesis}),
        "go_further": output.go_further.model_copy(update={"items": final_go}),
        "cta": output.cta.model_copy(update={"post_reading_questions": sel_cta_q}),
    })
