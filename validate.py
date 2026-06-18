"""Validate cross-references in an ArticleFullAnalysis JSON file.

Usage:
    python validate.py samples/outputs/article_1_analysis.json
"""
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from models.carousel import ArticleFullAnalysis


def validate(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Schema validation — enums, types, required fields
    try:
        output = ArticleFullAnalysis.model_validate(data)
    except ValidationError as e:
        return [f"Schema error: {e}"]

    errors = []
    fond = output.analysis_fond
    forme = output.analysis_forme

    # ── Node registry (id → label) for graph building ────────────────────────
    node_registry: dict[str, str] = {}

    def _register(items: list, label_fn) -> None:
        for item in items:
            if item.id:
                node_registry[item.id] = label_fn(item)

    _register(output.watch_out.items, lambda x: f"wo: {x.text[:40]}")
    _register(output.context.contexts, lambda x: f"ctx: {x.text[:40]}")
    _register(output.context.important_facts, lambda x: f"fact: {x.text[:40]}")
    _register(fond.observations, lambda x: f"obs: {x.aspect}")
    _register(fond.premisses, lambda x: f"pr: {x.statement[:40]}")
    _register(fond.implicit_assumptions, lambda x: f"ia: {x.text[:40]}")
    _register(fond.blind_spots, lambda x: f"bs: {x.text[:40]}")
    _register(fond.logical_reasoning, lambda x: f"lr: {x.step[:40]}")
    _register(forme.emotional_register, lambda x: f"er: {x.emotion}")
    _register(forme.cui_bono, lambda x: f"cb: {x.beneficiary}")
    _register(output.facts_vs_opinions.claims_and_sources, lambda x: f"claim: {x.quote[:40]}")
    _register(output.biases_and_focus.biases_and_rhetoric, lambda x: f"bias: {x.label}")
    _register(output.cta.post_reading_questions, lambda x: f"q: {x.question[:40]}")

    # ── Build valid targets per proves.type ───────────────────────────────────
    obs_by_label = {obs.aspect: obs for obs in fond.observations}
    er_by_label = {er.emotion: er for er in forme.emotional_register}
    cb_by_label = {cb.beneficiary: cb for cb in forme.cui_bono}
    valid_by_type = {
        "observation": obs_by_label,
        "emotional_register": er_by_label,
        "cui_bono": cb_by_label,
    }

    # ── Build seeds source maps ───────────────────────────────────────────────
    source_items: dict[str, list] = {
        "watch_out": output.watch_out.items,
        "context": output.context.contexts,
        "important_fact": output.context.important_facts,
        "premisse": fond.premisses,
        "implicit_assumption": fond.implicit_assumptions,
        "blind_spot": fond.blind_spots,
        "logical_reasoning": fond.logical_reasoning,
    }

    def check_proves(ref, path_str: str) -> list[str]:
        errs = []
        by_label = valid_by_type.get(ref.type, {})
        if ref.label not in by_label:
            errs.append(
                f"{path_str}.proves: type='{ref.type}' label='{ref.label}' not found. "
                f"Valid {ref.type} labels: {sorted(by_label.keys())}"
            )
        else:
            node = by_label[ref.label]
            if node.id:
                pass  # valid — node.id available for graph edge resolution
        return errs

    def check_seeds(ref, path_str: str) -> list[str]:
        errs = []
        items = source_items.get(ref.source)
        if items is None:
            errs.append(f"{path_str}.seeds.source='{ref.source}' is not a recognised source")
        elif not (0 <= ref.index < len(items)):
            errs.append(
                f"{path_str}.seeds: index={ref.index} out of range for source='{ref.source}' "
                f"(length={len(items)})"
            )
        else:
            target = items[ref.index]
            if hasattr(target, "id") and not target.id:
                errs.append(
                    f"{path_str}.seeds: target {ref.source}[{ref.index}] has no id — "
                    "run through the pipeline or assign ids manually"
                )
        if not ref.excerpt:
            errs.append(f"{path_str}.seeds.excerpt is empty")
        return errs

    # ── Count constraints ─────────────────────────────────────────────────────
    n_claims = len(output.facts_vs_opinions.claims_and_sources)
    if n_claims != 4:
        errors.append(f"claims_and_sources: expected 4, got {n_claims}")

    n_biases = len(output.biases_and_focus.biases_and_rhetoric)
    if n_biases != 3:
        errors.append(f"biases_and_rhetoric: expected 3, got {n_biases}")

    if len(output.synthesis.points) != 3:
        errors.append(f"synthesis.points: expected 3, got {len(output.synthesis.points)}")

    n_cta_q = len(output.cta.post_reading_questions)
    if n_cta_q != 2:
        errors.append(f"cta.post_reading_questions: expected 2, got {n_cta_q}")

    blind_spot_qs = [q for q in output.cta.post_reading_questions if q.type == "blind_spot"]
    if not blind_spot_qs:
        errors.append("cta.post_reading_questions: at least one must be type 'blind_spot'")

    # ── proves cross-references ───────────────────────────────────────────────
    for i, claim in enumerate(output.facts_vs_opinions.claims_and_sources):
        errors.extend(check_proves(claim.proves, f"claims_and_sources[{i}]"))

    bf = output.biases_and_focus
    for i, bias in enumerate(bf.biases_and_rhetoric):
        errors.extend(check_proves(bias.proves, f"biases_and_rhetoric[{i}]"))

    if bf.focus.proves.type != "observation":
        errors.append(f"focus.proves.type must be 'observation', got '{bf.focus.proves.type}'")
    else:
        errors.extend(check_proves(bf.focus.proves, "focus"))

    # ── seeds cross-references ────────────────────────────────────────────────
    for i, obs in enumerate(fond.observations):
        errors.extend(check_seeds(obs.seeds, f"observations[{i}]"))

    for i, er in enumerate(forme.emotional_register):
        errors.extend(check_seeds(er.seeds, f"emotional_register[{i}]"))

    for i, cb in enumerate(forme.cui_bono):
        errors.extend(check_seeds(cb.seeds, f"cui_bono[{i}]"))

    for i, sm in enumerate(fond.steel_man):
        errors.extend(check_seeds(sm.seeds, f"steel_man[{i}]"))

    # ── go_further cta_question_index ─────────────────────────────────────────
    for i, item in enumerate(output.go_further.items):
        if item.cta_question_index is not None:
            if not (0 <= item.cta_question_index < n_cta_q):
                errors.append(
                    f"go_further[{i}].cta_question_index={item.cta_question_index} "
                    f"out of range (0–{n_cta_q - 1})"
                )

    # ── proven_by coherence ───────────────────────────────────────────────────
    for i, obs in enumerate(fond.observations):
        for j, ref in enumerate(obs.proven_by):
            if ref.type == "claim" and not (0 <= ref.index < n_claims):
                errors.append(f"observations[{i}].proven_by[{j}]: claim index {ref.index} out of range")
            elif ref.type == "bias" and not (0 <= ref.index < n_biases):
                errors.append(f"observations[{i}].proven_by[{j}]: bias index {ref.index} out of range")

    return errors, node_registry


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <analysis.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    errs, registry = validate(path)
    if not errs:
        print(f"✓ {path.name}: all checks passed")
        if registry:
            print(f"\nNode registry ({len(registry)} nodes):")
            for node_id, label in sorted(registry.items()):
                print(f"  {node_id:12s}  {label}")
    else:
        print(f"✗ {path.name}: {len(errs)} error(s)")
        for e in errs:
            print(f"  • {e}")
        sys.exit(1)
