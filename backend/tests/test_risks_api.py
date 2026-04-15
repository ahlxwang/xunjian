import pytest


@pytest.mark.asyncio
async def test_list_risks_empty(client, admin_token):
    response = await client.get(
        "/api/v1/risks",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_update_risk_status(client, admin_token, db, seed_inspection_with_risk):
    risk_id = seed_inspection_with_risk
    response = await client.patch(
        f"/api/v1/risks/{risk_id}/status",
        json={"status": "processing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processing"


@pytest.mark.asyncio
async def test_update_risk_invalid_status(client, admin_token, db, seed_inspection_with_risk):
    risk_id = seed_inspection_with_risk
    response = await client.patch(
        f"/api/v1/risks/{risk_id}/status",
        json={"status": "invalid_status"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
