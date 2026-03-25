import threading
from datetime import date
from flask import Blueprint, jsonify, request
from app.database import get_db
from app.models import Digest

bp = Blueprint("api", __name__, url_prefix="/api")

_running = False


def _run_digest_bg(force: bool = False):
    global _running
    try:
        from app.digest.runner import run_digest
        run_digest(force=force)
    except Exception as e:
        print(f"[api] background digest error: {e}")
    finally:
        _running = False


@bp.route("/run-now", methods=["POST"])
def run_now():
    global _running
    if _running:
        return jsonify({"status": "already_running", "message": "A digest is already in progress."}), 409
    force = request.args.get("force", "").lower() in ("1", "true", "yes")
    _running = True
    t = threading.Thread(target=_run_digest_bg, args=(force,), daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Digest started in background. Refresh in ~2 minutes."})


@bp.route("/status")
def status():
    global _running
    with get_db() as db:
        latest = (
            db.query(Digest)
            .order_by(Digest.date.desc(), Digest.created_at.desc())
            .first()
        )
        return jsonify({
            "running": _running,
            "latest_digest": {
                "date": str(latest.date) if latest else None,
                "status": latest.status if latest else None,
                "articles_processed": latest.articles_processed if latest else 0,
                "created_at": latest.created_at.isoformat() if latest else None,
            } if latest else None,
        })
