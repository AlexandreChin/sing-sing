"""Deck controller: check a rendered document against the article it came from.

Everything here is deterministic — no API call. Three families of check:

* **structure** — the adapt validator's own rules (word caps, one présupposé per
  beat, bold spans, plain French), re-run on the final document, because a deck
  can be hand-edited long after adapt produced it;
* **accuracy** — quotes must appear in the article, and every figure we print in
  our own prose must exist in the article. This is what catches a quote quietly
  reworded during an edit pass, or a number nobody can source;
* **typography** — French spacing before `; : ! ?`, which decides whether a
  colon can orphan at the start of a rendered line;
* **vocabulary (advisory)** — words a late slide uses that the deck never showed.
  Advisory because new nouns can be legitimate (an objection may name asbestos
  and opioids); a high count means the slide was written from the analysis
  rather than from the carousel, which is how « ces systèmes » and « la logique
  de planification » reach a reader who can attach them to nothing.

Usage: `python main.py check <extract.json> [article.txt]`. The article is found
next to the analysis when not given.
"""

import json
import re
from pathlib import Path

from agent.instagram_carousel_adapt_agent import _validate, norm_for_match
from models.instagram_carousel_presentation import InstagramCarouselDocument

# Punctuation that French sets off with a no-break space.
_TIGHT_PUNCT = re.compile(r" [;:!?»]|« ")
_DIGITS = re.compile(r"\d+(?:[.,]\d+)?")
_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "à", "au", "aux",
    "en", "que", "qui", "quoi", "ce", "cet", "cette", "ses", "son", "sa", "leur",
    "leurs", "il", "elle", "on", "pour", "par", "sur", "sans", "dans", "plus",
    "pas", "ne", "est", "sont", "a", "ont", "se", "s", "l", "d", "n", "y",
    # Very common verbs, adverbs and fillers: their arrival on a late slide says
    # nothing, where a new noun ("système", "liste", "paramètres") says a lot.
    "dit", "dire", "faut", "peut", "fait", "faire", "être", "avoir", "vers", "ceux",
    "celle", "celui", "chose", "quelque", "quelques", "déjà", "encore", "aussi",
    "assez", "très", "bien", "alors", "donc", "mais", "comme", "quand", "avant",
    "après", "entre", "chaque", "autre", "autres", "même", "hui", "aujourd",
}


# One definition, shared with the adapt loop that now runs the same quote check.
_norm = norm_for_match


def _numbers(text: str) -> set[str]:
    """Figures in a string, with digit-group spaces closed up (4 400 → 4400)."""
    closed = re.sub(r"(?<=\d)[    ](?=\d)", "", _norm(text))
    return {m.group(0).replace(",", ".") for m in _DIGITS.finditer(closed)}


def _words(text: str) -> set[str]:
    """Content-word stems (first 5 letters), so inflections match: « expérimenter »
    and « expérimentons » are the same word for a consistency check."""
    return {w[:5] for w in re.findall(r"[a-zà-öø-ÿ]+", _norm(text))
            if w not in _STOPWORDS and len(w) > 2}


def _our_prose(doc: InstagramCarouselDocument) -> list[tuple[str, str]]:
    """(label, text) for every field written in our own voice — quotes excluded,
    since those are the article's words and are checked separately."""
    d, pres = doc.presentation.display, doc.presentation
    fields = [
        ("hook.sub_topic", pres.hook.sub_topic),
        ("display.selection_headline", d.selection_headline),
        ("display.why_selected", d.why_selected),
        ("display.reperes_headline", d.reperes_headline),
        ("display.root_issue", d.root_issue),
        ("cta.engagement_sentence", pres.cta.engagement_sentence),
    ]
    fields += [(f"display.essentiel[{i}]", p) for i, p in enumerate(d.essentiel)]
    if d.global_analysis:
        fields.append(("global_analysis.headline", d.global_analysis.headline))
        fields += [(f"global_analysis.core_recap[{i}]", p)
                   for i, p in enumerate(d.global_analysis.core_recap)]
    if d.steel_man:
        fields += [("steel_man.argument", d.steel_man.argument),
                   ("steel_man.alternative", d.steel_man.alternative)]
    for i, b in enumerate(d.reading_beats):
        if b.selected:
            fields += [(f"beat[{i}].moment", b.moment),
                       (f"beat[{i}].lens_question", b.lens_question),
                       (f"beat[{i}].answer", b.answer)]
    return [(label, text) for label, text in fields if text]


