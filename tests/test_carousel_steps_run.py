"""The eight-step runner: options generated, picks taken or awaited, steps reused."""
import pytest

from agent.carousel_steps import run
from agent.carousel_steps.steps import STEP_BY_NAME, Option
from agent.carousel_steps.store import load, save
from tests._carousel_steps_fixtures import FakeCalls, full as _full, load_deck

ORDER = ["question", "enjeu", "idees", "moments", "contexte", "socle", "hook", "writing"]


@pytest.fixture
def deck() -> dict:
    return load_deck()


@pytest.fixture
def fake(deck, monkeypatch) -> FakeCalls:
    calls = FakeCalls(deck)
    monkeypatch.setattr(run, "_call_with_retry", calls)
    return calls


@pytest.fixture
def steps_dir(tmp_path):
    return tmp_path / "adapt_steps"


def test_unattended_runs_eight_steps_and_rebuilds_the_deck(fake, steps_dir, deck):
    pres = run.adapt(_full(), steps_dir=steps_dir)
    assert fake.labels == ORDER
    assert pres.display.root_issue == deck["display"]["root_issue"]
    assert pres.display.essentiel == deck["display"]["essentiel"]
    assert pres.hook.sub_topic == deck["hook"]["sub_topic"]
    assert [b.moment for b in pres.display.reading_beats if b.selected] == \
        [b["moment"] for b in deck["display"]["reading_beats"] if b["selected"]]
    run.adapt(_full(), steps_dir=steps_dir)
    assert len(fake.labels) == 8                                   # all reused


def test_the_validator_accepts_the_sample_deck(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir)
    # the deck's own picks raise no slot error and no options[k] error at any step
    for label, errors in fake.errors.items():
        assert not [e for e in errors if "slot" in e or "recommended" in e], (label, errors)
    assert fake.errors["writing"] == []                            # beat copy lands on the selected beats
    # the sample's headline is too long: the error goes to the headline options only
    assert {e.split(":")[0] for e in fake.errors["socle"]} == {"options[0]", "options[1]"}


def test_guided_pauses_at_the_first_unchosen_step(fake, steps_dir, capsys):
    assert run.adapt(_full(), steps_dir=steps_dir, guided=True) is None
    assert fake.labels == ["question"]
    out = capsys.readouterr()
    assert "★" in out.out and "↳" in out.out and "Awaiting a choice at step 1 (question)" in out.err
    sf, _ = load(steps_dir, STEP_BY_NAME["question"])
    assert sf.picked == [] and sf.thesis_frame is not None


def test_guided_resumes_after_a_pick(fake, steps_dir, capsys):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    sf, stamp = load(steps_dir, STEP_BY_NAME["question"])
    sf.picked = ["b"]
    save(steps_dir, sf, stamp)
    assert run.adapt(_full(), steps_dir=steps_dir, guided=True) is None
    assert fake.labels == ["question", "enjeu"]
    assert "Awaiting a choice at step 2 (enjeu)" in capsys.readouterr().err
    sf, _ = load(steps_dir, STEP_BY_NAME["question"])
    assert sf.fragment["cta"]["engagement_sentence"] == sf.options[1].fields["text"]


def test_unattended_takes_recommended_on_an_unchosen_file(fake, steps_dir, deck):
    run.adapt(_full(), steps_dir=steps_dir, guided=True)
    pres = run.adapt(_full(), steps_dir=steps_dir)
    assert fake.labels == ORDER                                    # question reused
    assert pres.cta.engagement_sentence == deck["cta"]["engagement_sentence"]


def test_changed_pick_reruns_only_later_steps(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir)
    sf, stamp = load(steps_dir, STEP_BY_NAME["enjeu"])
    sf.fragment["display"]["root_issue"] = "Un enjeu réécrit"
    save(steps_dir, sf, stamp)
    pres = run.adapt(_full(), steps_dir=steps_dir)
    assert fake.labels[8:] == ["idees", "moments", "contexte", "socle", "hook", "writing"]
    assert pres.display.root_issue == "Un enjeu réécrit"
    assert next(steps_dir.glob("stale_*/3_idees.json"))


