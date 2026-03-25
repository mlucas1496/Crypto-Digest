from app.scrapers.rss import RssScraper


class CoinTelegraphScraper(RssScraper):
    name = "cointelegraph"
    feed_url = "https://cointelegraph.com/rss"
