# Carousel Agent — Specification

## Purpose

An agent that takes a news article (plain text or URL) and produces a structured output designed
to be turned into an Instagram carousel in French. The carousel has exactly five slides; each slide
maps to a discrete analytical task that must be independently well-formed.

The article URL (when provided) is stored in the output so it can be linked in the carousel.

---

## Carousel Structure

### Slide 1 — Hook

**Goal:** Stop the scroll. Make the reader feel "I need to see the rest of this."

The hook frames what the article is _really_ about — but it does not imply the article is
necessarily controversial. Some articles are straightforwardly important, surprising, or little covered. The hook reflects that honestly.

**Content:**

- A short headline (≤ 12 words) that captures the core tension, surprise, or significance
- One sub-line of context (≤ 20 words): who published it, when, and why it matters right now
- **Why read it** (1–2 sentences): what makes this article worth reading — could be the topic
  itself, the angle chosen, how it is written, what it reveals about media treatment of this
  subject, or why it is a good example to dissect
- An optional short pull-quote from the article if it is itself revealing or striking

**Tone:** Bold, direct. Not sensationalist.

---

### Slide 2 — Before You Read

**Goal:** Give the reader the background they need to read the article critically. After this
slide, they should feel **aware and sharp** — like they already know things most readers don't.

Four named lists, each with 1–3 short items (1 sentence each):

- **`contexts`** — The broader situation this article sits inside; what happened before
- **`who_is_speaking`** — Who produced this piece: outlet positioning, funding, editorial line, and (if signed) the author's background, known positions, track record on this topic. For unsigned editorials: the institution, its line, what signing collectively implies
- **`important_facts`** — Key facts the reader needs to assess the article; can be absent from the article entirely
- **`key_terms`** — Brief plain-language definitions of terms used in the article or the analysis that the reader may not know: acronyms, organizations, legal concepts, proper nouns. Each item: `term` + `definition` (1 sentence)
- **`watch_out`** — 2–4 reading instructions: "as you read, pay attention to X." Each item points to something specific in this article — a named source, a person, a pattern, an event — without stating the conclusion. Specific enough to be a real clue, open enough that the reader feels they found it themselves. The conclusion comes in `global_analysis`
- **`questions`** — Questions the reader carries into the article, before reading. Must make sense without prior knowledge of the content — about the topic, the context, or the stakes, not about what the article says. Framed to orient attention, not to anticipate conclusions

**Writing style:** Present facts and context as observations the reader can verify themselves
("the article was published one day after...", "the outlet's funding comes from..."). Avoid
conclusions — lay the groundwork and let the reader connect the dots. They should feel like they
figured it out, not like they were told what to think.

---

### Slide 3 — Global Analysis

**Goal:** Give the reader a clear picture of how the author treated the topic as a whole. After
this slide, the reader should feel like they have a fresh, sharper read on the article — one they
could not have reached by reading it passively.

**Link to slide 2:** Three fields from Before You Read must find their answer or confirmation here:

