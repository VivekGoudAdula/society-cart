"""Automated test suite for Phase 3 — Nexconn Chat Integration.

Tests cover:
- Token request authentication & derivation
- Access control & cross-society isolation
- Group channel association on society creation
- Membership synchronization & deactivation revocation
- System bot message dispatch
- Two-user token issuance for the same society group
"""

import uuid
import pytest
from httpx import AsyncClient
from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def test_prefix() -> str:
    return f"phase3_{uuid.uuid4().hex[:6]}"


async def create_user_and_token(client: AsyncClient, email: str, name: str) -> dict:
    """Helper to register a user and return access token and user doc."""
    res = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": name,
            "password": "Password123!",
            "phone": "+919876543210",
        },
    )
    assert res.status_code == 201, f"Registration failed: {res.text}"
    return res.json()


async def test_01_unauthenticated_cannot_request_chat_token(client: AsyncClient):
    """Scenario 1: Unauthenticated request to /api/chat/token is rejected with 401."""
    res = await client.post(
        "/api/chat/token",
        json={"society_id": "random_society_id"},
    )
    assert res.status_code == 401


async def test_02_to_05_society_group_association_and_token_issuance(
    client: AsyncClient, test_prefix: str
):
    """Scenario 2-5:
    - Creating a society provisions and stores `nexconn_group_id`.
    - Authenticated society member receives a valid chat token.
    - Identity is derived strictly from the authenticated account.
    - Repeated requests reuse the same group ID.
    """
    admin_auth = await create_user_and_token(
        client, f"{test_prefix}_admin@example.com", "Admin Creator"
    )
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # 1. Create society
    soc_res = await client.post(
        "/api/societies",
        headers=headers,
        json={
            "name": f"{test_prefix} Residency",
            "address": "Road 10, Banjara Hills",
            "city": "Hyderabad",
            "creator_flat_number": "A-101",
        },
    )
    assert soc_res.status_code == 201
    soc_data = soc_res.json()["society"]
    society_id = soc_data["id"]
    group_id = soc_data.get("nexconn_group_id")

    assert group_id is not None
    assert group_id == f"society_{society_id}"

    # 2. Request chat token as admin
    token_res = await client.post(
        "/api/chat/token",
        headers=headers,
        json={"society_id": society_id},
    )
    assert token_res.status_code == 200
    token_data = token_res.json()

    assert "token" in token_data
    assert len(token_data["token"]) > 10
    assert token_data["user_id"] == admin_auth["user"]["id"]
    assert token_data["group_id"] == group_id
    assert token_data["group_name"] == f"{test_prefix} Residency"

    # 3. Repeated token request yields the exact same group
    token_res_2 = await client.post(
        "/api/chat/token",
        headers=headers,
        json={"society_id": society_id},
    )
    assert token_res_2.status_code == 200
    assert token_res_2.json()["group_id"] == group_id


async def test_06_and_07_cross_society_isolation(
    client: AsyncClient, test_prefix: str
):
    """Scenario 6 & 7:
    - Non-member cannot access society chat (403 Forbidden).
    - Resident of Society A cannot access Society B's chat token (403 Forbidden).
    """
    # Create Society A
    user_a = await create_user_and_token(
        client, f"{test_prefix}_user_a@example.com", "User Society A"
    )
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    soc_a_res = await client.post(
        "/api/societies",
        headers=headers_a,
        json={
            "name": f"{test_prefix} Tower A",
            "address": "Locality A",
            "city": "Hyderabad",
            "creator_flat_number": "101",
        },
    )
    soc_a_id = soc_a_res.json()["society"]["id"]

    # Create Society B
    user_b = await create_user_and_token(
        client, f"{test_prefix}_user_b@example.com", "User Society B"
    )
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    soc_b_res = await client.post(
        "/api/societies",
        headers=headers_b,
        json={
            "name": f"{test_prefix} Tower B",
            "address": "Locality B",
            "city": "Hyderabad",
            "creator_flat_number": "201",
        },
    )
    soc_b_id = soc_b_res.json()["society"]["id"]

    # User A tries to request chat token for Society B -> Must be rejected with 403
    cross_res = await client.post(
        "/api/chat/token",
        headers=headers_a,
        json={"society_id": soc_b_id},
    )
    assert cross_res.status_code == 403
    assert "not an active member" in cross_res.json()["detail"].lower()


