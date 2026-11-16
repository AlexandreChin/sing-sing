"""The TROIS REGARDS carousel: model, extractor, registry, renderer. The deck in tests/fixtures/trois_regards_deck.json
(revision 4: a precise position, role-tagged prism cards without clue, the tensions grid) is written from
samples/articles/espagne-comment-la-crise-du-logement-a-t; trois_regards_deck_v3.json (revision 3: « Les angles morts »,
claims, clues on the prism cards, the media's note) and trois_regards_deck_v1.json (prism lines and sources, the matrix)
are the older deck shapes, kept to prove an older deck still loads and renders. The agent's steps, rules and prompts are
tested in tests/test_trois_regards_agent.py."""
import copy
import importlib
import json
import re
from pathlib import Path

from extractors.registry import FORMATS
from extractors.trois_regards import extract
from models.trois_regards_presentation import TroisRegardsPresentation
from tests._carousel_steps_fixtures import full

DECK = json.loads(Path("tests/fixtures/trois_regards_deck.json").read_text(encoding="utf-8"))
DECK_V3 = json.loads(Path("tests/fixtures/trois_regards_deck_v3.json").read_text(encoding="utf-8"))
DECK_V1 = json.loads(Path("tests/fixtures/trois_regards_deck_v1.json").read_text(encoding="utf-8"))


def test_the_deck_validates():
    pres = TroisRegardsPresentation.model_validate(DECK)
    assert [p.prism for p in pres.prisms] == pres.axe.prisms == ["economique", "politique", "sociologique"]
    assert len(pres.position.cards) == 4


def test_a_deck_without_an_axe_still_validates():
    assert TroisRegardsPresentation.model_validate({k: v for k, v in DECK.items() if k != "axe"}).axe is None


def test_the_extractor_passes_the_presentation_through():
    pres = TroisRegardsPresentation.model_validate(DECK)
    assert extract(full(), pres).presentation == pres


def test_the_format_is_registered():
    names = FORMATS["trois_regards"]
    assert names[1] == "extractors.trois_regards"
    assert importlib.import_module(names[1]).extract is extract

def test_the_v1_fixture_respects_the_older_caps_and_the_spec():
    p = TroisRegardsPresentation.model_validate(DECK_V1)
    n = lambda s: len(s.replace("**", ""))
    assert n(p.axe.question) <= 60 and n(p.axe.subject) <= 36
    assert n(p.axe.closing) <= 110 and p.axe.closing.endswith("?") and n(p.axe.media_grounding) <= 120
    assert n(p.position.kicker) <= 26 and n(p.position.title) <= 32 and n(p.position.lead) <= 90
    assert all(n(c.text) <= 76 and n(c.label) <= 30 for c in p.position.cards)
    for s in p.prisms:
        assert n(s.question) <= 50 and n(s.media_note) <= 90 and len(s.sources) <= 3
        assert all(n(x) <= 80 and all(re.fullmatch(r"(1[5-9]|20)\d\d", d) for d in re.findall(r"\d+", x)) for x in s.lines)
        assert all(n(x) <= 30 and not re.search(r"\d", x) for x in s.sources)
    assert n(p.matrix.title) <= 34
    assert all(n(c.variable) <= 60 and n(c.indicator) <= 40 for c in p.matrix.columns)
    assert not re.search(r"\d", json.dumps(DECK_V1["matrix"], ensure_ascii=False))
    assert n(p.hook.title) <= 70 and n(p.hook.promise) <= 100
    assert "http" not in json.dumps(DECK_V1, ensure_ascii=False) and p.caption.count("#") == 4
    assert p.matrix.title.endswith("?") and p.hook.title.endswith("?")
    assert p.hook.promise == "Trois regards sur la crise du logement ; à vous d'en juger."
    words = {"politique": "politique", "economique": "économi", "sociologique": "sociolog"}
    assert all(words[k] in p.axe.closing.lower() for k in p.axe.prisms)
    assert [s.prism for s in p.prisms if s.media_note] == [p.axe.media]
    outside = re.sub(r"«[^»]*»", "", json.dumps(DECK_V1, ensure_ascii=False).lower())
    for w in ("biais", "manipulation", "mensonge", "trompeur", "oublie", "ignore", "omet", "néglige", "ne dit pas"):
        assert w not in outside, w


