#!/usr/bin/env python3
"""
Entry point for Crypto Digest.

Usage:
  python run.py              # Start Flask + daily scheduler
  python run.py --once       # Run digest once now and exit
"""
import sys
import signal
from app import create_app
from app.config import config


def start_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from zoneinfo import ZoneInfo
    from datetime import date, datetime, timezone

    tz = ZoneInfo(config.DIGEST_TIMEZONE)
    scheduler = BackgroundScheduler(timezone=tz)

    def job():
        with app.app_context():
            from app.digest.runner import run_digest
            run_digest()

    scheduler.add_job(
        job,
        CronTrigger(hour=config.DIGEST_HOUR, minute=config.DIGEST_MINUTE, timezone=tz),
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()
    print(
        f"[scheduler] Daily digest scheduled at "
        f"{config.DIGEST_HOUR:02d}:{config.DIGEST_MINUTE:02d} {config.DIGEST_TIMEZONE}"
    )

    # Catch-up: if it's past the scheduled time and today's digest hasn't run, run it now
    def _catch_up():
        from app.database import get_db
        from app.models import Digest
        now_local = datetime.now(tz)
        scheduled_passed = (now_local.hour, now_local.minute) >= (config.DIGEST_HOUR, config.DIGEST_MINUTE)
        if not scheduled_passed:
            return
        with app.app_context():
            with get_db() as db:
                existing = db.query(Digest).filter(Digest.date == date.today()).first()
                if existing and existing.status == "complete" and existing.articles_processed > 0:
                    return  # already ran successfully today
        print("[scheduler] Catch-up: today's digest was missed — running now")
        job()

    import threading
    threading.Thread(target=_catch_up, daemon=True).start()

    def shutdown(sig, frame):
        print("\n[scheduler] Shutting down...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    return scheduler


if __name__ == "__main__":
    run_once = "--once" in sys.argv

    app = create_app()

    if run_once:
        with app.app_context():
            print("[run] Running digest once...")
            from app.digest.runner import run_digest
            run_digest()
            print("[run] Done.")
        sys.exit(0)

    # Normal mode: start scheduler + Flask
    scheduler = start_scheduler(app)

    print(f"[run] Starting server on http://localhost:{config.FLASK_PORT}")
    app.run(
        host="0.0.0.0",
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
        use_reloader=False,  # Reloader conflicts with APScheduler
    )
