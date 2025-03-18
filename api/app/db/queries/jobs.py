from sqlalchemy import select

from ..models.jobs import JobStatus
from ..models.jobs import Job
from ..models.jobs import FcLfcsJob
from ..models.jobs import MiiLfcsJob
from ..models.jobs import MsedJob


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


def get_job_by_id(session, job_id: str) -> Job:
    jobs = [
        *get_fc_lfcs_jobs(job_id),
        *get_mii_lfcs_jobs(job_id),
        *get_msed_jobs(job_id),
    ]

    return jobs


def get_fc_lfcs_jobs(session, friend_code: str) -> FcLfcsJob:
    statement = select(FcLfcsJob).filter(FcLfcsJob.friend_code == friend_code)
    return session.scalars(statement).all()


def get_mii_lfcs_jobs(session, system_id: str) -> MiiLfcsJob:
    statement = select(MiiLfcsJob).filter(MiiLfcsJob.system_id == system_id)
    return session.scalars(statement).all()


def get_msed_jobs(session, id0: str) -> MsedJob:
    statement = select(MsedJob).filter(MsedJob.id0 == id0)
    return session.scalars(statement).all()


def get_queued_jobs(session, job_types: list[str] = []) -> list[Job]:
    jobs = get_jobs_of_types(session, job_types)

    jobs = [j for j in jobs if JobStatus.queued == j.status]
    jobs.sort(key=lambda j: j.created_at)

    return jobs
