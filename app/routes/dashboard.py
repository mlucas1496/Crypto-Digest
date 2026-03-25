from datetime import date, datetime
from flask import Blueprint, render_template, abort, request
from app.database import get_db
from app.models import Digest, DigestItem, Article

bp = Blueprint("dashboard", __name__)

CATEGORIES = [
    ("ma", "M&A", "blue"),
    ("regulatory", "Regulatory", "purple"),
    ("trends", "Market Trends", "green"),
    ("headlines", "Major Headlines", "orange"),
]


@bp.route("/")
def index():
    with get_db() as db:
        digest = (
            db.query(Digest)
            .filter(Digest.status == "complete")
            .order_by(Digest.date.desc())
            .first()
        )
        recent_digests = (
            db.query(Digest)
            .filter(Digest.status == "complete")
            .order_by(Digest.date.desc())
            .limit(10)
            .all()
        )
        if digest:
            # Eagerly load items + articles
            _ = [(item.article, item.category) for item in digest.items]

        return render_template(
            "index.html",
            digest=digest,
            categories=CATEGORIES,
            recent_digests=recent_digests,
            today=date.today(),
        )


@bp.route("/digest/<string:date_str>")
def digest_by_date(date_str: str):
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        abort(400, "Invalid date format. Use YYYY-MM-DD.")

    with get_db() as db:
        digest = (
            db.query(Digest)
            .filter(Digest.date == target, Digest.status == "complete")
            .first()
        )
        if not digest:
            abort(404, f"No digest found for {date_str}")

        _ = [(item.article, item.category) for item in digest.items]

        recent_digests = (
            db.query(Digest)
            .filter(Digest.status == "complete")
            .order_by(Digest.date.desc())
            .limit(10)
            .all()
        )

        return render_template(
            "index.html",
            digest=digest,
            categories=CATEGORIES,
            recent_digests=recent_digests,
            today=date.today(),
        )


@bp.route("/history")
def history():
    with get_db() as db:
        digests = (
            db.query(Digest)
            .order_by(Digest.date.desc())
            .all()
        )
        return render_template("history.html", digests=digests, today=date.today())


@bp.route("/articles")
def articles():
    cat_filter = request.args.get("category", "all")
    if cat_filter not in ("all", "ma", "regulatory", "trends", "headlines"):
        cat_filter = "all"

    with get_db() as db:
        q = (
            db.query(DigestItem)
            .join(DigestItem.digest)
            .join(DigestItem.article)
            .filter(Digest.status == "complete")
        )
        if cat_filter != "all":
            q = q.filter(DigestItem.category == cat_filter)
        q = q.order_by(Digest.date.desc(), DigestItem.importance.desc())
        items = q.all()

        # Eagerly load relationships
        _ = [(i.article, i.digest.date) for i in items]

        # Count per category for badges
        counts = {}
        for cat_key, _, _ in CATEGORIES:
            counts[cat_key] = (
                db.query(DigestItem)
                .join(DigestItem.digest)
                .filter(Digest.status == "complete", DigestItem.category == cat_key)
                .count()
            )
        counts["all"] = sum(counts.values())

        recent_digests = (
            db.query(Digest)
            .filter(Digest.status == "complete")
            .order_by(Digest.date.desc())
            .limit(10)
            .all()
        )

        return render_template(
            "articles.html",
            items=items,
            active_cat=cat_filter,
            categories=CATEGORIES,
            counts=counts,
            recent_digests=recent_digests,
            today=date.today(),
        )
