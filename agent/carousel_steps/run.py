"""Run the eight adapt steps: generate each step's options with the model, take
the recommended picks (unattended) or stop for the author's (guided), and
assemble the deck. Each step is kept in `steps_dir` and reused while the earlier
steps' fragments are unchanged."""
import json
import re
import string
import sys
from pathlib import Path
from typing import Literal

from pydantic import ValidationError, create_model

from agent._base import _call_with_retry, _j, medium_directive
from agent.carousel_steps.steps import (
    STEPS, HookOption, MomentOption, Option, Step, StepName, WritingCopy, assemble, check_picks, default_picks,
    STEP_BY_NAME, examples_for, prompt_for, step_of, to_fragment,
)
from agent.carousel_steps.store import (
    StepFile, digest, load, log_choice, restamp_after, retire, retire_legacy, save, stamp_for,
)
from agent.instagram_carousel_adapt_agent import (
    _SHARED_PROMPT, _full_analysis_context, _off_axis_errors, _validate, caption_with_sources, split_rules,
)
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselPresentation, ThesisFrame

# Options per step in total, beyond the per-slot counts of `Step.slots`.
_TOTALS = {"moments": (5, 6)}
_INDEX = re.compile(r"[\w.]+\[(\d+)\]")
# The socle's fields, by the slot that writes them: an error on one is not another slot's.
_SOCLE_FIELDS = {"headline": "display.global_analysis.headline", "p": "display.global_analysis.core_recap",
                 "objection": "display.steel_man"}


class ChoiceError(ValueError):
    """A choice, a request for more options or a fix that cannot be applied."""


class AwaitingChoice(Exception):
    """A guided run reached a step with no pick; `adapt` returns None on it."""

    def __init__(self, step: StepName):
        super().__init__(step)
        self.step = step


def base_inputs(full: ArticleFullAnalysis, article_text: str | None) -> str:
    """The stamp's base. The article is stripped: `produce` reads it stripped, the
    format-folder commands read it as it is on disk, and both must agree."""
    return digest(full.model_dump_json(), (article_text or "").strip())


# ── Checks ──────────────────────────────────────────────────────────────────

def _deck_rules(deck: dict, article_text: str | None) -> tuple[list[str], list[str]]:
    """(hard, flags) of the deck as far as it goes. Before any beat carries an
    `axis_link`, `_validate` skips the axis checks: the bullets and the thesis are
    checked against slide 8 here."""
    errors = _validate(deck, article_text)
    pres = InstagramCarouselPresentation.model_validate(deck)
    if not any(b.axis_link.strip() for b in pres.display.reading_beats):
        errors += _off_axis_errors(pres, pres.display, [])
    return split_rules(list(dict.fromkeys(errors)))


def _substitute(option: Option, options: list[Option], picks: list[str]) -> list[str]:
    """`picks` with `option` taking the place of the last pick of its slot."""
    if option.id in picks:
        return picks
    slot_of = {o.id: o.slot for o in options}
    same = [p for p in picks if slot_of.get(p) == option.slot]
    if not same:
        return picks + [option.id]
    return [option.id if p == same[-1] else p for p in picks]


def _position(step: Step, option: Option, options: list[Option], picks: list[str]) -> int | None:
    """Where `option` sits in the list its step's fragment writes, for the steps
    that write one (an error labelled `[i]` belongs to the option at `i`)."""
    if step.name == "moments":
        return options.index(option)
    if step.name in ("idees", "contexte"):
        kept = [o for o in options if o.id in picks]
        if step.name == "idees":
            kept.sort(key=lambda o: o.slot)
        return kept.index(option)
    return None


def _candidate_rules(step: Step, option: Option, options: list[Option], picks: list[str],
                     fragments: dict, article_text: str | None) -> tuple[list[str], list[str]]:
    """(hard, flags) owned by `step` on the deck with `option` in its slot."""
    picks = _substitute(option, options, picks)
    deck = assemble(fragments | {step.name: to_fragment(step, options, picks, fragments)})
    pos = _position(step, option, options, picks)
    others = [f for slot, f in _SOCLE_FIELDS.items() if step.name == "socle" and not option.slot.startswith(slot)]

    def owned(rules):
        return [e for e in rules if step_of(e) == step.name and not e.startswith(tuple(others))
                and (pos is None or not (m := _INDEX.match(e)) or int(m.group(1)) == pos)]
    hard, flags = _deck_rules(deck, article_text)
    return owned(hard), owned(flags)


