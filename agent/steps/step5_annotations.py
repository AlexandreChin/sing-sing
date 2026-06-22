from pathlib import Path
from agent._base import _call_with_retry, _j, save_step
from models.full_analysis import AnalysisFond, AnalyseForme
from models.full_analysis_steps import Step5Output

_PROMPT = (Path(__file__).parent.parent / "prompts" / "step5_annotations.md").read_text(encoding="utf-8")


def _validate(data: dict, fond_data: dict, forme_data: dict) -> list[str]:
    step5 = Step5Output.model_validate(data)
    fond = AnalysisFond.model_validate(fond_data)
    forme = AnalyseForme.model_validate(forme_data)
    errors = []

    valid_by_type = {
        "observation": {obs.aspect for obs in fond.observations},
        "emotional_register": {e.emotion for e in forme.emotional_register},
        "cui_bono": {c.beneficiary for c in forme.cui_bono},
    }

    def _check_proves(ref, path: str) -> str | None:
        valid = valid_by_type.get(ref.type, set())
        if ref.label not in valid:
            return (
                f"{path}.proves has type='{ref.type}' label='{ref.label}' but "
                f"'{ref.label}' not found in {ref.type}. Valid: {sorted(valid)}"
            )
        return None

    fvo = step5.facts_vs_opinions
    n_claims = len(fvo.claims_and_sources)
    if not (1 <= n_claims <= 6):
        errors.append(f"claims_and_sources: expected 1–6, got {n_claims}")
    for i, claim in enumerate(fvo.claims_and_sources):
        err = _check_proves(claim.proves, f"claims_and_sources[{i}]")
        if err:
            errors.append(err)

    bf = step5.biases_and_focus
    n_biases = len(bf.biases_and_rhetoric)
    if not (1 <= n_biases <= 4):
        errors.append(f"biases_and_rhetoric: expected 1–4, got {n_biases}")
    for i, bias in enumerate(bf.biases_and_rhetoric):
        err = _check_proves(bias.proves, f"biases_and_rhetoric[{i}]")
        if err:
            errors.append(err)

    if bf.focus.proves.type != "observation":
        errors.append(f"focus.proves.type must be 'observation', got '{bf.focus.proves.type}'")
    else:
        err = _check_proves(bf.focus.proves, "focus")
        if err:
            errors.append(err)

    return errors


def run(
    article: str,
    fond_data: dict,
    forme_data: dict,
    steps_dir: Path,
    no_api: bool = False,
) -> dict:
    user_msg = (
        f"{article}\n\n---\n\n"
        f"ANALYSE — LE FOND (étape 3) :\n{_j(fond_data)}\n\n"
        f"ANALYSE — LA FORME (étape 4) :\n{_j(forme_data)}\n\n"
        f"---\n\n{_PROMPT}"
    )
    data = _call_with_retry(
        user_msg,
        Step5Output.model_json_schema(),
        validator=lambda d: _validate(d, fond_data, forme_data),
        no_api=no_api,
    )
    save_step(data, steps_dir, "step5_annotations.json")
    return data
