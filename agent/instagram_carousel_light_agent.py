"""adapt() for the light carousel: the full deck, condensed.

The light format keeps everything the full deck chose — angle, moments, enjeu,
question — and shortens only the words on the slides, so an A/B test compares
format, not content. The model returns just the displayed copy (`LightCopy`);
it is merged into the full presentation, so the selection, the analysis fields
and the newsletter fields stay those of the full deck.
"""
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from agent._base import _call_with_retry
from agent.instagram_carousel_adapt_agent import _BOLD_RE, _validate, adapt as adapt_full, caption_with_sources
from models.full_analysis import ArticleFullAnalysis
from models.instagram_carousel_presentation import InstagramCarouselPresentation

FULL_FORMAT = "instagram_carousel_optimized"
LIGHT_FORMAT = "instagram_carousel_light"

_PROMPT = (Path(__file__).parent / "prompts" / "instagram_carousel_light.md").read_text(encoding="utf-8")


class LightFact(BaseModel):
    label: str
    text: str


class LightMoment(BaseModel):
    index: int            # position in the full deck's reading_beats
    moment: str
    quote: str
    quote_original: str = ""
    lens_question: str
    answer: str


class LightCopy(BaseModel):
    hook_sub_topic: str
    hook_subtitle: str
    essentiel: list[str]
    reperes_fact: LightFact
    moments: list[LightMoment]
    headline: str
    presupposes: list[str]
    objection: str
    root_issue: str
    question: str
    where_to_look: list[str]


def merge(full: dict, copy: dict) -> dict:
    """The full presentation with the light copy written into its displayed fields."""
    c = LightCopy.model_validate(copy)
    out = json.loads(json.dumps(full))
    d = out["display"]
    out["hook"]["sub_topic"], out["hook"]["subtitle"] = c.hook_sub_topic, c.hook_subtitle
    d["essentiel"] = c.essentiel
    d["reperes_facts"] = [c.reperes_fact.model_dump()]
    beats = d["reading_beats"]
    for m in c.moments:
        if 0 <= m.index < len(beats) and beats[m.index].get("selected", True):
            beats[m.index].update(m.model_dump(exclude={"index"}))
    if d.get("global_analysis"):
        d["global_analysis"]["headline"] = c.headline
        d["global_analysis"]["core_recap"] = ["Ses présupposés : " + " ; ".join(c.presupposes)]
    if d.get("steel_man"):
        d["steel_man"]["argument"] = c.objection
    d["root_issue"] = c.root_issue
    out["cta"]["engagement_sentence"] = c.question
    out["cta"]["where_to_look"] = c.where_to_look
    return out


def _same_axis_errors(base: dict, merged: dict) -> list[str]:
    """The light deck keeps the full deck's slide 8: condensed, its question and its
    enjeu still carry the gold word they share in the full version."""
    errors = []
    for label, full_text, light_text in (
        ("cta.engagement_sentence", base["cta"]["engagement_sentence"], merged["cta"]["engagement_sentence"]),
        ("display.root_issue", base["display"]["root_issue"], merged["display"]["root_issue"]),
    ):
        gold = {w.lower()[:5] for span in _BOLD_RE.findall(full_text) for w in span.split()}
        kept = {w.lower()[:5] for span in _BOLD_RE.findall(light_text) for w in span.split()}
        if gold and not gold & kept:
            errors.append(f"light: {label} drops the full deck's gold word — condense « {full_text} », "
                          f"do not replace it")
    return errors


def _full_presentation(full: ArticleFullAnalysis, analysis_path: Path | None, no_api: bool,
                       article_text: str | None) -> dict:
    """The full deck's adapt.json beside the analysis, or a fresh full adapt (saved
    there, so both formats come from the same choices)."""
    path = Path(analysis_path).parent / FULL_FORMAT / "adapt.json" if analysis_path else None
    if path and path.exists():
        print(f"Light: condensing {path}", file=sys.stderr, flush=True)
        return json.loads(path.read_text(encoding="utf-8"))
    pres = adapt_full(full, no_api=no_api, article_text=article_text,
                      steps_dir=path.parent / "adapt_steps" if path else None)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(pres.model_dump_json(indent=2), encoding="utf-8")
        print(f"Light: full presentation written to {path}", file=sys.stderr, flush=True)
    return pres.model_dump(mode="json")


def adapt(
    full: ArticleFullAnalysis,
    no_api: bool = False,
    article_text: str | None = None,
    analysis_path: Path | None = None,
) -> InstagramCarouselPresentation:
    base = _full_presentation(full, analysis_path, no_api, article_text)
    user_msg = f"CARROUSEL COMPLET :\n{json.dumps(base, ensure_ascii=False, indent=2)}\n\n---\n\n{_PROMPT}"
    print("Adaptation carousel (light)…", file=sys.stderr, flush=True)
    copy = _call_with_retry(
        user_msg,
        LightCopy.model_json_schema(),
        validator=lambda data: (_validate(merge(base, data), article_text, light=True)
                                + _same_axis_errors(base, merge(base, data))),
        no_api=no_api,
        label="light",
    )
    pres = InstagramCarouselPresentation.model_validate(merge(base, copy))
    return pres.model_copy(update={"caption": caption_with_sources(pres.caption, pres.go_further)})