def option_flags(step: Step, option: Option, options: list[Option], recommended: list[str],
                 fragments: dict, article_text: str | None) -> list[str]:
    return _candidate_rules(step, option, options, recommended, fragments, article_text)[1]


def _coverage_errors(step: Step, options: list[Option]) -> list[str]:
    errors = []
    for slot, (lo, hi, _) in step.slots.items():
        n = sum(o.slot == slot for o in options)
        if not lo <= n <= hi:
            errors.append(f"options: slot {slot!r} has {n} option(s), must have {lo}–{hi}")
    if step.name in _TOTALS:
        lo, hi = _TOTALS[step.name]
        if not lo <= len(options) <= hi:
            errors.append(f"options: {len(options)} option(s) in total, must have {lo}–{hi}")
    return errors


def _recommended_ids(options: list[Option], indices: list[int]) -> tuple[list[str], list[str]]:
    bad = [i for i in indices if not 0 <= i < len(options)]
    return ([options[i].id for i in indices if 0 <= i < len(options)],
            [f"recommended: index {i} is out of range (0–{len(options) - 1})" for i in bad])


# ── Generating a step ───────────────────────────────────────────────────────

def _response_model(step: Step):
    if step.option_model is None:
        return WritingCopy
    proposal = create_model(f"{step.name.title()}Proposal", __base__=step.option_model,
                            slot=(Literal[tuple(step.slots)], ...), reason=(str, ...))
    fields = {"options": (list[proposal], ...), "recommended": (list[int], ...)}
    if step.name == "question":
        fields["thesis_frame"] = (ThesisFrame, ...)
    return create_model(f"{step.name.title()}Response", **fields)


def _to_options(step: Step, proposals: list, rejected: list[Option]) -> list[Option]:
    """Ids `a`, `b`, … (one slot) or `<slot><letter>`, continuing after `rejected`."""
    used = {o.id for o in rejected}
    out = []
    for p in proposals:
        prefix = "" if len(step.slots) == 1 else p.slot
        oid = next(prefix + c for c in string.ascii_lowercase if prefix + c not in used)
        used.add(oid)
        out.append(Option(id=oid, slot=p.slot, reason=p.reason,
                          fields=p.model_dump(mode="json", exclude={"slot", "reason"})))
    return out


def _message(step: Step, full: ArticleFullAnalysis, fragments: dict, article_text: str | None,
             rejected: list[Option], remarks: list[str]) -> str:
    parts = [_full_analysis_context(full, step.analysis_slice)]
    if article_text:
        parts.append(f"ARTICLE :\n{article_text.strip()}")
    fixed = {k: v for k, v in fragments.items() if k != "question_frame"}
    if fixed:
        parts.append(f"CHOIX FIXÉS (ne les réécris pas) :\n{_j(fixed)}")
    parts += [_SHARED_PROMPT, prompt_for(step)]
    if (examples := examples_for(step)):
        parts.append(f"EXEMPLES (décisions passées de l'auteur) :\n{examples}")
    if rejected:
        parts.append(f"DÉJÀ PROPOSÉES ET ÉCARTÉES :\n{_j([o.fields for o in rejected])}")
    if remarks:
        parts.append("REMARQUES DE L'AUTEUR :\n" + "\n".join(f"- {r}" for r in remarks))
    if (directive := medium_directive(full.article_metadata.medium)):
        parts.append(directive)
    return "\n\n---\n\n".join(parts)


