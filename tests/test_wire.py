"""The wire: one gold line through the carousel, continuous at every edge."""
import re

from renderer.shoot import wire_paths


def _ends(d):
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]
    return nums[1], nums[-1]          # y where it enters, y where it leaves


def test_continuous_at_every_edge():
    paths = wire_paths([500, 800, 300, 600])[1:3]          # inner slides: both edges shared
    for a, b in zip(paths, paths[1:]):
        assert _ends(a)[1] == _ends(b)[0]       # leaves one slide where it enters the next


def test_level_along_the_perch_across_the_text_column():
    d = wire_paths([500])[0]
    assert "L 990 499.0" in d and "90 499.0" in d   # level from 90 to 990, just above the perch


def test_slide_without_perch_is_crossed_along_its_foot():
    paths = wire_paths([500, None, 700])
    assert "L 990 1317.0" in paths[1]             # level under the content, not through it
    assert _ends(paths[0])[1] == _ends(paths[1])[0]
    assert all(p for p in paths)


def test_no_perch_no_wire():
    assert wire_paths([None, None]) == ["", ""]


def test_no_wire_before_the_first_perch_or_after_the_last():
    paths = wire_paths([None, 500, 700, None])
    assert paths[0] == "" and paths[3] == ""                # the bird at home: no wire
    assert paths[1].startswith("M90 499.0")                  # starts at the text column, not the edge
    assert paths[2].endswith("L 990 699.0")                  # and ends there
