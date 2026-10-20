from renderer.instagram_carousel._shared import background_image, cover_thumb, pill_parts

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


def test_background_is_opt_in_by_file(tmp_path):
    (tmp_path / "image.png").write_bytes(b"x")
    assert background_image(tmp_path) == ""               # a capture is not a background
    (tmp_path / "background.jpg").write_bytes(b"x")
    assert background_image(tmp_path).startswith("data:image/jpeg;base64,")


def test_pill_parts_order_short_month_and_gaps():
    from models.full_analysis import ArticleMetadata
    meta = ArticleMetadata(medium="podcast", reading_time_minutes=40, source="France Culture",
                           published_at="1 octobre 2026")
    assert pill_parts(meta) == ["Podcast", "40 min", "France Culture", "1 oct. 2026"]
    assert pill_parts(ArticleMetadata(source="Le Monde")) == ["Article", "Le Monde"]


def test_images_beside_the_input_file_are_found(tmp_path):
    # article_14/article.txt → analysis in article_14/article/, image beside the .txt
    (tmp_path / "article.txt").write_text("x")
    base = tmp_path / "article"; base.mkdir()
    (tmp_path / "background.png").write_bytes(PNG)
    assert background_image(base).startswith("data:image/png;base64,")


def test_parent_images_ignored_without_the_input_file(tmp_path):
    base = tmp_path / "podcast_1"; base.mkdir()
    (tmp_path / "image.png").write_bytes(PNG)               # some other sample's image
    assert cover_thumb(base) == ""


def test_card_hook_leaves_room_for_a_three_line_headline():
    # article_14's first render: a 1.6:1 photo and this headline clipped its third line
    from renderer.instagram_carousel._shared import _HOOK_BOX, _HOOK_FIXED, _HOOK_TAIL, _HEAD_GAP, hook_metrics
    head = "Mineurs blessés, **7000** interpellés, peu jugés : **nouvelle norme** ?"
    m = hook_metrics((962, 602), head)
    need = 3 * round(m["head_size"] * 1.06)
    assert m["slot_max"] + need <= _HOOK_BOX - _HOOK_FIXED - _HOOK_TAIL - _HEAD_GAP


def test_source_label_says_what_is_translated():
    from renderer.instagram_carousel._shared import source_label
    assert source_label("L'article", None) == "L'article"
    assert source_label("L'article", "espagnol") == "L'article · traduit de l'espagnol"
    assert source_label("L'épisode", "Anglais") == "L'épisode · traduit de l'anglais"
    assert source_label("L'article", "portugais") == "L'article · traduit du portugais"
