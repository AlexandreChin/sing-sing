"""Maps output format names to their extractor and renderer modules."""

FORMATS: dict[str, tuple[str, str]] = {
    "instagram_carousel": (
        "extractors.instagram_carousel",
        "renderer.instagram_carousel_renderer",
    ),
}
