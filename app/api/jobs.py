from datetime import datetime
from datetime import timezone

from quart import request

from sqlalchemy import select

from . import bp
from .utils import api_error
from ..db import db
from ..db.models.jobs import FcLfcsJob
from ..db.models.jobs import MiiLfcsJob
from ..db.models.jobs import MsedJob
from ..db.models.jobs import JobStatus
from ..db.utils import from_dict


@bp.get("/jobs")
async def list_jobs():
    with db.bind.Session() as session:
        jobs = [
            *session.scalars(select(FcLfcsJob)).all(),
            *session.scalars(select(MiiLfcsJob)).all(),
            *session.scalars(select(MsedJob)).all(),
        ]

        return [dict(j) for j in jobs]

@bp.post("/jobs")
async def submit_job():
    # Unpack job information from request body
    data = await request.get_json()
    job_type = data["type"]
    job_data = data["job"]

    # Set default job parameters
    now = datetime.now(timezone.utc)
    job_data = {
        "created_at": now,
        "updated_at": now,
        "status": JobStatus.submitted,
        **job_data
    }

    # Construct appropriate job object
    if "msed" == job_type:
        job = from_dict(MsedJob, job_data)
    elif "fc-lfcs" == job_type:
        job = from_dict(FcLfcsJob, job_data)
    elif "mii-lfcs" == job_type:
        job = from_dict(MiiLfcsJob, job_data)
    else:
        return api_error(f"Invalid job type: {job_type}", 400)

    # Add job to database
    with db.bind.Session() as session:
        with session.begin():
            session.add(job)
            session.flush()

    return dict(job)
