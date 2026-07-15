from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, computed_field

# The 12 core policy domains every candidate analysis covers (see overview spec).
CORE_DOMAINS: list[str] = [
    "Travail / Emploi",
    "Pouvoir d'achat",
    "Fiscalité / Impôts",
    "Économie & finances publiques",
    "Retraites",
    "Logement",
    "Écologie",
    "Santé & Éducation",
    "Société",
    "Immigration",
    "Sécurité & Justice",
    "Europe / Institutions & International",
]


class ProgramAnalysisInput(BaseModel):
    candidate: str
    program_text: str
    extra_instructions: str | None = None


# ── Sourcing primitives ───────────────────────────────────────────────────────

class SourceRef(BaseModel):
    """A candidate statement source: a verbatim passage from the program document."""
    quote: str
    url: str | None = None
    outlet: str | None = None


class SpecialistSource(BaseModel):
    """An independent expert source grounding a critical judgment (not the candidate)."""
    name: str
    kind: Literal["academic", "official_data", "ngo", "think_tank", "media", "other"]
    url: str
    finding: str


# ── Step 1: Ingest & structure ────────────────────────────────────────────────

class SourcedStatement(BaseModel):
    id: str = ""
    domain: str
    quote: str
    source: SourceRef


class ProgramResearch(BaseModel):
    statements: list[SourcedStatement]


# ── Step 2: Vision & diagnostic ───────────────────────────────────────────────

class RootCause(BaseModel):
    id: str = ""
    cause: str
    sources: list[SourceRef] = Field(default_factory=list)


class VisionDiagnostic(BaseModel):
    vision: str
    root_causes: list[RootCause]
    values: str | None = None


# ── Step 3: Contre-expertise ──────────────────────────────────────────────────

class DiagnosticAssessmentItem(BaseModel):
    id: str = ""
    root_cause_id: str
    verdict: str
    confidence: int | None = None
    expert_sources: list[SpecialistSource] = Field(default_factory=list)

    @computed_field
    @property
    def confidence_label(self) -> str:
        if self.confidence is None: return "invérifiable"
        if self.confidence <= 20: return "faux"
        if self.confidence <= 40: return "peu probable"
        if self.confidence <= 60: return "disputé"
        if self.confidence <= 80: return "probable"
        if self.confidence <= 90: return "avéré"
        return "consensuel"


class ContreExpertise(BaseModel):
    items: list[DiagnosticAssessmentItem]


# ── Step 4: Per-topic analysis ────────────────────────────────────────────────

class Measure(BaseModel):
    id: str = ""
    measure: str
    detail: str | None = None
    sources: list[SourceRef] = Field(default_factory=list)


class Faille(BaseModel):
    kind: Literal["efficacy", "funding", "feasibility", "coherence", "legal"]
    label: str
    explanation: str
    expert_sources: list[SpecialistSource] = Field(default_factory=list)


class TopicAnalysis(BaseModel):
    domain: str
    headline_measures: list[Measure]
    faille: Faille


class ProgramTopics(BaseModel):
    topics: list[TopicAnalysis]


# ── Step 5: Incidence ─────────────────────────────────────────────────────────

class IncidenceItem(BaseModel):
    id: str = ""
    group: str
    effect: Literal["benefits", "pays"]
    explanation: str
    expert_sources: list[SpecialistSource] = Field(default_factory=list)


class Incidence(BaseModel):
    items: list[IncidenceItem]


# ── Step 6: Review dimensions ─────────────────────────────────────────────────

class ProgramReviewDimension(BaseModel):
    dimension: Literal["funding_clarity", "feasibility", "internal_coherence", "evidence_grounding"]
    label: str
    score: int  # 1–5
    rationale: str


class ProgramReview(BaseModel):
    dimensions: list[ProgramReviewDimension]


# ── Step 7: Distill + verdict ─────────────────────────────────────────────────

class ProgramVerdict(BaseModel):
    summary: str
    open_question: str


class ProgramDistill(BaseModel):
    points: list[str]
    verdict: ProgramVerdict


# ── Composite ─────────────────────────────────────────────────────────────────

class ProgramMetadata(BaseModel):
    candidate: str
    generated_at: str | None = None
    domains: list[str] = Field(default_factory=lambda: list(CORE_DOMAINS))


class ProgramFullAnalysis(BaseModel):
    metadata: ProgramMetadata
    research: ProgramResearch
    vision_diagnostic: VisionDiagnostic
    contre_expertise: ContreExpertise
    topics: ProgramTopics
    incidence: Incidence
    review: ProgramReview
    distill: ProgramDistill
