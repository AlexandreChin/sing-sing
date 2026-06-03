# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`sing-sing` is a Python 3.14 agent that analyzes news articles. It scrapes article content, sends it to Claude via the Anthropic API, and returns a structured JSON analysis (summary, sentiment, entities, claims, topics).

## Commands

```bash
# Install / sync dependencies
uv add <package>
uv sync

# Run
python main.py
```

Always use `uv add` to install new packages — never `pip install`.

## Architecture

```
main.py              entry point — orchestrates scrape → analyze flow
tools/
  scrape.py          fetch + parse article HTML (httpx + BeautifulSoup)
  search.py          search for news articles via Brave / Serper / Tavily
agent/
  analyzer.py        calls Claude (claude-opus-4-6) with streaming + adaptive thinking
  prompts.py         SYSTEM_PROMPT constant
models/
  article.py         Pydantic schemas: Article (input), ArticleAnalysis (output)
```

**Data flow:** `main.py` calls `scrape_article(url)` → builds an `Article` → passes to `analyze_article(article)` → returns `ArticleAnalysis`.

**LLM output:** `analyzer.py` uses `output_config.format` (JSON schema) to constrain Claude's response to the `ArticleAnalysis` Pydantic schema. Adaptive thinking is enabled by default.

**Search providers:** Configured via `SEARCH_API_PROVIDER` env var (`brave` | `serper` | `tavily`). The provider routing lives in `tools/search.py`.

## Environment

Copy `.env.example` to `.env` and fill in keys before running:

```bash
cp .env.example .env
```