# ---- the seven-prism registry -----------------------------------------------------------------------------------

def test_the_catalogue_has_the_seven_prisms_in_the_spec_order():
    from agent.trois_regards_prisms import PRISM_IDS, PRISMS
    assert PRISM_IDS == ("economique", "sociologique", "juridique", "historique", "politique", "ecologique", "technologique")
    assert list(PRISMS) == list(PRISM_IDS)


def test_every_prism_has_a_name_a_definition_and_a_distinct_icon():
    from agent.trois_regards_prisms import PRISMS
    assert all(p.name and p.definition and p.icon_svg for p in PRISMS.values())
    assert len({p.icon_svg for p in PRISMS.values()}) == 7
    assert all("<" in p.icon_svg and "stroke" not in p.icon_svg and "#" not in p.icon_svg for p in PRISMS.values())
    assert PRISMS["economique"].name == "Économique" and PRISMS["ecologique"].name == "Écologique"


def test_the_prism_icons_are_not_in_the_canonical_lenses():
    from agent.lenses import CANONICAL_LENSES
    from agent.trois_regards_prisms import PRISM_IDS
    assert set(CANONICAL_LENSES) == {"sources", "chiffres", "causalite", "cadrage", "opinion_fait", "equilibre",
                                     "sophismes", "angles_morts"}
    assert not set(PRISM_IDS) & set(CANONICAL_LENSES)


def test_the_catalogue_text_names_every_prism():
    from agent.trois_regards_prisms import PRISM_IDS, PRISMS, catalogue_text
    lines = catalogue_text().splitlines()
    assert len(lines) == 7
    for line, pid in zip(lines, PRISM_IDS):
        assert pid in line and PRISMS[pid].name in line and PRISMS[pid].definition in line



# ---- the renderer: older decks still load and render --------------------------------------------------------------

import html  # noqa: E402
import random  # noqa: E402

import pytest  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from agent import trois_regards_adapt_agent as agent  # noqa: E402
from agent.trois_regards_prisms import PRISM_IDS, PRISMS  # noqa: E402
from renderer.instagram_carousel import trois_regards as renderer  # noqa: E402

_SLIDES = ["01_hook", "02_position", "03_prisme", "04_prisme", "05_prisme", "06_matrice", "07_cta"]
_SLIDES_V3 = ["01_hook", "02_position", "03_prisme", "04_prisme", "05_prisme", "06_tensions", "07_limites", "08_cta"]


def _texts(paths) -> dict[str, str]:
    clean = lambda s: html.unescape(s).replace("\u00a0", " ").replace("\u202f", " ").replace("\u2060", "")   # noqa: E731
    # the body only: the shared stylesheets name `data-perch` too
    return {p.stem: clean(p.read_text(encoding="utf-8")).split("<body>", 1)[1] for p in paths}


def _render(tmp_path, deck: dict = DECK) -> dict[str, str]:
    doc = extract(full(), TroisRegardsPresentation.model_validate(deck))
    return _texts(renderer.generate_html(doc, tmp_path / "html"))


def test_a_first_version_deck_loads_and_renders_seven_slides(tmp_path):
    pres = TroisRegardsPresentation.model_validate(DECK_V1)
    assert pres.tensions is None and pres.limites is None and pres.matrix is not None
    assert all(not s.cards and not s.title for s in pres.prisms)
    texts = _render(tmp_path, DECK_V1)
    assert list(texts) == _SLIDES
    assert "Le logement, enjeu d'élection" in texts["02_position"] and "Ce que dit l'article" in texts["02_position"]
    for stem, prism in zip(("03_prisme", "04_prisme", "05_prisme"), DECK_V1["prisms"]):
        assert PRISMS[prism["prism"]].name in texts[stem] and prism["question"] in texts[stem]
        assert all(line in texts[stem] for line in prism["lines"]), stem
        assert " · ".join(prism["sources"]) in texts[stem]
        assert 'class="card ln"' in texts[stem]
    assert "Que mesurer pour trancher ?" in texts["06_matrice"] and DECK_V1["axe"]["question"] in texts["06_matrice"]


