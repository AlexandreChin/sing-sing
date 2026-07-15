from models.program_analysis import (
    CORE_DOMAINS, ProgramFullAnalysis, DiagnosticAssessmentItem,
)


def _minimal_analysis_dict() -> dict:
    src = {"quote": "Nous porterons le SMIC à 1600 euros.", "url": None, "outlet": None}
    espec = {"name": "OFCE", "kind": "think_tank", "url": "https://ofce.fr/x", "finding": "Coût estimé à 10 Md€."}
    return {
        "metadata": {"candidate": "Candidat X", "generated_at": None, "domains": CORE_DOMAINS},
        "research": {"statements": [{"id": "", "domain": CORE_DOMAINS[0], "quote": "…", "source": src}]},
        "vision_diagnostic": {"vision": "Une France plus juste.", "values": None,
                              "root_causes": [{"id": "", "cause": "Inégalités croissantes.", "sources": [src]}]},
        "contre_expertise": {"items": [{"id": "", "root_cause_id": "rc_0", "verdict": "Partiellement étayé.",
                                        "confidence": 55, "expert_sources": [espec]}]},
        "topics": {"topics": [
            {
                "domain": d,
                "headline_measures": [{"id": "", "measure": f"Mesure {d}", "detail": None, "sources": [src]}],
                "faille": {"kind": "funding", "label": "Financement", "explanation": "Non chiffré.", "expert_sources": [espec]},
            }
            for d in CORE_DOMAINS
        ]},
        "incidence": {"items": [{"id": "", "group": "Ménages modestes", "effect": "benefits",
                                 "explanation": "Hausse du pouvoir d'achat.", "expert_sources": [espec]}]},
        "review": {"dimensions": [
            {"dimension": "funding_clarity", "label": "Clarté du financement", "score": 2, "rationale": "…"},
            {"dimension": "feasibility", "label": "Faisabilité", "score": 3, "rationale": "…"},
            {"dimension": "internal_coherence", "label": "Cohérence interne", "score": 3, "rationale": "…"},
            {"dimension": "evidence_grounding", "label": "Fondement factuel", "score": 2, "rationale": "…"},
        ]},
        "distill": {"points": ["a", "b", "c"],
                    "verdict": {"summary": "Programme ambitieux mais peu chiffré.", "open_question": "Comment financer ?"}},
    }


def test_core_domains_has_twelve():
    assert len(CORE_DOMAINS) == 12


def test_full_analysis_validates():
    a = ProgramFullAnalysis.model_validate(_minimal_analysis_dict())
    assert len(a.topics.topics) == 12
    assert len(a.review.dimensions) == 4


def test_confidence_label_bands():
    assert DiagnosticAssessmentItem(root_cause_id="rc_0", verdict="x", confidence=10, expert_sources=[]).confidence_label == "faux"
    assert DiagnosticAssessmentItem(root_cause_id="rc_0", verdict="x", confidence=95, expert_sources=[]).confidence_label == "consensuel"
    assert DiagnosticAssessmentItem(root_cause_id="rc_0", verdict="x", confidence=None, expert_sources=[]).confidence_label == "invérifiable"
