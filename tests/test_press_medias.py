import pytest

from tools.press_medias import CSV, load

HEADER = "id,name,kind,topic,orientation,country,language,access,access_note,feed_slug,url,notes,verified_on\n"


def _csv(tmp_path, *lines):
    p = tmp_path / "m.csv"
    p.write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_region_is_derived_from_country(tmp_path):
    rows = load(_csv(tmp_path, "a,A,press,general,left,IN,en,free,,,,,", "b,B,press,economy,center,,en,free,,,,,"))
    assert [r["region"] for r in rows] == ["asia", "international"]


@pytest.mark.parametrize("line", ["a,A,blog,general,left,FR,fr,free,,,,,", "a,A,press,general,left,XX,fr,free,,,,,"])
def test_bad_enum_or_country_is_rejected(tmp_path, line):
    with pytest.raises(ValueError):
        load(_csv(tmp_path, line))


def test_duplicate_ids_are_rejected(tmp_path):
    row = "a,A,press,general,left,FR,fr,free,,,,,"
    with pytest.raises(ValueError, match="duplicate"):
        load(_csv(tmp_path, row, row))


def test_the_real_list_is_valid():
    assert len(load(CSV)) > 100