async def test_08_deactivated_member_loses_chat_access(
    client: AsyncClient, test_prefix: str
):
    """Scenario 8: When a member is deactivated by admin, chat token access is revoked."""
    admin = await create_user_and_token(
        client, f"{test_prefix}_lead@example.com", "Lead Admin"
    )
    headers_admin = {"Authorization": f"Bearer {admin['access_token']}"}

    soc_res = await client.post(
        "/api/societies",
        headers=headers_admin,
        json={
            "name": f"{test_prefix} Heights",
            "address": "High Road",
            "city": "Hyderabad",
            "creator_flat_number": "H-101",
        },
    )
    soc_data = soc_res.json()["society"]
    society_id = soc_data["id"]
    invite_code = soc_data["invite_code"]

    # Resident joins
    resident = await create_user_and_token(
        client, f"{test_prefix}_to_remove@example.com", "Departing Resident"
    )
    headers_res = {"Authorization": f"Bearer {resident['access_token']}"}

    join_res = await client.post(
        "/api/societies/join",
        headers=headers_res,
        json={"invite_code": invite_code, "flat_number": "H-202"},
    )
    assert join_res.status_code == 200
    membership_id = join_res.json()["membership"]["id"]

    # Verify resident CAN get token while active
    token_ok = await client.post(
        "/api/chat/token",
        headers=headers_res,
        json={"society_id": society_id},
    )
    assert token_ok.status_code == 200

    # Admin deactivates resident membership
    del_res = await client.delete(
        f"/api/societies/{society_id}/members/{membership_id}",
        headers=headers_admin,
    )
    assert del_res.status_code in (200, 204)

    # Resident now tries to get token -> Must be rejected with 403
    token_denied = await client.post(
        "/api/chat/token",
        headers=headers_res,
        json={"society_id": society_id},
    )
    assert token_denied.status_code == 403


async def test_09_system_message_dispatch(
    client: AsyncClient, test_prefix: str
):
    """Scenario 9: Active member can dispatch a bot/system broadcast notification."""
    admin = await create_user_and_token(
        client, f"{test_prefix}_sysadmin@example.com", "Sys Admin"
    )
    headers = {"Authorization": f"Bearer {admin['access_token']}"}

    soc_res = await client.post(
        "/api/societies",
        headers=headers,
        json={
            "name": f"{test_prefix} Enclave",
            "address": "Inner Ring Road",
            "city": "Hyderabad",
            "creator_flat_number": "E-101",
        },
    )
    society_id = soc_res.json()["society"]["id"]

    msg_res = await client.post(
        "/api/chat/system-message",
        headers=headers,
        json={
            "society_id": society_id,
            "text": "Round #1 has opened. Please submit grocery items by 8:00 PM.",
            "extra": {"round_number": 1, "status": "open"},
        },
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["status"] == "ok"


async def test_10_two_user_same_society_chat_token_issuance(
    client: AsyncClient, test_prefix: str
):
    """Scenario 10 (Mandatory E2E):
    Resident A (Flat A-101) and Resident B (Flat B-204) belonging to the same society
    both receive valid distinct Nexconn tokens mapped to the identical group channel.
    """
    # 1. Resident A creates society with Flat A-101
    res_a = await create_user_and_token(
        client, f"{test_prefix}_res_a@example.com", "Resident A"
    )
    headers_a = {"Authorization": f"Bearer {res_a['access_token']}"}

    soc_res = await client.post(
        "/api/societies",
        headers=headers_a,
        json={
            "name": f"{test_prefix} Community",
            "address": "Palm Avenue",
            "city": "Hyderabad",
            "creator_flat_number": "A-101",
        },
    )
    assert soc_res.status_code == 201
    soc_data = soc_res.json()["society"]
    society_id = soc_data["id"]
    invite_code = soc_data["invite_code"]
    expected_group_id = soc_data["nexconn_group_id"]

    # 2. Resident B registers and joins with invite code & Flat B-204
    res_b = await create_user_and_token(
        client, f"{test_prefix}_res_b@example.com", "Resident B"
    )
    headers_b = {"Authorization": f"Bearer {res_b['access_token']}"}

    join_res = await client.post(
        "/api/societies/join",
        headers=headers_b,
        json={"invite_code": invite_code, "flat_number": "B-204"},
    )
    assert join_res.status_code == 200

    # 3. Resident A requests chat token
    token_a_res = await client.post(
        "/api/chat/token",
        headers=headers_a,
        json={"society_id": society_id},
    )
    assert token_a_res.status_code == 200
    data_a = token_a_res.json()

    # 4. Resident B requests chat token
    token_b_res = await client.post(
        "/api/chat/token",
        headers=headers_b,
        json={"society_id": society_id},
    )
    assert token_b_res.status_code == 200
    data_b = token_b_res.json()

    # Both tokens are valid strings
    assert len(data_a["token"]) > 10
    assert len(data_b["token"]) > 10

    # User IDs are unique to each resident
    assert data_a["user_id"] == res_a["user"]["id"]
    assert data_b["user_id"] == res_b["user"]["id"]
    assert data_a["user_id"] != data_b["user_id"]

    # Group IDs are identical and match the society's group channel
    assert data_a["group_id"] == expected_group_id
    assert data_b["group_id"] == expected_group_id
    assert data_a["group_id"] == data_b["group_id"]
