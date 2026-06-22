STEP 8/8 — CONSISTENCY AUDIT

You have the fully assembled article analysis below. Your only job is to return a corrected
`masterclass` section that is grounded, non-redundant, and internally coherent.

Do not touch any other section of the analysis.

---

## Check 1 — Score grounding

Each dimension score must be consistent with the actual evidence found in the analysis.
Use these mappings:

| Dimension              | Fields to examine                                                                    |
|------------------------|--------------------------------------------------------------------------------------|
| source_rigor           | `annotations.facts_vs_opinions.claims_and_sources`, `extraction.authority_anchors`   |
| reasoning_structure    | `analysis.fond.logical_reasoning`, `analysis.fond.premisses`                         |
| approach_transparency  | `analysis.fond.blind_spots`, `analysis.fond.implicit_assumptions`                    |
| treatment_fairness     | `annotations.biases_and_focus.biases_and_rhetoric`, `annotations.biases_and_focus.focus` |
| clarity                | `cadrage.title_analysis`, `context.key_terms`                                        |
| angle_originality      | `analysis.fond.observations`, `analysis.fond.emphasis`, `analysis.fond.steel_man`    |

Flag and correct any score that contradicts the density or severity of evidence in its
target fields. For example: source_rigor = 4 but claims_and_sources shows five single-source
attributions with no external validation — that is an inconsistency.

## Check 2 — Non-redundancy with synthesis

The verdict fields must evaluate journalistic CRAFT, not content. Compare each verdict field
against `synthesis.points` and `watch_out.items`:

- `why_worth_reading` must explain WHY the approach is instructive — not WHAT the article says.
  If it reads as a content summary, rewrite to focus on the journalistic or analytical dimension.
- `signature_move` must name a distinctive editorial or rhetorical technique, not a factual claim.
- `main_blind_side` must reveal what the EDITORIAL CHOICES say — not just name a missing fact
  (that belongs in blind_spots). It should explain why the absence is structurally revealing.

## Check 3 — Quality enum coherence

Compute the average of the 6 dimension scores. The `quality` label must match:

- "exemplary"              : avg ≥ 4.5
- "solid"                  : avg 3.5–4.4
- "adequate"               : avg 2.5–3.4
- "instructive_by_contrast": avg < 2.5, but the piece has clear pedagogical value for its flaws
- "weak"                   : avg < 2.5, no redeeming pedagogical value

If the label contradicts the average, correct it — or justify an exception in `changes`.

---

Return:
- `masterclass`: the corrected masterclass (unchanged fields if no correction needed)
- `changes`: list of strings — one entry per correction, describing what changed and why.
  Empty list if nothing was changed.
