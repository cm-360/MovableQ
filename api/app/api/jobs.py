from quart import current_app
from quart import request

from app.api.utils import api_error
from app.api.utils import api_exception
from app.db.queries.jobs import create_job
from app.db.queries.jobs import get_all_jobs
from app.db.queries.jobs import get_job_by_id
from app.db.queries.jobs import get_queued_jobs

from . import bp


@bp.get("/jobs/list")
async def list_jobs():
    job_type = request.args.get("type")

    with current_app.db.bind.Session() as session:
        jobs = get_all_jobs(session)

        if job_type:
            jobs = [j for j in jobs if j.job_type() == job_type]

        return [dict(j) for j in jobs]


@bp.post("/jobs/submit")
async def submit_job():
    # Unpack job information from request body
    try:
        data = await request.get_json()
        job_type = data["type"]
        job_data = data["job"]
    except KeyError:
        return api_error("Missing required parameter", 400)

    # Create job object in database
    try:
        with current_app.db.bind.Session() as session, session.begin():
            job = create_job(session, job_type, job_data)

            return dict(job)
    except ValueError as e:
        return api_exception(e, 400)


@bp.post("/jobs/request")
async def request_job():
    job_types = request.args.get("types")
    job_types = job_types.split(",") if job_types else []

    with current_app.db.bind.Session() as session:
        jobs = get_queued_jobs(session, job_types)

        job = jobs[0]

        return dict(job)


@bp.get("/jobs/<job_id>/details")
async def get_job_details(job_id: str):
    with current_app.db.bind.Session() as session:
        job = get_job_by_id(session, job_id)

        if job is None:
            return api_error(f"Unknown job ID: {job_id}", 404)

        return dict(job)


@bp.get("/jobs/<job_id>/release")
async def release_job(job_id: str):
    pass
