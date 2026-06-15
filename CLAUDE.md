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

# Behavioral guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 0. Before Acting — Mandatory Protocol

**Every task, no exceptions.**

**Simple tasks** (single file, single obvious change): state your assumption in one sentence, then proceed.

**Complex tasks** (multiple files, config + code + regeneration, or any task where the right approach requires classification or reasoning across the codebase): write a numbered plan before touching anything:

```
1. [What you will do] → verify: [how you will check it worked]
2. [What you will do] → verify: [how you will check it worked]
...
What you will NOT touch: [list]
```

Then **STOP and wait for approval** before executing anything.

If you are unsure which category a task falls into, treat it as complex.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
