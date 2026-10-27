import argparse
import asyncio
import importlib
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from agent import analyze_for_full_analysis
from extractors.registry import FORMATS
from models import FullAnalysisInput

load_dotenv()

OUTPUTS_DIR = Path("samples/outputs")
DEFAULT_FORMAT = "instagram_carousel_optimized"


def _base_dir(input_path: str | None, stem: str) -> Path:
    """Output root for an input file: its own folder when that folder is already
    named after it, else a <stem>/ folder beside it. No input path → outputs/<stem>."""
    if input_path is None:
        return OUTPUTS_DIR / stem
    parent = Path(input_path).resolve().parent
    return parent if parent.name == stem else parent / stem


def _layout(stem: str, fmt: str | None = None, base: Path | None = None) -> dict:
    """Per-analysis output layout:
    <base>/{analysis.json, steps/, <fmt>/{adapt.json, extract.json, slides/}}."""
    base = base if base is not None else OUTPUTS_DIR / stem
    paths = {"base": base, "analysis": base / "analysis.json", "steps": base / "steps"}
    if fmt:
        fdir = base / fmt
        paths |= {"fmt_dir": fdir, "adapt": fdir / "adapt.json",
                  "extract": fdir / "extract.json",
                  "html": fdir / "html", "slides": fdir / "slides"}
    return paths


async def run_full_analysis(text: str, no_api: bool = False, input_path: str | None = None, extra_instructions: str | None = None, medium: str = "article", source: str | None = None, url: str | None = None, published_at: str | None = None, duration_minutes: int | None = None, title: str | None = None, language: str | None = None) -> Path:
    analysis_input = FullAnalysisInput(body=text, extra_instructions=extra_instructions, medium=medium,
                                      source=source, url=url, published_at=published_at,
                                      duration_minutes=duration_minutes, title=title, language=language)

    stem = Path(input_path).stem if input_path else datetime.now().strftime("%Y%m%d_%H%M%S")
    lay = _layout(stem, base=_base_dir(input_path, stem))
    lay["base"].mkdir(parents=True, exist_ok=True)
    steps_dir = lay["steps"]
    output_path = lay["analysis"]

    result = await analyze_for_full_analysis(analysis_input, no_api=no_api, steps_dir=steps_dir)

    json_output = result.model_dump_json(indent=2)
    output_path.write_text(json_output, encoding="utf-8")
    print(f"Output written to {output_path}", file=sys.stderr)
    print(f"Step outputs → {steps_dir}/", file=sys.stderr)
    print(json_output)
    return output_path


# ── Command handlers ────────────────────────────────────────────────────────────

def _extra_instructions(args: argparse.Namespace) -> str | None:
    if args.instructions is not None:
        return args.instructions
    if args.instructions_file is not None:
        return Path(args.instructions_file).read_text(encoding="utf-8").strip()
    return None


async def cmd_analyze(args: argparse.Namespace) -> None:
    extra_instructions = _extra_instructions(args)

    if args.article:
        input_path = args.article
        text = Path(input_path).read_text(encoding="utf-8").strip()
    else:
        input_path = None
        text = sys.stdin.read().strip()
    if not text:
        print("No article text provided (pass <article.txt> or pipe via stdin).", file=sys.stderr)
        sys.exit(1)

    await run_full_analysis(text, no_api=args.no_api, input_path=input_path, extra_instructions=extra_instructions,
                            medium=args.medium, source=args.source, url=args.url, published_at=args.published_at,
                            duration_minutes=args.duration, title=args.title, language=args.language)


async def cmd_simplify(args: argparse.Namespace) -> None:
    from agent.instagram_carousel_simplify_agent import simplify_carousel
    json_path = Path(args.analysis)
    print(f"Simplifying{' (no-api)' if args.no_api else ''}…", file=sys.stderr, flush=True)
    result = await simplify_carousel(json_path, no_api=args.no_api)
    out_path = json_path.with_stem(json_path.stem + "_simplified")
    out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"Simplified JSON written to {out_path}", file=sys.stderr)


