import asyncio
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from agent import analyze_for_full_analysis
from models import FullAnalysisInput

load_dotenv()

OUTPUTS_DIR = Path("samples/outputs")



async def run_full_analysis(text: str, no_api: bool = False, input_path: str | None = None, extra_instructions: str | None = None) -> Path:
    analysis_input = FullAnalysisInput(body=text, extra_instructions=extra_instructions)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(input_path).stem if input_path else datetime.now().strftime("%Y%m%d_%H%M%S")
    steps_dir = OUTPUTS_DIR / f"{stem}_steps"
    output_path = OUTPUTS_DIR / f"{stem}_analysis.json"

    result = await analyze_for_full_analysis(analysis_input, no_api=no_api, steps_dir=steps_dir)

    json_output = result.model_dump_json(indent=2)
    output_path.write_text(json_output, encoding="utf-8")
    print(f"Output written to {output_path}", file=sys.stderr)
    print(f"Step outputs → {steps_dir}/", file=sys.stderr)
    print(json_output)
    return output_path


async def main():
    args = sys.argv[1:]
    if args and args[0] == "analyze":
        # Usage: python main.py analyze <article.txt> [--no-api] [--render]
        #                               [--instructions "..."] [--instructions-file <path>]
        no_api = "--no-api" in args
        do_render = "--render" in args
        instr_args = [args[i+1] for i, a in enumerate(args) if a == "--instructions" and i+1 < len(args)]
        instr_file_args = [args[i+1] for i, a in enumerate(args) if a == "--instructions-file" and i+1 < len(args)]
        flags = {"--no-api", "--render", "--instructions", "--instructions-file"} | set(instr_args) | set(instr_file_args)
        positional = [a for a in args[1:] if a not in flags and not a.startswith("--")]
        extra_instructions: str | None = None
        if instr_args:
            extra_instructions = instr_args[-1]
        elif instr_file_args:
            extra_instructions = Path(instr_file_args[-1]).read_text(encoding="utf-8").strip()
        if positional:
            input_path = positional[0]
            text = Path(input_path).read_text(encoding="utf-8").strip()
        else:
            input_path = None
            text = sys.stdin.read().strip()
        if not text:
            print("Usage: python main.py analyze <article.txt> [--no-api] [--render]", file=sys.stderr)
            print("                              [--instructions \"...\"] [--instructions-file <path>]", file=sys.stderr)
            sys.exit(1)
        output_path = await run_full_analysis(text, no_api=no_api, input_path=input_path, extra_instructions=extra_instructions)
        if do_render and output_path:
            from renderer.instagram_carousel_long.renderer import render_from_json
            stem = Path(input_path).stem if input_path else "analysis"
            slides_dir = OUTPUTS_DIR / stem
            print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
            await asyncio.to_thread(render_from_json, output_path, slides_dir)

    elif args and args[0] == "simplify":
        # Usage: python main.py simplify <carousel.json> [--no-api] [--render]
        no_api = "--no-api" in args
        do_render = "--render" in args
        positional = [a for a in args[1:] if not a.startswith("--")]
        if not positional:
            print("Usage: python main.py simplify <analysis.json> [--no-api] [--render]", file=sys.stderr)
            sys.exit(1)
        json_path = Path(positional[0])
        from agent.simplify_agent import simplify_carousel
        print(f"Simplifying{' (no-api)' if no_api else ''}…", file=sys.stderr, flush=True)
        result = await simplify_carousel(json_path, no_api=no_api)
        out_path = json_path.with_stem(json_path.stem + "_simplified")
        out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"Simplified JSON written to {out_path}", file=sys.stderr)
        if do_render:
            from renderer.instagram_carousel_long.renderer import render_from_json
            slides_dir = out_path.parent / out_path.stem
            print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
            await asyncio.to_thread(render_from_json, out_path, slides_dir)

    elif args and args[0] == "adapt":
        # Usage: python main.py adapt <analysis.json> [--format <fmt>] [--no-api]
        import importlib
        import json
        from models.full_analysis import ArticleFullAnalysis
        from extractors.registry import FORMATS

        no_api = "--no-api" in args
        fmt_args = [args[i + 1] for i, a in enumerate(args) if a == "--format" and i + 1 < len(args)]
        fmt = fmt_args[0] if fmt_args else "instagram_carousel_long"
        positional = [a for a in args[1:] if not a.startswith("--") and a not in fmt_args]
        if not positional or fmt not in FORMATS:
            known = ", ".join(FORMATS)
            print(f"Usage: python main.py adapt <analysis.json> [--format {{{known}}}] [--no-api]", file=sys.stderr)
            sys.exit(1)

        agent_mod = FORMATS[fmt][0]
        adapt_fn = importlib.import_module(agent_mod).adapt
        json_path = Path(positional[0])
        data = json.loads(json_path.read_text(encoding="utf-8"))
        full = ArticleFullAnalysis.model_validate(data)
        presentation = adapt_fn(full, no_api=no_api)
        out_path = json_path.with_stem(json_path.stem + f"_{fmt}_presentation")
        out_path.write_text(presentation.model_dump_json(indent=2), encoding="utf-8")
        print(f"Presentation written to {out_path}", file=sys.stderr)

    elif args and args[0] == "extract":
        # Usage: python main.py extract <analysis.json> <presentation.json> [--format <fmt>] [--render]
        import importlib
        import json
        from models.full_analysis import ArticleFullAnalysis
        from models.instagram_carousel_presentation import InstagramCarouselPresentation
        from extractors.registry import FORMATS

        do_render = "--render" in args
        fmt_args = [args[i + 1] for i, a in enumerate(args) if a == "--format" and i + 1 < len(args)]
        fmt = fmt_args[0] if fmt_args else "instagram_carousel_long"
        positional = [a for a in args[1:] if not a.startswith("--") and a not in fmt_args]
        if len(positional) < 2 or fmt not in FORMATS:
            known = ", ".join(FORMATS)
            print(f"Usage: python main.py extract <analysis.json> <presentation.json> [--format {{{known}}}] [--render]", file=sys.stderr)
            sys.exit(1)

        _, extractor_mod, renderer_mod = FORMATS[fmt]
        extract_fn = importlib.import_module(extractor_mod).extract
        full = ArticleFullAnalysis.model_validate(json.loads(Path(positional[0]).read_text(encoding="utf-8")))
        presentation = InstagramCarouselPresentation.model_validate(json.loads(Path(positional[1]).read_text(encoding="utf-8")))
        doc = extract_fn(full, presentation)
        out_path = Path(positional[0]).with_stem(Path(positional[0]).stem + f"_{fmt}")
        out_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
        print(f"Document written to {out_path}", file=sys.stderr)
        if do_render:
            render_from_json = importlib.import_module(renderer_mod).render_from_json
            slides_dir = out_path.parent / out_path.stem
            print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
            await asyncio.to_thread(render_from_json, out_path, slides_dir)

    elif args and args[0] == "render":
        # Usage: python main.py render <carousel.json> [<output_dir>]
        positional = [a for a in args[1:] if not a.startswith("--")]
        if not positional:
            print("Usage: python main.py render <analysis.json> [<output_dir>]", file=sys.stderr)
            sys.exit(1)
        json_path = Path(positional[0])
        slides_dir = Path(positional[1]) if len(positional) > 1 else json_path.parent / json_path.stem
        from renderer.instagram_carousel_long.renderer import render_from_json
        print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(render_from_json, json_path, slides_dir)

    elif args and args[0] == "validate":
        # Usage: python main.py validate <analysis.json>
        from tools.validate import validate as _validate
        positional = [a for a in args[1:] if not a.startswith("--")]
        if not positional:
            print("Usage: python main.py validate <analysis.json>", file=sys.stderr)
            sys.exit(1)
        path = Path(positional[0])
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

    elif args and args[0] == "verify":
        # Usage: python main.py verify <analysis.json> [--claim <index>]
        #        python main.py verify "<claim text>"
        import json as _json
        from tools.verify import find_sources_for_claim
        from models.article import Claim
        claim_idx_args = [args[i+1] for i, a in enumerate(args) if a == "--claim" and i+1 < len(args)]
        positional = [a for a in args[1:] if not a.startswith("--") and a not in claim_idx_args]
        if not positional:
            print("Usage: python main.py verify <analysis.json> [--claim <index>]", file=sys.stderr)
            print("       python main.py verify \"<claim text>\"", file=sys.stderr)
            sys.exit(1)
        candidate = Path(positional[0])
        if candidate.exists() and candidate.suffix == ".json":
            data = _json.loads(candidate.read_text(encoding="utf-8"))
            raw_claims = data.get("annotations", {}).get("facts_vs_opinions", {}).get("claims_and_sources", [])
            if not raw_claims:
                print("No claims found in JSON", file=sys.stderr)
                sys.exit(1)
            indices = [int(x) for x in claim_idx_args] if claim_idx_args else list(range(len(raw_claims)))
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
            text = " ".join(positional)
            print(f"Verifying: {text[:80]}")
            result = await find_sources_for_claim(Claim(text=text))
            print(f"  ✓ confirming:    {len(result.confirming)}")
            print(f"  ✗ contradicting: {len(result.contradicting)}")
            print(f"  ~ neutral:       {len(result.neutral)}")
            for src in result.confirming + result.contradicting:
                print(f"  [{src.stance}] {src.title[:60]} — {src.stance_reason}")

    elif args and args[0] == "graph":
        # Usage: python main.py graph <analysis.json> [output.html]
        positional = [a for a in args[1:] if not a.startswith("--")]
        if not positional:
            print("Usage: python main.py graph <analysis.json> [output.html]", file=sys.stderr)
            sys.exit(1)
        from tools.graph_generator import generate_from_json
        json_path = Path(positional[0])
        out_path = Path(positional[1]) if len(positional) > 1 else None
        out = generate_from_json(json_path, out_path)
        import json as _json
        from tools.graph_generator import build_graph as _build_graph
        _data = _json.loads(json_path.read_text(encoding="utf-8"))
        _nodes, _edges = _build_graph(_data)
        print(f"Graph: {len(_nodes)} nodes, {len(_edges)} edges → {out}", file=sys.stderr)

    elif args and args[0] == "produce":
        # Usage: python main.py produce <article.txt> [--format <fmt>] [--no-api] [--render]
        import importlib
        import json as _json
        from models.full_analysis import ArticleFullAnalysis
        from models.instagram_carousel_presentation import InstagramCarouselPresentation
        from extractors.registry import FORMATS

        no_api = "--no-api" in args
        do_render = "--render" in args
        fmt_args = [args[i + 1] for i, a in enumerate(args) if a == "--format" and i + 1 < len(args)]
        fmt = fmt_args[0] if fmt_args else "instagram_carousel_long"
        flags = {"--no-api", "--render", "--format"} | set(fmt_args)
        positional = [a for a in args[1:] if a not in flags and not a.startswith("--")]
        if not positional or fmt not in FORMATS:
            known = ", ".join(FORMATS)
            print(f"Usage: python main.py produce <article.txt> [--format {{{known}}}] [--no-api] [--render]", file=sys.stderr)
            sys.exit(1)

        agent_mod, extractor_mod, renderer_mod = FORMATS[fmt]

        # 1. Analyze
        input_path = positional[0]
        text = Path(input_path).read_text(encoding="utf-8").strip()
        stem = Path(input_path).stem
        steps_dir = OUTPUTS_DIR / f"{stem}_steps"
        analysis_path = OUTPUTS_DIR / f"{stem}_analysis.json"
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        full = await analyze_for_full_analysis(
            __import__("models", fromlist=["FullAnalysisInput"]).FullAnalysisInput(body=text),
            no_api=no_api,
            steps_dir=steps_dir,
        )
        analysis_path.write_text(full.model_dump_json(indent=2), encoding="utf-8")
        print(f"Analysis written to {analysis_path}", file=sys.stderr)

        # 2. Adapt
        adapt_fn = importlib.import_module(agent_mod).adapt
        presentation = adapt_fn(full, no_api=no_api)
        presentation_path = OUTPUTS_DIR / f"{stem}_analysis_{fmt}_presentation.json"
        presentation_path.write_text(presentation.model_dump_json(indent=2), encoding="utf-8")
        print(f"Presentation written to {presentation_path}", file=sys.stderr)

        # 3. Extract
        extract_fn = importlib.import_module(extractor_mod).extract
        doc = extract_fn(full, presentation)
        doc_path = OUTPUTS_DIR / f"{stem}_analysis_{fmt}.json"
        doc_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
        print(f"Document written to {doc_path}", file=sys.stderr)

        # 4. Render (optional)
        if do_render:
            render_from_json = importlib.import_module(renderer_mod).render_from_json
            slides_dir = doc_path.parent / doc_path.stem
            print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
            await asyncio.to_thread(render_from_json, doc_path, slides_dir)

    else:
        print("Usage: python main.py <analyze|adapt|extract|produce|render|validate|verify|graph> [args]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
