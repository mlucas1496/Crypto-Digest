from flask import Flask
from app.config import config
from app.database import init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY

    # Initialize DB tables
    init_db()

    # Register blueprints
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.api import bp as api_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)

    return app
