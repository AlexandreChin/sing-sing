from pathlib import Path


def _load(name: str) -> str:
    return (Path(__file__).parent / f"{name}.md").read_text(encoding="utf-8")


def get_analyze_media_trend_prompt(
    language: str = "English",
    audience: str = "general audience",
    reference_country: str = "France",
) -> str:
    return (
        _load("analyze_media_trend")
        .replace("{language}", language)
        .replace("{audience}", audience)
        .replace("{Reference Country}", reference_country)
    )

