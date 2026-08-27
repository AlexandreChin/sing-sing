"""`category` accepts the unaccented spelling hand-edited files tend to carry.

"Ecologie" instead of "Écologie" failed the Literal and blocked the render three
times in one editing session — a typography reason to stop a build.
"""
import pytest
from pydantic import ValidationError

from models.full_analysis import ArticleMetadata


@pytest.mark.parametrize("raw,expected", [
    ("Ecologie", "Écologie"),
    ("ECOLOGIE", "Écologie"),
    ("écologie", "Écologie"),
    ("Economie", "Économie"),
    ("Societe", "Société"),
    ("sciences & sante", "Sciences & Santé"),
    ("Écologie", "Écologie"),      # already canonical
    ("Autre", "Autre"),            # no accent to fix
])
def test_category_is_normalised(raw, expected):
    assert ArticleMetadata(category=raw).category == expected


def test_unknown_category_is_still_rejected():
    # the normaliser must not turn the Literal into "accept anything"
    with pytest.raises(ValidationError):
        ArticleMetadata(category="Gastronomie")


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_blank_category_stays_none(raw):
    assert ArticleMetadata(category=raw).category is None