def _slide_order(doc: InstagramCarouselDocument) -> list[tuple[str, str]]:
    """Displayed text in reading order, so a later slide can be checked against
    everything the reader has already seen."""
    d, pres = doc.presentation.display, doc.presentation
    paras = [p.strip() for p in d.why_selected.split("\n") if p.strip()]
    seq: list[tuple[str, str]] = [("01 hook", pres.hook.sub_topic)]
    seq += [("02 essentiel", paras[0] if paras else "")]
    seq += [("02 essentiel", p) for p in d.essentiel]
    context = ""
    if doc.analysis.context and doc.analysis.context.contexts:
        context = doc.analysis.context.contexts[0].text
    seq += [("03 reperes", d.reperes_headline), ("03 reperes", context)]
    for b in d.reading_beats:
        if b.selected:
            seq += [("beat", b.moment), ("beat", b.quote), ("beat", b.lens_question),
                    ("beat", b.answer), ("beat", b.figure_label or ""), ("beat", b.figure_caption or "")]
    if d.global_analysis:
        seq.append(("socle headline", d.global_analysis.headline))
        seq += [("socle présupposé", c.strip())
                for point in d.global_analysis.core_recap
                for c in (point.split(":", 1)[-1]).split(";") if c.strip()]
    seq.append(("socle question", pres.cta.engagement_sentence))
    seq.append(("recul enjeu", d.root_issue))
    if d.steel_man:
        seq += [("recul objection", d.steel_man.argument), ("recul objection", d.steel_man.alternative)]
    return [(label, text) for label, text in seq if text]


# The last slides are written from the analysis, so they arrive in its
# vocabulary — « la logique de planification », « ces systèmes », « son total » —
# naming things the deck never showed. Flag a field that introduces several
# content words the reader has not met.
_LATE_SLIDES = ("socle", "recul")
_NEW_WORD_LIMIT = 3


def _late_vocabulary(doc: InstagramCarouselDocument) -> list[str]:
    problems, seen = [], set()
    for label, text in _slide_order(doc):
        stems = _words(text)
        if label.startswith(_LATE_SLIDES):
            fresh = stems - seen
            if len(fresh) >= _NEW_WORD_LIMIT:
                problems.append(
                    f"{label} introduces {len(fresh)} words the deck has not used "
                    f"({', '.join(sorted(fresh))}…) — « {text[:60]}… »"
                )
        seen |= stems
    return problems