- `contexts` — at least one global item should address what the article does (or doesn't do) with the context provided
- `important_facts` — if a fact is absent from the article, at least one global item should name what that absence reveals about the framing
- `watch_out` — each watch_out item should be addressed by a global item showing its significance across the whole article

`questions` are also addressed here (as before). `source_profile` and `author` stay as standalone background — they inform how to read the analysis but don't require a global item.

The reader should feel like they had the right instinct.

**Writing style:** Never state verdicts. Write as neutral observations, not judgments. "The piece
opens and closes on the same image of X" rather than "the author manipulates the reader." The
reader should arrive at the implication themselves.

**Three sub-sections, all part of `global_analysis`:**

#### `observations` (3–5 items)

Each item: `aspect` (1 word) + `summary` (1–2 sentences, no quote). Address only what is genuinely relevant — framing, tone, omissions, rhetoric, who is centered/sidelined.

#### `emotional_register` (1–3 items)

What emotions the article is designed to produce, how, and what they prime the reader toward. Not a judgment — a description. Each item: `emotion` + `how` (1 sentence: the technique) + `effect` (1 sentence: what it primes).

#### `cui_bono` (1–3 items)

Who benefits from the framing adopted. Structural observation, not conspiracy framing. Each item: `beneficiary` + `explanation` (1–2 sentences).

---

### Slide 4 — Local Annotations

**Goal:** Show the reader exactly where in the text the global observations are visible. The
reader sees the quote, sees the observation, and arrives at the conclusion themselves. They should
feel like they are the ones doing the close reading.

**Link to slides 2 and 3:** Each annotation must anchor a specific item from `global_analysis`
(an observation, an emotional register item, or a cui bono item) in the text — which itself
answered a seed from slide 2. The full chain: slide 2 plants → slide 3 frames → slide 4 proves
in the text. The reader should be able to trace that thread without effort.

**Writing style:** Same as slide 3 — observations over verdicts. Show, don't tell. End each
annotation before the conclusion; leave the last step to the reader.

The slide has three annotation types, presented in this order:

#### 4.1 Claims & Sources

2–4 verbatim quotes that let the reader check a factual or sourcing issue themselves. For each:

- `quote`: verbatim from the article
- `presentation`: how the claim is **presented in the article**, independent of whether it is true. One of: `presented_as_established_fact` (no attribution, stated as obvious or certain), `attributed_to_source` (credited to a named or unnamed source)
- `explanation`: 1 plain-language sentence — what the issue is and where the reader could verify it
- `external_sources`: 1–3 legitimate external sources (institutions, official reports, academic work, established media) that validate or contradict the claim. Named specifically — not "experts say"
- `confidence`: estimated probability the claim is factually true. `null` = unverifiable (no means to assess regardless of sourcing). Integer scale: 0–20 false, 20–40 opinion stated as fact, 40–60 disputed, 60–80 likely true, 80–90 true, 90+ consensual.

  **Scoring methodology — three factors in order of importance:**

  1. **Evidence tangibility** (most important): raw data, official documents, measurements, or auditable records are the strongest basis. A claim backed only by assertions — even from a credible source — should stay below 60 unless corroborated by other factors.

  2. **Disinterested testimony**: multiple converging testimonies from people with no material interest to fabricate are strong probabilistic evidence, even without hard documents. Key criteria: independence between witnesses and absence of incentive to lie. Several concordant testimonies from unrelated, disinterested sources can push a score into the 60–80 range even without tangible documents.

  3. **Source credibility** (least important on its own): international institutions (UN, ICJ, WHO...) and peer-reviewed work carry more weight than NGOs, which carry more than interested parties. Credibility alone — without tangible evidence or disinterested testimony — cannot push a score above 50.

  **Critical asymmetry rule:** A denial or contestation without a published counter-methodology, counter-data, or alternative auditable count does NOT symmetrically offset documented evidence. An official denial with no supporting evidence weighs far less than a documented convergent source. Two independent organizations arriving at similar figures via separate documented methodologies is strong evidence — score accordingly even if an interested party disputes it without transparency.

  **Convergence bonus:** When two or more sources with independent methodologies reach the same conclusion, this is materially stronger than one source saying the same thing twice. Independent convergence should push the score upward.

  **Additional scoring criteria:**

  4. **Adversarial partial corroboration** (very high weight when it occurs): when a party whose interests oppose the claim nonetheless partially confirms it, this is among the strongest possible evidence. A concession from an opposing party is hard to fake and rarely accidental — it should push the score up significantly even if the concession is partial.

  5. **True independence of the evidentiary chain**: two sources that appear independent may both draw from the same upstream pool — the same NGO intake process, the same group of testimonies, the same journalist contact. Trace whether the evidence paths genuinely diverge at the origin. Convergence from truly separate chains is much stronger than the same upstream source appearing twice under different names.

  6. **Specificity of the claim**: specific, falsifiable claims ("100 deaths between date X and date Y") are harder to fabricate and easier to verify than vague ones ("conditions are degrading"). Higher specificity with consistent detail across independent sources should raise the score; vagueness or inability to be falsified should lower it.

  7. **Source track record on similar claims**: has this source been proven right or wrong in comparable past claims? A documented history of accuracy on this type of claim is evidence about future reliability. A source making this kind of assertion for the first time, or one with a history of errors in similar cases, should be discounted.

  8. **Physical/geographic verifiability**: claims about locations, measurable quantities, or physical events are in principle more checkable (satellite imagery, GPS, official registries) than claims about intentions, private decisions, or internal states. Structural verifiability — even if not yet verified — should push the score up; structural unverifiability should push it down.

  9. **Base rate**: how often are similar claims true in comparable contexts? If systematic mistreatment in wartime detention is well-documented historically (Abu Ghraib, Guantánamo, etc.), the prior probability of this type of claim being true is higher than for a novel, unprecedented allegation. Calibrate against the base rate of similar claims in similar situations.

  10. **Contemporaneous documentation**: was the claim documented at the time of the events (reports filed during the period, medical records at release, contemporaneous testimony) or reconstructed retrospectively? Contemporaneous documentation is more reliable — retrospective accounts are more susceptible to distortion, memory effects, and motivated reasoning. A large gap between events and documentation should lower the score.

- `confidence_label`: human-readable label matching the score range — "unverifiable", "false", "opinion stated as fact", "disputed", "likely true", "true", or "consensual"

#### 4.2 Biases & Rhetorical Moves

1–3 verbatim quotes that make a global pattern visible. For each:

- Verbatim quote from the article
- Plain-language label (e.g., "cherry-picking", "false equivalence", "emotional language") —
  no Latin names or academic jargon
- One sentence describing the effect on the reader, framed as an observation
  ("notice how this makes X seem inevitable") rather than a verdict

#### 4.3 Quote Deep Dive

One single quote: the most important or revealing sentence in the article — the line that most
concentrates the author's intent, a key claim, or a striking formulation.

Unpack it in 3–5 short sentences: what it literally says, what it implies, what it leaves unsaid,
and why that gap matters. Write it as guided close reading — walk the reader through it step by
step so they feel like they are the ones making the discovery. End on an open observation, not a
verdict.

No label or status field. Free-form prose, plain language.

---

### Synthesis (`synthesis`)

**Goal:** Land the reader after the analysis without telling them what to conclude. 3 short observations that surface the tensions, gaps, or questions left open by the article and the analysis. Each one opens a door — the reader walks through it themselves.

Written as neutral observations, not verdicts. No "donc", no "en conclusion", no "cet article prouve que". Stop one step before the conclusion every time.

Each point: 1–2 sentences maximum.

---

### Slide 5 — Go Further + Post-reading Questions

**Goal:** Give the reader the next concrete step — a specific piece worth exploring, tied to either a deep dive on the article's core topic or a direct answer to one of the post-reading questions. Any media format is valid: article, report, book, documentary, film, video, podcast, academic paper.

**Content (4–6 items):**

- `title` — title of the piece
- `source` — outlet, author, or institution
- `media_type` — `article` / `report` / `book` / `documentary` / `film` / `video` / `podcast` / `academic_paper` / `other`
- `category` — `deep_dive` (goes deeper on a topic central to the article) or `question_answer` (directly helps answer one of the post-reading questions, including `blind_spot` questions)
- `url` — if available
- `duration_minutes` — estimated reading/watching/listening time
- `why_explore` — 1 sentence: what this adds and why it is worth the time
- `answers_question` — if `question_answer`: the verbatim question from `post_reading_questions` it helps answer

**Tone:** Helpful, non-partisan. Not a bibliography — each item should feel like a personal recommendation.

### Post-reading Questions (`post_reading_questions`)

3–5 questions whose answers drive the reader's conclusion about the article — not about the world in general. Each question points to a reading judgment: do I find this argument convincing? Do I trust this source? Does this framing seem honest? The answer should lead somewhere: "I find this article reliable / partial / incomplete / useful despite its limits."

Frame them so the reader can answer "yes", "no", or "it depends" — and each answer leads somewhere different. Questions must not be leading: a reader who found the article convincing should be able to answer as naturally as a sceptical one. Avoid formulations that presuppose a critical conclusion ("given that...", "despite the absence of...", "although...").

Some questions should help the reader confront their own biases and inconsistencies: would they apply the same standards if the actors were different? Would they have read this article differently if the source were other? Is their reaction to the content consistent with how they usually evaluate articles? These questions don't point toward an answer — they create productive discomfort.

Others should be about the substance of the article's subject itself — not its form or its author. The reader should be able to take a position on the core issue, not just on the journalistic quality of the piece.

At least one question should be a `blind_spot` — it points the reader toward something the article, and the carousel analysis itself, did not address. It names an angle, a voice, or a question that would require the reader to go look for themselves. It is not answerable from the article or the carousel alone — it is an invitation to investigate further.

Each question must be anchored in something the analysis surfaced — a fact, a source, a bias, an omission. No abstract questions about European policy or the broader conflict. The `quote_deep_dive` must not reference other slides by number — it must read as self-contained prose.

---

## Carousel Consistency Contract

The full chain that must hold across all slides:

```
before_you_read.contexts        ──→ global_analysis.observations
before_you_read.important_facts ──→ global_analysis.observations   (absence reveals framing)
before_you_read.watch_out       ──→ global_analysis.observations
before_you_read.questions       ──→ global_analysis (confirmed or answered)

global_analysis.observations        ──→ local_annotations (claims_and_sources or biases_and_rhetoric)
global_analysis.emotional_register  ──→ local_annotations.biases_and_rhetoric
global_analysis.cui_bono            ──→ local_annotations (any)

local_annotations (all)   ──→ must trace back to a global_analysis item
synthesis.points          ──→ must trace back to global_analysis or local_annotations
post_reading_questions    ──→ must trace back to something surfaced in slides 3–4
```

**No orphans in either direction.** Every slide 2 seed lands in slide 3. Every slide 3 item is proved in slide 4. Every slide 4 annotation proves something from slide 3. Synthesis and post-reading questions close the loop — they do not introduce new subjects.

---

## Input

```python
class CarouselInput(BaseModel):
    body: str               # full article text (plain text)
    title: str | None = None
    url: HttpUrl | None = None   # stored in output for carousel linking
    source: str | None = None    # media outlet name
    published_at: str | None = None
```

Both `body` and `url` are optional independently — the agent accepts either or both. At least one
must be provided.

---

## Output Schema

```python
class Hook(BaseModel):
    headline: str                    # ≤ 12 words
    context_line: str                # ≤ 20 words
    why_read: str                    # 1–2 sentences on what makes this article worth reading
    pull_quote: str | None = None    # verbatim from article

class BeforeYouRead(BaseModel):
    contexts: list[str]
    source_profile: list[str]
    important_facts: list[str]
    questions: list[str]

class GlobalAnalysisItem(BaseModel):
    aspect: str                      # short label, e.g. "tone", "omissions", "framing"
    summary: str                     # 1–2 sentences, no quote

class EmotionalRegister(BaseModel):
    emotion: str                     # e.g. "indignation", "peur", "solidarité"
    how: str                         # 1 sentence: technique that produces the emotion
    effect: str                      # 1 sentence: what it primes the reader to think or do

class CuiBono(BaseModel):
    beneficiary: str                 # who benefits from this framing
    explanation: str                 # 1–2 sentences

class GlobalAnalysis(BaseModel):
    observations: list[GlobalAnalysisItem]        # 3–5 items
    emotional_register: list[EmotionalRegister]   # 1–3 items
    cui_bono: list[CuiBono]                        # 1–3 items

class ExternalSource(BaseModel):
    name: str
    supports: Literal["validates", "contradicts", "neutral"]
    evidence_type: Literal["official_data", "testimony", "academic", "media", "party_statement"]
    url: HttpUrl | None = None
    reading_time_minutes: int | None = None
    why_read: str | None = None      # 1 sentence: what this source adds

class ClaimOrSourceAnnotation(BaseModel):
    quote: str
    presentation: Literal["presented_as_established_fact", "attributed_to_source"]
    explanation: str                 # plain language, 1 sentence
    proves: str                      # aspect/emotion/beneficiary of the global item this anchors
    external_sources: list[ExternalSource]
    confidence: int | None           # null=unverifiable; scale: 0-20 false, 20-40 opinion as fact,
                                     # 40-60 disputed, 60-80 likely true, 80-90 true, 90+ consensual
    confidence_label: str

class BiasOrRhetoricalAnnotation(BaseModel):
    quote: str
    label: str                       # plain-language name, no jargon
    effect: str                      # 1 sentence, framed as observation
    proves: str                      # aspect/emotion/beneficiary of the global item this anchors

class QuoteDeepDive(BaseModel):
    quote: str
    analysis: str                    # 3 sentences max: what it says, implies, omits
    proves: str                      # aspect of the global item this anchors

class LocalAnnotationsSlide(BaseModel):
    claims_and_sources: list[ClaimOrSourceAnnotation]     # 2–4 items
    biases_and_rhetoric: list[BiasOrRhetoricalAnnotation] # 1–4 items
    quote_deep_dive: QuoteDeepDive                        # exactly 1

class GoFurtherItem(BaseModel):
    title: str
    source: str
    media_type: Literal["article", "report", "book", "documentary", "film", "video", "podcast", "academic_paper", "other"]
    category: Literal["deep_dive", "question_answer"]
    url: HttpUrl | None = None
    duration_minutes: int | None = None   # reading/watching/listening time
    why_explore: str                      # 1 sentence: what this adds and why it's worth the time
    answers_question: str | None = None   # verbatim question it helps answer

class ArticleMetadata(BaseModel):
    url: HttpUrl | None = None
    title: str | None = None
    source: str | None = None
    published_at: str | None = None
    article_type: Literal["editorial", "news_report", "opinion", "investigation", "interview", "other"] | None = None

class ArticleReliability(BaseModel):
    score: int                       # 0–100, same scale as confidence
    label: str                       # "unreliable", "partial", "mixed", "mostly reliable", "reliable"
    rationale: str                   # 1 sentence

class Synthesis(BaseModel):
    points: list[str]                # exactly 3 — open observations, no verdicts

class PostReadingQuestion(BaseModel):
    question: str
    type: Literal["article_quality", "topic_substance", "reader_bias", "blind_spot"]

class CarouselOutput(BaseModel):
    article_metadata: ArticleMetadata            # passed through from input
    hook: Hook                                   # slide 1
    before_you_read: BeforeYouRead               # slide 2
    global_analysis: GlobalAnalysis              # slide 3
    local_annotations: LocalAnnotationsSlide     # slide 4
    synthesis: Synthesis                         # slide 4 closer — 3 open observations
    go_further: list[GoFurtherItem]              # slide 5 — 4–6 items, any media format
    post_reading_questions: list[PostReadingQuestion]  # slide 5 — 3–6 questions
```

---

## Implementation Plan

### Phase 1 — Plain text + URL input (now)

1. Add `CarouselInput`, `CarouselOutput` and sub-models to a new `models/carousel.py`.
2. Add a system prompt `agent/prompts/analyze_carousel.md` enforcing the structure and tone
   constraints above.
3. Add `agent/carousel_agent.py` with `analyze_for_carousel(input: CarouselInput) -> CarouselOutput`,
   mirroring `article_agent.py` (streaming + `output_config` JSON schema).
4. Add a separate entry point or CLI flag in `main.py` to invoke the carousel agent independently
   from the existing article analysis flow.

### Phase 2 — URL scraping (later)

- `scrape_article(url)` already exists in `tools/scrape.py`.
- When a URL is provided without body text, the agent scrapes it first, then analyzes.
- No new scraping logic needed.

### Phase 3 — Search-enriched further reading (future)

- Use `tools/search.py` to automatically find counterpoint articles and primary sources.
- Populate `FurtherReadingItem.url` from search results.

### Phase 4 — Cross-outlet comparison (future)

- For a given article, search for coverage of the same story by 2–3 other outlets.
- Add a `cross_outlet_comparison` field to `CarouselOutput`: each item names the outlet, its framing angle, and the key difference from the source article.
- Requires Phase 3 search integration. Particularly valuable for showing the reader that framing is a choice, not a given.

---

## Key Design Decisions

| Decision                                                 | Rationale                                                                                                                       |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 5 slides instead of 4                                    | Global and local analysis have different reading experiences — combining them created too much text and muddied the distinction |
| `article_url` passed through to output                   | Required so the carousel can link back to the original article                                                                  |
| Global analysis before local annotations                 | Global sets the frame; local proves it in the text. Reader builds the picture first, then sees it                               |
| Local annotations are evidence for global findings       | Prevents annotations from feeling like a disconnected list of nitpicks                                                          |
| Claims + sourcing merged into one annotation sub-section | Both are about factual grounding — separating them created artificial distinction                                               |
| Separate `CarouselOutput` from `ArticleAnalysis`         | Different audience, different shape, different rendering requirements                                                           |
| Plain-language labels (no Latin fallacy names)           | Target audience is general Instagram readers, not academics                                                                     |
| `status` enum forces a verdict                           | Prevents the LLM from hedging with vague prose                                                                                  |
| Verbatim quotes mandatory for local findings             | Grounds analysis in the text; prevents hallucination of patterns that aren't there                                              |
| Output language is always French                         | Fixed requirement — not a runtime parameter                                                                                     |
| Observations over verdicts throughout                    | Reader must feel like they reached the conclusion themselves — not like they were told what to think                            |
