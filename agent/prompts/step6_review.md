STEP 6/9 — REVIEW

The full analysis is available above, including the Ethics audit.
Evaluate the quality of this content (article, editorial, documentary, video, report…) across
6 dimensions, then produce a verdict that tells the reader directly whether it is worth their time.

---

## Dimensions — produce exactly 6, one per key, in this order:

1. source_rigor          — Label: "Source Rigor"
2. reasoning_structure   — Label: "Reasoning Structure"
3. approach_transparency — Label: "Approach Transparency"
4. treatment_fairness    — Label: "Treatment Fairness"
5. clarity               — Label: "Clarity"
6. angle_originality     — Label: "Angle & Originality"

For each dimension:

- dimension : the exact machine key above
- label     : the exact English label above
- score     : integer 1 (very weak) to 5 (exemplary)
- rationale : in French — justifies the score explicitly: what earns it (strengths),
              what caps it (gaps or failures). Must cite at least one specific item from
              the analysis above by field name or verbatim quote. 2–3 sentences.
- lesson    : in French — one actionable insight a critical reader can draw, stated as
              a practical rule. Starts with a verb.

Evidence mapping:

| Dimension              | Primary evidence fields                                                                   |
|------------------------|-------------------------------------------------------------------------------------------|
| source_rigor           | `annotations.facts_vs_opinions.claims_and_sources`, `extraction.authority_anchors`        |
| reasoning_structure    | `analysis.fond.logical_reasoning`, `analysis.fond.premisses`                              |
| approach_transparency  | `analysis.fond.blind_spots`, `analysis.fond.implicit_assumptions`                         |
| treatment_fairness     | `annotations.biases_and_focus.biases_and_rhetoric`, `annotations.biases_and_focus.focus`  |
| clarity                | `analysis.forme.cadrage.title_analysis`, `context.key_terms`                              |
| angle_originality      | `analysis.fond.observations`, `analysis.fond.emphasis`, `analysis.fond.steel_man`         |

What each dimension covers:

source_rigor
  Diversity, independence, attribution quality. Single-source claims on heavy accusations?
  Anonymous sources justified? Expert authority earned or merely invoked?

reasoning_structure
  Coherence between premises, arguments, conclusions. Inferences valid? Logical jumps
  concealed or signalled? Is the argumentative chain legible?

approach_transparency
  Does the content make its POV, method, and limits explicit? Fact vs. interpretation
  vs. judgment clearly distinguished? Omissions acknowledged or silent?

treatment_fairness
  Fair voice for concerned parties? Complexity respected or flattened? Vocabulary or
  framing asymmetry across protagonists?

clarity
  Structure readable? Technical concepts explained? Examples anchor the abstract?
  Register appropriate for the intended audience?

angle_originality
  Fresh perspective, unique access, original framing? Or recycled coverage without added value?

---

## Verdict — reader-facing recommendation

The verdict answers one question: **is this worth the reader's time, and for whom?**
It evaluates journalistic CRAFT, not content — do not restate items from the analysis.
Account for the Ethics findings: a piece with a critical ethics violation
cannot be `reading_recommendation: "recommended"`.

- quality : "exemplary" | "solid" | "adequate" | "instructive_by_contrast" | "weak"
  Must match the dimension score average:
  exemplary ≥ 4.5 · solid 3.5–4.4 · adequate 2.5–3.4
  instructive_by_contrast < 2.5 but pedagogically rich · weak < 2.5, no redeeming value

- reading_recommendation : "recommended" | "with_reservations" | "not_recommended"
  Direct verdict for the reader. Must be consistent with `quality` and the Ethics findings:
  - "not_recommended" if ethics has any critical violation
  - "with_reservations" if ethics has cautions, or quality is "adequate" or below
  - "recommended" only if quality is "solid" or above AND ethics is clean

- for_whom : in French — 1 sentence naming the specific reader profile who gets most
  from this. Not generic ("tout lecteur curieux") — concrete: professional background,
  prior knowledge required, reason this piece serves them specifically.

- payoff : in French — 1–2 sentences on what the reader concretely gains from reading.
  Not a summary of the article — a value statement: what they will understand, see, or
  be able to do differently after reading.

- signature_move : in French — 1 sentence on the single most distinctive editorial or
  rhetorical technique of this piece; what makes it recognisable as a product of a
  certain journalistic tradition or school.

- main_blind_side : in French — 1 sentence on the most instructive gap and what its
  absence reveals about editorial choices or production constraints.

- further_resource : one reference (book, documentary, article, course, video…) that puts
  this piece's approach in perspective.

- summary : in French — 1 to 2 sentences for the reader. Plain language, no jargon.
  Combines `reading_recommendation`, `for_whom`, and `payoff` into a single direct verdict.
  Example: "Lecture recommandée pour qui suit ce dossier de près : l'article apporte des
  données solides, mais le cadrage mérite d'être mis en perspective avec d'autres sources."
  Fields: title, source, media_type, why_explore (1 sentence, in French), url (or null).