def test_a_revision_3_deck_loads_and_renders_eight_slides_with_its_angles_morts(tmp_path):
    pres = TroisRegardsPresentation.model_validate(DECK_V3)
    assert pres.limites is not None and len(pres.limites.cards) == 3 and pres.matrix is None
    assert [p.prism for p in pres.prisms if p.media_note] == [pres.axe.media]
    assert all(c.claim and c.source and c.find for c in pres.limites.cards)
    assert [c.pair for c in pres.tensions.cards] == [[1, 2], [1, 3], [2, 3]] and not pres.tensions.cards[0].views
    texts = _render(tmp_path, DECK_V3)
    assert list(texts) == _SLIDES_V3
    assert DECK_V3["limites"]["title"] in texts["07_limites"]
    assert DECK_V3["tensions"]["cards"][0]["head"].split(";")[0] in texts["06_tensions"]
    assert renderer.MEDIA_BADGE in "".join(texts[s] for s in ("03_prisme", "04_prisme", "05_prisme"))


def test_a_revision_3_prism_card_draws_its_answer_and_its_clue(tmp_path):
    texts = _render(tmp_path, DECK_V3)
    c = DECK_V3["prisms"][1]["cards"][0]
    assert c["answer"] in texts["04_prisme"] and f"<strong>{c['source']}</strong> : {c['find']}" in texts["04_prisme"]

# ── the layout: every field at its cap still fits its lines and the slide ───

_POOL = ("le la les de des du un une et à au en par sur pour dans avec plus que qui "
         "logement logements gouvernement Parlement locataires propriétaires intergénérationnelle "
         "constitutionnelle décentralisation institutionnelles municipalités investissements "
         "démographiques recensement observatoire statistiques européennes ménages métropoles "
         "spéculation rénovation copropriétés expulsions coalitions majoritaire").split()
_SHORT = [w for w in _POOL if len(w) <= 6]       # ordinary words of a narrow grid cell (an average French word has about 5 letters)


def _chars(rng: random.Random, n: int, pool=None) -> str:
    """Random French-looking text of EXACTLY `n` characters, long words included: words while they fit,
    then a long word cut to the room left (or the last word stretched by a letter), so no field undershoots its cap.
    `pool` narrows the words."""
    pool = pool or _POOL
    out = ""
    while True:
        w = rng.choice(pool)
        if len((out + " " + w).strip()) > n:
            break
        out = (out + " " + w).strip()
    room = n - len(out) - (1 if out else 0)
    if room >= 1:
        out = (out + " " + rng.choice([w for w in pool if len(w) >= max(room, 10)] or ["x" * 12])[:room]).strip()
    elif len(out) < n:
        out += "s"
    assert len(out) == n, (out, n)
    return out


def _ask(rng: random.Random, n: int) -> str:
    return _chars(rng, n - 2) + " ?"


# the older deck shape (prism question, lines and sources, the matrix) is no longer written by the agent: its caps,
# kept here as they were, and a builder of its deck keep the older-deck layout test alive

def _worst_frame(seed: int) -> dict:
    """The axe, the hook and the caption at their caps: the part of the worst-case deck the revision-4 steps do not change."""
    rng = random.Random(seed)
    cap = lambda name: agent._CAPS[name][1]   # noqa: E731
    prisms = rng.sample(PRISM_IDS, 3)
    axe = {"question": _ask(rng, cap(("axe", "question"))), "article_question": _ask(rng, 80),
           "subject": _chars(rng, cap(("axe", "subject"))), "prisms": prisms, "media": rng.choice(prisms),
           "media_grounding": _chars(rng, cap(("axe", "media_grounding"))), "closing": _ask(rng, cap(("axe", "closing")))}
    fixed = "Trois regards sur  ; à vous d'en juger."
    hook = {"title": _ask(rng, cap(("hook", "title"))),
            "promise": f"Trois regards sur {_chars(rng, cap(('hook', 'promise')) - len(fixed))} ; à vous d'en juger."}
    return {"axe": axe, "hook": hook, "caption": DECK["caption"]}



