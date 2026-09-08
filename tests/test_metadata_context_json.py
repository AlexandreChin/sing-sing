"""A URL in the metadata must survive the adapt agents' prompt context.

`ArticleMetadata.url` is a pydantic `HttpUrl`, which plain `json.dumps` cannot
serialise — so the metadata block has to be dumped with `mode="json"`.
"""
import inspect
import json

import pytest

from agent import instagram_carousel_adapt_agent, newsletter_adapt_agent
from agent._base import _j
from models.full_analysis import ArticleMetadata

URL = "https://aeon.co/essays/what-we-cant-measure-about-ai-yet"


def _meta():
    return ArticleMetadata(title="Avantages illisibles", source="Aeon", url=URL)


def test_json_mode_dump_serialises_the_url():
    assert "aeon.co" in _j(_meta().model_dump(mode="json"))


def test_plain_dump_is_the_trap_being_guarded():
    with pytest.raises(TypeError):
        json.dumps(_meta().model_dump())


@pytest.mark.parametrize("module, fn", [
    (instagram_carousel_adapt_agent, "_full_analysis_context"),
    (newsletter_adapt_agent, "_context"),
])
def test_adapt_agents_dump_metadata_in_json_mode(module, fn):
    src = inspect.getsource(getattr(module, fn))
    assert 'article_metadata.model_dump(mode="json")' in src
