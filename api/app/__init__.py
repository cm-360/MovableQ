from quart import Quart
from hypercorn.middleware import ProxyFixMiddleware

from .api import bp as api_bp
from .db import create_db


def create_app(db_echo: bool = False) -> Quart:
    app = Quart(__name__)
    app.asgi_app = ProxyFixMiddleware(app.asgi_app, mode="legacy", trusted_hops=1)

    app.register_blueprint(api_bp, url_prefix="/api")

    app.db = create_db("sqlite:///:memory:", echo=db_echo)
    app.db.init_app(app)
    app.db.create_all()

    return app
