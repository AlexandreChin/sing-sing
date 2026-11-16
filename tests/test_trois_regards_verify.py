"""The web check of the sources named in the clues (`indiceN`) of the tensions grid of a `trois_regards` deck (advisory)."""
import asyncio
import json
from types import SimpleNamespace

from agent import trois_regards_adapt_agent as agent
from agent import trois_regards_verify as tv
from tests._carousel_steps_fixtures import full
from tests.test_trois_regards_agent import ARTICLE, DECK, FIELDS, fake  # noqa: F401  (fake: the model stub fixture)

TENSIONS = FIELDS["tensions"]
SUBJECT = DECK["axe"]["subject"]


def _src(title="Eurostat", url="https://ec.europa.eu/x", why="series on housing"):
    return SimpleNamespace(title=title, url=url, stance_reason=why)


def _found(confirming=(), contradicting=()):
    return SimpleNamespace(confirming=list(confirming), contradicting=list(contradicting))


def _verify(search, pts=None):
    return asyncio.run(tv.verify_sources(pts or tv.points({"t": TENSIONS}), SUBJECT, search))


def test_each_tension_clue_source_becomes_a_claim_about_its_topic():
    pts = tv.points({"t": TENSIONS})
    assert [(s, f) for s, f, _, _ in pts] == [("t", "indice1"), ("t", "indice2"), ("t", "indice3")]
    assert [p[2] for p in pts] == [c["topic"] for c in DECK["tensions"]["cards"]]
    assert [p[3] for p in pts] == [c["source"] for c in DECK["tensions"]["cards"]]
    text = tv.claim_text(pts[0][2], pts[0][3], SUBJECT)
    assert pts[0][3] in text and SUBJECT in text and pts[0][2] in text
    assert tv.points({"t": {**TENSIONS, "indice2": "", "indice3": " | rien"}}) == pts[:1]


def test_unconfirmed_is_a_warning_with_the_news_caveat():
    async def search(text):
        return _found()
    results = _verify(search)
    assert {r["status"] for r in results} == {"unconfirmed"}
    warns = tv.warnings("tensions", results)
    assert len(warns) == len(results) and all("news" in w and "institutions" in w for w in warns)
    assert any(results[0]["source"] in w for w in warns)


def test_a_contradicted_source_is_a_warning_quoting_the_source():
    async def search(text):
        return _found(contradicting=[_src("Le Monde", "https://lemonde.fr/a", "dit le contraire")])
    warn = tv.warnings("tensions", _verify(search))[0]
    assert "https://lemonde.fr/a" in warn and "dit le contraire" in warn


def test_a_confirmed_source_gives_no_warning():
    async def search(text):
        return _found(confirming=[_src()])
    results = _verify(search)
    assert {r["status"] for r in results} == {"confirmed"} and tv.warnings("tensions", results) == []


def test_no_key_or_no_network_gives_an_unavailable_warning_and_never_raises():
    async def search(text):
        raise RuntimeError("no API key")
    results = _verify(search)
    assert {r["status"] for r in results} == {"unavailable"}
    assert all("could not be checked" in w for w in tv.warnings("tensions", results))


def test_a_warning_names_the_field_to_fix():
    async def search(text):
        return _found()
    assert tv.warnings("tensions", _verify(search))[1].startswith("tensions.indice2:")


def test_the_result_is_saved_beside_the_step(tmp_path):
    results = [{"slot": "t", "field": "indice1", "source": "OCDE", "claim": "c", "status": "confirmed",
                "source_ref": None, "reason": ""}]
    n = agent.STEP_BY_NAME["tensions"].n
    path = tv.save(tmp_path, n, "tensions", results)
    assert path == tmp_path / f"{n}_tensions.verification.json" and path.name == "4_tensions.verification.json"
    assert json.loads(path.read_text(encoding="utf-8")) == results


def test_verify_pick_checks_the_tensions_only(fake, tmp_path):  # noqa: F811
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps, article_text=ARTICLE)
    assert agent.VERIFIED_STEPS == ("tensions",)
    seen = []

    async def search(text):
        seen.append(text)
        return _found(contradicting=[_src("Autre", "https://x.org/y", "non")]) if "OCDE" in text else _found()
    warns = asyncio.run(agent.verify_pick(steps, "tensions", search))
    assert len(warns) == len(seen) == 3 and all(w.startswith("tensions.indice") for w in warns)
    assert any("https://x.org/y" in w for w in warns) and any("news" in w for w in warns)
    saved = json.loads((steps / "4_tensions.verification.json").read_text(encoding="utf-8"))
    assert [r["field"] for r in saved] == ["indice1", "indice2", "indice3"] and {r["slot"] for r in saved} == {"t"}
    events = [json.loads(line) for line in (tmp_path / "choices.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(e["step"] == "tensions" and e["event"] == "verify" for e in events)
    for step in ("prismes", "hook", "limites"):
        assert asyncio.run(agent.verify_pick(steps, step, search)) == [] if step != "limites" else True
