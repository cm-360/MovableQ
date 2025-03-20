from pytest import raises

from app.db.queries.jobs import create_job
from app.db.queries.jobs import get_all_jobs
from app.db.queries.jobs import get_fc_lfcs_job
from app.db.queries.jobs import get_job_by_id
from app.db.queries.jobs import get_mii_lfcs_job
from app.db.queries.jobs import get_msed_job
from app.db.queries.jobs import get_queued_jobs

test_id0 = "969dbbb25e8f636c391ed29432e2af53"
fake_id0 = "fef0fef0fef0fef0fef0fef0fef0fef0"
test_friend_code = "044770074962"
test_system_id = "10a76a225904ff99"

test_msed_job_data = {
    "id0": test_id0,
    "lfcs": "824f940500",
}

test_msed_job_data_no_lfcs = {
    "id0": fake_id0,
}

test_fc_lfcs_job_data = {
    "friend_code": test_friend_code,
}

test_mii_lfcs_job_data = {
    "console_model": "new",
    "console_year": "2015",
    "system_id": test_system_id,
}


def test_create_job(db):
    with db.bind.Session() as session, session.begin():
        # Create msed job
        job = create_job(session, "msed", test_msed_job_data)
        assert job.job_type() == "msed"
        assert job.id0 == test_id0

        # Create FC-LFCS job
        job = create_job(session, "fc-lfcs", test_fc_lfcs_job_data)
        assert job.job_type() == "fc-lfcs"
        assert job.friend_code == test_friend_code

        # Create Mii-LFCS job
        job = create_job(session, "mii-lfcs", test_mii_lfcs_job_data)
        assert job.job_type() == "mii-lfcs"
        assert job.system_id == test_system_id


def test_create_invalid_jobs(db):
    # TODO test invalid job creation
    pass


def test_get_all_jobs(db):
    with db.bind.Session() as session, session.begin():
        create_job(session, "msed", test_msed_job_data)

        jobs = get_all_jobs(session)
        assert len(jobs) == 1

        create_job(session, "fc-lfcs", test_fc_lfcs_job_data)

        jobs = get_all_jobs(session)
        assert len(jobs) == 2

        create_job(session, "mii-lfcs", test_mii_lfcs_job_data)

        jobs = get_all_jobs(session)
        assert len(jobs) == 3


def test_get_job_by_id(db):
    with db.bind.Session() as session, session.begin():
        create_job(session, "msed", test_msed_job_data)
        create_job(session, "fc-lfcs", test_fc_lfcs_job_data)
        create_job(session, "mii-lfcs", test_mii_lfcs_job_data)

        msed_job = get_job_by_id(session, test_id0)
        assert msed_job.id0 == test_id0

        fc_lfcs_job = get_job_by_id(session, test_friend_code)
        assert fc_lfcs_job.friend_code == test_friend_code

        mii_lfcs_job = get_job_by_id(session, test_system_id)
        assert mii_lfcs_job.system_id == test_system_id

        with raises(ValueError):
            get_job_by_id(session, "")


def test_get_fc_lfcs_job(db):
    with db.bind.Session() as session, session.begin():
        create_job(session, "fc-lfcs", test_fc_lfcs_job_data)

        job = get_fc_lfcs_job(session, test_friend_code)
        assert job.friend_code == test_friend_code

        with raises(ValueError):
            get_fc_lfcs_job(session, "")


def test_get_mii_lfcs_job(db):
    with db.bind.Session() as session, session.begin():
        create_job(session, "mii-lfcs", test_mii_lfcs_job_data)

        job = get_mii_lfcs_job(session, test_system_id)
        assert job.system_id == test_system_id

        with raises(ValueError):
            get_mii_lfcs_job(session, "")


def test_get_msed_job(db):
    with db.bind.Session() as session, session.begin():
        create_job(session, "msed", test_msed_job_data)

        job = get_msed_job(session, test_id0)
        assert job.id0 == test_id0

        with raises(ValueError):
            get_msed_job(session, "")


def test_get_queued_jobs(db):
    with db.bind.Session() as session, session.begin():
        create_job(session, "msed", test_msed_job_data)

        jobs = get_queued_jobs(session)
        assert len(jobs) == 1

        create_job(session, "msed", test_msed_job_data_no_lfcs)

        jobs = get_queued_jobs(session)
        assert len(jobs) == 1
