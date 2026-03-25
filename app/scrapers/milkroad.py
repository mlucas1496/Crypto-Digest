from app.scrapers.rss import RssScraper


class MilkRoadScraper(RssScraper):
    name = "milkroad"
    feed_url = "https://milkroad.com/feed/"
