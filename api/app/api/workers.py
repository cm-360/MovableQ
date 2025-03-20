from quart import Blueprint
from quart import current_app
from quart import request

from app.api.utils import api_exception
from app.api.utils import register_error_handlers
from app.db.queries.workers import create_or_update_worker
from app.db.queries.workers import get_all_workers

bp = Blueprint("API: Workers", __name__)
register_error_handlers(bp)


@bp.get("/list")
async def list_workers():
    worker_type = request.args.get("type")

    with current_app.db.bind.Session() as session:
        workers = get_all_workers(session)

        if worker_type:
            workers = [w for w in workers if w.worker_type() == worker_type]

        return [dict(w) for w in workers]


@bp.post("/register")
async def register_worker():
    worker_data = await request.get_json()

    # Set worker parameters
    worker_data = {
        **worker_data,
        "last_ip": request.remote_addr,
    }

    # Create/update worker in database
    with current_app.db.bind.Session() as session, session.begin():
        try:
            worker = create_or_update_worker(session, worker_data)
        except KeyError as e:
            return api_exception(e, 400)

        return dict(worker)
