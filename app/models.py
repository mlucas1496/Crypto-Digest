from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    url = Column(String(2048), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    source = Column(String(64), nullable=False)
    published_at = Column(DateTime, nullable=True)
    raw_content = Column(Text, nullable=True)  # first ~1000 chars
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    digest_items = relationship("DigestItem", back_populates="article")

    def __repr__(self):
        return f"<Article {self.source}: {self.title[:60]}>"


class Digest(Base):
    __tablename__ = "digests"

    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    executive_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    status = Column(String(16), default="pending", nullable=False)  # pending/complete/error
    error_message = Column(Text, nullable=True)
    articles_processed = Column(Integer, default=0)

    items = relationship(
        "DigestItem", back_populates="digest", order_by="DigestItem.rank"
    )

    def items_by_category(self, category: str):
        return [i for i in self.items if i.category == category]

    def __repr__(self):
        return f"<Digest {self.date} [{self.status}]>"


class DigestItem(Base):
    __tablename__ = "digest_items"
    __table_args__ = (UniqueConstraint("digest_id", "article_id"),)

    id = Column(Integer, primary_key=True)
    digest_id = Column(Integer, ForeignKey("digests.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    category = Column(String(32), nullable=False)  # ma / regulatory / trends / headlines
    importance = Column(Integer, nullable=False)  # 1–10
    summary = Column(Text, nullable=False)
    rank = Column(Integer, nullable=False)  # within category

    digest = relationship("Digest", back_populates="items")
    article = relationship("Article", back_populates="digest_items")

    CATEGORY_LABELS = {
        "ma": "M&A",
        "regulatory": "Regulatory",
        "trends": "Market Trends",
        "headlines": "Major Headlines",
    }

    @property
    def category_label(self):
        return self.CATEGORY_LABELS.get(self.category, self.category.title())

    def __repr__(self):
        return f"<DigestItem {self.category} importance={self.importance}>"
