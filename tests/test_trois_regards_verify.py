"""The web check of the sources named on the prism slides of a `trois_regards` deck (advisory)."""
import asyncio
import json
from types import SimpleNamespace

from agent import trois_regards_adapt_agent as agent
from agent import trois_regards_verify as tv
from tests.test_trois_regards import DECK, FIELDS, fake  # noqa: F401  (fake: the model stub fixture)
from tests._carousel_steps_fixtures import full

PRISMES = FIELDS["prismes"]
PRISM_IDS = DECK["axe"]["prisms"]
SUBJECT = DECK["axe"]["subject"]


def _src(title="Eurostat", url="https://ec.europa.eu/x", why="series on housing"):
    return SimpleNamespace(title=title, url=url, stance_reason=why)


def _found(confirming=(), contradicting=()):
    return SimpleNamespace(confirming=list(confirming), contradicting=list(contradicting))


def _verify(search, pts=None):
    pts = pts or tv.points(PRISMES, PRISM_IDS)
    return asyncio.run(tv.verify_sources(pts, SUBJECT, search))


def test_each_source_becomes_a_claim():
    pts = tv.points(PRISMES, PRISM_IDS)
    expected = sum(len([s for s in f["sources"].split(";") if s.strip()]) for f in PRISMES.values())
    assert len(pts) == expected and expected >= 3
    assert {slot for slot, _, _ in pts} == {"p1", "p2", "p3"}
    slot, prism_name, source = pts[0]
    assert source == PRISMES["p1"]["sources"].split(";")[0].strip()
    from agent.trois_regards_prisms import PRISMS
    assert prism_name == PRISMS[PRISM_IDS[0]].name
    text = tv.claim_text(prism_name, source, SUBJECT)
    assert source in text and SUBJECT in text


def test_unconfirmed_is_a_warning_with_the_news_caveat():
    async def search(text):
        return _found()
    results = _verify(search)
    assert {r["status"] for r in results} == {"unconfirmed"}
    warns = tv.warnings("prismes", results)
    assert len(warns) == len(results)
    assert all("news" in w and "institutions" in w for w in warns)
    assert any(results[0]["source"] in w for w in warns)


def test_a_contradicted_source_is_a_warning_quoting_the_source():
    async def search(text):
        return _found(contradicting=[_src("Le Monde", "https://lemonde.fr/a", "dit le contraire")])
    results = _verify(search)
    assert {r["status"] for r in results} == {"contradicted"}
    warn = tv.warnings("prismes", results)[0]
    assert "https://lemonde.fr/a" in warn and "dit le contraire" in warn


def test_a_confirmed_source_gives_no_warning():
    async def search(text):
        return _found(confirming=[_src()])
    results = _verify(search)
    assert {r["status"] for r in results} == {"confirmed"} and tv.warnings("prismes", results) == []


def test_no_key_or_no_network_gives_an_unavailable_warning_and_never_raises():
    async def search(text):
        raise RuntimeError("no API key")
    results = _verify(search)
    assert {r["status"] for r in results} == {"unavailable"}
    warns = tv.warnings("prismes", results)
    assert warns and all("could not be checked" in w for w in warns)


def test_the_result_is_saved_beside_the_step(tmp_path):
    results = [{"slot": "p1", "source": "Eurostat", "claim": "c", "status": "confirmed", "source_ref": None, "reason": ""}]
    n = agent.STEP_BY_NAME["prismes"].n
    path = tv.save(tmp_path, n, "prismes", results)
    assert path == tmp_path / f"{n}_prismes.verification.json" and path.name == "3_prismes.verification.json"
    assert json.loads(path.read_text(encoding="utf-8")) == results


def test_verify_pick_end_to_end_with_a_fake_search(fake, tmp_path):  # noqa: F811
    steps = tmp_path / "adapt_steps"
    agent.adapt(full(), steps_dir=steps)
    assert "prismes" in agent.VERIFIED_STEPS

    async def search(text):
        return _found(contradicting=[_src("Autre", "https://x.org/y", "non")]) if "Eurostat" in text else _found()
    warns = asyncio.run(agent.verify_pick(steps, "prismes", search))
    assert warns and any("https://x.org/y" in w for w in warns) and any("news" in w for w in warns)
    saved = json.loads((steps / "3_prismes.verification.json").read_text(encoding="utf-8"))
    assert {r["slot"] for r in saved} == {"p1", "p2", "p3"}
    events = [json.loads(line) for line in (tmp_path / "choices.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(e["step"] == "prismes" and e["event"] == "verify" for e in events)
    assert asyncio.run(agent.verify_pick(steps, "hook", search)) == []
