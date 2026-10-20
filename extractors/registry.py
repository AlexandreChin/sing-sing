"""Maps format names to their adapt agent, extractor, and renderer modules."""

FORMATS: dict[str, tuple[str, str, str]] = {
    "instagram_carousel_optimized": (
        "agent.instagram_carousel_adapt_agent",
        "extractors.instagram_carousel",
        "renderer.instagram_carousel.optimized",
    ),
    # the same deck condensed: same angle and moments, fewer words, larger type
    "instagram_carousel_light": (
        "agent.instagram_carousel_light_agent",
        "extractors.instagram_carousel",
        "renderer.instagram_carousel.light",
    ),
    "newsletter": (
        "agent.newsletter_adapt_agent",
        "extractors.newsletter",
        "renderer.newsletter.renderer",
    ),
}