def check(extract_path: Path, article_path: Path | None = None) -> dict[str, list[str]]:
    """Run every check. Returns {family: [problems]} — empty lists mean clean."""
    extract_path = Path(extract_path)
    doc = InstagramCarouselDocument.model_validate(json.loads(extract_path.read_text(encoding="utf-8")))
    report: dict[str, list[str]] = {"structure": [], "accuracy": [], "consistency": [],
                                    "typography": [], "vocabulary (advisory)": []}

    # `_validate` describes what adapt must produce; the extract is a trimmed
    # version of it (the extractor keeps one go_further, three dimensions), so
    # validate the adapt document when it is there.
    adapt_path = extract_path.parent / "adapt.json"
    if adapt_path.exists():
        from models.instagram_carousel_presentation import InstagramCarouselPresentation
        adapted = InstagramCarouselPresentation.model_validate(
            json.loads(adapt_path.read_text(encoding="utf-8")))
        report["structure"] = list(_validate(adapted))
    else:
        report["structure"] = [e for e in _validate(doc.presentation) if "go_further" not in e]

    if article_path is None:
        base = extract_path.parent.parent
        candidate = base / f"{base.name}.txt"
        article_path = candidate if candidate.exists() else None

    if article_path is None:
        report["accuracy"].append(
            "article text not found — pass it as the second argument to check quotes and figures"
        )
    else:
        article = _norm(Path(article_path).read_text(encoding="utf-8"))
        article_numbers = _numbers(article)
        for i, b in enumerate(doc.presentation.display.reading_beats):
            if b.selected and b.quote.strip():
                if _norm(b.quote.strip().strip("«»").strip()) not in article:
                    report["accuracy"].append(
                        f"beat[{i}].quote is not in the article verbatim — « {b.quote[:60]}… »"
                    )
        # A figure absent from the article may still be legitimate: the analysis
        # adds external reference points on purpose (`context.important_facts`).
        # Those are worth flagging as external — the reader will assume they come
        # from the piece — but a figure found in neither is invented.
        analysis_numbers: set[str] = set()
        analysis_path = extract_path.parent.parent / "analysis.json"
        if analysis_path.exists():
            analysis_numbers = _numbers(analysis_path.read_text(encoding="utf-8"))
        for label, text in _our_prose(doc):
            unknown = _numbers(text) - article_numbers
            invented = unknown - analysis_numbers
            external = unknown & analysis_numbers
            if invented:
                report["accuracy"].append(
                    f"{label} prints {', '.join(sorted(invented))} — in neither the article nor "
                    f"the analysis"
                )
            if external:
                report["accuracy"].append(
                    f"{label} prints {', '.join(sorted(external))} — not in the article as "
                    f"digits (it may be spelled out, or come from the analysis's external "
                    f"context); check the reader can source it"
                )

    # The title may only name what the two paragraphs name (it is read two lines
    # above them); a term appearing in neither describes another article.
    d = doc.presentation.display
    stray = _words(d.selection_headline) - _words(d.why_selected)
    if stray:
        report["consistency"].append(
            f"display.selection_headline says {', '.join(sorted(stray))}… — absent from "
            f"why_selected, so the title names something the slide does not"
        )
    # Advisory, not an error: a late slide may legitimately bring new nouns (the
    # steel man names asbestos, lead, opioids). What the count signals is a field
    # written from the analysis rather than from the deck — a human decides.
    report["vocabulary (advisory)"] = _late_vocabulary(doc)

    # Slide 4 lists one numbered réflexe per selected beat, and each beat repeats
    # that question; the renderer derives both from the same list, so a mismatch
    # means the document was edited in a way the renderer cannot reconcile.
    selected = [b for b in d.reading_beats if b.selected]
    missing_q = [i for i, b in enumerate(selected) if not b.lens_question.strip()]
    if missing_q:
        report["consistency"].append(
            f"selected beat(s) {missing_q} have no lens_question — slide 4 would list a réflexe "
            f"the beat cannot echo"
        )

    # Typography is applied at render time (the `fr`/`md_bold` filters), so the
    # check belongs on the rendered slides, not on the source strings.
    html_dir = extract_path.parent / "html"
    if not html_dir.is_dir():
        report["typography"].append("no rendered html/ next to the document — run `render` first")
    else:
        for f in sorted(html_dir.glob("*.html")):
            body = f.read_text(encoding="utf-8").split("<body>")[-1]
            for m in re.finditer(r"\S+ [;:?!»]", re.sub(r"<[^>]+>", " ", body)):
                report["typography"].append(f"{f.name}: plain space before French punctuation — {m.group(0)}")
    return report


def format_report(report: dict[str, list[str]]) -> str:
    lines = []
    for family, problems in report.items():
        mark = "OK" if not problems else f"{len(problems)} problem(s)"
        lines.append(f"── {family}: {mark}")
        lines += [f"   • {p}" for p in problems]
    return "\n".join(lines)
