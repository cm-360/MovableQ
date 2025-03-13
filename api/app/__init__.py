from quart import Quart
from hypercorn.middleware import ProxyFixMiddleware

from .api import bp as api_bp
from .ui import bp as ui_bp
from .db import db


def create_app() -> Quart:
    app = Quart(__name__)
    app.asgi_app = ProxyFixMiddleware(app.asgi_app, mode="legacy", trusted_hops=1)

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ui_bp)

    db.init_app(app)
    db.create_all()

    return app