def _adapt_stage_kwargs(adapt_params, kwargs: dict, steps_dir: Path, stop_after: str | None,
                        guided: bool = False) -> bool:
    """Pass the step cache (and the stop point, and guided mode) to an adapt agent
    that runs in steps. False when --stop-after was asked of one that does not."""
    if "steps_dir" in adapt_params:
        kwargs["steps_dir"] = steps_dir
    if guided and "guided" in adapt_params:
        kwargs["guided"] = True
    if stop_after:
        if "stop_after" not in adapt_params:
            print(f"--stop-after is only available for {DEFAULT_FORMAT}.", file=sys.stderr)
            return False
        kwargs["stop_after"] = stop_after
    return True


def _pending_step(steps_dir: Path) -> str | None:
    """The first of steps 1-7 whose file exists with no pick: the one awaiting a choice."""
    from agent.carousel_steps.steps import STEPS
    from agent.carousel_steps.store import load
    for s in STEPS[:-1]:
        sf, _ = load(steps_dir, s)
        if sf is not None and not sf.picked:
            return s.name
    return None


def _report_stop(steps_dir: Path, stop_after: str | None, guided: bool = False,
                 command: str = "produce") -> None:
    """Say why adapt returned nothing: a choice is awaited (a step has no pick), or
    the run stopped where --stop-after asked. `command` is the one to rerun."""
    pending = _pending_step(steps_dir) if guided else None
    if pending:
        print(f"Awaiting a choice: python main.py choose {steps_dir.parent} {pending} --pick <ids>\n"
              f"then rerun {command} with --guided", file=sys.stderr)
    else:
        print(f"Stopped after {stop_after}: review or edit the step files in {steps_dir}, then rerun "
              f"without --stop-after — the steps after it are rebuilt from your version.", file=sys.stderr)


def _article_beside(analysis_path: Path) -> str | None:
    """The article text next to an analysis: in its folder or beside it (see _base_dir)."""
    base = analysis_path.parent
    article = next((c for c in (base / f"{base.name}.txt", base.parent / f"{base.name}.txt")
                    if c.exists()), None)
    # stripped, as `produce` reads it: the step stamps hash this text
    return article.read_text(encoding="utf-8").strip() if article else None


def _parse_edits(items: list[str]) -> dict[str, str]:
    """`ID=TEXT` (or `ID.field=TEXT`) items → {key: text}, split on the first `=`."""
    bad = [i for i in items if "=" not in i]
    if bad:
        print(f"--edit expects ID=TEXT, got {bad[0]!r}", file=sys.stderr)
        sys.exit(2)
    return dict(item.split("=", 1) for item in items)


async def cmd_adapt(args: argparse.Namespace) -> None:
    from models.full_analysis import ArticleFullAnalysis

    agent_mod = FORMATS[args.format][0]
    adapt_fn = importlib.import_module(agent_mod).adapt
    json_path = Path(args.analysis)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    full = ArticleFullAnalysis.model_validate(data)
    kwargs = {"no_api": args.no_api}
    adapt_params = inspect.signature(adapt_fn).parameters
    if "analysis_path" in adapt_params:
        kwargs["analysis_path"] = json_path
    if "article_text" in adapt_params:
        article = _article_beside(json_path)
        if article:
            kwargs["article_text"] = article
    steps_dir = json_path.parent / args.format / "adapt_steps"
    if not _adapt_stage_kwargs(adapt_params, kwargs, steps_dir, args.stop_after, args.guided):
        return
    presentation = adapt_fn(full, **kwargs)
    if presentation is None:
        _report_stop(steps_dir, args.stop_after, args.guided, command="adapt")
        return
    out_path = json_path.with_stem(json_path.stem + f"_{args.format}_adapt")
    out_path.write_text(presentation.model_dump_json(indent=2), encoding="utf-8")
    print(f"Presentation written to {out_path}", file=sys.stderr)


def _load_fmt_dir(fmt_dir: str):
    """(ArticleFullAnalysis, steps_dir, article text) of a format folder."""
    from models.full_analysis import ArticleFullAnalysis
    fmt = Path(fmt_dir)
    analysis_path = fmt.parent / "analysis.json"
    if not analysis_path.exists():
        print(f"No analysis.json beside {fmt} (expected {analysis_path})", file=sys.stderr)
        sys.exit(1)
    full = ArticleFullAnalysis.model_validate(json.loads(analysis_path.read_text(encoding="utf-8")))
    return full, fmt / "adapt_steps", _article_beside(analysis_path)


