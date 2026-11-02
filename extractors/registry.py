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
    "temps_long": (
        "agent.temps_long_adapt_agent",
        "extractors.temps_long",
        "renderer.instagram_carousel.temps_long",
    ),
    "anatomie_chiffre": (
        "agent.anatomie_chiffre_adapt_agent",
        "extractors.anatomie_chiffre",
        "renderer.instagram_carousel.anatomie_chiffre",
    ),
    "newsletter": (
        "agent.newsletter_adapt_agent",
        "extractors.newsletter",
        "renderer.newsletter.renderer",
    ),
}
