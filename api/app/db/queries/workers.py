from sqlalchemy import select

from ..models.workers import Worker
from ..models.workers import MinerWorker
from ..models.workers import FriendbotWorker


def get_all_workers(session):
    workers = [
        *session.scalars(select(MinerWorker)).all(),
        *session.scalars(select(FriendbotWorker)).all(),
    ]

    return workers


def get_worker_by_id(session, worker_id: str) -> Worker:
    workers = [
        *get_miner_workers(worker_id),
        *get_friendbot_workers(worker_id),
    ]

    return workers


def get_miner_workers(session, client_id: str) -> MinerWorker:
    statement = select(MinerWorker).filter(MinerWorker.client_id == client_id)
    return session.scalars(statement).all()


def get_friendbot_workers(session, friend_code: str) -> FriendbotWorker:
    statement = select(FriendbotWorker).filter(
        FriendbotWorker.friend_code == friend_code
    )
    return session.scalars(statement).all()
