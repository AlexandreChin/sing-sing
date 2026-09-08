from renderer.instagram_carousel._shared import cover_thumb

PNG = bytes.fromhex("89504e470d0a1a0a")


def test_no_image_beside_the_analysis_means_no_thumbnail(tmp_path):
    assert cover_thumb(tmp_path) == ""


def test_image_png_is_embedded_as_a_data_url(tmp_path):
    (tmp_path / "image.png").write_bytes(PNG)
    assert cover_thumb(tmp_path).startswith("data:image/png;base64,")


def test_a_hand_made_cover_wins_over_the_raw_capture(tmp_path):
    (tmp_path / "image.png").write_bytes(PNG)
    (tmp_path / "cover.jpg").write_bytes(b"jpegbytes")
    assert cover_thumb(tmp_path).startswith("data:image/jpeg;base64,")
