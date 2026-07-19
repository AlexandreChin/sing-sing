"""Render an edited newsletter.md (YAML front-matter + Markdown body) to the
brand HTML + email HTML. Markdown is the editable source of truth; per-block
styling is inferred from the enclosing section title and overridable with
`:::` containers and `{icon=…}` heading attributes."""
from __future__ import annotations

import re

import yaml

_FM_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


def parse_source(md_text: str) -> tuple[dict, str]:
    """Split a leading `---`-fenced YAML front-matter block from the body.
    No front-matter → ({}, md_text)."""
    m = _FM_RE.match(md_text)
    if not m:
        return {}, md_text
    fm = yaml.safe_load(m.group(1)) or {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, m.group(2)
