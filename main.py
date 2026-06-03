import asyncio
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tools import scrape_article
from agent import analyze_article, analyze_for_carousel
from agent.carousel_mock import mock_carousel
from models import Article, CarouselInput

load_dotenv()

OUTPUTS_DIR = Path("samples/outputs")


async def run_article_analysis():
    url = "https://example.com/some-news-article"
    scraped = await scrape_article(url)
    article = Article(**scraped)
    analysis = await analyze_article(article)
    print(analysis.model_dump_json(indent=2))


async def run_carousel(text: str, mock: bool = False, input_path: str | None = None):
    carousel_input = CarouselInput(body=text)
    if mock:
        result = mock_carousel(carousel_input)
    else:
        result = await analyze_for_carousel(carousel_input)

    json_output = result.model_dump_json(indent=2)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(input_path).stem if input_path else datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUTS_DIR / f"{stem}_carousel.json"
    output_path.write_text(json_output, encoding="utf-8")
    print(f"Output written to {output_path}", file=sys.stderr)
    print(json_output)


async def main():
    args = sys.argv[1:]
    if args and args[0] == "carousel":
        # Usage:
        #   python main.py carousel <article.txt> [--mock]
        #   python main.py carousel --mock < article.txt   (output named by timestamp)
        use_mock = "--mock" in args
        positional = [a for a in args[1:] if not a.startswith("--")]
        if positional:
            input_path = positional[0]
            text = Path(input_path).read_text(encoding="utf-8").strip()
        else:
            input_path = None
            text = sys.stdin.read().strip()
        if not text:
            print("Usage: python main.py carousel <article.txt> [--mock]", file=sys.stderr)
            sys.exit(1)
        await run_carousel(text, mock=use_mock, input_path=input_path)
    else:
        await run_article_analysis()


if __name__ == "__main__":
    asyncio.run(main())
