import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_login_success(client, seed_admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "Admin123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client, seed_admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_without_token(client):
    response = await client.get("/api/v1/inspection/latest")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_token(client, admin_token):
    response = await client.get("/api/v1/inspection/latest", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    assert response.status_code == 200