async def cmd_choose(args: argparse.Namespace) -> None:
    from agent.carousel_steps import run
    from agent.carousel_steps.steps import STEP_BY_NAME
    if not args.pick and not args.more:
        print("choose needs --pick <ids> or --more", file=sys.stderr)
        sys.exit(2)
    full, steps_dir, article = _load_fmt_dir(args.fmt_dir)
    try:
        if args.more:
            sf = run.more(full, steps_dir, args.step, args.remark, article, args.no_api)
            print(run.format_options(STEP_BY_NAME[args.step], sf))
            return
        picks = [p.strip() for p in args.pick.split(",") if p.strip()]
        warnings = run.choose(full, steps_dir, args.step, picks, _parse_edits(args.edit), args.reason, article)
    except run.ChoiceError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    for w in warnings:
        print(f"⚠ {w}", file=sys.stderr)
    print(f"Kept {', '.join(picks)} at {args.step}; rerun produce (or adapt) with --guided to continue.", file=sys.stderr)


async def cmd_fix(args: argparse.Namespace) -> None:
    from agent.carousel_steps import run
    full, steps_dir, article = _load_fmt_dir(args.fmt_dir)
    try:
        step = run.fix(full, steps_dir, args.field, args.text, article)
    except run.ChoiceError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    print(f"Fixed {args.field} in {step}; the later steps keep your version.", file=sys.stderr)


async def cmd_extract(args: argparse.Namespace) -> None:
    import typing

    from models.full_analysis import ArticleFullAnalysis

    _, extractor_mod, renderer_mod = FORMATS[args.format]
    extract_fn = importlib.import_module(extractor_mod).extract
    # The presentation model is format-specific; read it off the extractor's own
    # `presentation` annotation so this stays correct for every registered format.
    presentation_model = typing.get_type_hints(extract_fn)["presentation"]
    full = ArticleFullAnalysis.model_validate(json.loads(Path(args.analysis).read_text(encoding="utf-8")))
    presentation = presentation_model.model_validate(json.loads(Path(args.presentation).read_text(encoding="utf-8")))
    doc = extract_fn(full, presentation)
    out_path = Path(args.analysis).with_stem(Path(args.analysis).stem + f"_{args.format}_extract")
    out_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    print(f"Document written to {out_path}", file=sys.stderr)
    if args.render:
        render_from_json = importlib.import_module(renderer_mod).render_from_json
        slides_dir = out_path.parent / out_path.stem
        print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(render_from_json, out_path, slides_dir)


def _report_check(extract_path: Path, fmt: str) -> None:
    """Print the deterministic deck check after a carousel is built or re-rendered,
    so a broken rule shows up in the loop that caused it. Never fails the run —
    `check` is the gate; this is the reminder."""
    if not fmt.startswith("instagram_carousel"):
        return
    from tools.check_deck import check, format_report
    print(format_report(check(extract_path)), file=sys.stderr)


async def cmd_render(args: argparse.Namespace) -> None:
    json_path = Path(args.document)
    # a deck sits in a folder named after its format: render it as that format
    # unless --format says otherwise
    if args.format == DEFAULT_FORMAT and json_path.parent.name in FORMATS:
        args.format = json_path.parent.name
    _, _, renderer_mod = FORMATS[args.format]
    mod = importlib.import_module(renderer_mod)
    out_dir = Path(args.output_dir) if args.output_dir else json_path.parent
    print(f"Rendering into {out_dir}/", file=sys.stderr)
    if json_path.suffix == ".md" and hasattr(mod, "render_from_markdown"):
        await asyncio.to_thread(mod.render_from_markdown, json_path, out_dir)
    else:
        await asyncio.to_thread(mod.render_from_json, json_path, out_dir)
        _report_check(json_path, args.format)


async def cmd_html(args: argparse.Namespace) -> None:
    # Step 1 of the render split: write standalone HTML slide files (no screenshots).
    json_path = Path(args.document)
    # Same layout as `render`, which writes <deck>/html and <deck>/slides: this
    # wrote to <deck>/<json stem>/ instead, leaving the deck's own html/ stale
    # while quietly creating an extract/ folder beside it.
    out_dir = Path(args.output_dir) if args.output_dir else json_path.parent / "html"
    _, _, renderer_mod = FORMATS[args.format]
    generate_html_from_json = importlib.import_module(renderer_mod).generate_html_from_json
    print(f"Writing HTML slides to {out_dir}/", file=sys.stderr)
    await asyncio.to_thread(generate_html_from_json, json_path, out_dir)


