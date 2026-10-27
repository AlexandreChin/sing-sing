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
