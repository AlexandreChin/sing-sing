"""A fake `_call_with_retry` for the adapt steps, answering each step from the
article_15 sample deck: 2+ options per slot, `recommended` = the deck's values,
writing with the deck's copy. Shared by the runner and the CLI tests."""
import copy
import json
from pathlib import Path

from models.full_analysis import ArticleFullAnalysis

DECK = Path("samples/articles/article_15/article/instagram_carousel_optimized/adapt.json")
ANALYSIS = Path("samples/articles/article_15/article/analysis.json")

_CAND = ("moment", "quote", "quote_original", "lens_ref", "factcheck", "theme", "centrality", "kind", "role", "rationale")
_COPY = ("lens_question", "note", "answer", "figure", "figure_label", "figure_caption", "pictogram")


def load_deck() -> dict:
    return json.loads(DECK.read_text(encoding="utf-8"))


def full() -> ArticleFullAnalysis:
    return ArticleFullAnalysis.model_validate_json(ANALYSIS.read_text(encoding="utf-8"))


def _pool(deck: dict) -> list[dict]:
    """The 3 selected beats plus the first 3 unselected, in pool order: 6 candidates."""
    beats = deck["display"]["reading_beats"]
    unselected = [i for i, b in enumerate(beats) if not b["selected"]][:3]
    return [b for i, b in enumerate(beats) if b["selected"] or i in unselected]


def responses(deck: dict) -> dict[str, dict]:
    """Each step's model response, cut from the finished deck. Within a slot the
    deck's own value comes first; slots come in `Step.slots` order."""
    d, cta, ga, hook = deck["display"], deck["cta"], deck["display"]["global_analysis"], deck["hook"]

    def opt(slot, reason="r", **fields):
        return {**fields, "slot": slot, "reason": reason}

    def answer(options, keep):
        return {"options": options, "recommended": [i for i, o in enumerate(options) if keep(i, o)]}

    out = {}
    qs = [cta["engagement_sentence"], *cta["engagement_sentence_alt"][:3]]
    out["question"] = answer([opt("question", text=q) for q in qs], lambda i, o: i == 0)
    out["question"]["thesis_frame"] = d["thesis_frame"]
    enjeux = [d["root_issue"], "Ce qui fait d'une jeunesse en colère une **voix** publique.",
              "Ce qu'une **école** doit à ceux qu'elle oblige."]
    out["enjeu"] = answer([opt("enjeu", text=t) for t in enjeux], lambda i, o: i == 0)
    idees = []
    for i, t in enumerate(d["essentiel"]):
        idees += [opt(str(i + 1), text=t), opt(str(i + 1), text=t.replace(".", ", disent-ils."))]
    out["idees"] = answer(idees, lambda i, o: i % 2 == 0)
    pool = _pool(deck)
    moments = [opt(str(b["spine_ref"]), b["axis_link"] or "r", **{k: b[k] for k in _CAND}) for b in pool]
    order = sorted(range(len(pool)), key=lambda i: (pool[i]["spine_ref"], not pool[i]["selected"]))
    out["moments"] = {"options": [moments[i] for i in order],
                      "recommended": [k for k, i in enumerate(order) if pool[i]["selected"]]}
    extra = [{"label": "Le bac", "text": "L'examen qui ouvre l'accès au **supérieur**."},
             {"label": "Les blocages", "text": "Des lycées fermés par leurs élèves depuis **septembre**."}]
    facts = d["reperes_facts"] + extra
    out["contexte"] = answer([opt("fact", **f) for f in facts], lambda i, o: i < len(d["reperes_facts"]))
    sel = [b for b in d["reading_beats"] if b["selected"]]
    texts = ga["core_recap"][0].split(" : ", 1)[1].split(" ; ")
    sm = d["steel_man"]
    socle = [opt("headline", text=ga["headline"]), opt("headline", text=ga["headline_alt"][0])]
    for b, t in sorted(zip(sel, texts), key=lambda bt: bt[0]["spine_ref"]):
        slot = f"p{b['spine_ref']}"
        socle += [opt(slot, text=t), opt(slot, text=f"que {t.removeprefix('que ')}, sans le dire")]
    target = f"p{sel[sm['targets'] - 1]['spine_ref']}"
    socle += [opt("objection", argument=sm["argument"], alternative=sm["alternative"], targets_slot=target),
              opt("objection", argument="Une mobilisation ne parle pas pour **toute** une génération.",
                  alternative="Elle dit ce que veulent ceux qui la font, pas les autres.", targets_slot=target)]
    out["socle"] = answer(socle, lambda i, o: i in (0, 2, 4, 6, 8))
    hooks = [{k: hook[k] for k in ("topic", "sub_topic", "subtitle", "headline")}]
    hooks += [{**hooks[0], "sub_topic": alt} for alt in hook["sub_topic_alt"][:2]]
    out["hook"] = answer([opt("hook", **h) for h in hooks], lambda i, o: i == 0)
    index = {id(pool[i]): k for k, i in enumerate(order)}           # position among the options
    out["writing"] = {
        "beats": [{"index": index[id(b)], **{k: b[k] for k in _COPY}} for b in pool if b["selected"]],
        "why_selected": d["why_selected"], "selection_headline": d["selection_headline"],
        "key_takeaways": d["key_takeaways"], "go_further": deck["go_further"],
        "where_to_look": cta["where_to_look"], "caption": deck["caption"]}
    return out


class FakeCalls:
    """Stands in for `_call_with_retry`. Records each label and message, calls the
    validator once on its answer (its errors land in `errors[label]`), and lets a
    test change an answer: `recommended_override[label]`, `edit[label](data)`."""

    def __init__(self, deck: dict):
        self.answers = responses(deck)
        self.labels: list[str] = []
        self.messages: list[str] = []
        self.errors: dict[str, list[str]] = {}
        self.recommended_override: dict[str, list[int]] = {}
        self.edit: dict[str, callable] = {}

    def __call__(self, user_message, schema, validator, no_api=False, label="", system=None):
        self.labels.append(label)
        self.messages.append(user_message)
        data = copy.deepcopy(self.answers[label])
        if label in self.recommended_override:
            data["recommended"] = list(self.recommended_override[label])
        if label in self.edit:
            data = self.edit[label](data)
        self.errors[label] = validator(data)
        return data
