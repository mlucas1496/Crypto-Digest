"""
Google News RSS search scraper.
Searches for companies, deal keywords, and crypto assets — no API key needed.
"""
import time
from urllib.parse import quote_plus
import requests
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, RawArticle

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CryptoDigestBot/1.0)"}
_TIMEOUT = 10
_DELAY = 0.4  # seconds between requests to avoid rate limiting

# ── Search terms ──────────────────────────────────────────────────────────────
# Each entry becomes a Google News search: "term when:1d"

COMPANY_SEARCHES = [
    # Exchanges
    "Coinbase",
    "Kraken crypto",
    "Gemini crypto",
    "Binance",
    "Bitfinex",
    "OKX crypto",
    # Issuers / infrastructure
    "Circle USDC",
    "Ripple XRP",
    "Chainlink",
    "Grayscale",
    "Galaxy Digital",
    "Securitize",
    "Anchorage Digital",
    "BitGo",
    "Fireblocks",
    "Copper crypto",
    # Institutional
    "BlackRock bitcoin",
    "Fidelity crypto",
    "NYSE crypto",
    "CME crypto",
    "Franklin Templeton crypto",
]

DEAL_SEARCHES = [
    "crypto acquisition",
    "crypto merger",
    "crypto fundraising round",
    "blockchain partnership deal",
    "tokenized securities",
    "tokenized assets",
    "digital asset acquisition",
    "stablecoin partnership",
    "crypto IPO",
    "crypto SPAC",
]

REGULATORY_SEARCHES = [
    "crypto regulation bill",
    "SEC cryptocurrency",
    "CFTC crypto",
    "stablecoin bill",
    "digital asset legislation",
    "crypto enforcement",
    "MiCA crypto",
    "crypto ETF",
]

ASSET_SEARCHES = [
    "Bitcoin institutional",
    "Ethereum upgrade",
    "Solana",
    "XRP Ripple",
    "USDC USDT stablecoin",
    "DeFi protocol",
]

ALL_SEARCHES = COMPANY_SEARCHES + DEAL_SEARCHES + REGULATORY_SEARCHES + ASSET_SEARCHES


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
    raw = ""
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        raw = entry.summary or ""
    return BeautifulSoup(raw, "lxml").get_text(separator=" ", strip=True)[:800]


class GoogleNewsScraper(BaseScraper):
    name = "googlenews"

    def _fetch(self) -> list[RawArticle]:
        seen_urls: set[str] = set()
        all_articles: list[RawArticle] = []

        for i, term in enumerate(ALL_SEARCHES):
            if i > 0:
                time.sleep(_DELAY)
            try:
                articles = self._search(term)
                for a in articles:
                    if a.url not in seen_urls:
                        seen_urls.add(a.url)
                        all_articles.append(a)
            except Exception as e:
                print(f"[googlenews] error searching '{term}': {e}")

        print(f"[googlenews] {len(all_articles)} unique articles from {len(ALL_SEARCHES)} searches")
        return all_articles

    def _search(self, term: str) -> list[RawArticle]:
        query = quote_plus(f"{term} when:1d")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        articles = []
        for entry in feed.entries:
            link = getattr(entry, "link", None)
            title = getattr(entry, "title", "").strip()
            if not link or not title:
                continue
            # Google News wraps the real URL — use it as-is (it redirects)
            articles.append(RawArticle(
                url=link,
                title=title,
                source="googlenews",
                published_at=_parse_date(entry),
                snippet=_extract_snippet(entry),
            ))
        return articles
