"""Maps format names to their adapt agent, extractor, and renderer modules."""

FORMATS: dict[str, tuple[str, str, str]] = {
    "instagram_carousel_long": (
        "agent.instagram_carousel_agent",
        "extractors.instagram_carousel_long",
        "renderer.instagram_carousel_renderer",
    ),
    "instagram_carousel_short": (
        "agent.instagram_carousel_agent",
        "extractors.instagram_carousel_short",
        "renderer.instagram_carousel_short_renderer",
    ),
}
