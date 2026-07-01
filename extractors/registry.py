"""Maps format names to their adapt agent, extractor, and renderer modules."""

FORMATS: dict[str, tuple[str, str, str]] = {
    "instagram_carousel_long": (
        "agent.instagram_carousel_adapt_agent",
        "extractors.instagram_carousel_long",
        "renderer.instagram_carousel_long.renderer",
    ),
    "instagram_carousel_short": (
        "agent.instagram_carousel_adapt_agent",
        "extractors.instagram_carousel_short",
        "renderer.instagram_carousel_short.renderer",
    ),
    "instagram_carousel_optimized": (
        "agent.instagram_carousel_adapt_agent",
        "extractors.instagram_carousel_short",
        "renderer.instagram_carousel_short.optimized",
    ),
    "instagram_carousel_optimized_short": (
        "agent.instagram_carousel_adapt_agent",
        "extractors.instagram_carousel_short",
        "renderer.instagram_carousel_short.optimized_short",
    ),
}
