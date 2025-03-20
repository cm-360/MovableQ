from quart import Blueprint
from quart import current_app
from quart import request

from app.api.utils import api_exception
from app.api.utils import register_error_handlers
from app.db.queries.workers import create_or_update_worker
from app.db.queries.workers import get_workers_of_types

bp = Blueprint("API: Workers", __name__)
register_error_handlers(bp)


@bp.get("/list")
async def list_workers():
    worker_types = request.args.get("types")
    worker_types = worker_types.split(",") if worker_types else []

    with current_app.db.bind.Session() as session:
        workers = get_workers_of_types(session, worker_types)

        return [dict(w) for w in workers]


@bp.post("/register")
async def register_worker():
    worker_data = await request.get_json()
    worker_data["last_ip"] = request.remote_addr

    # Create/update worker in database
    with current_app.db.bind.Session() as session, session.begin():
        try:
            worker = create_or_update_worker(session, worker_data)
        except KeyError as e:
            return api_exception(e, 400)

        return dict(worker)
