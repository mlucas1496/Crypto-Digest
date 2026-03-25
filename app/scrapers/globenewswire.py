from app.scrapers.rss import RssScraper
from app.scrapers.base import RawArticle
from app.config import config

# GlobeNewswire RSS feeds relevant to crypto/M&A
_FEEDS = [
    # M&A / Corporate announcements
    "https://www.globenewswire.com/RssFeed/subjectcode/23-Mergers%20Acquisitions%20/%20Takeovers",
    # Technology sector
    "https://www.globenewswire.com/RssFeed/industry/9798-Blockchain",
    # Broader financial services
    "https://www.globenewswire.com/RssFeed/industry/9751-Financial%20Services",
]


class GlobeNewswireScraper(RssScraper):
    name = "globenewswire"

    def _fetch(self) -> list[RawArticle]:
        seen_urls: set[str] = set()
        all_articles: list[RawArticle] = []

        for feed_url in _FEEDS:
            self.feed_url = feed_url
            articles = super()._fetch()
            for article in articles:
                if article.url in seen_urls:
                    continue
                seen_urls.add(article.url)
                if self._is_crypto_relevant(article):
                    all_articles.append(article)

        return all_articles

    def _is_crypto_relevant(self, article: RawArticle) -> bool:
        """Return True if the article title or snippet contains a crypto keyword."""
        text = (article.title + " " + article.snippet).lower()
        return any(kw in text for kw in config.GNW_KEYWORDS)
