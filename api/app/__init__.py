from hypercorn.middleware import ProxyFixMiddleware
from quart import Quart

from app.api.jobs import bp as api_jobs_bp
from app.api.workers import bp as api_workers_bp
from app.db import create_db


def create_app(db_echo: bool = False) -> Quart:
    app = Quart(__name__)
    app.asgi_app = ProxyFixMiddleware(app.asgi_app, mode="legacy", trusted_hops=1)

    app.register_blueprint(api_jobs_bp, url_prefix="/api/jobs")
    app.register_blueprint(api_workers_bp, url_prefix="/api/workers")

    app.db = create_db("sqlite:///:memory:", echo=db_echo)
    app.db.init_app(app)
    app.db.create_all()

    return app
