from quart import request

from sqlalchemy import select

from . import bp
from ..db import db
from ..db.models.jobs import FcLfcsJob
from ..db.models.jobs import MiiLfcsJob
from ..db.models.jobs import MsedJob
from ..db.utils import from_dict


@bp.get("/jobs")
async def list_jobs():
    with db.bind.Session() as session:
        jobs = session.scalars(select(MsedJob)).all()
        return jobs

@bp.post("/jobs")
async def create_job():
    data = await request.get_json()

    if "msed" == data.type:
        pass
    elif "fc-lfcs" == data.type:
        pass
    elif "mii-lfcs" == data.type:
        pass
    else:
        raise ValueError(f"")

    with db.bind.Session() as session:
        with session.begin():
            session.add(job)
            session.flush
