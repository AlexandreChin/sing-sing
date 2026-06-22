"""Extractor for the 6-slide short Instagram carousel format."""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselDocument, InstagramCarouselPresentation
from extractors._base import select, select_with_must, score_nodes

CAPS = {
    "contexts": 2,
    "watch_out": 3,
    "observations": 1,
    "title_analysis": 1,
    "emotional_register": 1,
    "claims": 2,
    "biases": 2,
    "go_further": 3,
    "cta_questions": 2,
}


def extract(full: ArticleFullAnalysis, presentation: InstagramCarouselPresentation, connected: bool = False) -> InstagramCarouselDocument:
    """Return a trimmed InstagramCarouselDocument for the 6-slide short carousel."""
    scores = score_nodes(full)

    def node_score(item) -> float:
        return scores.get(getattr(item, "id", ""), 0.0)

    fond = full.analysis.fond
    forme = full.analysis.forme

    sel_ctx = full.context.contexts[: CAPS["contexts"]]
    sel_title = full.cadrage.title_analysis[: CAPS["title_analysis"]]

    sel_obs, _ = select(
        fond.observations, CAPS["observations"], lambda i: node_score(fond.observations[i])
    )
    sel_er, _ = select(
        forme.emotional_register, CAPS["emotional_register"],
        lambda i: node_score(forme.emotional_register[i]),
    )

    if connected:
        must_wo: set[int] = set()
        for item in sel_obs + sel_er:
            if hasattr(item, "seeds") and item.seeds.source == "watch_out":
                must_wo.add(item.seeds.index)
        sel_wo, _ = select_with_must(
            full.watch_out.items, CAPS["watch_out"], must_wo,
            lambda i: node_score(full.watch_out.items[i]),
        )
        sel_obs_aspects = {obs.aspect for obs in sel_obs}
        sel_er_emotions = {er.emotion for er in sel_er}

        def proves_selected(item) -> bool:
            t, label = item.proves.type, item.proves.label
            if t == "observation":
                return label in sel_obs_aspects
            if t == "emotional_register":
                return label in sel_er_emotions
            return False

        all_claims = full.annotations.facts_vs_opinions.claims_and_sources
        claims_pool = [c for c in all_claims if proves_selected(c)] or list(all_claims)
        sel_claims, _ = select(claims_pool, CAPS["claims"], lambda i: node_score(claims_pool[i]))

        all_biases = full.annotations.biases_and_focus.biases_and_rhetoric
        biases_pool = [b for b in all_biases if proves_selected(b)] or list(all_biases)
        sel_biases, _ = select(biases_pool, CAPS["biases"], lambda i: node_score(biases_pool[i]))
    else:
        sel_wo, _ = select(
            full.watch_out.items, CAPS["watch_out"],
            lambda i: node_score(full.watch_out.items[i]),
        )
        all_claims = full.annotations.facts_vs_opinions.claims_and_sources
        sel_claims, _ = select(all_claims, CAPS["claims"], lambda i: node_score(all_claims[i]))
        all_biases = full.annotations.biases_and_focus.biases_and_rhetoric
        sel_biases, _ = select(all_biases, CAPS["biases"], lambda i: node_score(all_biases[i]))

    # ── CTA questions ─────────────────────────────────────────────────────────
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

    # ── Trim go_further + remap CTA indices ───────────────────────────────────
    sel_go_raw = presentation.go_further[: CAPS["go_further"]]
    final_go = []
    for item in sel_go_raw:
        if item.cta_question_index is not None:
            item = item.model_copy(update={
                "cta_question_index": cta_old_to_new.get(item.cta_question_index)
            })
        final_go.append(item)

    # ── Assemble ───────────────────────────────────────────────────────────────
    trimmed_full = full.model_copy(update={
        "context": full.context.model_copy(update={
            "contexts": sel_ctx,
            "important_facts": [],
        }),
        "watch_out": full.watch_out.model_copy(update={"items": sel_wo}),
        "cadrage": full.cadrage.model_copy(update={"title_analysis": sel_title}),
        "analysis": full.analysis.model_copy(update={
            "fond": fond.model_copy(update={"observations": sel_obs}),
            "forme": forme.model_copy(update={"emotional_register": sel_er}),
        }),
        "annotations": full.annotations.model_copy(update={
            "facts_vs_opinions": full.annotations.facts_vs_opinions.model_copy(update={
                "claims_and_sources": sel_claims,
            }),
            "biases_and_focus": full.annotations.biases_and_focus.model_copy(update={
                "biases_and_rhetoric": sel_biases,
            }),
        }),
    })

    trimmed_presentation = presentation.model_copy(update={
        "go_further": final_go,
        "cta": presentation.cta.model_copy(update={"post_reading_questions": sel_cta_q}),
    })

    return InstagramCarouselDocument(analysis=trimmed_full, presentation=trimmed_presentation)