# ── revision 4: the seven-slide deck the author validated on rendered images ──
# position (precise facts) · three « Le prisme … » slides (four role cards, a lead, no clue) · « Les tensions » as a grid · CTA

DECK_V4 = DECK
_SLIDES_V4 = ["01_hook", "02_position", "03_prisme", "04_prisme", "05_prisme", "06_tensions", "07_cta"]
_ROLES_V4 = ["Origine", "Mécanisme", "Amplificateur", "Ce qu'on en voit"]
_PRISM_SLIDES = ("03_prisme", "04_prisme", "05_prisme")
_LABEL, _TEXT = (c for _, c in agent._PART_CAPS[("position", "card1")])
_FIND = agent._PART_CAPS[("tensions", "indice1")][1][1]


def test_a_v4_deck_validates():
    pres = TroisRegardsPresentation.model_validate(DECK_V4)
    assert [p.prism for p in pres.prisms] == pres.axe.prisms
    assert all(p.title and p.lead and len(p.cards) == 4 for p in pres.prisms)
    # the prism cards answer and carry no clue and no media note: the sources were removed to relieve the density
    assert all(c.head and c.answer and not c.source and not c.find and not c.claim for p in pres.prisms for c in p.cards)
    assert not any(p.media_note for p in pres.prisms)
    t = pres.tensions
    assert t.title and t.lead and len(t.cards) == 3
    assert all(c.topic and len(c.views) == 3 and all(c.views) and c.source and c.find for c in t.cards)
    assert pres.limites is None and pres.matrix is None and len(pres.position.cards) == 4


def test_a_v4_deck_renders_seven_slides(tmp_path):
    texts = _render(tmp_path, DECK_V4)
    assert list(texts) == _SLIDES_V4
    assert "2 / 7" in texts["02_position"] and "7 / 7" in texts["07_cta"]


def test_the_v4_position_draws_its_labelled_cards(tmp_path):
    t = _render(tmp_path, DECK_V4)["02_position"]
    pos = DECK_V4["position"]
    assert pos["kicker"] in t and pos["lead"] in t
    for c in pos["cards"]:
        assert c["label"] in t and c["text"] in t, c
    assert [t.index(c["label"]) for c in pos["cards"]] == sorted(t.index(c["label"]) for c in pos["cards"])


def test_each_v4_prism_slide_reads_le_prisme_its_title_its_lead_and_the_four_role_tags_in_order(tmp_path):
    texts = _render(tmp_path, DECK_V4)
    for stem, p in zip(_PRISM_SLIDES, DECK_V4["prisms"]):
        t = texts[stem]
        assert f"Le prisme {PRISMS[p['prism']].name.lower()}" in t, stem
        assert p["lead"] in t and p["title"].replace("**", "") in t.replace("<strong>", "").replace("</strong>", ""), stem
        assert PRISMS[p["prism"]].icon_svg in t, stem
        assert all(c["head"] in t and c["answer"] in t for c in p["cards"]), stem
        at = [t.index(r) for r in _ROLES_V4]
        assert at == sorted(at), (stem, "the role tags come in this order")
        assert renderer.MEDIA_BADGE not in t, stem           # no « Le regard du média » pill any more
        assert 'class="foot' not in t, stem                   # no clue line on a prism card


def test_a_v4_role_tag_sits_on_the_head_line(tmp_path):
    t = _render(tmp_path, DECK_V4)["03_prisme"]
    for role, c in zip(_ROLES_V4, DECK_V4["prisms"][0]["cards"]):
        assert re.search(rf'<div class="nm"><span class="rl">{re.escape(role)}</span><span class="sep">·</span>', t), role


