from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, computed_field, field_validator


# ── Cross-reference types ─────────────────────────────────────────────────────

class ProvesRef(BaseModel):
    type: Literal["observation", "emotional_register", "cui_bono"]
    label: str  # must match aspect / emotion / beneficiary in the referenced item
    strength: float | None = None
    nature: Literal["illustration", "nuance", "contradiction"] | None = None


class SeedsRef(BaseModel):
    source: Literal["context", "important_fact", "premisse", "implicit_assumption", "blind_spot", "logical_reasoning"]
    index: int   # 0-based position in the source list
    excerpt: str  # short snippet for human readability
    strength: float | None = None
    nature: Literal["inference", "illustration", "contradiction", "specification"] | None = None


class ProvenByRef(BaseModel):
    type: Literal["claim", "bias", "focus"]
    index: int   # 0-based position in claims_and_sources / biases_and_rhetoric


class TextItem(BaseModel):
    """String item with a stable ID for cross-referencing. Renders as plain text in templates."""
    id: str = ""
    text: str

    def __str__(self) -> str:
        return self.text


class ImplicitAssumption(BaseModel):
    id: str = ""
    statement: str  # the assumption itself (one sentence)
    impact: str     # what breaks if the assumption is wrong

    def __str__(self) -> str:
        return self.statement


class BlindSpot(BaseModel):
    id: str = ""
    topic: str        # what is absent or downplayed
    significance: str  # why it matters to the conclusion

    def __str__(self) -> str:
        return self.topic


class DistillPoint(BaseModel):
    """One key takeaway from Distill, with back-references to analysis nodes."""
    text: str
    references: list[str] = Field(default_factory=list)  # node IDs: obs_N, claim_N, bias_N, er_N, cb_N

    def __str__(self) -> str:
        return self.text


class FullAnalysisInput(BaseModel):
    body: str
    title: str | None = None
    url: HttpUrl | None = None
    source: str | None = None
    published_at: str | None = None
    extra_instructions: str | None = None


class ArticleMetadata(BaseModel):
    url: HttpUrl | None = None
    title: str | None = None
    source: str | None = None
    published_at: str | None = None
    type: Literal["editorial", "news_report", "opinion", "investigation", "interview", "other"] | None = None
    reading_time_minutes: int | None = None
    chapo: str | None = None


# ── Step 1: Scan ──────────────────────────────────────────────────────────────

class AuthorityAnchor(BaseModel):
    entity: str    # person, organization, or institution cited
    used_for: str  # which claim or argument it legitimizes


class ArticleExtraction(BaseModel):
    authority_anchors: list[AuthorityAnchor]
    key_quotes: list[str]
    notable_omissions: list[str]
    rhetorical_patterns: list[str]


class TermDefinition(BaseModel):
    term: str
    definition: str


class Context(BaseModel):
    contexts: list[TextItem]
    who_is_speaking: list[str]
    important_facts: list[TextItem]
    key_terms: list[TermDefinition]

    @field_validator("contexts", "important_facts", mode="before")
    @classmethod
    def _coerce_text_items(cls, v: list) -> list:
        return [{"id": "", "text": item} if isinstance(item, str) else item for item in v]


# ── Step 3: Rhetoric (cadrage lives here) ────────────────────────────────────

class TitleAnalysisItem(BaseModel):
    label: str        # short label for the rhetorical device or framing technique (1–2 words)
    observation: str  # analytical observation on the title (post-reading)


class Cadrage(BaseModel):
    title_analysis: list[TitleAnalysisItem] = []


# ── Step 9: Guide (watch_out lives here) ─────────────────────────────────────

class WatchOutItem(BaseModel):
    id: str = ""
    text: str
    references: list[str] = Field(default_factory=list)  # node IDs from the analysis


class WatchOut(BaseModel):
    items: list[WatchOutItem]


# ── Step 2: Logic ─────────────────────────────────────────────────────────────

class GlobalAnalysisItem(BaseModel):
    id: str = ""
    aspect: str
    summary: str
    seeds: SeedsRef
    proven_by: list[ProvenByRef] = Field(default_factory=list)  # computed at assembly, not by LLM


