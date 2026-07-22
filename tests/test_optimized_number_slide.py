from models.instagram_carousel_presentation import ReadingBeat


def test_reading_beat_figure_fields_default_empty():
    b = ReadingBeat(moment="m", quote="q", lens_ref="chiffres", note="n")
    assert b.figure == "" and b.figure_label == "" and b.figure_caption == ""


def test_reading_beat_accepts_figure_fields():
    b = ReadingBeat(moment="m", quote="q", lens_ref="chiffres", note="n",
                    figure="4 400 %", figure_label="de voyageurs", figure_caption="230 → 10 000")
    assert b.figure == "4 400 %"
    assert b.figure_label == "de voyageurs"
    assert b.figure_caption == "230 → 10 000"
