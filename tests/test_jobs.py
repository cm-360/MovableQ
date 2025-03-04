import pytest


@pytest.mark.asyncio
async def test_msed_job(client):
    id0 = "969dbbb25e8f636c391ed29432e2af53"

    # Create msed job
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

    data = await response.get_json()
    assert data["id0"] == id0

    response = await client.get("/api/jobs")
    assert response.status_code == 200