def test_the_v4_tensions_grid_names_the_regards_once_in_a_header_and_draws_the_views_without_names(tmp_path):
    t = _render(tmp_path, DECK_V4)["06_tensions"]
    names = [PRISMS[x].name for x in DECK_V4["axe"]["prisms"]]
    assert [t.count(f"</svg>{n}</div>") for n in names] == [1, 1, 1], "each regard is named once, in the header row"
    assert [t.index(f"</svg>{n}</div>") for n in names] == sorted(t.index(f"</svg>{n}</div>") for n in names)
    for c in DECK_V4["tensions"]["cards"]:
        assert c["topic"] in t
        assert [t.index(v) for v in c["views"]] == sorted(t.index(v) for v in c["views"]), c["topic"]
        assert f"<strong>{c['source']}</strong> : {c['find']}" in t, c["topic"]
        assert not any(n.lower() in v.lower() for n in names for v in c["views"]), c["topic"]
    assert t.count("tclue") == 3 + 1 or t.count('class="tclue"') == 3          # one clue line per row
    assert 'class="card pc"' not in t, "a grid, not three cards"


def test_the_v4_title_block_is_slide_2s_on_slides_3_to_6_and_the_deck_question_is_not_repeated(tmp_path):
    texts = _render(tmp_path, DECK_V4)
    for stem in (*_PRISM_SLIDES, "06_tensions"):
        assert 'class="top ctr"' in texts[stem], stem              # the title and the lead centred, as slide 2's
    q = DECK_V4["axe"]["question"]
    for stem in ("02_position", *_PRISM_SLIDES, "06_tensions"):
        assert q not in texts[stem], stem
    for p in DECK_V4["prisms"]:
        assert p["lead"].endswith(".") and not p["lead"].endswith("?")
    assert DECK_V4["tensions"]["lead"] in texts["06_tensions"]


# the seeded worst case of the revision-4 fields: every capped field at its cap exactly

def worst_case_deck_v4(seed: int = 0) -> dict:
    """Every revision-4 field at its cap exactly. The caps are the validated deck's own longest texts, so the words are
    ordinary French (at most six letters, an average word has five): a pathological unbreakable word is not what a model
    writes in a 70 px title or a 25 px fact. The axe, the hook and the caption are `_worst_frame`'s."""
    rng = random.Random(4000 + seed)
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    plain = lambda step, name: _chars(rng, cap(step, name), _SHORT)   # noqa: E731
    deck = _worst_frame(seed)
    deck["position"] = {"kicker": plain("position", "kicker"), "title": plain("position", "title"),
                        "lead": plain("position", "lead"),
                        "cards": [{"label": _chars(rng, _LABEL, _SHORT), "text": _chars(rng, _TEXT, _SHORT)}
                                  for i in (1, 2, 3, 4)]}
    deck["prisms"] = [{"prism": p, "title": plain("prismes", "title"), "lead": plain("prismes", "lead"),
                       "cards": [{"head": plain("prismes", f"head{k}"), "answer": plain("prismes", f"answer{k}")}
                                 for k in (1, 2, 3, 4)]} for p in deck["axe"]["prisms"]]
    deck["tensions"] = {"title": plain("tensions", "title"), "lead": plain("tensions", "lead"),
                        "cards": [{"topic": plain("tensions", f"topic{k}"),
                                   "views": [plain("tensions", f"view{k}_{j}") for j in (1, 2, 3)],
                                   "source": _chars(rng, 30, _SHORT), "find": _chars(rng, _FIND, _SHORT)}
                                  for k in (1, 2, 3)]}
    return deck


