import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from app.scrapers.base import BaseScraper, RawArticle

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class WSJScraper(BaseScraper):
    """
    Scrapes WSJ crypto headlines from public pages only.
    Article bodies are paywalled — we collect titles + URLs only.
    """

    name = "wsj"
    _urls = [
        "https://www.wsj.com/news/markets/cryptocurrency",
        "https://www.wsj.com/tech/crypto",
    ]

    def _fetch(self) -> list[RawArticle]:
        seen: set[str] = set()
        articles: list[RawArticle] = []

        for url in self._urls:
            try:
                resp = requests.get(url, headers=_HEADERS, timeout=10)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "lxml")
                for a in soup.find_all("a", href=True):
                    href: str = a["href"]
                    title = a.get_text(strip=True)
                    if not title or len(title) < 15:
                        continue
                    if "/articles/" not in href:
                        continue
                    full_url = (
                        href if href.startswith("http") else f"https://www.wsj.com{href}"
                    )
                    if full_url in seen:
                        continue
                    seen.add(full_url)
                    articles.append(
                        RawArticle(
                            url=full_url,
                            title=title,
                            source=self.name,
                            published_at=datetime.now(timezone.utc),
                            snippet="[WSJ — headline only, article behind paywall]",
                        )
                    )
            except Exception as e:
                print(f"[wsj] error fetching {url}: {e}")

        return articles
