import json
from pathlib import Path

import anthropic

from models.carousel import ArticleMetadata, CarouselInput, CarouselOutput

client = anthropic.Anthropic()

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "analyze_carousel.md").read_text(
    encoding="utf-8"
)


async def analyze_for_carousel(input: CarouselInput) -> CarouselOutput:
    parts = []
    if input.title:
        parts.append(f"Titre : {input.title}")
    if input.source:
        parts.append(f"Source : {input.source}")
    if input.published_at:
        parts.append(f"Date : {input.published_at}")
    if input.url:
        parts.append(f"URL : {input.url}")
    parts.append(f"\nContenu de l'article :\n{input.body}")
    user_message = "\n".join(parts)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": CarouselOutput.model_json_schema(),
            }
        },
    ) as stream:
        response = stream.get_final_message()

    text = next(b.text for b in response.content if b.type == "text")
    result = CarouselOutput.model_validate(json.loads(text))
    result.article_metadata = ArticleMetadata(
        url=input.url,
        title=input.title,
        source=input.source,
        published_at=input.published_at,
    )
    return result
