from quart import request

from . import bp
from .utils import api_error
from ..db import db
from ..db.queries.workers import get_all_workers
from ..db.queries.workers import get_miner_workers
from ..db.queries.workers import get_friendbot_workers
from ..db.queries.workers import get_worker_by_id


@bp.get("/workers/list")
async def list_workers():
    worker_type = request.args.get("type")

    with db.bind.Session() as session:
        if "miner" == worker_type:
            workers = get_miner_workers(session)
        elif "friendbot" == worker_type:
            workers = get_friendbot_workers(session)
        elif "" == worker_type:
            # No filter provided, get all workers
            workers = get_all_workers(session)
        else:
            # Unrecognized worker type
            return []

        return [dict(w) for w in workers]


@bp.get("/workers/<worker_id>/details")
async def get_worker_details(worker_id: str):
    with db.bind.Session() as session:
        worker = get_worker_by_id(session, worker_id)

        if worker is None:
            return api_error(f"Unknown worker ID: {worker_id}", 404)

        return dict(worker)