def _writing_errors(data: dict, fragments: dict, article_text: str | None) -> list[str]:
    step = STEPS[-1]
    fields = WritingCopy.model_validate(data).model_dump(mode="json")
    frag = to_fragment(step, [Option(id="a", slot="writing", reason="", fields=fields)], ["a"], fragments)
    deck = assemble(fragments | {"writing": frag})
    hard, _ = _deck_rules(deck, article_text)
    selected = {i for i, b in enumerate(deck["display"].get("reading_beats", [])) if b.get("selected")}
    hard += [f"beats: index {b['index']} is not a selected beat of reading_beats"
             for b in fields["beats"] if b["index"] not in selected]
    return [e for e in hard if step_of(e) == "writing"]


def _schema_errors(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors()] or [str(exc)]


def _failed(step: Step, steps_dir: Path | None, data, errors: list[str]) -> RuntimeError:
    """The error for an answer still invalid after the retries; the raw answer is
    saved beside the steps for inspection when they are kept on disk."""
    where = ""
    if steps_dir is not None:
        steps_dir.mkdir(parents=True, exist_ok=True)
        path = steps_dir / f"{step.n}_{step.name}.failed.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        where = f" (raw answer saved to {path})"
    return RuntimeError(f"step {step.n} ({step.name}): the model's answer is still invalid after the retries"
                        f"{where}:\n" + "\n".join(f"- {e}" for e in errors))


def generate(step: Step, full: ArticleFullAnalysis, fragments: dict[str, dict], article_text: str | None,
             no_api: bool, rejected: list[Option] = [], remarks: list[str] = [],
             steps_dir: Path | None = None) -> StepFile:
    """One model call for `step`'s options (writing: its copy), checked against the
    deck so far. The StepFile comes back with nothing picked. An answer that still
    breaks the schema or leaves a slot uncovered after the retries raises RuntimeError."""
    model = _response_model(step)
    message = _message(step, full, fragments, article_text, rejected, remarks)
    if step.option_model is None:
        data = _call_with_retry(message, model.model_json_schema(),
                                validator=lambda d: _writing_errors(d, fragments, article_text),
                                no_api=no_api, label=step.name)
        try:
            fields = WritingCopy.model_validate(data).model_dump(mode="json")
        except ValidationError as exc:
            raise _failed(step, steps_dir, data, _schema_errors(exc)) from None
        return StepFile(step=step.name, options=[Option(id="a", slot="writing", reason="", fields=fields)],
                        recommended=["a"], rejected=rejected, remarks=remarks)

    def parse(data):
        resp = model.model_validate(data)
        frags = fragments | ({"question_frame": resp.thesis_frame.model_dump()} if step.name == "question" else {})
        options = _to_options(step, resp.options, rejected)
        recommended, errors = _recommended_ids(options, resp.recommended)
        return resp, frags, options, recommended, errors

    def validator(data):
        _, frags, options, recommended, errors = parse(data)
        errors = _coverage_errors(step, options) + errors
        if errors:
            return errors
        errors = check_picks(step, options, recommended)
        picks = default_picks(step, options) if errors else recommended
        for k, o in enumerate(options):
            hard, _ = _candidate_rules(step, o, options, picks, frags, article_text)
            errors += [f"options[{k}]: {e}" for e in hard]
        return errors

    data = _call_with_retry(message, model.model_json_schema(), validator=validator, no_api=no_api, label=step.name)
    try:
        resp, frags, options, recommended, errors = parse(data)
    except ValidationError as exc:
        raise _failed(step, steps_dir, data, _schema_errors(exc)) from None
    if (uncovered := _coverage_errors(step, options)):
        raise _failed(step, steps_dir, data, uncovered)
    if errors or check_picks(step, options, recommended):
        print("  ⚠  recommended picks invalid, taking the first per slot", file=sys.stderr)
        recommended = default_picks(step, options)
    for o in options:
        o.flags = option_flags(step, o, options, recommended, frags, article_text)
    return StepFile(step=step.name, thesis_frame=getattr(resp, "thesis_frame", None), options=options,
                    rejected=rejected, recommended=recommended, remarks=remarks)


# ── Showing a step ──────────────────────────────────────────────────────────

