STEP 5/9 — ETHICS

The full analysis is available above. Your job is to identify any breach of journalistic
deontology in this content (article, editorial, documentary, video, report…).

Output ONLY what you actually find. If nothing crosses a line, return an empty violations list.
Do not produce entries for categories that are clear. Every violation must be anchored to a
specific, verbatim passage from the source — if you cannot quote the article, do not flag it.

---

## Hard red lines — Tier 1 (severity: "critical")

These are unambiguous. A single instance is a violation regardless of context.

source_endangerment        — Label: "Source Endangerment"
  Information that could identify a protected source or put a person at physical risk.

hate_speech                — Label: "Hate Speech"
  Language that stigmatizes a group by race, religion, gender, origin, or sexual orientation —
  including through framing and implication, not only explicit statements.

presumption_of_innocence   — Label: "Presumption of Innocence"
  Suspects or accused persons treated as guilty before any judicial determination;
  accusatory language presented as established fact.

fabrication                — Label: "Fabrication / Misattribution"
  Quotes presented as verbatim that are invented or substantially altered; claims attributed
  to sources who said something materially different.

fact_inversion             — Label: "Fact Inversion"
  Evidence or source says X; the article presents it as not-X. Includes misread statistics,
  inverted causality, reversed study conclusions.

## Hard red lines — Tier 2 (severity: "significant")

High impact, often high intentionality. Flag as "violation" when the breach is clear;
"caution" when borderline.

misleading_title           — Label: "Misleading Title"
  The title makes a claim the article body contradicts, does not support, or substantially
  walks back. Includes headlines that assert what the article only speculates.

lying_by_omission          — Label: "Lying by Omission"
  An omission that inverts the meaning — not merely nuances it. A key finding is absent
  and its absence makes the article's central claim factually false or opposite.

decontextualized_quote     — Label: "Decontextualized Quote"
  A real source's words are truncated or reframed so the quote means the opposite of the
  speaker's intent. Distinct from fabrication — the source is real, the meaning is inverted.

hidden_commercial_interest — Label: "Hidden Commercial Interest"
  Sponsored content, advertorial, or PR material not clearly and prominently labeled as such.

conflict_of_interest       — Label: "Conflict of Interest"
  The journalist or outlet has a material stake in the subject that is either undisclosed,
  or disclosed only via a buried disclaimer (footer, small print) — not prominent enough
  for the reader to factor in before reading.

false_statistics           — Label: "False Statistics"
  Figures that are technically correct but arithmetically structured to deceive: cherry-picked
  data, incompatible denominators, misleading before/after framing, base-rate manipulation.

astroturfing               — Label: "Astroturfing"
  A coordinated campaign, PR operation, or funded advocacy presented as spontaneous public
  opinion or independent expert consensus.

privacy                    — Label: "Privacy Violation"
  Private life of individuals exposed with no credible public interest justification
  (health, family, home address, sexual life…).

victim_exploitation        — Label: "Victim Exploitation"
  Victims of violence, accident, or sexual assault named or described without consent;
  gratuitous detail; minors identifiable.

identity_misrepresentation — Label: "Identity Misrepresentation"
  The outlet presents itself as neutral or independent while being structurally funded by
  or affiliated with a political, commercial, or ideological actor — undisclosed.

## Soft red lines — (severity: "minor", status: "caution" unless severe)

These are context-dependent. Flag only when the breach is concrete and quotable.

false_balance              — Label: "False Balance"
  Fringe or scientifically discredited positions given equal weight to expert consensus.

right_of_reply             — Label: "Right of Reply"
  Serious allegations made against a person or institution with no trace of a solicited
  response.

sensationalism             — Label: "Sensationalism"
  Distressing content (death, violence, suffering) foregrounded beyond what the story requires.

stereotyping               — Label: "Stereotyping"
  Groups described through reductive or stigmatizing shorthand not anchored in the specific story.

---

## Output rules

- violations: list all breaches found, one entry per distinct breach.
  If none, return [].
- verdict.overall:
  - "clean"     — no violations or cautions
  - "caution"   — only caution-level entries, no confirmed violations
  - "violation" — at least one status="violation" entry
  Critically: if any entry has severity="critical", overall MUST be "violation".
- verdict.editorial_note: one sentence in French on what an editor must address before
  publication. Null if overall is "clean".
- summary: 1–2 sentences in French giving a global overview of the deontological picture.
  Always state explicitly whether deontology is clean or not. If clean: say so directly
  (e.g. "Aucun manquement déontologique n'a été relevé."). If not clean: name the nature
  and number of issues without repeating the full detail.
- explanation: in French — why this specific passage crosses or approaches the line.
  Be precise: name the mechanism (e.g. "l'omission du chiffre X inverse le sens de Y").
  1 sentence, ≤20 words.
