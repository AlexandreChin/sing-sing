"""Maps format names to their adapt agent, extractor, and renderer modules."""

FORMATS: dict[str, tuple[str, str, str]] = {
    "instagram_carousel_optimized": (
        "agent.instagram_carousel_adapt_agent",
        "extractors.instagram_carousel",
        "renderer.instagram_carousel.optimized",
    ),
    "cadrage_logique": (
        "agent.cadrage_adapt_agent",
        "extractors.cadrage",
        "renderer.instagram_carousel.cadrage",
    ),
    "newsletter": (
        "agent.newsletter_adapt_agent",
        "extractors.newsletter",
        "renderer.newsletter.renderer",
    ),
}
