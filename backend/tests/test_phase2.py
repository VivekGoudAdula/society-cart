"""Automated test suite verifying Phase 2 backend, database, auth, and RBAC requirements.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_01_user_registration(client: AsyncClient):
    """Test 1: User registration succeeds with valid data."""
    payload = {
        "name": "Arun Kumar",
        "email": "arun.kumar@example.com",
        "password": "StrongPassword123!",
        "phone": "+91 9876543210",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "arun.kumar@example.com"
    assert data["user"]["name"] == "Arun Kumar"
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_02_duplicate_email_rejection(client: AsyncClient):
    """Test 2: Registration with an existing email returns 409 Conflict."""
    payload = {
        "name": "Duplicate Arun",
        "email": "ARUN.KUMAR@example.com",  # Test case normalization
        "password": "AnotherPassword123!",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_03_login_correct_credentials(client: AsyncClient):
    """Test 3: Login with correct email and password returns token and user."""
    payload = {
        "email": "arun.kumar@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "arun.kumar@example.com"


@pytest.mark.asyncio
async def test_04_login_incorrect_credentials(client: AsyncClient):
    """Test 4: Login with incorrect password returns 401 Unauthorized."""
    payload = {
        "email": "arun.kumar@example.com",
        "password": "WrongPassword!",
    }
    response = await client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_05_access_protected_routes(client: AsyncClient):
    """Test 5: Access to protected routes without a token returns 401 Unauthorized."""
    response = await client.get("/api/users/me")
    assert response.status_code == 401

    invalid_headers = {"Authorization": "Bearer invalid.jwt.token"}
    response2 = await client.get("/api/users/me", headers=invalid_headers)
    assert response2.status_code == 401


@pytest.mark.asyncio
async def test_06_and_07_society_creation_and_automatic_admin(client: AsyncClient):
    """Tests 6 & 7: Society creation succeeds and creator automatically becomes admin."""
    # Register creator
    reg = await client.post("/api/auth/register", json={
        "name": "Priya Creator",
        "email": "priya.creator@example.com",
        "password": "CreatorPassword123!",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_payload = {
        "name": "Palm Meadows Residency",
        "address": "Whitefield Main Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "creator_flat_number": "A-101",
    }
    response = await client.post("/api/societies", json=create_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert data["society"]["name"] == "Palm Meadows Residency"
    assert data["society"]["city"] == "Bengaluru"
    assert "invite_code" in data["society"]
    assert len(data["society"]["invite_code"]) >= 6

    # Test 7: Confirm creator membership is admin
    assert data["membership"]["role"] == "admin"
    assert data["membership"]["flat_number"] == "A-101"


@pytest.mark.asyncio
async def test_08_join_society_valid_invite_code(client: AsyncClient):
    """Test 8: Resident joins society using valid invite code and receives resident role."""
    # Login creator to get invite code
    login_creator = await client.post("/api/auth/login", json={
        "email": "priya.creator@example.com",
        "password": "CreatorPassword123!",
    })
    creator_token = login_creator.json()["access_token"]
    my_soc = await client.get("/api/societies/my", headers={"Authorization": f"Bearer {creator_token}"})
    society_info = my_soc.json()[0]["society"]
    invite_code = society_info["invite_code"]

    # Register new resident
    reg_resident = await client.post("/api/auth/register", json={
        "name": "Karthik Resident",
        "email": "karthik.resident@example.com",
        "password": "ResidentPassword123!",
    })
    resident_token = reg_resident.json()["access_token"]

    join_payload = {
        "invite_code": invite_code,
        "flat_number": "B-204",
    }
    response = await client.post("/api/societies/join", json=join_payload, headers={"Authorization": f"Bearer {resident_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["society"]["id"] == society_info["id"]
    assert data["membership"]["role"] == "resident"
    assert data["membership"]["flat_number"] == "B-204"


@pytest.mark.asyncio
async def test_09_rejection_invalid_invite_code(client: AsyncClient):
    """Test 9: Joining with an invalid invite code returns 404 Not Found."""
    login_res = await client.post("/api/auth/login", json={
        "email": "karthik.resident@example.com",
        "password": "ResidentPassword123!",
    })
    token = login_res.json()["access_token"]

    response = await client.post("/api/societies/join", json={
        "invite_code": "INVALID-CODE-9999",
        "flat_number": "C-305",
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
    assert "Invalid society invitation code" in response.json()["detail"]


@pytest.mark.asyncio
async def test_10_duplicate_membership_rejection(client: AsyncClient):
    """Test 10: Resident cannot join the same society twice."""
    login_creator = await client.post("/api/auth/login", json={
        "email": "priya.creator@example.com",
        "password": "CreatorPassword123!",
    })
    creator_token = login_creator.json()["access_token"]
    my_soc = await client.get("/api/societies/my", headers={"Authorization": f"Bearer {creator_token}"})
    invite_code = my_soc.json()[0]["society"]["invite_code"]

    # Karthik is already in this society (from Test 8)
    login_res = await client.post("/api/auth/login", json={
        "email": "karthik.resident@example.com",
        "password": "ResidentPassword123!",
    })
    resident_token = login_res.json()["access_token"]

    response = await client.post("/api/societies/join", json={
        "invite_code": invite_code,
        "flat_number": "D-401",
    }, headers={"Authorization": f"Bearer {resident_token}"})
    assert response.status_code == 409
    assert "already an active member" in response.json()["detail"]


@pytest.mark.asyncio
async def test_11_duplicate_flat_number_rejection(client: AsyncClient):
    """Test 11: An active flat number cannot be registered by another resident."""
    login_creator = await client.post("/api/auth/login", json={
        "email": "priya.creator@example.com",
        "password": "CreatorPassword123!",
    })
    creator_token = login_creator.json()["access_token"]
    my_soc = await client.get("/api/societies/my", headers={"Authorization": f"Bearer {creator_token}"})
    invite_code = my_soc.json()[0]["society"]["invite_code"]

    # Register a third user who tries to claim B-204 (already held by Karthik)
    reg_third = await client.post("/api/auth/register", json={
        "name": "Sneha Neighbor",
        "email": "sneha.neighbor@example.com",
        "password": "SnehaPassword123!",
    })
    third_token = reg_third.json()["access_token"]

    response = await client.post("/api/societies/join", json={
        "invite_code": invite_code,
        "flat_number": "B-204",  # Already occupied
    }, headers={"Authorization": f"Bearer {third_token}"})
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_12_resident_cannot_assign_volunteer_privileges(client: AsyncClient):
    """Test 12: A standard resident cannot promote members to volunteer."""
    login_creator = await client.post("/api/auth/login", json={
        "email": "priya.creator@example.com",
        "password": "CreatorPassword123!",
    })
    creator_token = login_creator.json()["access_token"]
    my_soc = await client.get("/api/societies/my", headers={"Authorization": f"Bearer {creator_token}"})
    society_id = my_soc.json()[0]["society"]["id"]

    # Get members list as admin
    members_resp = await client.get(f"/api/societies/{society_id}/members", headers={"Authorization": f"Bearer {creator_token}"})
    resident_mem_id = [m["id"] for m in members_resp.json() if m["role"] == "resident"][0]

    # Login standard resident Karthik
    login_karthik = await client.post("/api/auth/login", json={
        "email": "karthik.resident@example.com",
        "password": "ResidentPassword123!",
    })
    karthik_token = login_karthik.json()["access_token"]

    # Karthik tries to assign volunteer role
    response = await client.patch(
        f"/api/societies/{society_id}/members/{resident_mem_id}/role",
        json={"role": "volunteer"},
        headers={"Authorization": f"Bearer {karthik_token}"},
    )
    assert response.status_code == 403
    assert "administrator privileges are required" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_13_admin_can_assign_volunteer_privileges(client: AsyncClient):
    """Test 13: An administrator can successfully promote a resident to volunteer."""
    login_creator = await client.post("/api/auth/login", json={
        "email": "priya.creator@example.com",
        "password": "CreatorPassword123!",
    })
    creator_token = login_creator.json()["access_token"]
    my_soc = await client.get("/api/societies/my", headers={"Authorization": f"Bearer {creator_token}"})
    society_id = my_soc.json()[0]["society"]["id"]

    members_resp = await client.get(f"/api/societies/{society_id}/members", headers={"Authorization": f"Bearer {creator_token}"})
    resident_mem_id = [m["id"] for m in members_resp.json() if m["role"] == "resident"][0]

    # Admin promotes to volunteer
    response = await client.patch(
        f"/api/societies/{society_id}/members/{resident_mem_id}/role",
        json={"role": "volunteer"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "volunteer"


@pytest.mark.asyncio
async def test_14_user_cannot_access_another_society_data(client: AsyncClient):
    """Test 14: A user cannot access members or details of a society they do not belong to."""
    # User Arun from Test 1 does not belong to Palm Meadows
    login_arun = await client.post("/api/auth/login", json={
        "email": "arun.kumar@example.com",
        "password": "StrongPassword123!",
    })
    arun_token = login_arun.json()["access_token"]

    login_creator = await client.post("/api/auth/login", json={
        "email": "priya.creator@example.com",
        "password": "CreatorPassword123!",
    })
    creator_token = login_creator.json()["access_token"]
    my_soc = await client.get("/api/societies/my", headers={"Authorization": f"Bearer {creator_token}"})
    society_id = my_soc.json()[0]["society"]["id"]

    # Arun attempts to view Palm Meadows members
    response = await client.get(
        f"/api/societies/{society_id}/members",
        headers={"Authorization": f"Bearer {arun_token}"},
    )
    assert response.status_code == 403
    assert "not an active member" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_15_profile_updates_cannot_modify_protected_fields(client: AsyncClient):
    """Test 15: Profile updates modify name/phone but ignore/reject protected fields (id, email, password_hash, role)."""
    login_arun = await client.post("/api/auth/login", json={
        "email": "arun.kumar@example.com",
        "password": "StrongPassword123!",
    })
    token = login_arun.json()["access_token"]
    original_id = login_arun.json()["user"]["id"]

    # Send payload attempting to alter email, id, password_hash, role
    update_payload = {
        "name": "Arun Kumar Updated",
        "phone": "+91 9999988888",
        "email": "hacked@example.com",
        "id": "new_id_attempt",
        "role": "admin",
    }
    response = await client.patch(
        "/api/users/me",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Arun Kumar Updated"
    assert data["phone"] == "+91 9999988888"
    assert data["email"] == "arun.kumar@example.com"  # Email remains unchanged
    assert data["id"] == original_id  # ID remains unchanged
