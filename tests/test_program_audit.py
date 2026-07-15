from agent.program_analysis_agent import _audit_program


def _clean() -> dict:
    src = {"quote": "verbatim", "url": None, "outlet": None}
    espec = [{"name": "OFCE", "kind": "think_tank", "url": "https://x", "finding": "…"}]
    return {
        "research": {"statements": []},
        "vision_diagnostic": {"vision": "v", "values": None,
                              "root_causes": [{"id": "rc_0", "cause": "c", "sources": [src]}]},
        "contre_expertise": {"items": [{"id": "ce_0", "root_cause_id": "rc_0", "verdict": "v",
                                        "confidence": 50, "expert_sources": espec}]},
        "topics": {"topics": [{"domain": "Retraites",
                               "headline_measures": [{"id": "m_0", "measure": "m", "detail": None, "sources": [src]}],
                               "faille": {"kind": "funding", "label": "F", "explanation": "e", "expert_sources": espec}}]},
        "incidence": {"items": [{"id": "inc_0", "group": "g", "effect": "pays", "explanation": "e", "expert_sources": espec}]},
    }


def test_audit_clean_passes():
    assert _audit_program(_clean()) == []


def test_audit_flags_unsourced_measure():
    d = _clean()
    d["topics"]["topics"][0]["headline_measures"][0]["sources"] = [{"quote": "  "}]
    issues = _audit_program(d)
    assert any("UNSOURCED_MEASURE" in i for i in issues)


def test_audit_flags_faille_without_expert():
    d = _clean()
    d["topics"]["topics"][0]["faille"]["expert_sources"] = []
    issues = _audit_program(d)
    assert any("UNSOURCED_JUDGMENT" in i for i in issues)


def test_audit_flags_dangling_root_cause_ref():
    d = _clean()
    d["contre_expertise"]["items"][0]["root_cause_id"] = "rc_99"
    issues = _audit_program(d)
    assert any("DANGLING_ROOT_CAUSE" in i for i in issues)
