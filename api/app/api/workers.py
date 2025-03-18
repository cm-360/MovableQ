from quart import current_app
from quart import request

from . import bp
from .utils import api_error
from ..db.queries.workers import get_all_workers
from ..db.queries.workers import get_worker_by_id


@bp.get("/workers/list")
async def list_workers():
    worker_type = request.args.get("type")

    with current_app.db.bind.Session() as session:
        workers = get_all_workers(session)

        if worker_type:
            workers = [w for w in workers if w.worker_type() == worker_type]

        return [dict(w) for w in workers]


@bp.get("/workers/<worker_id>/details")
async def get_worker_details(worker_id: str):
    with current_app.db.bind.Session() as session:
        worker = get_worker_by_id(session, worker_id)

        if worker is None:
            return api_error(f"Unknown worker ID: {worker_id}", 404)

        return dict(worker)