def test_the_v4_worst_case_sits_exactly_at_its_caps():
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    for seed in range(12):
        d = worst_case_deck_v4(seed)
        TroisRegardsPresentation.model_validate(d)
        assert [len(c["text"]) for c in d["position"]["cards"]] == [_TEXT for i in (1, 2, 3, 4)]
        assert [len(c["label"]) for c in d["position"]["cards"]] == [_LABEL for i in (1, 2, 3, 4)]
        for p in d["prisms"]:
            assert len(p["title"]) == cap("prismes", "title") and len(p["lead"]) == cap("prismes", "lead"), seed
            for k, c in enumerate(p["cards"], 1):
                assert len(c["head"]) == cap("prismes", f"head{k}") and len(c["answer"]) == cap("prismes", f"answer{k}")
        t = d["tensions"]
        assert len(t["title"]) == cap("tensions", "title") and len(t["lead"]) == cap("tensions", "lead"), seed
        for k, c in enumerate(t["cards"], 1):
            assert len(c["topic"]) == cap("tensions", f"topic{k}")
            assert [len(v) for v in c["views"]] == [cap("tensions", f"view{k}_{j}") for j in (1, 2, 3)], seed


_LINES_V4 = """() => { const box = (s) => ['paddingTop', 'paddingBottom', 'borderTopWidth', 'borderBottomWidth']
    .reduce((a, k) => a + parseFloat(s[k]), 0);
  const n = (sel) => [...document.querySelectorAll(sel)].map(e => { const s = getComputedStyle(e);
    return Math.round((e.getBoundingClientRect().height - box(s)) / parseFloat(s.lineHeight)); });
  const bottom = Math.max(0, ...[...document.querySelectorAll('.stage *')].map(e => e.getBoundingClientRect().bottom));
  const cut = [...document.querySelectorAll('.card, .card *, .ld, .ld *, .tgrid > div, .row, .row *')]
    .filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.className);
  const first = document.querySelector('.card.pc') || document.querySelector('.tbl');
  const h = document.querySelector('.head') || document.querySelector('.mh'), hs = h ? getComputedStyle(h) : null;
  return {head: n('.head, .mh'), lead: n('.ld > span, .ml'), nm: n('.card .nm'), see: n('.card .see'), say: n('.row .say'),
          label: n('.row .h span'), view: n('.tview'), topic: n('.ttopic'), clue: n('.tclue .foot > span'),
          cards: document.querySelectorAll('.card.pc').length, first: first ? first.getBoundingClientRect().top : null,
          titleBottom: h ? h.getBoundingClientRect().bottom : null, size: hs ? parseFloat(hs.fontSize) : null,
          align: hs ? hs.textAlign : null, perches: document.querySelectorAll('[data-perch]').length,
          onFirst: !!(first && first.hasAttribute('data-perch')), onRow: !!document.querySelector('.row[data-perch]'),
          text: (document.querySelector('.stage') || document.body).innerText, bottom, cut,
          page: document.documentElement.scrollWidth}; }"""


