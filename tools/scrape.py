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

    # Prefer <article> body; fall back to <main>, then <body>
    container = soup.find("article") or soup.find("main") or soup.body
    body = container.get_text(separator="\n", strip=True) if container else ""

    return {"url": url, "title": title, "body": body}
