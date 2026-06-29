import asyncio
from dataclasses import dataclass

import anthropic

from config import MODEL
from .prompts import get_analyze_media_trend_prompt
from tools.search import search_news


@dataclass
class MediaTrendAnalysis:
    topic: str
    reference_country: str
    analysis: str


_client = anthropic.Anthropic()


async def analyze_media_trend(
    topic: str,
    reference_country: str = "France",
    language: str = "English",
    audience: str = "general audience",
    num_search_results: int = 8,
) -> MediaTrendAnalysis:
    """Analyze how a topic is covered across media in a given country.

    Searches for recent articles on the topic to enrich the analysis with
    real source snippets, then calls Claude with the media trend prompt.

    Args:
        topic: The topic or event to analyze (e.g. "retraite à 68 ans").
        reference_country: Country whose media landscape to focus on.
        language: Language for the analysis output.
        audience: Target format (e.g. "Substack Newsletter", "Executive Board Briefing").
        num_search_results: Number of news articles to fetch as context.
    """
    articles_context = ""
    try:
        results = await search_news(topic, num_results=num_search_results)
        if results:
            articles_context = "\n\nRecent articles collected on this topic:\n"
            for i, r in enumerate(results, 1):
                articles_context += (
                    f"\n---\nSource {i}: {r['title']}\n"
                    f"URL: {r['url']}\n"
                    f"Snippet: {r['snippet']}\n"
                )
    except Exception:
        pass

    user_message = (
        f"[Reference Country]: {reference_country}\n"
        f"[Topic / Event]: {topic}"
        + articles_context
    )

    response = await asyncio.to_thread(
        lambda: _client.messages.create(
            model=MODEL,
            max_tokens=6000,
            system=get_analyze_media_trend_prompt(language, audience, reference_country),
            messages=[{"role": "user", "content": user_message}],
        )
    )

    analysis_text = response.content[0].text
    return MediaTrendAnalysis(
        topic=topic,
        reference_country=reference_country,
        analysis=analysis_text,
    )
