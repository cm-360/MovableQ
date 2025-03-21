from quart import Blueprint
from quart import current_app
from quart import request

from app.api.utils import api_error
from app.api.utils import api_exception
from app.api.utils import register_error_handlers
from app.db.queries.jobs import assign_job
from app.db.queries.jobs import create_job
from app.db.queries.jobs import get_job_by_id
from app.db.queries.jobs import get_jobs_of_types
from app.db.queries.jobs import get_queued_jobs
from app.db.queries.workers import get_worker

bp = Blueprint("API: Jobs", __name__)
register_error_handlers(bp)


@bp.get("/list")
async def list_jobs():
    job_types = request.args.get("types")
    job_types = job_types.split(",") if job_types else []

    with current_app.db.bind.Session() as session:
        jobs = get_jobs_of_types(session, job_types)

        return [dict(j) for j in jobs]


@bp.post("/submit")
async def submit_job():
    job_data = await request.get_json()

    # Create job object in database
    try:
        with current_app.db.bind.Session() as session, session.begin():
            job = create_job(session, job_data)

            return dict(job)
    except Exception as e:
        return api_exception(e, 400)


@bp.post("/request")
async def request_job():
    worker_data = await request.get_json()

    with current_app.db.bind.Session() as session:
        worker = get_worker(session, worker_data)

        # Request Parameters

        # Set job type filter from query parameter or defaults
        allowed_job_types = worker.allowed_job_types()
        job_types = request.args.get("types")
        job_types = job_types.split(",") if job_types else allowed_job_types

        # Restrict illegal job requests
        illegal_job_types = [j for j in job_types if j not in allowed_job_types]
        if illegal_job_types:
            illegal_joined = ", ".join(illegal_job_types)
            return api_error(f"Illegal job type(s) requested: {illegal_joined}", 400)

        # Set max job count from query parameter or default
        max_jobs = request.args.get("max")
        try:
            max_jobs = int(max_jobs) if max_jobs is not None else 1
        except ValueError:
            return api_error(f"Invalid max job count: {max_jobs}", 400)

        # Job Assignment

        jobs = get_queued_jobs(session, job_types)

        # Assign jobs from queue
        assigned_count = min(max_jobs, len(jobs))
        assigned_jobs = jobs[:assigned_count]
        for job in assigned_jobs:
            assign_job(session, job, worker)

        return [dict(j) for j in assigned_jobs]


@bp.get("/<job_id>/details")
async def get_job_details(job_id: str):
    with current_app.db.bind.Session() as session:
        job = get_job_by_id(session, job_id)

        if job is None:
            return api_error(f"Unknown job ID: {job_id}", 404)

        return dict(job)


@bp.get("/<job_id>/release")
async def release_job(job_id: str):
    pass
