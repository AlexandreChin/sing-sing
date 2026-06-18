from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, computed_field, field_validator


# ── Cross-reference types ─────────────────────────────────────────────────────

class ProvesRef(BaseModel):
    type: Literal["observation", "emotional_register", "cui_bono"]
    label: str  # must match aspect / emotion / beneficiary in the referenced item


class SeedsRef(BaseModel):
    source: Literal["watch_out", "context", "important_fact", "premisse", "implicit_assumption", "blind_spot", "logical_reasoning"]
    index: int   # 0-based position in the source list
    excerpt: str  # short snippet for human readability


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
    """What the argument silently requires to be true. Single-line in carousel, two-field in richer formats."""
    id: str = ""
    statement: str  # the assumption itself (one sentence)
    impact: str     # what breaks if the assumption is wrong

    def __str__(self) -> str:
        return self.statement


class BlindSpot(BaseModel):
    """An angle absent or minimised in the article. Single-line in carousel, two-field in richer formats."""
    id: str = ""
    topic: str        # what is absent or downplayed
    significance: str  # why it matters to the conclusion

    def __str__(self) -> str:
        return self.topic


class SynthesisPoint(BaseModel):
    """One key takeaway from the analysis, with explicit back-references to the nodes that support it."""
    text: str
    references: list[str] = Field(default_factory=list)  # node IDs: obs_N, claim_N, bias_N, er_N, cb_N, focus

    def __str__(self) -> str:
        return self.text


class FullAnalysisInput(BaseModel):
    body: str
    title: str | None = None
    url: HttpUrl | None = None
    source: str | None = None
    published_at: str | None = None


class ArticleMetadata(BaseModel):
    url: HttpUrl | None = None
    title: str | None = None
    source: str | None = None
    published_at: str | None = None
    article_type: Literal["editorial", "news_report", "opinion", "investigation", "interview", "other"] | None = None
    reading_time_minutes: int | None = None
    article_title: str | None = None   # original article title extracted from body
    article_chapo: str | None = None   # lead paragraph extracted from body


# Extraction (promoted from step 1)
class AuthorityAnchor(BaseModel):
    entity: str    # person, organization, or institution cited
    used_for: str  # which claim or argument it legitimizes


class ArticleExtraction(BaseModel):
    authority_anchors: list[AuthorityAnchor]
    key_quotes: list[str]
    notable_omissions: list[str]
    rhetorical_patterns: list[str]


# Partie 1
class Hook(BaseModel):
    topic: str
    sub_topic: str
    headline: str
    context_line: str


# Partie 2
class Interest(BaseModel):
    why_read: str
    pull_quote: str | None = None
    next_slide_hook: str


# Partie 3 (cadrage)
class TitleAnalysisItem(BaseModel):
    label: str        # short label for the rhetorical device or framing technique (1–2 words)
    observation: str  # analytical observation on the title (post-reading)


class Cadrage(BaseModel):
    title_bullets: list[str] = []              # pre-reading watch-out tips on title rhetoric (slide 3)
    title_analysis: list[TitleAnalysisItem] = []  # post-reading analytical observations on title framing (slide 5)
    chapo_bullets: list[str] = []              # 2–3 bullet observations about how the CHAPO frames the reader


# Partie 4 (context)
class TermDefinition(BaseModel):
    term: str
    definition: str


class Context(BaseModel):
    contexts: list[TextItem]
    who_is_speaking: list[str]
    important_facts: list[TextItem]
    key_terms: list[TermDefinition]
    next_slide_hook: str

    @field_validator("contexts", "important_facts", mode="before")
    @classmethod
    def _coerce_text_items(cls, v: list) -> list:
        return [{"id": "", "text": item} if isinstance(item, str) else item for item in v]


# Partie 5 (watch_out)
class WatchOutItem(BaseModel):
    id: str = ""
    text: str
    refers_to: Literal["analysis_fond", "analysis_forme", "facts_vs_opinions", "biases_and_focus"]


class WatchOut(BaseModel):
    items: list[WatchOutItem]
    next_slide_hook: str


# Partie 6 (analysis_fond)
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
    problem_type: Literal["validity", "soundness"] | None = None  # validity = conclusion doesn't follow; soundness = premise is false/poorly grounded
    diagnosis: str | None = None


class AnalysisFond(BaseModel):
    main_claim: str
    premisses: list[PremisseItem]
    implicit_assumptions: list[ImplicitAssumption]
    blind_spots: list[BlindSpot]
    emphasis: list[str]            # what the author foregrounded disproportionately (1–3)
    logical_reasoning: list[LogicalReasoningItem]
    observations: list[GlobalAnalysisItem]
    steel_man: list[SteelManItem]  # strongest challenges to the author's argument (1–4)

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


# Partie 7 (analysis_forme)
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
    next_slide_hook: str


# Partie 8 (facts_vs_opinions)
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


# Partie 9 (biases_and_focus)
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
    next_slide_hook: str


# Partie 10
class Synthesis(BaseModel):
    points: list[SynthesisPoint]  # 1–5, sorted most important first
    open_question: str  # analytical question from bias analysis (displayed first on slide 8)
    engagement_question: str  # reader engagement CTA (displayed second on slide 8)

    @field_validator("points", mode="before")
    @classmethod
    def _coerce_synthesis_points(cls, v: list) -> list:
        return [{"text": item, "references": []} if isinstance(item, str) else item for item in v]


# Partie 11
class GoFurtherItem(BaseModel):
    title: str
    source: str
    media_type: Literal["article", "report", "book", "documentary", "film", "video", "podcast", "academic_paper", "other"]
    category: Literal["deep_dive", "question_answer"]
    url: str | None = None
    duration_minutes: int | None = None
    why_explore: str
    cta_question_index: int | None = None  # index into cta.post_reading_questions; replaces text duplication


class GoFurther(BaseModel):
    items: list[GoFurtherItem]


# Partie 12
class PostReadingQuestion(BaseModel):
    id: str = ""
    question: str
    type: Literal["article_quality", "topic_substance", "reader_bias", "blind_spot"]


class CTA(BaseModel):
    engagement_sentence: str
    post_reading_questions: list[PostReadingQuestion]  # exactly 2


class ArticleFullAnalysis(BaseModel):
    article_metadata: ArticleMetadata
    extraction: ArticleExtraction | None = None  # promoted from step 1; None for older outputs
    hook: Hook
    interest: Interest
    cadrage: Cadrage
    context: Context
    watch_out: WatchOut
    analysis_fond: AnalysisFond
    analysis_forme: AnalyseForme
    facts_vs_opinions: FactsVsOpinions
    biases_and_focus: BiasesAndFocus
    synthesis: Synthesis
    go_further: GoFurther
    cta: CTA
