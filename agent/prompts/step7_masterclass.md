STEP 7/7 — MASTERCLASS

The full analysis is available above. Evaluate the journalistic and pedagogical quality
of this content (article, editorial, documentary, video, report…) across 6 dimensions.

Goal: what can a critical reader, journalist, or media literacy student learn from this
piece — from its strengths AND its flaws?

---

Produce exactly 6 dimension objects, one per key, in this order:

1. source_rigor         — Label: "Source Rigor"
2. reasoning_structure  — Label: "Reasoning Structure"
3. approach_transparency — Label: "Approach Transparency"
4. treatment_fairness   — Label: "Treatment Fairness"
5. clarity              — Label: "Clarity"
6. angle_originality    — Label: "Angle & Originality"

For each dimension:

- dimension : the exact machine key above
- label     : the exact English label above
- score     : integer 1 (very weak) to 5 (exemplary)
- rationale : in French — justifies the score explicitly: what earns it (strengths),
              what caps it (gaps or failures). Must cite at least one specific item from
              the analysis above — reference it by field name (e.g. "logical_reasoning[2]",
              "claims_and_sources[0]") or with a verbatim quote from the article. 2–3 sentences.
- lesson    : in French — one actionable insight a critical reader can draw from this
              dimension, stated as a practical rule. Starts with a verb.
              (Same role as `effect` on a bias: what this produces in the reader.)

Evidence mapping — for each dimension, these are the primary fields to examine
in the analysis above:

| Dimension              | Primary evidence fields                                                              |
|------------------------|--------------------------------------------------------------------------------------|
| source_rigor           | `annotations.facts_vs_opinions.claims_and_sources`, `extraction.authority_anchors`   |
| reasoning_structure    | `analysis.fond.logical_reasoning`, `analysis.fond.premisses`                         |
| approach_transparency  | `analysis.fond.blind_spots`, `analysis.fond.implicit_assumptions`                    |
| treatment_fairness     | `annotations.biases_and_focus.biases_and_rhetoric`, `annotations.biases_and_focus.focus` |
| clarity                | `cadrage.title_analysis`, `context.key_terms`                                        |
| angle_originality      | `analysis.fond.observations`, `analysis.fond.emphasis`, `analysis.fond.steel_man`    |

What each dimension covers:

source_rigor
  Diversity, independence, attribution quality. Single-source claims on heavy
  accusations? Anonymous sources justified? Expert authority earned or merely invoked?

reasoning_structure
  Coherence between premises, arguments, conclusions. Are inferences valid?
  Logical jumps — concealed or signalled? Is the argumentative chain legible?

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
  Fresh perspective, unique access, original framing? Or recycled coverage without
  added value?

---

Then produce a verdict object.

The verdict evaluates HOW the piece is made, not WHAT it says. Do not restate items already
present in `synthesis.points` or `watch_out.items` — those describe the content. The verdict
describes editorial and journalistic craft. The quality label must be consistent with the
dimension scores: exemplary ≥ 4.5 avg, solid 3.5–4.4, adequate 2.5–3.4,
instructive_by_contrast < 2.5 but pedagogically rich, weak < 2.5 with no redeeming value.

- quality          : "exemplary" | "solid" | "adequate" | "instructive_by_contrast" | "weak"
                     ("instructive_by_contrast" = worth studying precisely for its flaws)
- why_worth_reading : in French — 1–2 sentences on the concrete value this content
                      offers to an attentive reader, even if imperfect
- signature_move   : in French — 1 sentence on the single most distinctive characteristic
                     of this piece; what makes it recognisable as a product of a certain
                     journalistic tradition or editorial school
- main_blind_side  : in French — 1 sentence on the most instructive gap; what its absence
                     reveals about editorial choices or production constraints
- further_resource : one reference (book, documentary, article, course, video…) that puts
                     this piece's approach in perspective
                     Fields: title, source, media_type, why_explore (1 sentence, in French),
                     url (if verifiable, else null)
