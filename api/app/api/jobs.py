from datetime import datetime
from datetime import timezone

from quart import request

from . import bp
from .utils import api_error
from .utils import api_exception
from ..db import db
from ..db.models.jobs import FcLfcsJob
from ..db.models.jobs import MiiLfcsJob
from ..db.models.jobs import MsedJob
from ..db.models.jobs import JobStatus
from ..db.queries.jobs import get_all_jobs
from ..db.queries.jobs import get_job_by_id
from ..db.utils import from_dict


@bp.get("/jobs/list")
async def list_jobs():
    with db.bind.Session() as session:
        jobs = get_all_jobs(session)
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

    # Set default job parameters
    now = datetime.now(timezone.utc)
    job_data = {
        "created_at": now,
        "updated_at": now,
        "status": JobStatus.submitted,
        **job_data,
    }

    # Construct appropriate job object
    try:
        if "msed" == job_type:
            job = from_dict(MsedJob, job_data)
        elif "fc-lfcs" == job_type:
            job = from_dict(FcLfcsJob, job_data)
        elif "mii-lfcs" == job_type:
            job = from_dict(MiiLfcsJob, job_data)
        else:
            return api_error(f"Invalid job type: {job_type}", 400)
    except ValueError as e:
        return api_exception(e, 400)

    # Add job to database
    with db.bind.Session() as session, session.begin():
        session.add(job)
        session.flush()

    return dict(job)


@bp.get("/jobs/<job_id>/details")
async def get_job_details(job_id: str):
    with db.bind.Session() as session:
        job = get_job_by_id(session, job_id)

        if job is None:
            return api_error(f"Unknown job ID: {job_id}", 404)

        return dict(job)


@bp.get("/jobs/<job_id>/release")
async def release_job(job_id: str):
    pass
