"""Extractor for 6-slide short Instagram carousel format."""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
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
}


def extract(output: ArticleFullAnalysis, connected: bool = False) -> ArticleFullAnalysis:
    """Return a trimmed ArticleFullAnalysis for the 6-slide short carousel.

    connected=True  — watch_out items are seeded from selected observations/emotions;
                      claims and biases are filtered to those that prove them.
    connected=False — all sections selected independently by synthesis score.
    """
    scores = score_nodes(output)

    def node_score(item) -> float:
        return scores.get(getattr(item, "id", ""), 0.0)

    fond = output.analysis_fond
    forme = output.analysis_forme

    # ── Always scored independently ────────────────────────────────────────────

    # Contexts: first 2 (no synthesis refs, scoring adds nothing)
    sel_ctx = output.context.contexts[: CAPS["contexts"]]

    # Title analysis: first 1 (no IDs, can't score)
    sel_title = output.cadrage.title_analysis[: CAPS["title_analysis"]]

    # Observations: top 1 by synthesis score
    sel_obs, _ = select(
        fond.observations, CAPS["observations"], lambda i: node_score(fond.observations[i])
    )

    # Emotional register: top 1 by synthesis score
    sel_er, _ = select(
        forme.emotional_register, CAPS["emotional_register"],
        lambda i: node_score(forme.emotional_register[i]),
    )

    # Go further: first 3
    sel_go = output.go_further.items[: CAPS["go_further"]]

    # ── Connected vs independent selection ─────────────────────────────────────

    if connected:
        # Watch_out: prioritise items that are seeds of selected obs + emotions
        must_wo: set[int] = set()
        for item in sel_obs + sel_er:
            if hasattr(item, "seeds") and item.seeds.source == "watch_out":
                must_wo.add(item.seeds.index)
        sel_wo, _ = select_with_must(
            output.watch_out.items, CAPS["watch_out"], must_wo,
            lambda i: node_score(output.watch_out.items[i]),
        )

        # Claims/biases: filter to those proving selected observations or emotions
        sel_obs_aspects = {obs.aspect for obs in sel_obs}
        sel_er_emotions = {er.emotion for er in sel_er}

        def proves_selected(item) -> bool:
            t, label = item.proves.type, item.proves.label
            if t == "observation":
                return label in sel_obs_aspects
            if t == "emotional_register":
                return label in sel_er_emotions
            return False

        all_claims = output.facts_vs_opinions.claims_and_sources
        claims_pool = [c for c in all_claims if proves_selected(c)] or list(all_claims)
        sel_claims, _ = select(claims_pool, CAPS["claims"], lambda i: node_score(claims_pool[i]))

        all_biases = output.biases_and_focus.biases_and_rhetoric
        biases_pool = [b for b in all_biases if proves_selected(b)] or list(all_biases)
        sel_biases, _ = select(biases_pool, CAPS["biases"], lambda i: node_score(biases_pool[i]))

    else:
        sel_wo, _ = select(
            output.watch_out.items, CAPS["watch_out"],
            lambda i: node_score(output.watch_out.items[i]),
        )
        all_claims = output.facts_vs_opinions.claims_and_sources
        sel_claims, _ = select(all_claims, CAPS["claims"], lambda i: node_score(all_claims[i]))
        all_biases = output.biases_and_focus.biases_and_rhetoric
        sel_biases, _ = select(all_biases, CAPS["biases"], lambda i: node_score(all_biases[i]))

    # ── Assemble ───────────────────────────────────────────────────────────────
    return output.model_copy(update={
        "context": output.context.model_copy(update={
            "contexts": sel_ctx,
            "important_facts": [],
        }),
        "watch_out": output.watch_out.model_copy(update={"items": sel_wo}),
        "cadrage": output.cadrage.model_copy(update={
            "title_analysis": sel_title,
        }),
        "analysis_fond": fond.model_copy(update={
            "observations": sel_obs,
        }),
        "analysis_forme": forme.model_copy(update={
            "emotional_register": sel_er,
        }),
        "facts_vs_opinions": output.facts_vs_opinions.model_copy(update={
            "claims_and_sources": sel_claims,
        }),
        "biases_and_focus": output.biases_and_focus.model_copy(update={
            "biases_and_rhetoric": sel_biases,
        }),
        "go_further": output.go_further.model_copy(update={"items": sel_go}),
    })