def _measure_v4(tmp_path, deck: dict) -> dict[str, dict]:
    from renderer.shoot import _FIT, FIT_CAP, FIT_MARGIN
    doc = extract(full(), TroisRegardsPresentation.model_validate(deck))
    renderer.generate_html(doc, tmp_path)
    measured = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for f in sorted(tmp_path.glob("*.html")):
            page.set_content(f.read_text(encoding="utf-8"), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.evaluate(_FIT, [FIT_MARGIN, FIT_CAP])
            measured[f.stem] = page.evaluate(_LINES_V4)
        browser.close()
    return measured


@pytest.fixture(scope="module")
def v4_fixture_measured(tmp_path_factory):
    return _measure_v4(tmp_path_factory.mktemp("v4_fixture"), DECK_V4)


def test_the_v4_fixture_deck_fits_and_slides_2_to_6_share_the_title_block(v4_fixture_measured):
    m = v4_fixture_measured
    assert list(m) == _SLIDES_V4
    for stem, s in m.items():
        assert s["page"] <= 1080 and s["bottom"] <= 1255 and s["cut"] == [], (stem, s["bottom"], s["cut"])
    for stem in ("02_position", *_PRISM_SLIDES, "06_tensions"):
        assert m[stem]["size"] == 70 and m[stem]["align"] == "center", (stem, m[stem]["size"], m[stem]["align"])
        assert all(x <= 2 for x in m[stem]["head"]) and all(x <= 2 for x in m[stem]["lead"]), stem
        assert m[stem]["lead"], (stem, "a lead is drawn")


def test_the_bird_perches_on_the_first_card_row_or_grid_edge_of_slides_2_to_6(v4_fixture_measured):
    m = v4_fixture_measured
    assert m["02_position"]["onRow"] and m["02_position"]["perches"] == 1
    for stem in (*_PRISM_SLIDES, "06_tensions"):
        assert m[stem]["onFirst"] and m[stem]["perches"] == 1, stem
        assert m[stem]["titleBottom"] < m[stem]["first"], (stem, "the title sits above the wire")


def test_the_first_prism_card_starts_at_the_same_height_on_the_three_prism_slides(v4_fixture_measured):
    tops = [v4_fixture_measured[s]["first"] for s in _PRISM_SLIDES]
    assert max(tops) - min(tops) <= 2, tops


@pytest.mark.parametrize("seed", range(12))
def test_every_v4_field_at_its_cap_fits_on_the_slide(tmp_path, seed):
    deck = worst_case_deck_v4(seed)
    m = _measure_v4(tmp_path, deck)
    assert list(m) == _SLIDES_V4
    for stem, s in m.items():
        assert s["page"] <= 1080, (stem, "horizontal overflow", s["page"])
        assert s["bottom"] <= 1255, (stem, "passes the page number", s["bottom"])
        assert s["cut"] == [], (stem, "a card, a lead or a cell overflows sideways", s["cut"])
    p = m["02_position"]
    assert all(x <= 2 for x in p["head"]) and all(x <= 2 for x in p["lead"]), p
    assert all(x <= 3 for x in p["say"]) and all(x <= 2 for x in p["label"]), (p["say"], p["label"])
    for stem in _PRISM_SLIDES:
        s = m[stem]
        assert s["cards"] == 4 and all(x <= 2 for x in s["head"]) and all(x <= 2 for x in s["lead"]), (stem, s["head"], s["lead"])
        assert all(x == 1 for x in s["nm"]), (stem, "the role tag and the head share one line", s["nm"])
        assert all(x <= 2 for x in s["see"]), (stem, "an answer takes more than two lines", s["see"])
    t = m["06_tensions"]
    assert all(x <= 2 for x in t["head"]) and all(x <= 2 for x in t["lead"]), t
    assert len(t["view"]) == 9 and all(x <= 4 for x in t["view"]), (t["view"])
    assert len(t["topic"]) == 3 and all(x <= 4 for x in t["topic"]), t["topic"]
    tops = [m[s]["first"] for s in _PRISM_SLIDES]
    assert max(tops) - min(tops) <= 2, ("the prism slides' first cards", tops)


def test_the_v4_fixture_respects_the_v4_caps():
    """The validated deck is inside the caps the worst-case test renders at."""
    cap = lambda step, name: agent._CAPS[(step, name)][1]   # noqa: E731
    n = lambda s: len(s.replace("**", ""))   # noqa: E731
    pos = DECK_V4["position"]
    assert n(pos["kicker"]) <= cap("position", "kicker") and n(pos["title"]) <= cap("position", "title")
    assert n(pos["lead"]) <= cap("position", "lead")
    for i, c in enumerate(pos["cards"], 1):
        assert n(c["label"]) <= _LABEL and n(c["text"]) <= _TEXT, c
    for s in DECK_V4["prisms"]:
        assert n(s["title"]) <= cap("prismes", "title") and n(s["lead"]) <= cap("prismes", "lead"), s["prism"]
        for i, c in enumerate(s["cards"], 1):
            assert n(c["head"]) <= cap("prismes", f"head{i}") and n(c["answer"]) <= cap("prismes", f"answer{i}"), c
    t = DECK_V4["tensions"]
    assert n(t["title"]) <= cap("tensions", "title") and n(t["lead"]) <= cap("tensions", "lead")
    for i, c in enumerate(t["cards"], 1):
        assert n(c["topic"]) <= cap("tensions", f"topic{i}") and n(c["find"]) <= _FIND, c
        assert all(n(v) <= cap("tensions", f"view{i}_{j}") for j, v in enumerate(c["views"], 1)) and n(c["source"]) <= 30, c

