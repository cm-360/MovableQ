from datetime import datetime
from datetime import timezone

from sqlalchemy import select

from ..models.jobs import Job
from ..models.jobs import JobStatus
from ..models.jobs import FcLfcsJob
from ..models.jobs import MiiLfcsJob
from ..models.jobs import MsedJob
from ..utils import from_dict
from ...utils.validators import is_valid_friend_code
from ...utils.validators import is_valid_id0
from ...utils.validators import is_valid_system_id


def create_job(session, job_type: str, job_data: dict) -> Job:
    # Set default job parameters
    now = datetime.now(timezone.utc)
    job_data = {
        **job_data,
        "created_at": now,
        "updated_at": now,
        "status": JobStatus.submitted,
    }

    # Construct appropriate job object
    if "msed" == job_type:
        job = from_dict(MsedJob, job_data)

        if job.lfcs is not None:
            job.status = JobStatus.queued
    elif "fc-lfcs" == job_type:
        job = from_dict(FcLfcsJob, job_data)
    elif "mii-lfcs" == job_type:
        job = from_dict(MiiLfcsJob, job_data)
    else:
        raise ValueError(f"Invalid job type: {job_type}")

    session.add(job)
    session.flush()

    return job


def get_all_jobs(session) -> list[Job]:
    jobs = [
        *session.scalars(select(FcLfcsJob)).all(),
        *session.scalars(select(MiiLfcsJob)).all(),
        *session.scalars(select(MsedJob)).all(),
    ]

    return jobs


def get_jobs_of_types(session, job_types: list[str] = []) -> list[Job]:
    jobs = get_all_jobs(session)

    if job_types:
        jobs = [j for j in jobs if j.job_type() in job_types]

    return jobs


def get_job_by_id(session, job_id: str) -> Job | None:
    if is_valid_friend_code():
        return get_fc_lfcs_job(job_id)
    elif is_valid_system_id(job_id):
        return get_mii_lfcs_job(job_id)
    elif is_valid_id0(job_id):
        return get_msed_job(job_id)
    else:
        raise ValueError("Invalid job ID")


def get_fc_lfcs_job(session, friend_code: str) -> FcLfcsJob | None:
    statement = select(FcLfcsJob).filter(FcLfcsJob.friend_code == friend_code)
    return session.scalars(statement).first()


def get_mii_lfcs_job(session, system_id: str) -> MiiLfcsJob | None:
    statement = select(MiiLfcsJob).filter(MiiLfcsJob.system_id == system_id)
    return session.scalars(statement).first()


def get_msed_job(session, id0: str) -> MsedJob | None:
    statement = select(MsedJob).filter(MsedJob.id0 == id0)
    return session.scalars(statement).first()


def get_queued_jobs(session, job_types: list[str] = []) -> list[Job]:
    jobs = get_jobs_of_types(session, job_types)

    jobs = [j for j in jobs if JobStatus.queued == j.status]
    jobs.sort(key=lambda j: j.updated_at)

    return jobs
