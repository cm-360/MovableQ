from binascii import unhexlify
from enum import IntEnum
from enum import StrEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import validates

from app.db.models.base import Base
from app.db.models.base import GenericBase
from app.db.utils import format_timestamp
from app.utils.validators import is_valid_friend_code
from app.utils.validators import is_valid_id0
from app.utils.validators import is_valid_lfcs
from app.utils.validators import is_valid_system_id


class JobStatus(IntEnum):
    """Possible job statuses.

    Attributes:
        submitted (int): Submitted but not yet in the queue.
        queued (int): In the queue, waiting to be assigned.
        working (int): Currently being processed by a worker.
        canceled (int): Canceled by the owning user.
        failed (int): Reported as failed by the assigned worker.
        completed (int): Successfully completed.
    """

    submitted = 0
    queued = 1
    working = 2
    canceled = 3
    failed = 4
    completed = 5


class Job(GenericBase):
    """A generic job with a status and timestamps.

    Attributes:
        status (JobStatus): The current status of this job.
        created_at (str): The timestamp when this job was created.
        updated_at (str): The timestamp when this job was last updated.
        completed_at (str): The timestamp when this job was completed, if any.
    """

    created_at: Mapped[str] = mapped_column(DateTime)
    updated_at: Mapped[str] = mapped_column(DateTime)
    completed_at: Mapped[str | None] = mapped_column(DateTime)
    status: Mapped[JobStatus] = mapped_column(SqlEnum(JobStatus))

    def __iter__(self):
        yield from super().__iter__()
        yield "created_at", format_timestamp(self.created_at)
        yield "updated_at", format_timestamp(self.updated_at)
        yield "completed_at", format_timestamp(self.completed_at)
        yield "status", self.status.name
        yield "type", self.subclass_id()


class ConsoleModel(StrEnum):
    """The 3DS console model families.

    Attributes:
        old (str): A console from the original lineup (3DS, 3DSXL, 2DS).
        new (str): A console from the "New" lineup with a C-stick and improved
            hardware (N3DS, N3DSXL, N2DS).
    """

    old = "old"
    new = "new"


class MiiLfcsJob(Base, Job):
    """A bruteforcing job for obtaining a LFCS from a system ID.

    These jobs use the system ID contained in an exported Mii QR code to
    bruteforce a console's unique LocalFriendCodeSeed.

    Attributes:
        system_id (str): The unique system ID of the user's console as a
            hexadecimal string.
        console_model (ConsoleModel): The user's console's model (new/old).
        console_year (int): The manufacturing year of the user's console.
        assignee (str | None): The client ID of the worker assigned to this
            job, if any.

    Note:
        For more information on the LFCS, refer to
        https://wiki.hacks.guide/wiki/3DS:System_files and
        https://3dbrew.org/wiki/Nandrw/sys/LocalFriendCodeSeed_B.
    """

    __tablename__ = "mii_lfcs_jobs"

    system_id: Mapped[str] = mapped_column(primary_key=True)
    console_model: Mapped[ConsoleModel] = mapped_column(SqlEnum(ConsoleModel))
    console_year: Mapped[int]
    assignee: Mapped[str | None] = mapped_column(ForeignKey("miner_workers.client_id"))

    @validates("system_id")
    def validate_system_id(self, key: str, system_id: str):
        if not is_valid_system_id(system_id):
            raise ValueError("Invalid system ID")
        return system_id


class MiiLfcsOffsetJob(Base, Job):
    """A sub-job for bruteforcing a specific LFCS offset for Mii-LFCS jobs.

    These jobs allow more efficient distribution of bruteforce work for
    Mii-LFCS jobs, as chunking the search space allows multiple miners to work
    on a job simultaneously.

    Attributes:
        system_id (str): The unique system ID of the user's console as a
            hexadecimal string.
        offset (int): This job's offset from the starting point in the LFCS
            search space.
        index (int): This job's index into the LFCS search space.
        assignee (str | None): The client ID of the worker assigned to this
            job, if any.
    """

    __tablename__ = "mii_lfcs_offset_jobs"

    system_id: Mapped[str] = mapped_column(
        ForeignKey("mii_lfcs_jobs.system_id"),
        primary_key=True,
    )
    offset: Mapped[int] = mapped_column(primary_key=True)
    index: Mapped[int] = mapped_column(primary_key=True)
    assignee: Mapped[str | None] = mapped_column(ForeignKey("miner_workers.client_id"))


class FcLfcsJob(Base, Job):
    """A job for obtaining a user's LFCS via an automated friend request.

    Attributes:
        friend_code (str): The user's unique 12-digit friend code.
        assignee (str | None): The friend code of the worker assigned to this
            job, if any.
    """

    __tablename__ = "fc_lfcs_jobs"

    friend_code: Mapped[str] = mapped_column(primary_key=True)
    assignee: Mapped[str | None] = mapped_column(
        ForeignKey("friendbot_workers.friend_code")
    )

    @validates("friend_code", "assignee")
    def validate_friend_code(self, key: str, friend_code: str):
        if "friend_code" == key and not is_valid_friend_code(friend_code):
            raise ValueError("Invalid friend code")
        return friend_code


class MsedJob(Base, Job):
    """A bruteforcing job to obtain a `movable.sed` file from a LFCS.

    These jobs use a console's LocalFriendCodeSeed and ID0 to bruteforce the
    KeyY encryption key contained in `movable.sed`. The LFCS is also sometimes
    refered to as a `movable_part1.sed` file.

    Attributes:
        id0 (str): The unique ID0 value associated with this job as a
            hexadecimal string.
        lfcs (str | None): The LFCS needed to complete this job as a
            hexadecimal string, if known.
        assignee (str | None): The client ID of the worker assigned to this
            job, if any.
        prereq_id (str | None): The job ID of this job's prerequisite, if any.
            This should be either a system ID or friend code.

    Note:
        For more information about KeyY and the `movable.sed` file, refer to
        https://wiki.hacks.guide/wiki/3DS:System_files,
        https://zoogie.github.io/web/34%E2%85%95c3, and
        https://www.3dbrew.org/wiki/Nand/private/movable.sed.
    """

    __tablename__ = "msed_jobs"

    id0: Mapped[str] = mapped_column(primary_key=True)
    lfcs: Mapped[str | None]
    assignee: Mapped[str | None] = mapped_column(ForeignKey("miner_workers.client_id"))
    prereq_id: Mapped[str | None]

    def __post_init__(self):
        if self.lfcs is None and self.prereq_id is None:
            raise ValueError("Either an LFCS or prerequisite ID must be provided")

        if self.lfcs is None and JobStatus.queued == self.status:
            self.status = JobStatus.submitted

    @validates("id0")
    def validate_id0(self, key: str, id0: str):
        if not is_valid_id0(id0):
            raise ValueError("Invalid ID0")
        return id0

    @validates("lfcs")
    def validate_lfcs(self, key: str, lfcs: str | None):
        if lfcs is not None and not is_valid_lfcs(unhexlify(lfcs)):
            raise ValueError("Invalid LFCS")
        return lfcs

    @validates("prereq_id")
    def validate_prereq_id(self, key: str, prereq_id: str | None):
        if prereq_id is not None:
            if is_valid_system_id(prereq_id):
                return prereq_id
            if is_valid_friend_code(prereq_id):
                return prereq_id

            raise ValueError("Invalid prerequisite ID")

        return prereq_id