async def cmd_shoot(args: argparse.Namespace) -> None:
    # Step 2 of the render split: screenshot HTML to PNG.
    # A directory → every slide (shoot_dir); a single file → one slide, or a
    # newsletter page full-page.
    from renderer.shoot import is_slide, shoot_dir, shoot_page, shoot_slide
    path = Path(args.path)
    if path.is_dir():
        print(f"Screenshotting HTML in {path}/", file=sys.stderr)
        await asyncio.to_thread(shoot_dir, path)
    else:
        print(f"Screenshotting {path.name}", file=sys.stderr)
        # A carousel slide keeps its 1080×1350 frame; a newsletter page has no
        # fixed height and is captured full-page.
        shot = shoot_slide if is_slide(path) else shoot_page
        await asyncio.to_thread(shot, path, args.output)


async def cmd_validate(args: argparse.Namespace) -> None:
    from tools.validate import validate as _validate
    path = Path(args.analysis)
    errs, registry = _validate(path)
    if not errs:
        print(f"✓ {path.name}: all checks passed")
        if registry:
            print(f"\nNode registry ({len(registry)} nodes):")
            for node_id, label in sorted(registry.items()):
                print(f"  {node_id:<20s}  {label}")
    else:
        print(f"✗ {path.name}: {len(errs)} error(s)")
        for e in errs:
            print(f"  • {e}")
        sys.exit(1)


async def cmd_verify(args: argparse.Namespace) -> None:
    from tools.verify import find_sources_for_claim
    from models.article import Claim
    candidate = Path(args.target[0])
    if candidate.exists() and candidate.suffix == ".json":
        data = json.loads(candidate.read_text(encoding="utf-8"))
        raw_claims = data.get("annotations", {}).get("facts_vs_opinions", {}).get("claims_and_sources", [])
        if not raw_claims:
            print("No claims found in JSON", file=sys.stderr)
            sys.exit(1)
        indices = args.claim if args.claim else list(range(len(raw_claims)))
        for i in indices:
            if not (0 <= i < len(raw_claims)):
                print(f"Claim index {i} out of range (0–{len(raw_claims)-1})", file=sys.stderr)
                continue
            text = raw_claims[i].get("quote", "")
            print(f"\n[{i}] {text[:80]}{'…' if len(text) > 80 else ''}")
            result = await find_sources_for_claim(Claim(text=text))
            print(f"  ✓ confirming:    {len(result.confirming)}")
            print(f"  ✗ contradicting: {len(result.contradicting)}")
            print(f"  ~ neutral:       {len(result.neutral)}")
            for src in result.confirming:
                print(f"      [supports]    {src.title[:60]} — {src.stance_reason}")
            for src in result.contradicting:
                print(f"      [contradicts] {src.title[:60]} — {src.stance_reason}")
    else:
        text = " ".join(args.target)
        print(f"Verifying: {text[:80]}")
        result = await find_sources_for_claim(Claim(text=text))
        print(f"  ✓ confirming:    {len(result.confirming)}")
        print(f"  ✗ contradicting: {len(result.contradicting)}")
        print(f"  ~ neutral:       {len(result.neutral)}")
        for src in result.confirming + result.contradicting:
            print(f"  [{src.stance}] {src.title[:60]} — {src.stance_reason}")


