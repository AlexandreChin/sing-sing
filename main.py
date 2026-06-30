import argparse
import asyncio
import importlib
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
DEFAULT_FORMAT = "instagram_carousel_long"


def _layout(stem: str, fmt: str | None = None) -> dict:
    """Per-analysis output layout:
    outputs/<stem>/{analysis.json, steps/, <fmt>/{adapt.json, extract.json, slides/}}."""
    base = OUTPUTS_DIR / stem
    paths = {"base": base, "analysis": base / "analysis.json", "steps": base / "steps"}
    if fmt:
        fdir = base / fmt
        paths |= {"fmt_dir": fdir, "adapt": fdir / "adapt.json",
                  "extract": fdir / "extract.json",
                  "html": fdir / "html", "slides": fdir / "slides"}
    return paths


async def run_full_analysis(text: str, no_api: bool = False, input_path: str | None = None, extra_instructions: str | None = None) -> Path:
    analysis_input = FullAnalysisInput(body=text, extra_instructions=extra_instructions)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(input_path).stem if input_path else datetime.now().strftime("%Y%m%d_%H%M%S")
    lay = _layout(stem)
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

async def cmd_analyze(args: argparse.Namespace) -> None:
    if args.instructions is not None:
        extra_instructions = args.instructions
    elif args.instructions_file is not None:
        extra_instructions = Path(args.instructions_file).read_text(encoding="utf-8").strip()
    else:
        extra_instructions = None

    if args.article:
        input_path = args.article
        text = Path(input_path).read_text(encoding="utf-8").strip()
    else:
        input_path = None
        text = sys.stdin.read().strip()
    if not text:
        print("No article text provided (pass <article.txt> or pipe via stdin).", file=sys.stderr)
        sys.exit(1)

    output_path = await run_full_analysis(text, no_api=args.no_api, input_path=input_path, extra_instructions=extra_instructions)
    if args.render and output_path:
        from renderer.instagram_carousel_long.renderer import render_from_json
        stem = Path(input_path).stem if input_path else "analysis"
        slides_dir = _layout(stem, "instagram_carousel_long")["slides"]
        print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(render_from_json, output_path, slides_dir)


async def cmd_simplify(args: argparse.Namespace) -> None:
    from agent.instagram_carousel_simplify_agent import simplify_carousel
    json_path = Path(args.analysis)
    print(f"Simplifying{' (no-api)' if args.no_api else ''}…", file=sys.stderr, flush=True)
    result = await simplify_carousel(json_path, no_api=args.no_api)
    out_path = json_path.with_stem(json_path.stem + "_simplified")
    out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"Simplified JSON written to {out_path}", file=sys.stderr)
    if args.render:
        from renderer.instagram_carousel_long.renderer import render_from_json
        slides_dir = out_path.parent / out_path.stem
        print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(render_from_json, out_path, slides_dir)


async def cmd_adapt(args: argparse.Namespace) -> None:
    from models.full_analysis import ArticleFullAnalysis

    agent_mod = FORMATS[args.format][0]
    adapt_fn = importlib.import_module(agent_mod).adapt
    json_path = Path(args.analysis)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    full = ArticleFullAnalysis.model_validate(data)
    presentation = adapt_fn(full, no_api=args.no_api)
    out_path = json_path.with_stem(json_path.stem + f"_{args.format}_adapt")
    out_path.write_text(presentation.model_dump_json(indent=2), encoding="utf-8")
    print(f"Presentation written to {out_path}", file=sys.stderr)


async def cmd_extract(args: argparse.Namespace) -> None:
    from models.full_analysis import ArticleFullAnalysis
    from models.instagram_carousel_presentation import InstagramCarouselPresentation

    _, extractor_mod, renderer_mod = FORMATS[args.format]
    extract_fn = importlib.import_module(extractor_mod).extract
    full = ArticleFullAnalysis.model_validate(json.loads(Path(args.analysis).read_text(encoding="utf-8")))
    presentation = InstagramCarouselPresentation.model_validate(json.loads(Path(args.presentation).read_text(encoding="utf-8")))
    doc = extract_fn(full, presentation)
    out_path = Path(args.analysis).with_stem(Path(args.analysis).stem + f"_{args.format}_extract")
    out_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    print(f"Document written to {out_path}", file=sys.stderr)
    if args.render:
        render_from_json = importlib.import_module(renderer_mod).render_from_json
        slides_dir = out_path.parent / out_path.stem
        print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(render_from_json, out_path, slides_dir)


