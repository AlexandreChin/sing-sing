from types import SimpleNamespace as NS

from agent.instagram_carousel_adapt_agent import _quote_errors, is_french

EN = "The government said that the police was in the streets and the students were angry."
FR = "Le gouvernement a dit que la police est dans les rues et que les lycéens sont en colère."


def _beat(quote, original=""):
    return NS(selected=True, quote=quote, quote_original=original)


def test_language_guess():
    assert is_french(FR) and not is_french(EN)


def test_french_article_quotes_verbatim():
    d = NS(reading_beats=[_beat("la police est dans les rues")])
    assert _quote_errors(d, FR) == []


def test_english_article_needs_original_and_translation():
    d = NS(reading_beats=[_beat("the police was in the streets")])
    errs = _quote_errors(d, EN)
    assert len(errs) == 1 and "quote_original is empty" in errs[0]


def test_translation_checked_through_its_original():
    d = NS(reading_beats=[_beat("la police était dans les rues", "the police was in the streets")])
    assert _quote_errors(d, EN) == []
    d = NS(reading_beats=[_beat("la police était dans les rues", "the police were everywhere")])
    assert "quote_original is not in the article" in _quote_errors(d, EN)[0]
