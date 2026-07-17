from agent.steps.step10_core import _validate


def _ce(n, centralities=(5, 4, 3)):
    return {"elements": [
        {"statement": f"élément {i}", "kind": "enjeu", "centrality": c}
        for i, c in enumerate(centralities[:n])
    ]}


def test_valid_core_elements_pass():
    assert _validate(_ce(3)) == []


def test_rejects_wrong_count():
    assert any("3–5" in e or "3-5" in e for e in _validate(_ce(2, (5, 4))))
    assert any("3–5" in e or "3-5" in e for e in _validate(_ce(6, (5, 5, 4, 4, 3, 2))))


def test_rejects_bad_centrality():
    bad = {"elements": [{"statement": "x", "kind": "fait", "centrality": 9},
                        {"statement": "y", "kind": "fait", "centrality": 3},
                        {"statement": "z", "kind": "fait", "centrality": 2}]}
    assert any("centrality" in e for e in _validate(bad))
