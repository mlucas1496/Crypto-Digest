from app.scrapers.rss import RssScraper


class DecryptScraper(RssScraper):
    name = "decrypt"
    feed_url = "https://decrypt.co/feed"
