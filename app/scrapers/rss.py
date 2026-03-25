import feedparser
import requests
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, RawArticle

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CryptoDigestBot/1.0)"}
_TIMEOUT = 10  # seconds


def _parse_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_snippet(entry) -> str:
    """Pull plain-text snippet from RSS entry summary or content."""
    raw = ""
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        raw = entry.summary or ""
    text = BeautifulSoup(raw, "lxml").get_text(separator=" ", strip=True)
    return text[:800]


class RssScraper(BaseScraper):
    """Generic RSS scraper. Subclass and set `name` and `feed_url`."""

    feed_url: str = ""
    name: str = "rss"

    def _fetch(self) -> list[RawArticle]:
        # Fetch with a hard timeout, then parse the content string
        resp = requests.get(self.feed_url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries:
            url = getattr(entry, "link", None)
            title = getattr(entry, "title", "").strip()
            if not url or not title:
                continue
            articles.append(
                RawArticle(
                    url=url,
                    title=title,
                    source=self.name,
                    published_at=_parse_date(entry),
                    snippet=_extract_snippet(entry),
                )
            )
        return articles
