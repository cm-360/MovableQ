import pytest


@pytest.mark.asyncio
async def test_create_msed_job(client):
    id0 = "969dbbb25e8f636c391ed29432e2af53"

    # Create new msed job
    response = await client.post(
        "/api/jobs",
        json={
            "type": "msed",
            "job": {
                "id0": id0,
            },
        },
    )
    assert response.status_code == 200

    def validate_job_data(data: dict):
        assert data["type"] == "msed"
        assert data["id0"] == id0
        assert data["lfcs"] is None
        assert data["assignee"] is None
        assert data["status"] == 0

    # Validate job creation response
    job_data = await response.get_json()
    validate_job_data(job_data)

    # Check job list
    response = await client.get("/api/jobs")
    assert response.status_code == 200

    # Validate job list response
    jobs = await response.get_json()
    assert len(jobs) == 1
    validate_job_data(jobs[0])
