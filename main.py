import asyncio
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from agent import analyze_for_full_analysis
from models import FullAnalysisInput

load_dotenv()

OUTPUTS_DIR = Path("samples/outputs")



async def run_full_analysis(text: str, no_api: bool = False, input_path: str | None = None) -> Path:
    analysis_input = FullAnalysisInput(body=text)
    result = await analyze_for_full_analysis(analysis_input, no_api=no_api)

    json_output = result.model_dump_json(indent=2)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(input_path).stem if input_path else datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUTS_DIR / f"{stem}_analysis.json"
    output_path.write_text(json_output, encoding="utf-8")
    print(f"Output written to {output_path}", file=sys.stderr)
    print(json_output)
    return output_path


async def main():
    args = sys.argv[1:]
    if args and args[0] == "analyze":
        # Usage: python main.py analyze <article.txt> [--no-api] [--render]
        no_api = "--no-api" in args
        do_render = "--render" in args
        positional = [a for a in args[1:] if not a.startswith("--")]
        if positional:
            input_path = positional[0]
            text = Path(input_path).read_text(encoding="utf-8").strip()
        else:
            input_path = None
            text = sys.stdin.read().strip()
        if not text:
            print("Usage: python main.py analyze <article.txt> [--no-api] [--render]", file=sys.stderr)
            sys.exit(1)
        output_path = await run_full_analysis(text, no_api=no_api, input_path=input_path)
        if do_render and output_path:
            from renderer.instagram_carousel_renderer import render_from_json
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
            from renderer.instagram_carousel_renderer import render_from_json
            slides_dir = out_path.parent / out_path.stem
            print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
            await asyncio.to_thread(render_from_json, out_path, slides_dir)

    elif args and args[0] == "extract":
        # Usage: python main.py extract <analysis.json> [--format <fmt>] [--render]
        import importlib
        import json
        from models.full_analysis import ArticleFullAnalysis
        from extractors.registry import FORMATS

        do_render = "--render" in args
        fmt_args = [args[i + 1] for i, a in enumerate(args) if a == "--format" and i + 1 < len(args)]
        fmt = fmt_args[0] if fmt_args else "instagram_carousel"
        positional = [a for a in args[1:] if not a.startswith("--") and a not in fmt_args]
        if not positional or fmt not in FORMATS:
            known = ", ".join(FORMATS)
            print(f"Usage: python main.py extract <analysis.json> [--format {{{known}}}] [--render]", file=sys.stderr)
            sys.exit(1)

        extractor_mod, renderer_mod = FORMATS[fmt]
        extract = importlib.import_module(extractor_mod).extract
        json_path = Path(positional[0])
        data = json.loads(json_path.read_text(encoding="utf-8"))
        full = ArticleFullAnalysis.model_validate(data)
        extracted = extract(full)
        out_path = json_path.with_stem(json_path.stem + f"_{fmt}")
        out_path.write_text(extracted.model_dump_json(indent=2), encoding="utf-8")
        print(f"Extracted JSON written to {out_path}", file=sys.stderr)
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
        from renderer.instagram_carousel_renderer import render_from_json
        print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(render_from_json, json_path, slides_dir)

    else:
        print("Usage: python main.py <analyze|extract|simplify|render> [args]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
