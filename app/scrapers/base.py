from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawArticle:
    url: str
    title: str
    source: str
    published_at: Optional[datetime] = None
    snippet: str = ""  # first ~800 chars of content


class BaseScraper(ABC):
    name: str = "base"

    def fetch(self) -> list[RawArticle]:
        """Fetch articles. Returns empty list on any error."""
        try:
            return self._fetch()
        except Exception as e:
            print(f"[{self.name}] scrape error: {e}")
            return []

    @abstractmethod
    def _fetch(self) -> list[RawArticle]:
        """Implement scraping logic here."""
        ...
