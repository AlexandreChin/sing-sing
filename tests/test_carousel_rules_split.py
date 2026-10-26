import pytest

from agent.instagram_carousel_adapt_agent import split_rules
from tools.check_deck import check

DECK = "samples/articles/article_15/article/instagram_carousel_optimized/extract.json"


@pytest.mark.parametrize("msg, kind", [
    ("display.root_issue is 140 characters (max 125) — …", "hard"),
    ("caption contains hashtag(s) (#x) — …", "hard"),
    ("display.reading_beats[2].quote is not found verbatim …", "hard"),
    ("display.reperes_facts must have 2–3 items, got 4", "hard"),
    ("display.reading_beats: 2 selected beat(s) carry spine_ref=1 …", "hard"),
    ("slide socle has no **gilded** phrase — …", "hard"),
    ("display.essentiel[0] shares no key word with slide 8 (root_issue / …", "flag"),
    ("cta.engagement_sentence shares no **gilded** word with display.root_issue — …", "flag"),
    ("display.essentiel[1] restates the lede printed two lines above it …", "flag"),
    ("hook.sub_topic opens on « Derrière » — …; vary the construction from one deck to the next", "flag"),
    ("cta.engagement_sentence is a yes/no question — make it open …", "flag"),
    ("cta.engagement_sentence uses « légitime » — a word that answers …", "flag"),
    ("display.reading_beats[0].answer names no place to look — …", "flag"),
])
def test_each_message_lands_in_its_family(msg, kind):
    hard, flags = split_rules([msg])
    assert (hard, flags) == (([msg], []) if kind == "hard" else ([], [msg]))


def test_split_keeps_order():
    a, b, c = "x is empty", "y shares no key word with slide 8", "z is empty"
    assert split_rules([a, b, c]) == ([a, c], [b])


def test_check_reports_flags_as_advisory():
    report = check(DECK)
    assert "editorial (advisory)" in report
    _, flags = split_rules(report["editorial (advisory)"])
    assert flags == report["editorial (advisory)"]
    assert not split_rules(report["structure (extract)"])[1]
