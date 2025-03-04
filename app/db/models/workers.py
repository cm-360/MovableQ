from dataclasses import dataclass

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from . import Base


@dataclass
class Worker:
    """
    Parent class representing the common attributes shared between different
    worker types.

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

@dataclass
class MinerWorker(Base, Worker):
    """
    Represents a worker running the bfCL mining client script and capable of
    completing bruteforce jobs.

    Attributes:
        client_id (str): The unique identifier for the miner as reported by
            their client.
    """
    __tablename__ = "miner_workers"

    client_id: Mapped[str] = mapped_column(primary_key=True)

@dataclass
class FriendbotWorker(Base, Worker):
    """
    Represents a worker running the friendbot software and capable of obtaining
    LFCSes from friend requests.

    https://github.com/bleck9999/friendbot

    Attributes:
        friend_code (str): The unique 12-digit friend code associated with this
            friendbot worker.
    """
    __tablename__ = "friendbot_workers"

    friend_code: Mapped[str] = mapped_column(primary_key=True)
