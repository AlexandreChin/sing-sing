"""distill.open_questions — list of neutral, subject-level questions (replaces the
single `open_question` string) + backward-compat migration."""
from agent.steps.step8_distill import _validate
from models.full_analysis import Distill


def _distill(**over):
    d = {"points": [{"text": f"p{i}", "references": ["r"]} for i in range(3)],
         "open_questions": ["Q1 ?", "Q2 ?"]}
    d.update(over)
    return d


def test_new_list_shape():
    d = Distill.model_validate(_distill())
    assert d.open_questions == ["Q1 ?", "Q2 ?"]


def test_legacy_string_is_migrated():
    # old analyses carried a single `open_question` string
    d = Distill.model_validate({"points": [{"text": "p", "references": ["r"]}],
                                "open_question": "Question ancienne ?"})
    assert d.open_questions == ["Question ancienne ?"]
    assert not hasattr(d, "open_question")


def test_validator_accepts_2_to_3():
    assert _validate({"distill": _distill()}) == []


def test_validator_rejects_one_question():
    errs = _validate({"distill": _distill(open_questions=["seule ?"])})
    assert any("open_questions" in e for e in errs)


def test_validator_rejects_empty_question():
    errs = _validate({"distill": _distill(open_questions=["ok ?", "  "])})
    assert any("open_questions" in e for e in errs)
