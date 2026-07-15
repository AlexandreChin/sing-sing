import inspect
from agent import _base


def test_call_accepts_system_param():
    assert "system" in inspect.signature(_base._call).parameters
    assert "system" in inspect.signature(_base._call_with_retry).parameters


def test_no_api_uses_override_system(monkeypatch):
    captured = {}
    def fake_run(cmd, capture_output, text, encoding):
        captured["prompt"] = cmd[2]
        class R:  # minimal CompletedProcess stand-in
            returncode = 0
            stdout = '{"ok": true}'
            stderr = ""
        return R()
    monkeypatch.setattr(_base.subprocess, "run", fake_run)
    _base._call("hello", {"type": "object"}, no_api=True, system="SYSTEME PROGRAMME")
    assert "SYSTEME PROGRAMME" in captured["prompt"]