async def cmd_render(args: argparse.Namespace) -> None:
    json_path = Path(args.document)
    _, _, renderer_mod = FORMATS[args.format]
    mod = importlib.import_module(renderer_mod)
    if args.output_dir:
        slides_dir = Path(args.output_dir)
        print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(mod.render_from_json, json_path, slides_dir)
    else:
        # Default: write to the canonical html/ + slides/ next to the document,
        # matching `produce` — not a <stem>/ subfolder.
        from renderer.shoot import shoot_dir
        html_dir, slides_dir = json_path.parent / "html", json_path.parent / "slides"
        print(f"Writing HTML to {html_dir}/ and PNG to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(mod.generate_html_from_json, json_path, html_dir)
        await asyncio.to_thread(shoot_dir, html_dir, slides_dir)


async def cmd_html(args: argparse.Namespace) -> None:
    # Step 1 of the render split: write standalone HTML slide files (no screenshots).
    json_path = Path(args.document)
    out_dir = Path(args.output_dir) if args.output_dir else json_path.parent / json_path.stem
    _, _, renderer_mod = FORMATS[args.format]
    generate_html_from_json = importlib.import_module(renderer_mod).generate_html_from_json
    print(f"Writing HTML slides to {out_dir}/", file=sys.stderr)
    await asyncio.to_thread(generate_html_from_json, json_path, out_dir)


async def cmd_shoot(args: argparse.Namespace) -> None:
    # Step 2 of the render split: screenshot the HTML slide files to PNG.
    from renderer.shoot import shoot_dir
    html_dir = Path(args.html_dir)
    print(f"Screenshotting HTML in {html_dir}/", file=sys.stderr)
    await asyncio.to_thread(shoot_dir, html_dir)


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
    lay = _layout(stem, args.format)
    lay["fmt_dir"].mkdir(parents=True, exist_ok=True)
    full = await analyze_for_full_analysis(
        FullAnalysisInput(body=text),
        no_api=args.no_api,
        steps_dir=lay["steps"],
    )
    lay["analysis"].write_text(full.model_dump_json(indent=2), encoding="utf-8")
    print(f"Analysis written to {lay['analysis']}", file=sys.stderr)

    # 2. Adapt
    adapt_fn = importlib.import_module(agent_mod).adapt
    presentation = adapt_fn(full, no_api=args.no_api)
    lay["adapt"].write_text(presentation.model_dump_json(indent=2), encoding="utf-8")
    print(f"Presentation written to {lay['adapt']}", file=sys.stderr)

    # 3. Extract
    extract_fn = importlib.import_module(extractor_mod).extract
    doc = extract_fn(full, presentation)
    lay["extract"].write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    print(f"Render document written to {lay['extract']}", file=sys.stderr)

    # 4. Render (optional) — HTML and PNG into separate subfolders
    if args.render:
        from renderer.shoot import shoot_dir
        generate_html_from_json = importlib.import_module(renderer_mod).generate_html_from_json
        print(f"Writing HTML slides to {lay['html']}/", file=sys.stderr)
        await asyncio.to_thread(generate_html_from_json, lay["extract"], lay["html"])
        print(f"Rendering PNG slides to {lay['slides']}/", file=sys.stderr)
        await asyncio.to_thread(shoot_dir, lay["html"], lay["slides"])


# ── Argument parser ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="main.py", description="Analyze news articles and render Instagram carousels.")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_format(p: argparse.ArgumentParser) -> None:
        p.add_argument("--format", choices=list(FORMATS), default=DEFAULT_FORMAT,
                       help="output format (default: %(default)s)")

    p = sub.add_parser("analyze", help="run the full analysis pipeline on an article")
    p.add_argument("article", nargs="?", help="article .txt file (reads stdin if omitted)")
    p.add_argument("--no-api", action="store_true", help="use the local claude CLI instead of the API")
    p.add_argument("--render", action="store_true", help="also render long-format slides")
    p.add_argument("--instructions", help="extra analysis instructions (inline)")
    p.add_argument("--instructions-file", help="extra analysis instructions (from file)")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("adapt", help="adapt an analysis into a carousel presentation")
    p.add_argument("analysis", help="analysis.json")
    _add_format(p)
    p.add_argument("--no-api", action="store_true")
    p.set_defaults(func=cmd_adapt)

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
    p.set_defaults(func=cmd_produce)

    p = sub.add_parser("render", help="render slides (HTML + screenshots) from a document")
    p.add_argument("document", help="extract.json (the render document)")
    p.add_argument("output_dir", nargs="?", help="output directory (default: alongside the json)")
    _add_format(p)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("html", help="write standalone HTML slide files (no screenshots)")
    p.add_argument("document", help="extract.json (the render document)")
    p.add_argument("output_dir", nargs="?", help="output directory (default: alongside the json)")
    _add_format(p)
    p.set_defaults(func=cmd_html)

    p = sub.add_parser("shoot", help="screenshot HTML slide files to PNG")
    p.add_argument("html_dir", help="directory of HTML slide files")
    p.set_defaults(func=cmd_shoot)

    p = sub.add_parser("simplify", help="shrink an existing analysis for readability")
    p.add_argument("analysis", help="analysis.json")
    p.add_argument("--no-api", action="store_true")
    p.add_argument("--render", action="store_true")
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

    return parser


async def main() -> None:
    args = _build_parser().parse_args()
    await args.func(args)


if __name__ == "__main__":
    asyncio.run(main())
