import httpx
from bs4 import BeautifulSoup


async def scrape_article(url: str) -> dict:
    """Fetch a news article URL and return its title and cleaned body text."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove boilerplate elements
    for tag in soup(["script", "style", "nav", "footer", "aside", "figure"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""

    # The richest <article>/<main> block, not the first one: on blog pages the
    # first <article> is often a comment or a related-post card.
    blocks = soup.find_all(["article", "main"])
    best = max(blocks, key=lambda b: len(b.get_text(strip=True)), default=None)
    body_len = len(soup.body.get_text(strip=True)) if soup.body else 0
    # Some sites tag only their comments as <article> and wrap the post in a
    # plain <div>: a block holding a sliver of the page is not the article.
    keep = best is not None and len(best.get_text(strip=True)) > 0.25 * body_len
    container = best if keep else soup.body
    body = container.get_text(separator="\n", strip=True) if container else ""

    return {"url": url, "title": title, "body": body}
