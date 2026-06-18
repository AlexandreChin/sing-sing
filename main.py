import asyncio
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tools import scrape_article
from agent import analyze_article, analyze_for_carousel
from models import Article, CarouselInput

load_dotenv()

OUTPUTS_DIR = Path("samples/outputs")


async def run_article_analysis():
    url = "https://example.com/some-news-article"
    scraped = await scrape_article(url)
    article = Article(**scraped)
    analysis = await analyze_article(article)
    print(analysis.model_dump_json(indent=2))


async def run_carousel(text: str, no_api: bool = False, input_path: str | None = None) -> Path:
    carousel_input = CarouselInput(body=text)
    result = await analyze_for_carousel(carousel_input, no_api=no_api)

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
    if args and args[0] == "carousel":
        # Usage: python main.py carousel <article.txt> [--no-api] [--render]
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
            print("Usage: python main.py carousel <article.txt> [--no-api] [--render]", file=sys.stderr)
            sys.exit(1)
        output_path = await run_carousel(text, no_api=no_api, input_path=input_path)
        if do_render and output_path:
            from renderer.render import render_from_json
            stem = Path(input_path).stem if input_path else "carousel"
            slides_dir = OUTPUTS_DIR / stem
            print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
            await asyncio.to_thread(render_from_json, output_path, slides_dir)

    elif args and args[0] == "simplify":
        # Usage: python main.py simplify <carousel.json> [--no-api] [--render]
        no_api = "--no-api" in args
        do_render = "--render" in args
        positional = [a for a in args[1:] if not a.startswith("--")]
        if not positional:
            print("Usage: python main.py simplify <carousel.json> [--no-api] [--render]", file=sys.stderr)
            sys.exit(1)
        json_path = Path(positional[0])
        from agent.simplify_agent import simplify_carousel
        print(f"Simplifying{' (no-api)' if no_api else ''}…", file=sys.stderr, flush=True)
        result = await simplify_carousel(json_path, no_api=no_api)
        out_path = json_path.with_stem(json_path.stem + "_simplified")
        out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"Simplified JSON written to {out_path}", file=sys.stderr)
        if do_render:
            from renderer.render import render_from_json
            slides_dir = out_path.parent / out_path.stem
            print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
            await asyncio.to_thread(render_from_json, out_path, slides_dir)

    elif args and args[0] == "render":
        # Usage: python main.py render <carousel.json> [<output_dir>]
        positional = [a for a in args[1:] if not a.startswith("--")]
        if not positional:
            print("Usage: python main.py render <carousel.json> [<output_dir>]", file=sys.stderr)
            sys.exit(1)
        json_path = Path(positional[0])
        slides_dir = Path(positional[1]) if len(positional) > 1 else json_path.parent / json_path.stem
        from renderer.render import render_from_json
        print(f"Rendering slides to {slides_dir}/", file=sys.stderr)
        await asyncio.to_thread(render_from_json, json_path, slides_dir)

    else:
        await run_article_analysis()


if __name__ == "__main__":
    asyncio.run(main())
