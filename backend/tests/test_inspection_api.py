import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_trigger_inspection_returns_task_id(client, admin_token):
    with patch("app.api.inspection.run_inspection_sync", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "test-task-uuid"
        response = await client.post(
            "/api/v1/inspection/trigger",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 202
    data = response.json()
    assert data["task_id"] == "test-task-uuid"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_trigger_inspection_requires_auth(client):
    response = await client.post("/api/v1/inspection/trigger")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_latest_inspection_empty(client, admin_token):
    response = await client.get(
        "/api/v1/inspection/latest",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["task"] is None