async def cmd_graph(args: argparse.Namespace) -> None:
    from tools.graph_generator import generate_from_json, build_graph
    json_path = Path(args.analysis)
    out_path = Path(args.output) if args.output else None
    out = generate_from_json(json_path, out_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    nodes, edges = build_graph(data)
    print(f"Graph: {len(nodes)} nodes, {len(edges)} edges → {out}", file=sys.stderr)


async def cmd_produce(args: argparse.Namespace) -> None:
    agent_mod, extractor_mod, renderer_mod = FORMATS[args.format]

    # 1. Analyze
    input_path = args.article
    text = Path(input_path).read_text(encoding="utf-8").strip()
    stem = Path(input_path).stem
    lay = _layout(stem, args.format, base=_base_dir(input_path, stem))
    lay["fmt_dir"].mkdir(parents=True, exist_ok=True)
    full = await analyze_for_full_analysis(
        FullAnalysisInput(body=text, extra_instructions=_extra_instructions(args),
                          medium=args.medium, source=args.source,
                          url=args.url, published_at=args.published_at,
                          duration_minutes=args.duration, title=args.title, language=args.language),
        no_api=args.no_api,
        steps_dir=lay["steps"],
    )
    lay["analysis"].write_text(full.model_dump_json(indent=2), encoding="utf-8")
    print(f"Analysis written to {lay['analysis']}", file=sys.stderr)

    # 2. Adapt
    adapt_fn = importlib.import_module(agent_mod).adapt
    kwargs = {"no_api": args.no_api}
    adapt_params = inspect.signature(adapt_fn).parameters
    if "analysis_path" in adapt_params:
        kwargs["analysis_path"] = lay["analysis"]
    if "article_text" in adapt_params:
        kwargs["article_text"] = text      # lets the loop verify quotes verbatim
    steps_dir = lay["fmt_dir"] / "adapt_steps"
    if not _adapt_stage_kwargs(adapt_params, kwargs, steps_dir, args.stop_after, args.guided):
        return
    presentation = adapt_fn(full, **kwargs)
    if presentation is None:
        _report_stop(steps_dir, args.stop_after, args.guided)
        return
    lay["adapt"].write_text(presentation.model_dump_json(indent=2), encoding="utf-8")
    print(f"Presentation written to {lay['adapt']}", file=sys.stderr)

    # 3. Extract
    extract_fn = importlib.import_module(extractor_mod).extract
    doc = extract_fn(full, presentation)
    lay["extract"].write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    print(f"Render document written to {lay['extract']}", file=sys.stderr)

    # 4. Render (optional) — each renderer lays out its own files under the format dir
    #    (carousels → html/ + slides/; newsletter → newsletter.md/.html).
    if args.render:
        render_from_json = importlib.import_module(renderer_mod).render_from_json
        print(f"Rendering into {lay['fmt_dir']}/", file=sys.stderr)
        await asyncio.to_thread(render_from_json, lay["extract"], lay["fmt_dir"])
    _report_check(lay["extract"], args.format)


async def cmd_program(args: argparse.Namespace) -> None:
    from agent import analyze_program
    from models.program_analysis import ProgramAnalysisInput

    input_path = args.program
    text = Path(input_path).read_text(encoding="utf-8").strip()
    if not text:
        print("Empty program file.", file=sys.stderr)
        sys.exit(1)

    stem = Path(input_path).stem
    candidate = args.candidate or stem
    lay = _layout(stem, base=_base_dir(input_path, stem))
    lay["base"].mkdir(parents=True, exist_ok=True)

    result = await analyze_program(
        ProgramAnalysisInput(candidate=candidate, program_text=text),
        no_api=args.no_api,
        steps_dir=lay["steps"],
    )
    lay["analysis"].write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"Analysis written to {lay['analysis']}", file=sys.stderr)
    print(f"Step outputs → {lay['steps']}/", file=sys.stderr)


