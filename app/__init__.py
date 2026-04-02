from datetime import timezone, timedelta
from flask import Flask
from app.config import config
from app.database import init_db

_EASTERN = timezone(timedelta(hours=-4))  # EDT (UTC-4); winter: timedelta(hours=-5)


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY

    @app.template_filter("eastern")
    def eastern_filter(dt):
        if dt is None:
            return ""
        return dt.replace(tzinfo=timezone.utc).astimezone(_EASTERN).strftime("%b %-d · %-I:%M %p ET")

    # Initialize DB tables
    init_db()

    # Register blueprints
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.api import bp as api_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)

    return app
