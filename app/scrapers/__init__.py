from app.scrapers.coindesk import CoinDeskScraper
from app.scrapers.cointelegraph import CoinTelegraphScraper
from app.scrapers.decrypt import DecryptScraper
from app.scrapers.bitcoinmagazine import BitcoinMagazineScraper
from app.scrapers.theblock import TheBlockScraper
from app.scrapers.globenewswire import GlobeNewswireScraper
from app.scrapers.wsj import WSJScraper
from app.scrapers.googlenews import GoogleNewsScraper
from app.scrapers.milkroad import MilkRoadScraper
from app.scrapers.base import RawArticle
from app.config import config

SCRAPERS = {
    "milkroad": MilkRoadScraper,
    "coindesk": CoinDeskScraper,
    "theblock": TheBlockScraper,
    "cointelegraph": CoinTelegraphScraper,
    "decrypt": DecryptScraper,
    "bitcoinmagazine": BitcoinMagazineScraper,
    "globenewswire": GlobeNewswireScraper,
    "wsj": WSJScraper,
    "googlenews": GoogleNewsScraper,
}


def run_all_scrapers() -> list[RawArticle]:
    """Run all enabled scrapers and return deduplicated articles."""
    seen_urls: set[str] = set()
    all_articles: list[RawArticle] = []

    enabled = config.ENABLED_SOURCES
    for name, scraper_cls in SCRAPERS.items():
        if name not in enabled:
            print(f"[scrapers] skipping disabled source: {name}")
            continue
        print(f"[scrapers] fetching: {name}")
        scraper = scraper_cls()
        articles = scraper.fetch()
        for a in articles:
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                all_articles.append(a)
        print(f"[scrapers] {name}: {len(articles)} articles")

    print(f"[scrapers] total unique articles: {len(all_articles)}")
    return all_articles
