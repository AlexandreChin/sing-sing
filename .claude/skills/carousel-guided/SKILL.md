---
name: carousel-guided
description: Use when the author asks to generate or make a carousel for an article, video or podcast (« génère / fais un carrousel pour … »). Runs the guided carousel adapt one step at a time — the author picks among options, Claude relays and applies the choices, then runs the reader check.
---

# Guided carousel run

The author decides, you carry. Never pick an option for them, never skip a step, never rewrite an option yourself unless they give you the text. One step per message.

## 1. Start

```bash
python main.py produce <input.txt> --guided [--no-api] [--medium article|video|podcast] [--title "…"] [--source "…"] [--url …] [--published-at "…"] [--language <langue>]
```

Pass the source metadata flags the author gave you (they fill the slide-1 pill). Add `--no-api` when the run goes through the local `claude` CLI.

The run pauses at the first step with no pick (steps 1–7: question, enjeu, idees, moments, contexte, socle, hook; `writing` runs without stopping). stdout holds the options, stderr the line `Awaiting a choice: python main.py choose <fmt_dir> <step> --pick <ids>` — use that exact `<fmt_dir>` and `<step>`.

## 2. Relay the options

Show the author the options of the paused step in chat, faithfully: each option's id, its text, its reason (↳), its flags (⚠) and which one is ★ recommended. Do not summarise, merge or reorder. Say which step it is (n of 7) and ask for their choice. Stop there and wait.

## 3. Map the reply to a command

| Author says | Run |
|---|---|
| « go with b » / « b et d » | `python main.py choose <fmt_dir> <step> --pick b` (comma-separated ids when the step keeps several) |
| a rewrite of an option | `… --pick b --edit "b=<their text>"` (`b.field=…` for another field; `--edit` is repeatable) |
| « other suggestions », with or without a remark | `… --more [--remark "<their words>"]` — prints new options; relay them and wait again |

When the author gives a reason, pass it verbatim with `--reason "…"`; it goes in the choice log. Never invent one. Relay any ⚠ warning `choose` prints, and propose a fix for each (a rewritten text); apply it only once the author accepts — `choose … --edit ID=TEXT` again, or `fix` for a deck field.

Then rerun `produce <input.txt> --guided …` (same flags) to reach the next pause. Repeat until no step is awaiting. `produce` renders only with `--render`: after the last pick (step 7), the final rerun is `produce <input.txt> --guided --render` (an unattended run needs `--render` too for slides). A rerun right after `choose --more` re-prints the same pending step with the new options — expected, not a loop. `--no-api` goes on `choose --more` too.

## 4. After the render

```bash
python main.py check <fmt_dir>/extract.json --reader [--no-api]
```

Hard-check errors must be fixed; « editorial (advisory) » flags are for the author to weigh. Show each finding to the author with a proposed fix (a field path and new text). Apply only the accepted ones:

```bash
python main.py fix <fmt_dir> <field> "<text>"     # e.g. hook.subtitle or display.reading_beats[0].answer
```

`fix` edits the field and re-stamps the steps without regenerating. Then `python main.py produce <input.txt> --guided --render` to re-render, and show the slide PNGs (`<fmt_dir>/slides/`).

## Going back

To change an earlier step, run a new `choose` on it (`--pick`, `--edit` or `--more`), then rerun `produce --guided`: the later steps are rebuilt from the new choice. Warn the author that their later picks on the rebuilt steps are asked again.

## The log

Every choice, edit and reason lands in `<fmt_dir>/choices.jsonl`, which also holds the `more` and `fix` events (a `fix` is a promotable correction). When a correction there looks reusable (a rewrite that repeats a pattern), **propose** to the author promoting it to `agent/prompts/carousel_steps/examples/<n>_<step>.md`, in that file's format: a `## Retenus` section and a `## Écartés (et pourquoi)` section. Do it only if they agree; never automatically.

## Unattended

`produce <input.txt>` without `--guided` takes the ★ recommended option at every step. Use it only if the author asks for a run without choosing.

## The CADRAGE & LOGIQUE archetype

For an opinion piece, essay or expert interview the author may ask for the `cadrage_logique` format (`--format cadrage_logique` on `produce`). The loop is the same — relay options, map the reply, `choose`, rerun — with seven steps: `axe` first (the arbitrage the deck leads to: `· variable`, `· position1`, `· position2`, `· thesis`; never rendered), then in slide order `constat`, `these`, `angle_mort`, `depassement`, `boussole`, `hook` (each keeps ONE option; ids `a`, `b`, …); `writing` (the caption) runs without a pause. An option shows its main text, then its other fields (`· fig1`, `· these_claim`, `· note1`, `· lever1`, `· question1`, `· pro1`…), then its reason (↳). A figure is `valeur | libellé | comparaison`, a note `source | texte` or `remarque | texte`, a lever `titre | détail`: keep that shape when the author rewrites one. `--edit` takes `ID=TEXT` or `ID.field=TEXT`. `fix` fields are `<step>.<field>` (`axe.position1`, `constat.fig1`, `these.solution_claim`, `angle_mort.title`, `boussole.con2`, `hook.promise`…) and `caption`. Slides 4 to 6 rest on the model's general knowledge, not on the source: tell the author the sources there are unverified pointers. `check` does not cover this format: the ⚠ that `choose` prints are its checks (a word cap, a malformed figure, note or lever, an accusing word, a figure not found in the source) — relay them and propose a fix as usual.

For a hot-news piece (a dispatch, a reaction, a polemic) the author may ask for the `temps_long` format (`--format temps_long` on `produce`). Same loop, with five steps: `tournants` first (the laws, doctrine texts and public statements that changed the rules over 30–50 years; `· lead`, `· rep1`…`· rep4`, the latest from the last three years — a bill under discussion included, with its status; its remark gives what it could change for the right to demonstrate, each thesis attributed to its camp), then `episodes` (the events of the last ten years people remember most, each with a documented trace), `lecture` (`· lead` — « Pour trancher : comparer … d'un épisode à l'autre » — `· rupture`, `· continuite`, `· cycle`, `· question`), `pieges` (`· piege1`…`· piege3`), `hook`; `writing` runs without a pause. A reference point is `date | repère | remarque` (the date holds a year; the remark is one line saying what happened or what the text changed, different on every row and never repeating the label's words or the lead's quoted word; `episodes` takes 4 or 5 points), a reading `signature | indicateur` (the second part is what to look at, drawn from slides 2–3 and different in form on each line: the last episode against named ones, the texts in order, the gap between episodes; the measure itself is in the lead, at the widest level the media claims — an age or place subgroup is a breakdown, not the measure), a trap `titre | question`: keep that shape when the author rewrites one. `fix` fields are `<step>.<field>` (`episodes.rep1`, `lecture.cycle`, `pieges.piege1`, `hook.title`…) and `caption`. The dates and the organisations rest on the model's general knowledge, not on the source: tell the author to verify each date, and that « remembered most » is the model's judgement, made checkable only by the documented trace. No figure of any trend is allowed (a `%` or an amount comes back as ⚠). The `lead` of the two timelines must quote a word of the media; if the source makes no temporal claim, say that `temps_long` is a poor fit. Every text field has a character cap that keeps it within its lines: relay the ⚠ that `choose` prints rather than trimming silently. `check` does not cover this format.
