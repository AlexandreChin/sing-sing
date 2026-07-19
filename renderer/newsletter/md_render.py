"""Render an edited newsletter.md (YAML front-matter + Markdown body) to the
brand HTML + email HTML. Markdown is the editable source of truth; per-block
styling is inferred from the enclosing section title and overridable with
`:::` containers and `{icon=…}` heading attributes."""
from __future__ import annotations

import re

import yaml

_FM_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
_OPEN = re.compile(r"^:::\s*([A-Za-z]+)\s*$")
_CLOSE = re.compile(r"^:::\s*$")


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


def segment(body_md: str) -> list[tuple[str | None, str]]:
    """Split the body into (forced_style, chunk) pairs. `::: name` … `:::`
    fences delimit a forced-style chunk; text outside carries style None."""
    segs: list[tuple[str | None, str]] = []
    cur: list[str] = []
    style: str | None = None
    for line in body_md.splitlines():
        opn, cls = _OPEN.match(line), _CLOSE.match(line)
        if opn and style is None:
            if cur:
                segs.append((None, "\n".join(cur)))
                cur = []
            style = opn.group(1)
        elif cls and style is not None:
            segs.append((style, "\n".join(cur)))
            cur = []
            style = None
        else:
            cur.append(line)
    if cur:
        segs.append((style, "\n".join(cur)))
    return segs
