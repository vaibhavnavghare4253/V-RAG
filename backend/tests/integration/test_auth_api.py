import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient):
    payload = {
        "email": "scientist@university.edu",
        "password": "StrongPassword987!",
        "full_name": "Scientist One",
        "organization_name": "AI Lab",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "scientist@university.edu"
    assert data["user"]["full_name"] == "Scientist One"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient):
    payload = {
        "email": "duplicate@test.com",
        "password": "Password123!",
    }
    # First registration
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    # Second registration with identical email
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400
    assert "already exists" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient, test_user_and_token):
    # Valid credentials
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "researcher@lab.ac.in", "password": "ResearchPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "researcher@lab.ac.in"

    # Invalid credentials
    bad_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "researcher@lab.ac.in", "password": "WrongPassword!"},
    )
    assert bad_resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_me(client: AsyncClient, test_user_and_token):
    headers = test_user_and_token["headers"]
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "researcher@lab.ac.in"
    assert data["organization"]["name"] == "Test University Lab"

    # Without token
    unauth_resp = await client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

