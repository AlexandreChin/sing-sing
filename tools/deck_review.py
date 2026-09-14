"""Model-driven review of a finished deck — the pipeline's first LLM-side gate.

Everything else that validates is deterministic: `_validate` enforces the rules
we wrote down, `check_deck` re-runs them on the final file plus quote fidelity
and figure sourcing. None of it ever reads the deck the way a reader would, which
is how « sous-indexation » on slide 2, a presupposé the article's last paragraph
refutes, and three beats making the same move all passed clean.

Two passes, because the two questions need different eyes:

* **reader** — the slides ALONE, in reading order. Withholding the article is the
  point: a judge that has just read the piece fills every gap unconsciously and
  declares the deck clear. Comprehension, the arc between slides, what the deck
  is about. Advisory by construction.
* **fidelity** — the article plus our own prose (quotes excluded, they are checked
  word for word elsewhere). Did we add, extrapolate, compute or causally link
  something the text does not; do we answer questions it never asks; are the
  chosen beats load-bearing; do the presupposés pass the three tests.

An LLM judge's failure mode is inventing problems, so every fidelity finding must
carry a citation and the citation is verified HERE, in code: a passage must appear
in the article (same matcher the quote check uses), and a claim of absence must
name terms that are genuinely absent. A finding whose evidence does not check out
is dropped or demoted before anyone reads it.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from agent._base import _call_with_retry, _j
from agent.instagram_carousel_adapt_agent import norm_for_match, quote_is_faithful
from models.instagram_carousel_presentation import InstagramCarouselDocument

_PROMPTS = Path(__file__).parent.parent / "agent" / "prompts"
_READER_PROMPT = (_PROMPTS / "deck_review_reader.md").read_text(encoding="utf-8")
_FIDELITY_PROMPT = (_PROMPTS / "deck_review_fidelity.md").read_text(encoding="utf-8")

MAX_FINDINGS = 8

_KINDS = ["comprehension", "coherence", "centrality", "fidelity", "frame", "presupposition"]

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "field", "our_text", "evidence_kind", "evidence", "severity"],
                "properties": {
                    "kind": {"type": "string", "enum": _KINDS},
                    "field": {"type": "string"},
                    "our_text": {"type": "string"},
                    "evidence_kind": {"type": "string", "enum": ["reader", "article_passage", "absent"]},
                    "evidence": {"type": "string"},
                    "severity": {"type": "string", "enum": ["blocking", "advisory"]},
                    "suggestion": {"type": "string"},
                },
            },
        },
    },
}


def _validator(data: dict) -> list[str]:
    findings = data.get("findings")
    if not isinstance(findings, list):
        return ["findings must be a list"]
    errors = []
    if len(findings) > MAX_FINDINGS:
        errors.append(f"findings: {len(findings)} items (max {MAX_FINDINGS}) — keep the most serious")
    for i, f in enumerate(findings):
        for key in ("kind", "field", "our_text", "evidence_kind", "evidence", "severity"):
            if not str(f.get(key, "")).strip():
                errors.append(f"findings[{i}].{key} is empty")
    return errors


# ── what each pass sees ───────────────────────────────────────────────────────

def _slides_as_read(doc: InstagramCarouselDocument) -> str:
    """The deck as it renders, in swipe order — the reader pass's whole world.

    The réflexes on slide 3 are DERIVED by the renderer from the selected beats,
    so they appear in no field of the document. Left out, the pass reports the
    slide as announcing three réflexes it never shows — a phantom finding caused
    by our own payload. Anything the reader sees has to be in here.
    """
    from agent.lenses import CANONICAL_LENSES
    from tools.check_deck import _slide_order
    d = doc.presentation.display
    lenses, seen = [], set()
    for b in d.reading_beats:
        if not b.selected or b.lens_ref in seen:
            continue
        seen.add(b.lens_ref)
        canon = CANONICAL_LENSES.get(b.lens_ref, {})
        question = b.lens_question.strip().replace("**", "") or canon.get("question", "")
        lenses.append(f"[03 reperes réflexe] {len(seen):02d} {canon.get('name', b.lens_ref)} — {question}")
    lines = [f"[{label}] {text}" for label, text in _slide_order(doc)]
    # Slide 3 shows its context first, then the numbered réflexes.
    idx = max((i for i, l in enumerate(lines) if l.startswith("[03 reperes]")), default=len(lines) - 1)
    lines[idx + 1:idx + 1] = lenses
    return "\n".join(lines)


def _our_voice(doc: InstagramCarouselDocument) -> str:
    from tools.check_deck import _our_prose
    return "\n".join(f"[{label}] {text}" for label, text in _our_prose(doc))


def _beats_digest(doc: InstagramCarouselDocument) -> str:
    """Selected beats, then the pool left on the bench — centrality needs both."""
    d = doc.presentation.display
    out = []
    for i, b in enumerate(d.reading_beats):
        mark = "RETENU " if b.selected else "vivier "
        out.append(f"{mark}[{i}] ({b.thesis_step or '?'}/{b.role or '?'}) {b.moment} "
                   f"— « {b.quote[:90]} » → {b.answer[:120]}")
    return "\n".join(out)


# ── the citation check: the model finds, this verifies ────────────────────────

def _verify(finding: dict, article: str, article_norm: str) -> tuple[bool, str]:
    """(keep, note). A finding whose evidence does not check out loses its teeth."""
    kind = finding.get("evidence_kind")
    evidence = (finding.get("evidence") or "").strip()
    if kind == "reader":
        return True, ""
    if kind == "article_passage":
        if quote_is_faithful(evidence, article_norm):
            return True, ""
        return False, "quoted passage is not in the article"
    if kind == "absent":
        present = [t.strip() for t in evidence.split(",")
                   if t.strip() and norm_for_match(t.strip()) in article_norm]
        if present:
            return False, f"terms said to be absent are in the article: {', '.join(present)}"
        return True, ""
    return False, f"unknown evidence_kind {kind!r}"


def _format(finding: dict) -> str:
    bits = f"[{finding['kind']}] {finding['field']} — « {finding['our_text'][:90]} »"
    if finding.get("suggestion"):
        bits += f" → {finding['suggestion']}"
    if finding["evidence_kind"] == "article_passage":
        bits += f"  (article : « {finding['evidence'][:80]}… »)"
    elif finding["evidence_kind"] == "absent":
        bits += f"  (absent de l'article : {finding['evidence'][:60]})"
    else:
        bits += f"  ({finding['evidence'][:90]})"
    return bits


def review(extract_path: Path, article_path: Path | None = None,
           no_api: bool = False) -> dict[str, list[str]]:
    """Run both passes. Returns {family: [lines]}, same shape as `check_deck.check`.

    The findings are also written to `review.json` beside the deck: a model call
    costs minutes, and its result has to survive the terminal scroll — it is what
    you work from while editing, and what you compare the next run against.
    """
    extract_path = Path(extract_path)
    doc = InstagramCarouselDocument.model_validate(
        json.loads(extract_path.read_text(encoding="utf-8")))
    report: dict[str, list[str]] = {"reader (model)": [], "fidelity (model)": [], "dropped (model)": []}

    reader = _call_with_retry(
        f"CARROUSEL (dans l'ordre de lecture) :\n{_slides_as_read(doc)}\n\n---\n\n{_READER_PROMPT}",
        _SCHEMA, validator=_validator, no_api=no_api, label="reader",
    )
    for f in reader.get("findings", []):
        report["reader (model)"].append(_format(f))

    if article_path is None:
        base = extract_path.parent.parent
        candidate = base / f"{base.name}.txt"
        article_path = candidate if candidate.exists() else None
    if article_path is None:
        report["fidelity (model)"].append(
            "article text not found — pass it as the second argument to run the fidelity pass")
        _save(extract_path, doc, reader, {}, report)
        return report

    article = Path(article_path).read_text(encoding="utf-8")
    article_norm = norm_for_match(article)
    d = doc.presentation.display
    payload = (
        f"ARTICLE :\n{article}\n\n"
        f"CADRE DE LA THÈSE :\n{_j(d.thesis_frame.model_dump() if d.thesis_frame else {})}\n\n"
        f"MOMENTS (retenus et vivier) :\n{_beats_digest(doc)}\n\n"
        f"NOTRE PROSE (citations exclues) :\n{_our_voice(doc)}\n\n"
        f"---\n\n{_FIDELITY_PROMPT}"
    )
    fidelity = _call_with_retry(payload, _SCHEMA, validator=_validator, no_api=no_api, label="fidelity")
    for f in fidelity.get("findings", []):
        keep, note = _verify(f, article, article_norm)
        if keep:
            report["fidelity (model)"].append(_format(f))
        else:
            report["dropped (model)"].append(f"{_format(f)}  ✗ {note}")
    _save(extract_path, doc, reader, fidelity, report)
    return report


def _save(extract_path: Path, doc, reader: dict, fidelity: dict,
          report: dict[str, list[str]]) -> Path:
    """Both passes' raw findings, plus the rendered lines, next to the deck."""
    out = extract_path.parent / "review.json"
    out.write_text(json.dumps({
        "deck": str(extract_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "reader": reader.get("findings", []),
        "fidelity": fidelity.get("findings", []),
        "report": report,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {out}", file=sys.stderr)
    return out


def format_report(report: dict[str, list[str]]) -> str:
    lines = []
    for family, problems in report.items():
        if family == "dropped (model)" and not problems:
            continue
        head = "OK" if not problems else f"{len(problems)} finding(s)"
        lines.append(f"── {family}: {head}")
        lines += [f"   • {p}" for p in problems]
    return "\n".join(lines)