def _main_text(step: Step, o: Option) -> str:
    f = o.fields
    if step.name == "socle" and o.slot == "objection":
        return f"{f.get('argument', '')} → {f.get('alternative', '')} ({f.get('targets_slot', '')})"
    if step.name == "contexte":
        return f"{f.get('label', '')} : {f.get('text', '')}"
    return str(f.get(step.text_field, ""))


def format_options(step: Step, sf: StepFile) -> str:
    """The options as the author reads them: one block per slot, ★ on the recommended."""
    lines = [f"Thèse : {sf.thesis_frame.main_claim}", ""] if sf.thesis_frame else []
    slots = list(dict.fromkeys([*step.slots, *(o.slot for o in sf.options)]))
    for slot in slots:
        opts = [o for o in sf.options if o.slot == slot]
        if not opts:
            continue
        lines.append(f"[{slot}]")
        for o in opts:
            lines.append(f"{o.id} — {_main_text(step, o)}" + (" ★" if o.id in sf.recommended else ""))
            lines.append(f"   ↳ {o.reason}")
            lines += [f"   ⚠ {flag}" for flag in o.flags]
        lines.append("")
    return "\n".join(lines).rstrip()


# ── The run ─────────────────────────────────────────────────────────────────

def _pick(step: Step, sf: StepFile, picks: list[str], fragments: dict) -> None:
    sf.picked = list(picks)
    sf.fragment = to_fragment(step, sf.options, sf.picked, fragments)


def _run(full, no_api, article_text, steps_dir, stop_after, guided) -> InstagramCarouselPresentation | None:
    if steps_dir is not None and retire_legacy(steps_dir):
        print("old 3-stage adapt files moved to stale_legacy/; the deck is rebuilt from the 8 steps", file=sys.stderr)
    base = base_inputs(full, article_text)
    fragments: dict[str, dict] = {}
    for step in STEPS:
        stamp = stamp_for(base, [fragments[s.name] for s in STEPS if s.n < step.n])
        sf, saved = load(steps_dir, step) if steps_dir is not None else (None, "")
        tag = f"Adaptation carousel — étape {step.n}/{len(STEPS)} ({step.name})"
        if sf is None or saved != stamp:
            if sf is not None:
                retire(steps_dir, step, saved)
            print(f"{tag}…", file=sys.stderr, flush=True)
            sf = generate(step, full, fragments, article_text, no_api, steps_dir=steps_dir)
            if sf.thesis_frame:
                fragments["question_frame"] = sf.thesis_frame.model_dump()
            if not guided or step.option_model is None:   # writing offers no choice
                _pick(step, sf, sf.recommended, fragments)
        else:
            print(f"{tag} : {steps_dir / f'{step.n}_{step.name}.json'} réutilisé", file=sys.stderr, flush=True)
            if sf.thesis_frame:
                fragments["question_frame"] = sf.thesis_frame.model_dump()
            if not sf.picked and not guided:
                _pick(step, sf, sf.recommended, fragments)
            elif sf.picked and not sf.fragment:
                _pick(step, sf, sf.picked, fragments)
        if steps_dir is not None:
            save(steps_dir, sf, stamp)
        if not sf.picked:
            print(format_options(step, sf))
            raise AwaitingChoice(step.name)
        fragments[step.name] = sf.fragment
        hard, flags = _deck_rules(assemble(fragments), article_text)
        for e in hard + flags:
            if step_of(e) == step.name:
                print(f"  ⚠  {e}", file=sys.stderr)
        if step.name == stop_after:
            return None
    pres = InstagramCarouselPresentation.model_validate(assemble(fragments))
    return pres.model_copy(update={"caption": caption_with_sources(pres.caption, pres.go_further)})


def adapt(full: ArticleFullAnalysis, no_api: bool = False, article_text: str | None = None,
          steps_dir: Path | None = None, stop_after: StepName | None = None,
          guided: bool = False) -> InstagramCarouselPresentation | None:
    """The deck, step by step. Unattended, each step takes its recommended picks;
    guided, the run stops at the first step with no pick and prints its options.
    Returns None when it stops (`stop_after` reached, or a choice awaited)."""
    try:
        return _run(full, no_api, article_text, steps_dir, stop_after, guided)
    except AwaitingChoice as e:
        print(f"Awaiting a choice at step {next(s.n for s in STEPS if s.name == e.step)} ({e.step})",
              file=sys.stderr)
        return None


