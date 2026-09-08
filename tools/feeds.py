"""Curated free-to-read French news feeds — candidate articles for `analyze`.

Every source here is free (no paywall, no metered wall on most pieces) and
scrapes cleanly. Paywalled titles (Le Monde, Libération, Les Échos) and
bot-blocked ones (RFI, France 24 — 403 on every page) are deliberately absent:
their feeds would only yield teasers or errors.
"""

import asyncio
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from .scrape import scrape_article

# slug → (label, feed url)
FEEDS = {
    # généraliste
    "franceinfo": ("franceinfo", "https://www.francetvinfo.fr/titres.rss"),
    "20minutes": ("20 Minutes", "https://www.20minutes.fr/feeds/rss-une.xml"),
    "rts": ("RTS Info (Suisse)", "https://www.rts.ch/info/?format=rss/news"),
    # francophonie — enquêtes et longs formats
    "lapresse": ("La Presse (Montréal)", "https://www.lapresse.ca/actualites/rss"),
    "radiocanada": ("Radio-Canada Info", "https://ici.radio-canada.ca/rss/4159"),
    "ledevoir": ("Le Devoir", "https://www.ledevoir.com/rss/manchettes.xml"),
    # politique et institutions
    "publicsenat": ("Public Sénat", "https://www.publicsenat.fr/rss"),
    "euractiv": ("Euractiv France", "https://www.euractiv.fr/feed/"),
    # écologie et social
    "reporterre": ("Reporterre", "https://reporterre.net/spip.php?page=backend"),
    "basta": ("Basta!", "https://basta.media/spip.php?page=backend"),
    "vert": ("Vert", "https://vert.eco/feed"),
    # sciences et techno
    "sciencesavenir": ("Sciences et Avenir", "https://www.sciencesetavenir.fr/rss.xml"),
    "numerama": ("Numerama", "https://www.numerama.com/feed/"),
}

_ATOM = "{http://www.w3.org/2005/Atom}"


def _text(node: ET.Element | None) -> str:
    return " ".join(node.itertext()).strip() if node is not None else ""


def _parse(xml: str, label: str) -> list[dict]:
    """RSS 2.0 <item> and Atom <entry> into {source, title, url, date}."""
    root = ET.fromstring(xml)
    entries = []
    for item in root.iter("item"):
        entries.append({
            "title": _text(item.find("title")),
            "url": _text(item.find("link")),
            "date": _text(item.find("pubDate"))[:16],
        })
    for entry in root.iter(f"{_ATOM}entry"):
        link = next(
            (l for l in entry.findall(f"{_ATOM}link") if l.get("rel", "alternate") == "alternate"),
            None,
        )
        entries.append({
            "title": _text(entry.find(f"{_ATOM}title")),
            "url": link.get("href", "") if link is not None else "",
            "date": (_text(entry.find(f"{_ATOM}published")) or _text(entry.find(f"{_ATOM}updated")))[:10],
        })
    return [e | {"source": label} for e in entries if e["url"]]


async def _fetch_feed(client: httpx.AsyncClient, slug: str, limit: int) -> list[dict]:
    label, url = FEEDS[slug]
    try:
        response = await client.get(url)
        response.raise_for_status()
        return _parse(response.text, label)[:limit]
    except (httpx.HTTPError, ET.ParseError) as exc:
        print(f"  ! {label}: {type(exc).__name__}")
        return []


async def list_candidates(sources: list[str] | None = None, limit: int = 5) -> list[dict]:
    """Latest `limit` items per source. Unknown slugs raise."""
    slugs = sources or list(FEEDS)
    unknown = [s for s in slugs if s not in FEEDS]
    if unknown:
        raise ValueError(f"unknown source(s): {', '.join(unknown)} — known: {', '.join(FEEDS)}")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20,
                                 headers={"User-Agent": "Mozilla/5.0"}) as client:
        batches = await asyncio.gather(*(_fetch_feed(client, s, limit) for s in slugs))
    return [item for batch in batches for item in batch]


def _slugify(title: str, words: int = 8) -> str:
    title = re.split(r" [-|–] ", title)[0]  # drop the trailing site name
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    parts = re.findall(r"[a-z0-9]+", ascii_title.lower())
    return "-".join(parts[:words]) or "article"


def _drop_chrome(body: str) -> str:
    """Skip the site's leading nav/menu lines: everything before the first
    prose-length line. `scrape_article` falls back to <body> when a page has no
    <article>, and that chrome is noise the analysis would pay tokens for."""
    lines = body.splitlines()
    start = next((i for i, line in enumerate(lines[:40]) if len(line) > 120), 0)
    return "\n".join(lines[start:]).strip()


async def fetch_article(url: str, dest_dir: Path) -> Path:
    """Scrape `url` into `dest_dir/<slug>.txt`, title and source URL on top."""
    article = await scrape_article(url)
    body = _drop_chrome(article["body"])
    if len(body.split()) < 200:
        print(f"  ! only {len(body.split())} words extracted — check the file before analyzing")

    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{_slugify(article['title'])}.txt"
    path.write_text(f"{article['title']}\n{url}\n\n{body}\n", encoding="utf-8")
    return path
