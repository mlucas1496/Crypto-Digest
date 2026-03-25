from app.scrapers.rss import RssScraper
from app.scrapers.base import RawArticle
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone


class TheBlockScraper(RssScraper):
    name = "theblock"
    feed_url = "https://www.theblock.co/rss.xml"

    def _fetch(self) -> list[RawArticle]:
        # Try RSS first
        articles = super()._fetch()
        if articles:
            return articles
        # Fallback: scrape headlines page
        return self._scrape_headlines()

    def _scrape_headlines(self) -> list[RawArticle]:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CryptoDigestBot/1.0)"}
        resp = requests.get(
            "https://www.theblock.co/latest", headers=headers, timeout=10
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        articles = []
        for a in soup.select("a[href*='/post/']")[:30]:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title or not href:
                continue
            url = href if href.startswith("http") else f"https://www.theblock.co{href}"
            articles.append(
                RawArticle(
                    url=url,
                    title=title,
                    source=self.name,
                    published_at=datetime.now(timezone.utc),
                )
            )
        return articles
