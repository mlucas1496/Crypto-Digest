from datetime import date, datetime, timezone, timedelta
from app.scrapers import run_all_scrapers
from app.scrapers.base import RawArticle
from app.claude.pipeline import run_pipeline
from app.database import get_db
from app.models import Article, Digest, DigestItem
from app.config import config
from sqlalchemy.orm import Session


def _store_articles(db: Session, raw_articles: list[RawArticle]) -> dict[str, Article]:
    """Upsert raw articles and return URL → Article mapping."""
    url_map: dict[str, Article] = {}
    for raw in raw_articles:
        existing = db.query(Article).filter(Article.url == raw.url).first()
        if existing:
            url_map[raw.url] = existing
        else:
            article = Article(
                url=raw.url,
                title=raw.title,
                source=raw.source,
                published_at=raw.published_at,
                raw_content=raw.snippet,
                fetched_at=datetime.now(timezone.utc),
            )
            db.add(article)
            db.flush()
            url_map[raw.url] = article
    return url_map


def _filter_recent(articles: list[RawArticle]) -> list[RawArticle]:
    """Keep only articles published within LOOKBACK_HOURS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.LOOKBACK_HOURS)
    recent = []
    for a in articles:
        if a.published_at is None:
            # No date → include (can't filter)
            recent.append(a)
        elif a.published_at.tzinfo is None:
            # Naive datetime → assume UTC
            if a.published_at >= cutoff.replace(tzinfo=None):
                recent.append(a)
        else:
            if a.published_at >= cutoff:
                recent.append(a)
    return recent


def run_digest(target_date: date | None = None, force: bool = False) -> Digest:
    """
    Run the full digest pipeline for target_date (defaults to today).
    Set force=True to re-run even if a completed digest already exists.
    Returns the completed Digest object.
    """
    if target_date is None:
        target_date = date.today()

    print(f"\n{'='*60}")
    print(f"[runner] Starting digest for {target_date}{' (forced)' if force else ''}")
    print(f"{'='*60}")

    with get_db() as db:
        # Check if digest already exists
        existing = db.query(Digest).filter(Digest.date == target_date).first()
        if existing and existing.status == "complete" and not force:
            print(f"[runner] Digest for {target_date} already complete, skipping.")
            return existing

        # Create or reset digest record
        if existing:
            digest = existing
            digest.status = "pending"
            digest.error_message = None
        else:
            digest = Digest(date=target_date, status="pending")
            db.add(digest)
        db.flush()

        try:
            # Step 1: Scrape
            print("[runner] Scraping sources...")
            all_articles = run_all_scrapers()
            if not all_articles:
                raise RuntimeError("All scrapers returned 0 articles — possible network/SSL failure")
            recent_articles = _filter_recent(all_articles)
            print(f"[runner] {len(recent_articles)} articles within lookback window")

            # Step 2: Store raw articles
            url_map = _store_articles(db, all_articles)

            # Step 3: Run Claude pipeline
            processed, exec_summary = run_pipeline(
                recent_articles,
                max_per_category=config.MAX_ARTICLES_PER_CATEGORY,
            )

            # Step 4: Store digest items
            # Clear old items if re-running
            db.query(DigestItem).filter(DigestItem.digest_id == digest.id).delete()

            rank_counters: dict[str, int] = {}
            for item in processed:
                cat = item.category
                rank_counters[cat] = rank_counters.get(cat, 0) + 1

                article = url_map.get(item.url)
                if not article:
                    continue

                digest_item = DigestItem(
                    digest_id=digest.id,
                    article_id=article.id,
                    category=cat,
                    importance=item.importance,
                    summary=item.summary,
                    rank=rank_counters[cat],
                )
                db.add(digest_item)

            # Step 5: Finalize digest
            digest.executive_summary = exec_summary
            digest.status = "complete"
            digest.articles_processed = len(all_articles)

            print(f"[runner] Digest complete: {len(processed)} items across {len(rank_counters)} categories")
            return digest

        except Exception as e:
            digest.status = "error"
            digest.error_message = str(e)
            print(f"[runner] ERROR: {e}")
            raise
