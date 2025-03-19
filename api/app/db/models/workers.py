from dataclasses import dataclass

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.models.base import Base
from app.db.utils import Serializable
from app.utils.strings import camel_to_kebab_case


@dataclass
class Worker(Serializable):
    """Common attributes shared between different worker types.

    Attributes:
        name (str): The name of the worker as reported by their client.
        last_ip (str): The last known IP address of this worker.
        version (str): The version identifier of this worker's software.
        updated_at (str): The timestamp of this worker's last update.
    """

    name: Mapped[str]
    last_ip: Mapped[str]
    version: Mapped[str]
    updated_at: Mapped[str] = mapped_column(DateTime)

    @classmethod
    def worker_type(cls) -> str:
        return camel_to_kebab_case(cls.__name__.removesuffix("Worker"))

    def __iter__(self):
        yield from super().__iter__()
        yield "updated_at", self.updated_at.isoformat()
        yield "type", self.worker_type()


@dataclass
class MinerWorker(Base, Worker):
    """A worker running the bfCL mining client script.

    These workers are capable of completing bruteforcing jobs.

    Attributes:
        client_id (str): The unique identifier for the miner as reported by
            their client.
    """

    __tablename__ = "miner_workers"

    client_id: Mapped[str] = mapped_column(primary_key=True)


@dataclass
class FriendbotWorker(Base, Worker):
    """A worker running the friendbot software.

    These workers are capable of obtaining LFCSes from friend requests.

    Attributes:
        friend_code (str): This worker's unique 12-digit friend code.

    Note:
        The friendbot software is available at
        https://github.com/bleck9999/friendbot.
    """

    __tablename__ = "friendbot_workers"

    friend_code: Mapped[str] = mapped_column(primary_key=True)
