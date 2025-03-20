from datetime import datetime
from datetime import timezone

from sqlalchemy import select
from sqlalchemy import update

from app.db.models.workers import FriendbotWorker
from app.db.models.workers import MinerWorker
from app.db.models.workers import Worker
from app.db.utils import from_dict
from app.utils.validators import is_valid_friend_code

allowed_update_columns = ["name", "last_ip", "version"]


def create_or_update_worker(session, worker_type: str, worker_data: dict) -> Worker:
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
    if "miner" == worker_type:
        # Check for existing worker
        client_id = worker_data["client_id"]
        worker = get_miner_worker(session, client_id)

        if worker is None:
            return create_miner_worker(session, worker_data)

        # Update existing worker
        worker = update_miner_worker(session, client_id, worker_data)
    elif "friendbot" == worker_type:
        # Check for existing worker
        friend_code = worker_data["friend_code"]
        worker = get_friendbot_worker(session, friend_code)

        if worker is None:
            return create_friendbot_worker(session, worker_data)

        # Update existing worker

    else:
        raise ValueError(f"Invalid worker type: {worker_type}")

    return worker


def create_miner_worker(session, worker_data: dict) -> MinerWorker:
    """Creates a new miner worker in the database.

    Args:
        session (Session): The database session object.
        worker_data (dict): Dictionary of data for the new worker.

    Returns:
        MinerWorker: The newly-created miner worker object.
    """
    worker = from_dict(MinerWorker, worker_data)

    session.add(worker)
    session.flush()

    return worker


def create_friendbot_worker(session, worker_data: dict) -> FriendbotWorker:
    """Creates a new friendbot worker in the database.

    Args:
        session (Session): The database session object.
        worker_data (dict): Dictionary of data for the new worker.

    Returns:
        FriendbotWorker: The newly-created friendbot worker object.
    """
    worker = from_dict(FriendbotWorker, worker_data)

    session.add(worker)
    session.flush()

    return worker


def update_miner_worker(session, client_id: str, worker_data: dict) -> MinerWorker:
    """Updates an existing miner worker in the database.

    Args:
        session (Session): The database session object.
        client_id (str): The miner worker's unique client ID.
        worker_data (dict): Dictionary of data to update the worker with.

    Returns:
        MinerWorker: The updated miner worker object.
    """
    worker_data = {k: v for k, v in worker_data.items() if k in allowed_update_columns}
    worker_data["updated_at"] = datetime.now(timezone.utc)

    # Update worker in DB
    worker = session.execute(
        update(MinerWorker)
        .where(MinerWorker.client_id == client_id)
        .values(worker_data)
    )
    session.flush()

    # Get updated worker object
    worker = get_miner_worker(session, client_id)

    return worker


def update_friendbot_worker(
    session, friend_code: str, worker_data: dict
) -> FriendbotWorker:
    """Updates an existing friendbot worker in the database.

    Args:
        session (Session): The database session object.
        friend_code (str): The friendbot worker's unique friend code.
        worker_data (dict): Dictionary of data to update the worker with.

    Returns:
        MinerWorker: The updated friendbot worker object.

    Raises:
        ValueError: If the provided friend code is invalid.
    """
    if not is_valid_friend_code(friend_code):
        raise ValueError("Invalid friend code")

    worker_data = {k: v for k, v in worker_data.items() if k in allowed_update_columns}
    worker_data["updated_at"] = datetime.now(timezone.utc)

    # Update worker in DB
    worker = session.execute(
        update(FriendbotWorker)
        .where(FriendbotWorker.friend_code == friend_code)
        .values(worker_data)
    )
    session.flush()

    # Get updated worker object
    worker = get_friendbot_worker(session, friend_code)

    return worker


def get_all_workers(session):
    """Retrieves all workers from the database.

    Args:
        session (Session): The database session object.

    Returns:
        list[Worker]: A list of all workers.
    """
    workers = [
        *get_miner_workers(session),
        *get_friendbot_workers(session),
    ]

    return workers


def get_miner_workers(session) -> list[MinerWorker]:
    """Retrieves all miner workers from the database.

    Args:
        session (Session): The database session object.

    Returns:
        list[MinerWorker]: A list of miner worker objects.
    """
    return session.scalars(select(MinerWorker)).all()


def get_friendbot_workers(session) -> list[FriendbotWorker]:
    """Retrieves all friendbot workers from the database.

    Args:
        session (Session): The database session object.

    Returns:
        list[FriendbotWorker]: A list of friendbot worker objects.
    """
    return session.scalars(select(FriendbotWorker)).all()


def get_miner_worker(session, client_id: str) -> MinerWorker | None:
    """Retrieves a specific miner worker by their client ID.

    Args:
        session (Session): The database session object.
        client_id (str): The miner worker's unique client ID.

    Returns:
        MinerWorker | None: The retrieved miner worker object, or None if not
            found.
    """
    statement = select(MinerWorker).filter(MinerWorker.client_id == client_id)
    return session.scalars(statement).first()


def get_friendbot_worker(session, friend_code: str) -> FriendbotWorker | None:
    """Retrieves a specific friendbot worker by their friend code.

    Args:
        session (Session): The database session object.
        client_id (str): The friendbot worker's unique friend code.

    Returns:
        MinerWorker | None: The retrieved friendbot worker object, or None if
            not found.

    Raises:
        ValueError: If the provided friend code is invalid.
    """
    if not is_valid_friend_code(friend_code):
        raise ValueError("Invalid friend code")

    statement = select(FriendbotWorker).filter(
        FriendbotWorker.friend_code == friend_code
    )
    return session.scalars(statement).first()
