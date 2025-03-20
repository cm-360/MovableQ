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
    worker = from_dict(MinerWorker, worker_data)

    session.add(worker)
    session.flush()

    return worker


def create_friendbot_worker(session, worker_data: dict) -> FriendbotWorker:
    worker = from_dict(FriendbotWorker, worker_data)

    session.add(worker)
    session.flush()

    return worker


def update_miner_worker(session, client_id: str, worker_data: dict) -> MinerWorker:
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
    workers = [
        *get_miner_workers(session),
        *get_friendbot_workers(session),
    ]

    return workers


def get_miner_workers(session) -> list[MinerWorker]:
    return session.scalars(select(MinerWorker)).all()


def get_friendbot_workers(session) -> list[FriendbotWorker]:
    return session.scalars(select(FriendbotWorker)).all()


def get_miner_worker(session, client_id: str) -> MinerWorker | None:
    statement = select(MinerWorker).filter(MinerWorker.client_id == client_id)
    return session.scalars(statement).first()


def get_friendbot_worker(session, friend_code: str) -> FriendbotWorker | None:
    if not is_valid_friend_code(friend_code):
        raise ValueError("Invalid friend code")

    statement = select(FriendbotWorker).filter(
        FriendbotWorker.friend_code == friend_code
    )
    return session.scalars(statement).first()