async def cmd_fetch(args: argparse.Namespace) -> None:
    from tools.feeds import FEEDS, fetch_article, list_candidates

    if args.url:
        import httpx
        try:
            path = await fetch_article(args.url, Path(args.dir))
        except httpx.HTTPError as exc:
            print(f"Could not fetch {args.url}: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"Saved to {path}", file=sys.stderr)
        print(f"Next: python main.py produce {path} --render", file=sys.stderr)
        return

    if args.list_sources:
        for slug, (label, url) in FEEDS.items():
            print(f"{slug:16} {label:26} {url}")
        return

    try:
        candidates = await list_candidates(args.source, args.limit)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    for item in candidates:
        print(f"[{item['source']}] {item['date']}\n  {item['title']}\n  {item['url']}")
    sys.stdout.flush()
    print(f"\n{len(candidates)} candidates. "
          "Fetch one with: python main.py fetch <url>", file=sys.stderr)


async def cmd_check(args: argparse.Namespace) -> None:
    from tools.check_deck import check, format_report

    article = Path(args.article) if args.article else None
    report = check(Path(args.document), article)
    print(format_report(report))
    if args.reader:
        # The model-driven pass: opt-in, so the deterministic controller stays
        # free and instant in an edit loop. Its findings never fail the run —
        # a judge is advice, the rules we wrote down are the gate.
        from tools.deck_review import review, format_report as format_review
        model_report = await asyncio.to_thread(
            review, Path(args.document), article, args.no_api)
        print(format_review(model_report))
    # Advisory families are printed but do not fail the run.
    if any(problems for family, problems in report.items() if "advisory" not in family):
        sys.exit(1)


# ── Argument parser ───────────────────────────────────────────────────────────

def _add_source_args(p: argparse.ArgumentParser) -> None:
    """Source metadata — never inferred from the body, shown on the hook slide."""
    p.add_argument("--title", help="the source's own title, as published (shown on slide 1)")
    p.add_argument("--source", help="publication name (e.g. \"Aeon\")")
    p.add_argument("--url", help="canonical article URL")
    p.add_argument("--published-at", help="publication date as it should read (e.g. \"7 septembre 2026\")")
    p.add_argument("--language", metavar="LANGUE",
                   help="the source's language in French when not French (e.g. \"espagnol\"); "
                        "slide 1 says the title and quotes are translated from it")
    p.add_argument("--duration", type=int, metavar="MIN",
                   help="listening/viewing time in minutes (default: estimated from the word count)")


def _add_stop_after(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stop-after", choices=["question", "enjeu", "idees", "moments", "contexte", "socle", "hook"],
                   help="stop the carousel adapt after this step, to review or edit it "
                        "(<format>/adapt_steps/); rerun to continue from it")
    p.add_argument("--guided", action="store_true",
                   help="stop at each step awaiting your pick (see `choose`) instead of taking the recommended ones")


def _add_instruction_args(p: argparse.ArgumentParser) -> None:
    """Editorial angle for the run — reaches the analysis steps and the adapt agent."""
    g = p.add_mutually_exclusive_group()
    g.add_argument("--instructions", help="extra analysis instructions (inline)")
    g.add_argument("--instructions-file", help="extra analysis instructions (from file)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="main.py", description="Analyze news articles and render Instagram carousels.")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_format(p: argparse.ArgumentParser) -> None:
        p.add_argument("--format", choices=list(FORMATS), default=DEFAULT_FORMAT,
                       help="output format (default: %(default)s)")

    p = sub.add_parser("analyze", help="run the full analysis pipeline on an article")
    p.add_argument("article", nargs="?", help="article .txt file (reads stdin if omitted)")
    p.add_argument("--no-api", action="store_true", help="use the local claude CLI instead of the API")
    _add_instruction_args(p)
    p.add_argument("--medium", choices=["article", "video", "podcast"], default="article",
                   help="source medium — drives reader-facing vocabulary (default: article)")
    _add_source_args(p)
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("adapt", help="adapt an analysis into a carousel presentation")
    p.add_argument("analysis", help="analysis.json")
    _add_format(p)
    p.add_argument("--no-api", action="store_true")
    _add_stop_after(p)
    p.set_defaults(func=cmd_adapt)

    p = sub.add_parser("choose", help="keep options at a carousel adapt step (or ask for other options)")
    p.add_argument("fmt_dir", help="format folder, e.g. samples/outputs/<stem>/instagram_carousel_optimized")
    p.add_argument("step", choices=["question", "enjeu", "idees", "moments", "contexte", "socle", "hook"])
    p.add_argument("--pick", help="comma-separated option ids to keep")
    p.add_argument("--edit", action="append", default=[], metavar="ID=TEXT",
                   help="rewrite an option's text (ID.field=TEXT for another field); repeatable")
    p.add_argument("--reason", default="", help="why, kept in the choice log")
    p.add_argument("--more", action="store_true", help="set the options aside and generate others")
    p.add_argument("--remark", default="", help="with --more: what was missing from the options")
    p.add_argument("--no-api", action="store_true")
    p.set_defaults(func=cmd_choose)

    p = sub.add_parser("fix", help="overwrite one field of a carousel adapt, without regenerating")
    p.add_argument("fmt_dir", help="format folder")
    p.add_argument("field", help="deck field path, e.g. hook.subtitle or display.reading_beats[0].answer")
    p.add_argument("text")
    p.set_defaults(func=cmd_fix)

    p = sub.add_parser("extract", help="trim a presentation into a render-ready document")
    p.add_argument("analysis", help="analysis.json")
    p.add_argument("presentation", help="presentation.json")
    _add_format(p)
    p.add_argument("--render", action="store_true")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("produce", help="full pipeline: analyze → adapt → extract → render")
    p.add_argument("article", help="article .txt file")
    _add_format(p)
    p.add_argument("--no-api", action="store_true")
    p.add_argument("--render", action="store_true")
    _add_stop_after(p)
    _add_instruction_args(p)
    p.add_argument("--medium", choices=["article", "video", "podcast"], default="article",
                   help="source medium — drives reader-facing vocabulary (default: article)")
    _add_source_args(p)
    p.set_defaults(func=cmd_produce)

    p = sub.add_parser("program", help="analyze a candidate's program (hors-série)")
    p.add_argument("program", help="candidate program .txt file")
    p.add_argument("--candidate", help="candidate display name (default: file stem)")
    p.add_argument("--no-api", action="store_true", help="use cached steps / local claude CLI")
    p.set_defaults(func=cmd_program)

    p = sub.add_parser("render", help="render a document (carousel slides, or newsletter md/html)")
    p.add_argument("document", help="extract.json (the render document)")
    p.add_argument("output_dir", nargs="?", help="output directory (default: alongside the json)")
    _add_format(p)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("html", help="write standalone HTML slide files (no screenshots)")
    p.add_argument("document", help="extract.json (the render document)")
    p.add_argument("output_dir", nargs="?", help="output directory (default: alongside the json)")
    _add_format(p)
    p.set_defaults(func=cmd_html)

    p = sub.add_parser("shoot", help="screenshot HTML to PNG (slide dir → each slide; single html → full page)")
    p.add_argument("path", help="directory of HTML slides, or a single HTML file (e.g. newsletter.email.html)")
    p.add_argument("output", nargs="?", help="output PNG path (single-file mode only; default: alongside the html)")
    p.set_defaults(func=cmd_shoot)

    p = sub.add_parser("simplify", help="shrink an existing analysis for readability")
    p.add_argument("analysis", help="analysis.json")
    p.add_argument("--no-api", action="store_true")
    p.set_defaults(func=cmd_simplify)

    p = sub.add_parser("validate", help="node-graph integrity checks on an analysis")
    p.add_argument("analysis", help="analysis.json")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("verify", help="find sources for/against claims")
    p.add_argument("target", nargs="+", help="analysis.json, or claim text")
    p.add_argument("--claim", type=int, action="append", help="claim index to verify (repeatable)")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("graph", help="render the node graph to HTML")
    p.add_argument("analysis", help="analysis.json")
    p.add_argument("output", nargs="?", help="output .html (default: alongside the json)")
    p.set_defaults(func=cmd_graph)

    p = sub.add_parser("fetch", help="list free-to-read French analysis feeds, or fetch an article")
    p.add_argument("url", nargs="?", help="article URL to scrape into --dir")
    p.add_argument("--source", "-s", action="append", help="feed slug to list (repeatable; default: all)")
    p.add_argument("--limit", type=int, default=5, help="items per feed (default: 5)")
    p.add_argument("--list-sources", action="store_true", help="print the known feeds and exit")
    p.add_argument("--dir", default="samples/articles", help="where to save (default: samples/articles)")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("check", help="controller: structure, accuracy against the article, French typography")
    p.add_argument("document", help="extract.json (the render document)")
    p.add_argument("article", nargs="?", help="article .txt (default: found next to the analysis)")
    p.add_argument("--reader", action="store_true",
                   help="also run the model-driven review (reader + fidelity passes)")
    p.add_argument("--no-api", action="store_true",
                   help="--reader: use the local claude CLI instead of the API")
    p.set_defaults(func=cmd_check)

    return parser


async def main() -> None:
    args = _build_parser().parse_args()
    await args.func(args)


if __name__ == "__main__":
    asyncio.run(main())