# ── Choosing, asking for more, fixing ───────────────────────────────────────

def _earlier(full, steps_dir: Path, step: Step, article_text: str | None) -> tuple[dict, StepFile, str]:
    """(fragments of the earlier steps, `step`'s file, its stamp) — refused unless
    the file exists, was made from those very fragments, and every earlier step has picks."""
    fragments: dict[str, dict] = {}
    for s in STEPS:
        if s.n >= step.n:
            break
        sf, _ = load(steps_dir, s)
        if sf is None or not sf.picked:
            raise ChoiceError(f"{s.name} has no pick: run `produce --guided` to reach step {step.n} ({step.name})")
        fragments[s.name] = sf.fragment
        if sf.thesis_frame:
            fragments["question_frame"] = sf.thesis_frame.model_dump()
    sf, saved = load(steps_dir, step)
    if sf is not None and sf.thesis_frame:      # the question step's own frame, for its fragment
        fragments["question_frame"] = sf.thesis_frame.model_dump()
    stamp = stamp_for(base_inputs(full, article_text), [fragments[s.name] for s in STEPS if s.n < step.n])
    if sf is None or saved != stamp:
        raise ChoiceError(f"step {step.n} ({step.name}) is missing or stale: run `produce --guided` to regenerate it")
    return fragments, sf, stamp


def choose(full, steps_dir: Path, step: StepName, picks: list[str], edits: dict[str, str],
           reason: str = "", article_text: str | None = None) -> list[str]:
    """Keep `picks` at `step`, with the author's rewrites (`ID` or `ID.field` → text).
    Only the slot rules block; hard-check failures on the result come back as warnings."""
    st = STEP_BY_NAME[step]
    if st.option_model is None:
        raise ChoiceError(f"{step} offers no options to choose from")
    fragments, sf, stamp = _earlier(full, steps_dir, st, article_text)
    by_id = {o.id: o for o in sf.options}
    offered = [{"id": o.id, "text": _main_text(st, o)} for o in sf.options]
    valid = list(st.option_model.model_fields)
    for key in edits:
        oid, _, field = key.partition(".")
        if oid not in by_id:
            raise ChoiceError(f"{step}: unknown option {oid!r}")
        if field and field not in valid:
            raise ChoiceError(f"{step}: unknown field {field!r} — the options have {', '.join(valid)}")
    for key, text in edits.items():
        oid, _, field = key.partition(".")
        by_id[oid].fields[field or st.text_field] = text
        by_id[oid].edited = True
    if errors := check_picks(st, sf.options, picks):
        raise ChoiceError("; ".join(errors))
    _pick(st, sf, picks, fragments)
    for oid in {k.partition(".")[0] for k in edits}:
        by_id[oid].flags = option_flags(st, by_id[oid], sf.options, picks, fragments, article_text)
    hard, _ = _deck_rules(assemble(fragments | {step: sf.fragment}), article_text)
    save(steps_dir, sf, stamp)
    log_choice(steps_dir.parent, {"step": step, "event": "pick", "offered": offered,
                                  "picked": picks, "edits": edits, "reason": reason})
    return [e for e in hard if step_of(e) == step]


def more(full, steps_dir: Path, step: StepName, remark: str = "", article_text: str | None = None,
         no_api: bool = False) -> StepFile:
    """Set the options aside and generate others, told what was rejected and why."""
    st = STEP_BY_NAME[step]
    fragments, sf, stamp = _earlier(full, steps_dir, st, article_text)
    remarks = sf.remarks + ([remark] if remark else [])
    new = generate(st, full, fragments, article_text, no_api, rejected=sf.rejected + sf.options, remarks=remarks,
                   steps_dir=steps_dir)
    save(steps_dir, new, stamp)
    log_choice(steps_dir.parent, {"step": step, "event": "more", "remark": remark})
    return new


