from datetime import datetime
from datetime import timezone

from sqlalchemy import select
from sqlalchemy import update

from app.db.models.workers import Worker

allowed_update_columns = ["name", "last_ip", "version"]


def get_all_workers(session) -> list[Worker]:
    """Retrieves all workers from the database.

    Args:
        session (Session): The database session object.

    Returns:
        list[Worker]: A list of all workers.
    """
    workers = []

    for worker_class in Worker.get_all_subclasses():
        workers.extend(session.scalars(select(worker_class)))

    return workers


def get_workers_of_types(session, worker_types: list[str] = []) -> list[Worker]:
    """Retrieves all workers of the specified types from the database.

    Args:
        session (Session): The database session object.
        worker_types (list[str]): The types of workers to retrieve.

    Returns:
        list[Worker]: A list of matching workers.
    """
    if not worker_types:
        return get_all_workers(session)

    workers = []

    for worker_type in worker_types:
        worker_class = Worker.get_subclass(worker_type)
        workers.extend(session.scalars(select(worker_class)))

    return workers


def get_worker(session, worker_data: dict) -> Worker | None:
    """Retrieves a specific worker from the database.

    Args:
        session (Session): The database session object.
        worker_data (dict): A dictionary containing the worker type to retrieve
            and the attribute(s) of their unique ID.

    Returns:
        Worker | None: The retrieved worker, or None if not found.
    """
    worker_type = worker_data["type"]
    worker_class = Worker.get_subclass(worker_type)

    worker = session.scalars(
        select(worker_class).where(worker_class.primary_key_matches(worker_data))
    ).first()

    return worker


def create_or_update_worker(session, worker_data: dict) -> Worker:
    """Creates or updates a worker in the database.

    Args:
        session (Session): The database session object.
        worker_type (str): The type of worker.
        worker_data (dict): Dictionary of the worker's data.

    Returns:
        Worker: The newly-created or updated worker object.

    Raises:
        ValueError: If an invalid worker type is provided.
    """
    worker = get_worker(session, worker_data)

    if worker is None:
        return create_worker(session, worker_data)
    else:
        return update_worker(session, worker, worker_data)


def create_worker(session, worker_data: dict) -> Worker:
    """Creates a new worker in the database.

    Args:
        session (Session): The database session object.
        worker_data (dict): Dictionary of data for the new worker.

    Returns:
        Worker: The newly-created worker object.
    """
    # Default worker data
    worker_data["updated_at"] = datetime.now(timezone.utc)

    # Create worker object
    worker_type = worker_data["type"]
    worker_class = Worker.get_subclass(worker_type)
    worker = worker_class.from_dict(worker_data)

    session.add(worker)

    return worker


def update_worker(session, worker: Worker, worker_data: dict) -> Worker:
    """Updates an existing worker in the database.

    Args:
        session (Session): The database session object.
        worker_data (dict): A dictionary of data to update the worker with and
            their unique ID.

    Returns:
        Worker: The updated worker object.
    """
    # Filter input columns
    update_data = {k: v for k, v in worker_data.items() if k in allowed_update_columns}
    update_data["updated_at"] = datetime.now(timezone.utc)

    # Update worker in database
    session.execute(
        update(type(worker))
        .where(worker.primary_key_matches(worker_data))
        .values(update_data)
    )
    session.refresh(worker)

    return worker
