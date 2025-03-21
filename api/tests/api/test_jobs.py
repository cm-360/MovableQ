from pytest import fixture
from pytest import mark

api_submit_endpoint = "/api/jobs/submit"
api_list_endpoint = "/api/jobs/list"

test_id0 = "969dbbb25e8f636c391ed29432e2af53"
zero_id0 = "00000000000000000000000000000000"
test_lfcs = "824f940500"

test_msed_job_data = {
    "type": "msed",
    "id0": test_id0,
    "lfcs": test_lfcs,
}


@fixture
def submit_job(client):
    async def submit_inner(job_data: dict):
        return await client.post(api_submit_endpoint, json=job_data)

    return submit_inner


@mark.asyncio
async def test_create_msed_job(client, submit_job):
    # Create new msed job
    response = await submit_job(test_msed_job_data)
    assert response.status_code == 200

    def validate_job_data(data: dict):
        assert data["type"] == "msed"
        assert data["id0"] == test_id0
        assert data["lfcs"] == test_lfcs
        assert data["assignee"] is None
        assert data["status"] == "queued"

    # Validate job creation response
    job_data = await response.get_json()
    validate_job_data(job_data)

    # Check job list
    response = await client.get("/api/jobs/list")
    assert response.status_code == 200

    # Validate job list response
    jobs = await response.get_json()
    assert len(jobs) == 1
    validate_job_data(jobs[0])


@mark.asyncio
async def test_create_job_missing_data(client, submit_job):
    # Missing type
    response = await client.post(api_submit_endpoint, json={"id0": test_id0})
    assert response.status_code == 400

    # Missing job data
    response = await client.post(api_submit_endpoint, json={"type": "msed"})
    assert response.status_code == 400

    # Missing ID0 in job data
    response = await submit_job({"type": "msed"})
    assert response.status_code == 400


@mark.asyncio
async def test_create_job_invalid_data(client, submit_job):
    # Invalid job type
    response = await submit_job({"type": "fake", "id0": test_id0})
    assert response.status_code == 400

    # Invalid ID0
    response = await submit_job({"type": "msed", "id0": zero_id0})
    assert response.status_code == 400


@mark.asyncio
async def test_list_jobs(client, submit_job):
    # Get all jobs
    response = await client.get(api_list_endpoint)
    assert response.status_code == 200
    data = await response.get_json()
    assert len(data) == 0

    # Submit one msed job
    await submit_job(test_msed_job_data)

    # Get all jobs
    response = await client.get(api_list_endpoint)
    assert response.status_code == 200
    data = await response.get_json()
    assert len(data) == 1

    # Get msed jobs
    response = await client.get(f"{api_list_endpoint}?types=msed")
    assert response.status_code == 200
    data = await response.get_json()
    assert len(data) == 1

    # Get Mii LFCS jobs
    response = await client.get(f"{api_list_endpoint}?types=mii-lfcs")
    assert response.status_code == 200
    data = await response.get_json()
    assert len(data) == 0


# TODO: Test get job details
# TODO: Test release job
