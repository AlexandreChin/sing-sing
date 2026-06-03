import anthropic
from .prompts import get_analyze_article_prompt
from models.article import Article, ArticleAnalysis


client = anthropic.Anthropic()


async def analyze_article(
    article: Article,
    language: str = "English",
    tone: str = "neutral",
    audience: str = "general audience",
) -> ArticleAnalysis:
    """Analyze a news article and return a structured ArticleAnalysis.

    Args:
        article: The article to analyze.
        language: Language for the analysis output (e.g. "French", "English").
        tone: Desired tone (e.g. "neutral", "academic", "accessible").
        audience: Target audience/format (e.g. "Instagram post carousel", "academic report").
    """
    user_message = f"Title: {article.title}\n\nURL: {article.url}\n\nBody:\n{article.body}"

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=get_analyze_article_prompt(language, tone, audience),
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": ArticleAnalysis.model_json_schema(),
            }
        },
    ) as stream:
        response = stream.get_final_message()

    text = next(b.text for b in response.content if b.type == "text")

    import json
    return ArticleAnalysis.model_validate(json.loads(text))
