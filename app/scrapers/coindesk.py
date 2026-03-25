from app.scrapers.rss import RssScraper


class CoinDeskScraper(RssScraper):
    name = "coindesk"
    feed_url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
