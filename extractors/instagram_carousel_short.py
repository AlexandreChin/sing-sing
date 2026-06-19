"""Extractor for 6-slide short Instagram carousel format."""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis
from extractors._base import select, score_nodes

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


def extract(output: ArticleFullAnalysis) -> ArticleFullAnalysis:
    """Return a trimmed ArticleFullAnalysis for the 6-slide short carousel."""
    scores = score_nodes(output)

    def node_score(item) -> float:
        return scores.get(getattr(item, "id", ""), 0.0)

    fond = output.analysis_fond
    forme = output.analysis_forme

    # Contexts: first 2
    sel_ctx = output.context.contexts[: CAPS["contexts"]]

    # Watch_out: top 3 by score (exactly 3, no per-category guarantee)
    sel_wo, _ = select(
        output.watch_out.items, CAPS["watch_out"],
        lambda i: node_score(output.watch_out.items[i]),
    )

    # Observations: top 1 by score
    sel_obs, _ = select(
        fond.observations, CAPS["observations"], lambda i: node_score(fond.observations[i])
    )

    # Title analysis: first 1
    sel_title = output.cadrage.title_analysis[: CAPS["title_analysis"]]

    # Emotional register: first 1
    sel_er = forme.emotional_register[: CAPS["emotional_register"]]

    # Claims: top 1 by score
    all_claims = output.facts_vs_opinions.claims_and_sources
    sel_claims, _ = select(all_claims, CAPS["claims"], lambda i: node_score(all_claims[i]))

    # Biases: top 1 by score
    all_biases = output.biases_and_focus.biases_and_rhetoric
    sel_biases, _ = select(all_biases, CAPS["biases"], lambda i: node_score(all_biases[i]))

    # Go further: first 3
    sel_go = output.go_further.items[: CAPS["go_further"]]

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
