from tools.feeds import _drop_chrome, _parse, _slugify

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Feed</title>
  <item><title>Premier papier</title><link>https://ex.fr/a</link>
        <pubDate>Mon, 07 Sep 2026 15:18:55 +0200</pubDate></item>
  <item><title>Sans lien</title><link></link></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <link rel="self" href="https://ex.fr/feed"/>
  <entry>
    <published>2026-09-07T09:41:28Z</published>
    <link rel="related" type="text/html" href="https://ex.fr/nope"/>
    <link rel="alternate" type="text/html" href="https://ex.fr/b"/>
    <title>Une analyse</title>
  </entry>
</feed>"""


def test_parse_rss_keeps_titled_items_with_a_link():
    items = _parse(RSS, "Feed")
    assert items == [{"title": "Premier papier", "url": "https://ex.fr/a",
                      "date": "Mon, 07 Sep 2026", "source": "Feed"}]


def test_parse_atom_takes_the_alternate_link():
    items = _parse(ATOM, "Feed")
    assert items == [{"title": "Une analyse", "url": "https://ex.fr/b",
                      "date": "2026-09-07", "source": "Feed"}]


def test_drop_chrome_skips_nav_lines_before_the_first_paragraph():
    body = "Menu\nS'abonner\n" + "Le texte réel de l'article " * 8 + "\nsuite"
    assert _drop_chrome(body).startswith("Le texte réel")


def test_drop_chrome_keeps_a_body_with_no_long_line():
    assert _drop_chrome("Court.\nAussi court.") == "Court.\nAussi court."


def test_slugify_drops_the_site_name_suffix():
    assert _slugify("Égaux face à la canicule ? - La Vie des idées") == "egaux-face-a-la-canicule"
