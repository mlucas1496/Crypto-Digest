from app.scrapers.rss import RssScraper


class BitcoinMagazineScraper(RssScraper):
    name = "bitcoinmagazine"
    feed_url = "https://bitcoinmagazine.com/.rss/full/"