def _walk(node, path: str):
    """(container, key) of the last step of a dotted / `[i]` path; ChoiceError if it does not resolve."""
    keys = [(int(i) if i else k) for k, i in re.findall(r"(\w+)|\[(\d+)\]", path)]
    for k in keys[:-1]:
        try:
            node = node[k]
        except (KeyError, IndexError, TypeError):
            raise ChoiceError(f"{path!r} does not resolve") from None
    try:
        node[keys[-1]]
    except (KeyError, IndexError, TypeError):
        raise ChoiceError(f"{path!r} does not resolve") from None
    return node, keys[-1]


_LISTED = re.compile(r"display\.(essentiel|reperes_facts|reading_beats)\[(\d+)\](?:\.(\w+))?")


def _option_for(step: Step, sf: StepFile, field: str) -> tuple[Option, str] | None:
    """(option, option field) a deck field of an option step was written from, so a
    `fix` survives a later `choose`. None when no single option field holds it:
    the thesis frame (the step's, not an option's), the socle's `core_recap` (the
    présupposés joined into one line) and `steel_man.targets` (a position worked
    out from `targets_slot`), a beat's `selected`/`spine_ref` (the pick and the
    slot) and `axis_link` (the option's reason) — those stay fragment-only."""
    kept = [o for o in sf.options if o.id in sf.picked]
    in_slot = {o.slot: o for o in kept}
    m = _LISTED.fullmatch(field)
    if step.name == "question" and field == "cta.engagement_sentence":
        return kept[0], "text"
    if step.name == "enjeu" and field == "display.root_issue":
        return kept[0], "text"
    if step.name == "hook" and field.removeprefix("hook.") in HookOption.model_fields:
        return kept[0], field.removeprefix("hook.")
    if step.name == "socle" and field == "display.global_analysis.headline":
        return in_slot["headline"], "text"
    if step.name == "socle" and field in ("display.steel_man.argument", "display.steel_man.alternative"):
        return in_slot["objection"], field.rsplit(".", 1)[1]
    if m and step.name == "idees" and not m.group(3):
        return sorted(kept, key=lambda o: o.slot)[int(m.group(2))], "text"
    if m and step.name == "contexte" and m.group(3) in ("label", "text"):
        return kept[int(m.group(2))], m.group(3)
    if m and step.name == "moments" and m.group(3) in MomentOption.model_fields:
        return sf.options[int(m.group(2))], m.group(3)
    return None


def fix(full, steps_dir: Path, field: str, text: str, article_text: str | None = None) -> StepName:
    """Overwrite one deck field inside the fragment of the step that owns it. Nothing
    is regenerated: the later steps are re-stamped to accept the change."""
    owner = STEP_BY_NAME[step_of(field)]
    files = {s.name: load(steps_dir, s)[0] for s in STEPS}
    deck = assemble({n: f.fragment for n, f in files.items() if f and f.fragment})
    _walk(deck, field)
    sf = files[owner.name]
    if sf is None or not sf.fragment:
        raise ChoiceError(f"{owner.name} has no fragment to fix: run `produce` first")
    target = sf.fragment
    if owner.name == "writing" and (m := re.fullmatch(r"display\.reading_beats\[(\d+)\]\.(\w+)", field)):
        i = int(m.group(1))
        entry = next((c for c in sf.fragment["beat_copy"] if c["index"] == i), None)
        if entry is None:
            raise ChoiceError(f"{field!r}: beat {i} has no copy")
        target, path = entry, m.group(2)
        for c in sf.options[0].fields["beats"]:
            if c["index"] == i:
                c[path] = text
    else:
        path = field
    node, key = _walk(target, path)
    before, node[key] = node[key], text
    if owner.option_model is not None and (found := _option_for(owner, sf, field)):
        option, name = found
        option.fields[name] = text
        option.edited = True
    save(steps_dir, sf, load(steps_dir, owner)[1])
    restamp_after(steps_dir, owner, base_inputs(full, article_text))
    log_choice(steps_dir.parent, {"step": owner.name, "event": "fix", "field": field,
                                  "before": before, "after": text})
    return owner.name
