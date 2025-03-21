from datetime import datetime
from datetime import timezone

from sqlalchemy import inspect
from sqlalchemy import select
from sqlalchemy import update

from app.db.models.jobs import FcLfcsJob
from app.db.models.jobs import Job
from app.db.models.jobs import JobStatus
from app.db.models.jobs import MiiLfcsJob
from app.db.models.jobs import MsedJob
from app.db.models.workers import Worker
from app.utils.validators import is_valid_friend_code
from app.utils.validators import is_valid_id0
from app.utils.validators import is_valid_system_id


def get_all_jobs(session) -> list[Job]:
    """Retrieves all jobs from the database.

    Args:
        session (Session): The database session object.

    Returns:
        list[Job]: A list of all jobs.
    """
    jobs = []

    for job_class in Job.get_all_subclasses():
        jobs.extend(session.scalars(select(job_class)))

    return jobs


def get_jobs_of_types(session, job_types: list[str] = []) -> list[Job]:
    """Retrieves all jobs of the specified types from the database.

    Args:
        session (Session): The database session object.
        job_types (list[str]): The types of jobs to retrieve.

    Returns:
        list[Job]: A list of matching jobs.
    """
    if not job_types:
        return get_all_jobs(session)

    jobs = []

    for job_type in job_types:
        job_class = Job.get_subclass(job_type)
        jobs.extend(session.scalars(select(job_class)))

    return jobs


def get_job_by_id(session, job_id: str) -> Job | None:
    if is_valid_friend_code(job_id):
        return get_fc_lfcs_job(session, job_id)
    elif is_valid_system_id(job_id):
        return get_mii_lfcs_job(session, job_id)
    elif is_valid_id0(job_id):
        return get_msed_job(session, job_id)
    else:
        raise ValueError(f"Invalid job ID: {job_id}")


def get_fc_lfcs_job(session, friend_code: str) -> FcLfcsJob | None:
    if not is_valid_friend_code(friend_code):
        raise ValueError("Invalid friend code")

    statement = select(FcLfcsJob).filter(FcLfcsJob.friend_code == friend_code)
    return session.scalars(statement).first()


def get_mii_lfcs_job(session, system_id: str) -> MiiLfcsJob | None:
    if not is_valid_system_id(system_id):
        raise ValueError("Invalid system ID")

    statement = select(MiiLfcsJob).filter(MiiLfcsJob.system_id == system_id)
    return session.scalars(statement).first()


def get_msed_job(session, id0: str) -> MsedJob | None:
    if not is_valid_id0(id0):
        raise ValueError("Invalid ID0")

    statement = select(MsedJob).filter(MsedJob.id0 == id0)
    return session.scalars(statement).first()


def get_queued_jobs(session, job_types: list[str] = []) -> list[Job]:
    jobs = get_jobs_of_types(session, job_types)

    jobs = [j for j in jobs if JobStatus.queued == j.status]
    jobs.sort(key=lambda j: j.updated_at)

    return jobs


def create_job(session, job_data: dict) -> Job:
    job_type = job_data["type"]
    job_class = Job.get_subclass(job_type)

    now = datetime.now(timezone.utc)
    job_data = {
        **job_data,
        "created_at": now,
        "updated_at": now,
        "status": JobStatus.queued,
    }
    job = job_class.from_dict(job_data)

    session.add(job)
    session.flush()

    return job


def assign_job(session, job: Job, worker: Worker) -> Job | None:
    worker_id_attr = inspect(type(worker)).primary_key[0].name
    worker_id = getattr(worker, worker_id_attr)

    # TODO handle nonexistent jobs

    session.execute(
        update(type(job))
        .where(job.primary_key_matches(dict(job)))
        .values(assignee=worker_id)
    )

    job = session.scalars(
        select(type(job)).where(job.primary_key_matches(dict(job)))
    ).one()

    return job
