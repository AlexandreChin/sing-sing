"""Maps format names to their adapt agent, extractor, and renderer modules."""

FORMATS: dict[str, tuple[str, str, str]] = {
    "instagram_carousel_optimized": (
        "agent.instagram_carousel_adapt_agent",
        "extractors.instagram_carousel",
        "renderer.instagram_carousel.optimized",
    ),
    "newsletter": (
        "agent.newsletter_adapt_agent",
        "extractors.newsletter",
        "renderer.newsletter.renderer",
    ),
}