class SteelManItem(BaseModel):
    counterargument: str  # strongest possible challenge to the author's reasoning
    seeds: SeedsRef       # which premise/assumption/blind_spot/logical_reasoning is most vulnerable
    alternative_conclusion: str  # conclusion that would follow if the counterargument holds


class PremisseItem(BaseModel):
    id: str = ""
    statement: str  # the premise in one sentence
    quality: str    # assessment of evidential grounding (solid data, weak analogy, anecdote, etc.)


class LogicalReasoningItem(BaseModel):
    id: str = ""
    step: str
    problem_type: Literal["validity", "soundness"] | None = None
    diagnosis: str | None = None


class AnalysisFond(BaseModel):
    main_claim: str
    premisses: list[PremisseItem]
    implicit_assumptions: list[ImplicitAssumption]
    blind_spots: list[BlindSpot]
    emphasis: list[str]
    logical_reasoning: list[LogicalReasoningItem]
    observations: list[GlobalAnalysisItem]
    steel_man: list[SteelManItem]

    @field_validator("implicit_assumptions", mode="before")
    @classmethod
    def _coerce_implicit_assumptions(cls, v: list) -> list:
        result = []
        for item in v:
            if isinstance(item, str):
                result.append({"id": "", "statement": item, "impact": ""})
            elif isinstance(item, dict) and "text" in item and "statement" not in item:
                result.append({"id": item.get("id", ""), "statement": item["text"], "impact": ""})
            else:
                result.append(item)
        return result

    @field_validator("blind_spots", mode="before")
    @classmethod
    def _coerce_blind_spots(cls, v: list) -> list:
        result = []
        for item in v:
            if isinstance(item, str):
                result.append({"id": "", "topic": item, "significance": ""})
            elif isinstance(item, dict) and "text" in item and "topic" not in item:
                result.append({"id": item.get("id", ""), "topic": item["text"], "significance": ""})
            else:
                result.append(item)
        return result


# ── Step 3: Rhetoric ──────────────────────────────────────────────────────────

class EmotionalRegister(BaseModel):
    id: str = ""
    emotion: str
    how: str
    effect: str
    seeds: SeedsRef


class CuiBono(BaseModel):
    id: str = ""
    beneficiary: str
    explanation: str
    seeds: SeedsRef


class AnalyseForme(BaseModel):
    emotional_register: list[EmotionalRegister]
    cui_bono: list[CuiBono]
    cadrage: Cadrage  # title analysis — moved here from former Frame step


# ── Step 4: Probe ─────────────────────────────────────────────────────────────

class ExternalSource(BaseModel):
    name: str
    supports: Literal["validates", "contradicts", "neutral"]
    evidence_type: Literal["official_data", "testimony", "academic", "media", "party_statement"]


class ClaimAndSource(BaseModel):
    id: str = ""
    quote: str
    presentation: Literal["presented_as_established_fact", "attributed_to_source", "opinion_stated_as_fact"]
    proves: ProvesRef
    explanation: str
    external_sources: list[ExternalSource]
    confidence: int | None = None

    @computed_field
    @property
    def confidence_label(self) -> str:
        if self.confidence is None: return "unverifiable"
        if self.confidence <= 20: return "false"
        if self.confidence <= 40: return "likely false"
        if self.confidence <= 60: return "disputed"
        if self.confidence <= 80: return "likely true"
        if self.confidence <= 90: return "true"
        return "consensual"


class FactsVsOpinions(BaseModel):
    claims_and_sources: list[ClaimAndSource]


class BiasRhetoric(BaseModel):
    id: str = ""
    quote: str
    item_type: Literal["bias", "fallacy"]
    label: str
    effect: str
    proves: ProvesRef


class Focus(BaseModel):
    quote: str
    proves: ProvesRef
    analysis: str


class BiasesAndFocus(BaseModel):
    biases_and_rhetoric: list[BiasRhetoric]
    focus: Focus


# ── Step 5: Ethics ────────────────────────────────────────────────────────────

