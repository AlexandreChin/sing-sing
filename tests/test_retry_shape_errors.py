"""A wrong-SHAPE response must be repairable, like a wrong-CONTENT one.

Step validators typically open with `Model.model_validate(data)`, which raises
instead of returning an error list. Before this, such a response escaped
`_call_with_retry`'s repair loop and aborted the run — which is how a video_3
analysis died on a `verdict` nested inside a `dimensions` entry.
"""
import pytest
from pydantic import BaseModel

from agent import _base


class _Shape(BaseModel):
    dimension: str
    score: int


def _validator(data: dict) -> list[str]:
    """Typical step validator: raises ValidationError on a malformed payload."""
    _Shape.model_validate(data)
    return []


def test_shape_error_is_repaired_not_raised(monkeypatch):
    calls = []
    responses = [
        {"score": 3},                          # wrong shape: `dimension` missing
        {"dimension": "exactitude", "score": 3},  # corrected
    ]

    def fake_call(msg, schema, no_api=False, system=None):
        calls.append(msg)
        return responses[len(calls) - 1]

    monkeypatch.setattr(_base, "_call", fake_call)
    out = _base._call_with_retry("prompt", {}, _validator)

    assert out == {"dimension": "exactitude", "score": 3}
    assert len(calls) == 2, "the shape error should have triggered one repair call"
    # the repair prompt must name the offending field so the model can fix it
    assert "dimension" in calls[1]


def test_unrepairable_shape_error_returns_without_raising(monkeypatch):
    # a model that never gets it right must still not abort the pipeline
    monkeypatch.setattr(_base, "_call", lambda *a, **k: {"score": 3})
    out = _base._call_with_retry("prompt", {}, _validator)
    assert out == {"score": 3}


def test_content_errors_still_work(monkeypatch):
    responses = [{"dimension": "", "score": 3}, {"dimension": "ok", "score": 3}]
    calls = []

    def fake_call(msg, schema, no_api=False, system=None):
        calls.append(msg)
        return responses[len(calls) - 1]

    def validator(data):
        _Shape.model_validate(data)
        return ["dimension is empty"] if not data["dimension"] else []

    monkeypatch.setattr(_base, "_call", fake_call)
    assert _base._call_with_retry("prompt", {}, validator)["dimension"] == "ok"
    assert "dimension is empty" in calls[1]
