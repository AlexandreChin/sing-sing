from agent.carousel_steps.steps import STEP_BY_NAME, STEPS, prompt_for, examples_for


def test_every_step_has_its_prompt_and_options_preamble():
    for s in STEPS:
        p = prompt_for(s)
        assert p.strip()
        assert ("PROPOSITIONS (impératif)" in p) is (s.name != "writing")
        assert "_alt" not in p


def test_slide_8_examples_are_seeded_from_the_five_decks():
    import json
    from pathlib import Path
    q, e = examples_for(STEPS[0]), examples_for(STEPS[1])
    for deck in ("samples/podcasts/podcast_1", "samples/articles/article_14/article",
                 "samples/articles/article_15/article", "samples/videos/video_4", "samples/videos/video_5"):
        d = json.loads(Path(deck, "instagram_carousel_optimized/adapt.json").read_text(encoding="utf-8"))
        assert d["cta"]["engagement_sentence"] in q
        assert d["display"]["root_issue"] in e
    assert "## Écartés" in e


def test_each_step_prompt_names_its_slots():
    for name, step in STEP_BY_NAME.items():
        p = prompt_for(step)
        for slot in step.slots:
            assert f"`{slot}`" in p, (name, slot)


def test_socle_examples_split_the_presupposes():
    s = examples_for(STEP_BY_NAME["socle"])
    for label in ("p1", "p2", "p3"):
        assert f"- {label} : " in s
    assert "Ses présupposés" not in s and "tient pour acquis" not in s

