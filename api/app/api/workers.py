from datetime import datetime
from datetime import timezone

from quart import Blueprint
from quart import current_app
from quart import request

from app.api.utils import api_error
from app.api.utils import register_error_handlers
from app.db.queries.workers import create_or_update_worker
from app.db.queries.workers import get_all_workers
from app.db.queries.workers import get_worker_by_id

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
    # Unpack worker information from request body
    try:
        worker_data = await request.get_json()
        worker_type = worker_data["type"]
    except KeyError:
        return api_error("Missing required parameter", 400)

    # Set worker parameters
    worker_data = {
        **worker_data,
        "last_ip": request.remote_addr,
        "updated_at": datetime.now(timezone.utc),
    }

    # Create/update worker in database
    with current_app.db.bind.Session() as session, session.begin():
        worker = create_or_update_worker(session, worker_type, worker_data)

        return dict(worker)


@bp.get("/<worker_id>/details")
async def get_worker_details(worker_id: str):
    with current_app.db.bind.Session() as session:
        worker = get_worker_by_id(session, worker_id)

        if worker is None:
            return api_error(f"Unknown worker ID: {worker_id}", 404)

        return dict(worker)
