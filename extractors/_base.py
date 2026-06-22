"""Shared graph traversal primitives for format-specific extractors."""
from __future__ import annotations

from models.full_analysis import ArticleFullAnalysis


def score_nodes(output: ArticleFullAnalysis) -> dict[str, float]:
    """Score each node from distill.references. Earlier point → higher weight."""
    if not output.distill:
        return {}
    scores: dict[str, float] = {}
    for i, point in enumerate(output.distill.points):
        w = 1.0 / (i + 1)
        for ref_id in point.references:
            scores[ref_id] = scores.get(ref_id, 0.0) + w
    return scores


def select(items: list, cap: int, score_fn) -> tuple[list, dict[int, int]]:
    """Select top-cap items by score, preserving original order among ties.

    Returns (selected_items, old_index → new_index mapping).
    """
    indexed = list(enumerate(items))
    sorted_by_score = sorted(indexed, key=lambda p: (score_fn(p[0]), -p[0]), reverse=True)
    chosen = sorted(sorted_by_score[:cap], key=lambda p: p[0])
    old_to_new = {orig_i: new_i for new_i, (orig_i, _) in enumerate(chosen)}
    return [item for _, item in chosen], old_to_new


def select_with_must(
    items: list, cap: int, must_indices: set[int], score_fn
) -> tuple[list, dict[int, int]]:
    """Select top-cap items by score, always including must_indices.

    Returns (selected_items, old_index → new_index mapping).
    """
    valid_must = {i for i in must_indices if 0 <= i < len(items)}
    optional = [(i, item) for i, item in enumerate(items) if i not in valid_must]
    optional_sorted = sorted(optional, key=lambda p: (score_fn(p[0]), -p[0]), reverse=True)
    remaining = max(0, cap - len(valid_must))
    chosen = sorted(
        [(i, items[i]) for i in valid_must] + optional_sorted[:remaining],
        key=lambda p: p[0],
    )
    old_to_new = {orig_i: new_i for new_i, (orig_i, _) in enumerate(chosen)}
    return [item for _, item in chosen], old_to_new


def remap_seeds(seeds, source_remap: dict[str, dict[int, int]]):
    """Return a seeds ref with its index remapped to the new source list position."""
    remap = source_remap.get(seeds.source, {})
    return seeds.model_copy(update={"index": remap.get(seeds.index, seeds.index)})


def rebuild_proven_by(obs, claim_orig_to_new: dict[int, int], bias_orig_to_new: dict[int, int]) -> list:
    """Return a new proven_by list with indices remapped to selected claim/bias positions.

    Refs to dropped nodes are removed; focus refs are kept as-is.
    """
    result = []
    for ref in obs.proven_by:
        if ref.type == "claim" and ref.index in claim_orig_to_new:
            result.append(ref.model_copy(update={"index": claim_orig_to_new[ref.index]}))
        elif ref.type == "bias" and ref.index in bias_orig_to_new:
            result.append(ref.model_copy(update={"index": bias_orig_to_new[ref.index]}))
        elif ref.type == "focus":
            result.append(ref)
    return result


def filter_distill_refs(points: list, kept_ids: set[str]) -> list:
    """Remove references to dropped nodes from each distill point."""
    return [
        pt.model_copy(update={"references": [r for r in pt.references if r in kept_ids]})
        for pt in points
    ]