def test_stop_after_returns_once_that_step_is_chosen(fake, steps_dir):
    assert run.adapt(_full(), steps_dir=steps_dir, stop_after="enjeu") is None
    assert fake.labels == ["question", "enjeu"]


def test_legacy_stage_files_are_retired(fake, steps_dir):
    steps_dir.mkdir()
    (steps_dir / "1_axis.json").write_text("{}")
    run.adapt(_full(), steps_dir=steps_dir)
    assert (steps_dir / "stale_legacy" / "1_axis.json").exists()


def test_invalid_recommended_falls_back_to_first_per_slot(fake, steps_dir, capsys):
    fake.recommended_override["idees"] = [0, 1, 2]                 # three options of slot 1
    run.adapt(_full(), steps_dir=steps_dir)
    sf, _ = load(steps_dir, STEP_BY_NAME["idees"])
    assert sf.picked == ["1a", "2a", "3a"]
    assert "recommended picks invalid" in capsys.readouterr().err
    assert any("slot '1' keeps 2" in e for e in fake.errors["idees"])


def test_option_ids_continue_after_rejected(fake):
    rejected = [Option(id=i, slot="question", reason="r", fields={"text": t}) for i, t in (("a", "x ?"), ("b", "y ?"))]
    sf = run.generate(STEP_BY_NAME["question"], _full(), {}, None, False, rejected=rejected, remarks=["plus large"])
    assert [o.id for o in sf.options] == ["c", "d", "e", "f"]
    assert sf.recommended == ["c"]
    assert sf.rejected == rejected and sf.remarks == ["plus large"]
    assert "DÉJÀ PROPOSÉES ET ÉCARTÉES" in fake.messages[-1] and "x ?" in fake.messages[-1]
    assert "REMARQUES DE L'AUTEUR" in fake.messages[-1] and "plus large" in fake.messages[-1]


def test_option_ids_continue_per_slot(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, stop_after="enjeu")
    frags = {}
    for name in ("question", "enjeu"):
        sf, _ = load(steps_dir, STEP_BY_NAME[name])
        frags[name] = sf.fragment
    rejected = [Option(id=i, slot="1", reason="r", fields={"text": "t"}) for i in ("1a", "1b")]
    sf = run.generate(STEP_BY_NAME["idees"], _full(), frags, None, False, rejected=rejected)
    assert [o.id for o in sf.options] == ["1c", "1d", "2a", "2b", "3a", "3b"]


def test_message_holds_its_parts_in_order(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, stop_after="enjeu")
    msg = fake.messages[1]
    step = STEP_BY_NAME["enjeu"]
    parts = ['"fond"', "CHOIX FIXÉS (ne les réécris pas) :", run._SHARED_PROMPT[:80], run.prompt_for(step)[:80],
             "EXEMPLES (décisions passées de l'auteur) :"]
    positions = [msg.index(p) for p in parts]
    assert positions == sorted(positions)
    assert "DÉJÀ PROPOSÉES" not in msg and "REMARQUES DE L'AUTEUR" not in msg


def test_flags_attach_to_their_option(fake, steps_dir):
    def off_axis(data):
        data["options"][3]["text"] = "Les **pommes** rouges tombent en automne."   # slot 2's alternate
        return data
    fake.edit["idees"] = off_axis
    run.adapt(_full(), steps_dir=steps_dir)
    sf, _ = load(steps_dir, STEP_BY_NAME["idees"])
    by_id = {o.id: o for o in sf.options}
    assert any("shares no key word" in f for f in by_id["2b"].flags)
    for i in ("1a", "1b", "2a", "3a", "3b"):
        assert not any("shares no key word" in f for f in by_id[i].flags), i


def test_format_options_marks_recommended_and_flags(fake, steps_dir):
    run.adapt(_full(), steps_dir=steps_dir, stop_after="question")
    sf, _ = load(steps_dir, STEP_BY_NAME["question"])
    sf.options[1].flags = ["un drapeau"]
    out = run.format_options(STEP_BY_NAME["question"], sf)
    lines = out.splitlines()
    assert sf.thesis_frame.main_claim in lines[0]
    assert any(l.startswith("a — ") and "★" in l for l in lines)
    assert any(l.startswith("b — ") and "★" not in l for l in lines)
    assert "   ⚠ un drapeau" in lines
