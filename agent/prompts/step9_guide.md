STEP 9/9 — GUIDE

The full analysis is complete: Logic, Rhetoric, Probe, Ethics, Review, Blend, and Distill
have produced their findings. Your job is to translate this picture into a reader's companion
— concrete guidance for anyone who will read or has read this article.

Speak to the reader directly. This is not analysis for an analyst; it is guidance for a reader.
Draw from the Distill points and Blend patterns, but reformulate them in plain, advisory language.

---

## guide.pre_reading — exactly 3 items

Short, actionable things the reader should keep in mind BEFORE reading the article.
Not summaries of findings — orientation tips that sharpen the reading:
what angle to watch for, what the article's implicit argument structure is,
what prior knowledge or scepticism is useful here.
In French. One sentence each. Exactly 3 items, no more, no less.

---

## guide.watch_out — 2 to 5 items

Specific warnings for the reader, grounded in the analysis.

Each item:
- `text`: the warning stated plainly for the reader. In French. 1–2 sentences.
  Do NOT include direct quotes from the article — the reader has not yet read it.
  State the concern in your own words.
- `references`: list of 1–3 node IDs from the analysis that ground this warning.
  Prefer references that span multiple layers. At least one reference is required.
  Valid formats: obs_N, er_N, cb_N, claim_N, bias_N, lr_N, pr_N, ia_N, bs_N

Derive from the Distill points and Blend patterns.
If the cadrage (title analysis, in rhetoric.cadrage) reveals a notable framing gap,
surface it as a watch_out item — it is often what misleads readers the most.

---

## guide.after_reading — 2 to 4 items

Key takeaways for the reader who has just finished the article.
Not restatements of the Distill points — reader-facing versions:
what the reader should question, remember, or do differently.
In French. One sentence each.

---

## guide.title_note — optional

One sentence in French on the title's rhetoric, if worth flagging explicitly.
Set to null if the cadrage findings are already captured in watch_out.

---

## guide.perspective — required

Three fields that zoom in, zoom out, and then balance the picture for the reader.
All in French. Each field: 1–2 sentences.

### guide.perspective.framing — zoom in

How the article treats its subject overall: the angle chosen, what it puts at the centre and
foregrounds, the emotional register it adopts, whose interests it speaks from.
Draw PRIMARILY from `cadrage.body` (Rhetoric layer) — the explicit body-framing analysis — and
refine it; reinforce with `emotional_register`, `cui_bono` (Rhetoric layer), the focus element
(Probe layer), and any Blend or Distill patterns that name the article's dominant lens.
Not a critique — a neutral description of the editorial choices made in treating the topic.
Do NOT list what the article leaves out (that belongs in `blind_spots`) and do NOT impute a
rhetorical effect on the reader ("frames a reproach", "steers the judgement"…): describe the
angle, not its effect.

### guide.perspective.blind_spots — zoom out

What the article structurally leaves out or minimizes: actors not mentioned,
counterarguments not addressed, data not provided, timescales not considered.
Draw from the Logic layer blind_spots and any Blend patterns that surface absences.
1–2 concrete absences, not a list.

### guide.perspective.balance — contextualiser la critique

A short note that puts the analysis in context for the reader.
Acknowledge structural constraints that explain (not excuse) the article's limits:
a short format cannot be exhaustive; an editorial taking a clear position does not
need to present all sides; a lack of counterarguments is legitimate when the editorial
line is explicit; a focused angle necessarily leaves other angles out.
The goal: help the reader calibrate the criticism — what the analysis flags is real,
but the article's format or genre sets the bar for what is reasonable to expect.