class DeontologyViolation(BaseModel):
    id: str = ""
    category: Literal[
        "source_endangerment",
        "hate_speech",
        "presumption_of_innocence",
        "fabrication",
        "fact_inversion",
        "misleading_title",
        "lying_by_omission",
        "decontextualized_quote",
        "hidden_commercial_interest",
        "conflict_of_interest",
        "false_statistics",
        "astroturfing",
        "privacy",
        "victim_exploitation",
        "identity_misrepresentation",
        "false_balance",
        "right_of_reply",
        "sensationalism",
        "stereotyping",
    ]
    label: str       # English display label
    severity: Literal["critical", "significant", "minor"]
    status: Literal["violation", "caution"]
    evidence: str    # verbatim quote or specific passage from the article
    explanation: str  # in French — why this crosses or approaches the line


class DeontologyVerdict(BaseModel):
    overall: Literal["clean", "caution", "violation"]
    editorial_note: str | None = None


class Deontology(BaseModel):
    violations: list[DeontologyViolation]  # empty = clean
    verdict: DeontologyVerdict
    summary: str  # 1–2 sentences in French: global overview, explicit clean/not-clean statement


# ── Step 6: Review ────────────────────────────────────────────────────────────

class ResourceReference(BaseModel):
    title: str
    source: str
    media_type: Literal["article", "report", "book", "documentary", "film", "serie", "video", "podcast", "academic_paper", "other"]
    why_explore: str
    url: str | None = None


class ReviewDimension(BaseModel):
    dimension: Literal[
        "source_rigor",
        "reasoning_structure",
        "approach_transparency",
        "treatment_fairness",
        "clarity",
        "angle_originality",
    ]
    label: str
    score: int      # 1 (very weak) to 5 (exemplary)
    rationale: str
    lesson: str


class ReviewVerdict(BaseModel):
    quality: Literal["exemplary", "solid", "adequate", "instructive_by_contrast", "weak"]
    reading_recommendation: Literal["recommended", "with_reservations", "not_recommended"]
    for_whom: str
    payoff: str
    signature_move: str
    main_blind_side: str
    further_resource: ResourceReference
    summary: str  # 1–2 sentences in French: reader-facing verdict combining recommendation + for_whom + payoff


class Review(BaseModel):
    dimensions: list[ReviewDimension]  # exactly 6, one per dimension
    verdict: ReviewVerdict


# ── Step 7: Blend ─────────────────────────────────────────────────────────────

class BlendPattern(BaseModel):
    text: str
    layers: list[str]  # which analysis layers this spans, e.g. ["logic", "rhetoric", "probe"]
    references: list[str]  # node IDs from the analysis


class Blend(BaseModel):
    patterns: list[BlendPattern]  # up to 8, each spanning ≥2 layers


# ── Step 8: Distill ───────────────────────────────────────────────────────────

class Distill(BaseModel):
    points: list[DistillPoint]  # 3–5, most important first
    open_question: str

    @field_validator("points", mode="before")
    @classmethod
    def _coerce_distill_points(cls, v: list) -> list:
        return [{"text": item, "references": []} if isinstance(item, str) else item for item in v]


# ── Step 9: Guide ─────────────────────────────────────────────────────────────

class Perspective(BaseModel):
    framing: str      # zoom in — how the article frames its subject: angle, emphasis, what it foregrounds
    blind_spots: str  # zoom out — what's structurally absent or minimized, and why it matters
    balance: str      # contextualizes the criticism: format constraints, genre expectations, editorial line


class ReadingGuide(BaseModel):
    pre_reading: list[str]    # orientation tips for the reader before reading
    watch_out: WatchOut       # grounded in actual findings, with node ID references
    after_reading: list[str]  # key takeaways after reading
    title_note: str | None = None  # notable cadrage insight worth flagging to the reader
    perspective: Perspective  # framing + blind_spots + balance note


# ── Composite structures ──────────────────────────────────────────────────────

class Analysis(BaseModel):
    fond: AnalysisFond
    forme: AnalyseForme


class Annotations(BaseModel):
    facts_vs_opinions: FactsVsOpinions
    biases_and_focus: BiasesAndFocus


class ArticleFullAnalysis(BaseModel):
    article_metadata: ArticleMetadata
    extraction: ArticleExtraction | None = None
    context: Context
    analysis: Analysis
    annotations: Annotations
    deontology: Deontology | None = None
    review: Review | None = None
    blend: Blend | None = None
    distill: Distill | None = None
    guide: ReadingGuide | None = None
