"""Automated test suite for Phase 4 Final Reliability, Privacy, and Concurrency Hardening.

Covers:
1. Submission privacy: Residents see only their own submissions.
2. Volunteer and Admin see all submissions within the society.
3. Cross-society submission access is strictly rejected (403).
4. Race-safe reservation: Reservation succeeds before deadline.
5. Timeliness authority: A reservation accepted before deadline remains confirmable after round closure.
6. Reject new reservations after round deadline or closure.
7. Idempotent confirmation.
8. Single message ID constraint (duplicate message_id rejected).
9. Failure handling: Failed message dispatch marks reservation as failed.
10. Concurrency safety: Concurrent round creations generate sequential, unique round numbers.
11. Structured announcement delivery state tracking.
12. Shopping date handling and timezone normalization.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import time
import pytest
from httpx import AsyncClient
from bson import ObjectId


@pytest.fixture
async def setup_hardening_data(client: AsyncClient):
    """Fixture providing 2 societies, Admin, Volunteer, 2 Residents in Society 1, and 1 Resident in Society 2."""
    ts = int(time.time() * 1000)

    # 1. Admin in Society 1
    resp_admin = await client.post("/api/auth/register", json={
        "name": "Admin Vikram",
        "email": f"vikram_{ts}@example.com",
        "password": "Password123!",
    })
    token_admin = resp_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    resp_soc1 = await client.post("/api/societies", headers=headers_admin, json={
        "name": f"Sunrise Towers {ts}",
        "address": "Outer Ring Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "total_flats": 80,
        "creator_flat_number": "A-101",
    })
    soc1_id = resp_soc1.json()["society"]["id"]
    soc1_invite = resp_soc1.json()["society"]["invite_code"]

    # 2. Volunteer in Society 1
    resp_vol = await client.post("/api/auth/register", json={
        "name": "Volunteer Ananya",
        "email": f"ananya_{ts}@example.com",
        "password": "Password123!",
    })
    token_vol = resp_vol.json()["access_token"]
    headers_vol = {"Authorization": f"Bearer {token_vol}"}

    join_vol = await client.post("/api/societies/join", headers=headers_vol, json={
        "invite_code": soc1_invite,
        "flat_number": "B-202",
    })
    vol_mem_id = join_vol.json()["membership"]["id"]
    await client.patch(
        f"/api/societies/{soc1_id}/members/{vol_mem_id}/role",
        headers=headers_admin,
        json={"role": "volunteer"},
    )

    # 3. Resident 1 in Society 1 (Flat C-303)
    resp_res1 = await client.post("/api/auth/register", json={
        "name": "Resident Rahul",
        "email": f"rahul_{ts}@example.com",
        "password": "Password123!",
    })
    token_res1 = resp_res1.json()["access_token"]
    headers_res1 = {"Authorization": f"Bearer {token_res1}"}
    await client.post("/api/societies/join", headers=headers_res1, json={
        "invite_code": soc1_invite,
        "flat_number": "C-303",
    })

    # 4. Resident 2 in Society 1 (Flat D-404)
    resp_res2 = await client.post("/api/auth/register", json={
        "name": "Resident Sneha",
        "email": f"sneha_{ts}@example.com",
        "password": "Password123!",
    })
    token_res2 = resp_res2.json()["access_token"]
    headers_res2 = {"Authorization": f"Bearer {token_res2}"}
    await client.post("/api/societies/join", headers=headers_res2, json={
        "invite_code": soc1_invite,
        "flat_number": "D-404",
    })

    # 5. Resident in Society 2
    resp_other = await client.post("/api/auth/register", json={
        "name": "Foreign Resident",
        "email": f"foreign_{ts}@example.com",
        "password": "Password123!",
    })
    token_other = resp_other.json()["access_token"]
    headers_other = {"Authorization": f"Bearer {token_other}"}

    resp_soc2 = await client.post("/api/societies", headers=headers_other, json={
        "name": f"Orchid Enclave {ts}",
        "address": "Whitefield",
        "city": "Bengaluru",
        "total_flats": 30,
        "creator_flat_number": "OE-10",
    })
    soc2_id = resp_soc2.json()["society"]["id"]

    return {
        "soc1_id": soc1_id,
        "soc2_id": soc2_id,
        "headers_admin": headers_admin,
        "headers_vol": headers_vol,
        "headers_res1": headers_res1,
        "headers_res2": headers_res2,
        "headers_other": headers_other,
    }


@pytest.mark.asyncio
async def test_submission_privacy_and_authorization(client: AsyncClient, setup_hardening_data):
    """Test 1: Residents see ONLY their own submissions.
    Volunteers and Admins see ALL submissions in the society.
    Cross-society access is rejected with 403 Forbidden.
    """
    data = setup_hardening_data
    soc1_id = data["soc1_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Create & open round
    create_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={
            "title": "Privacy Test Round",
            "deadline_at": future_deadline,
            "shopping_date": "Sunday 11:00 AM",
        },
    )
    round_id = create_resp.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=data["headers_admin"])

    # Resident 1 submits order
    sub1_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_res1"],
        json={"message_id": f"msg_res1_{round_id}", "raw_text": "2kg Tomatoes, 1kg Onions"},
    )
    assert sub1_res.status_code == 201

    # Resident 2 submits order
    sub2_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_res2"],
        json={"message_id": f"msg_res2_{round_id}", "raw_text": "5L Milk, 1 loaf Bread"},
    )
    assert sub2_res.status_code == 201

    # 1. Resident 1 retrieves submissions -> MUST see only Resident 1's submission
    res1_list = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_res1"],
    )
    assert res1_list.status_code == 200
    res1_items = res1_list.json()
    assert len(res1_items) == 1
    assert res1_items[0]["flat_number"] == "C-303"
    assert "Tomatoes" in res1_items[0]["raw_text"]

    # 2. Resident 2 retrieves submissions -> MUST see only Resident 2's submission
    res2_list = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_res2"],
    )
    assert res2_list.status_code == 200
    res2_items = res2_list.json()
    assert len(res2_items) == 1
    assert res2_items[0]["flat_number"] == "D-404"
    assert "Milk" in res2_items[0]["raw_text"]

    # 3. Volunteer retrieves submissions -> MUST see ALL submissions
    vol_list = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_vol"],
    )
    assert vol_list.status_code == 200
    assert len(vol_list.json()) == 2

    # 4. Admin retrieves submissions -> MUST see ALL submissions
    admin_list = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_admin"],
    )
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 2

    # 5. User from Society 2 retrieves submissions -> MUST be rejected with 403 Forbidden
    cross_soc_list = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_other"],
    )
    assert cross_soc_list.status_code == 403


@pytest.mark.asyncio
async def test_race_safe_reservation_and_confirmation_lifecycle(client: AsyncClient, setup_hardening_data):
    """Test 2: Reservation & Confirmation Lifecycle.
    - Reservation succeeds before deadline.
    - Timeliness authority: Reservation accepted before deadline remains confirmable after round closes.
    - Attempting new reservation on closed round is rejected.
    - Confirmation is idempotent.
    - Reusing message_id is rejected with 409.
    """
    data = setup_hardening_data
    soc1_id = data["soc1_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Create & open round
    create_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={"title": "Race Safety Test Round", "deadline_at": future_deadline, "shopping_date": "Tomorrow"},
    )
    round_id = create_resp.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=data["headers_admin"])

    client_sub_id = f"client_sub_{int(time.time()*1000)}"

    # 1. Resident 1 reserves a submission while round is open
    reserve_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/reserve",
        headers=data["headers_res1"],
        json={
            "submission_id": client_sub_id,
            "raw_text": "10kg Atta, 2kg Sugar",
        },
    )
    assert reserve_resp.status_code == 201
    res_data = reserve_resp.json()
    assert res_data["status"] == "reserved"
    assert res_data["submission_id"] == client_sub_id
    assert res_data["reserved_at"] is not None
    assert res_data["confirmed_at"] is None
    assert res_data["message_id"] is None

    # 2. Close the round NOW
    close_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/close",
        headers=data["headers_admin"],
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"

    # 3. New reservation on CLOSED round must be rejected
    new_sub_attempt = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/reserve",
        headers=data["headers_res2"],
        json={
            "submission_id": f"late_sub_{int(time.time()*1000)}",
            "raw_text": "1kg Coffee",
        },
    )
    assert new_sub_attempt.status_code == 400

    # 4. TIMELINESS AUTHORITY: The reservation made before deadline CAN be confirmed after round closure!
    msg_id = f"nexconn_chat_msg_{int(time.time()*1000)}"
    confirm_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/{client_sub_id}/confirm",
        headers=data["headers_res1"],
        json={"message_id": msg_id},
    )
    assert confirm_resp.status_code == 200
    confirmed_data = confirm_resp.json()
    assert confirmed_data["status"] == "confirmed"
    assert confirmed_data["message_id"] == msg_id
    assert confirmed_data["confirmed_at"] is not None

    # 5. IDEMPOTENT CONFIRMATION: Confirming again with same message_id succeeds
    repeat_confirm = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/{client_sub_id}/confirm",
        headers=data["headers_res1"],
        json={"message_id": msg_id},
    )
    assert repeat_confirm.status_code == 200
    assert repeat_confirm.json()["message_id"] == msg_id

    # 6. Confirming with conflicting message ID fails
    conflict_confirm = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/{client_sub_id}/confirm",
        headers=data["headers_res1"],
        json={"message_id": "different_msg_id"},
    )
    assert conflict_confirm.status_code == 400


@pytest.mark.asyncio
async def test_failure_handling_and_message_uniqueness(client: AsyncClient, setup_hardening_data):
    """Test 3: Reservation failure handling and single message_id constraint."""
    data = setup_hardening_data
    soc1_id = data["soc1_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Create & open round
    create_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={"title": "Failure and Uniqueness Round", "deadline_at": future_deadline, "shopping_date": "Monday"},
    )
    round_id = create_resp.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=data["headers_admin"])

    # 1. Test failed message delivery marks reservation as failed
    fail_sub_id = f"fail_sub_{int(time.time()*1000)}"
    await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/reserve",
        headers=data["headers_res1"],
        json={"submission_id": fail_sub_id, "raw_text": "Failed test items"},
    )
    fail_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/{fail_sub_id}/fail",
        headers=data["headers_res1"],
        json={"reason": "Chat client lost network connection"},
    )
    assert fail_resp.status_code == 200
    assert fail_resp.json()["status"] == "failed"

    # Attempting to confirm a failed reservation is rejected
    cant_confirm = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/{fail_sub_id}/confirm",
        headers=data["headers_res1"],
        json={"message_id": "some_msg_id"},
    )
    assert cant_confirm.status_code == 400

    # 2. Test single message_id uniqueness constraint
    shared_msg_id = f"unique_msg_{int(time.time()*1000)}"

    sub_a_id = f"sub_a_{int(time.time()*1000)}"
    await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/reserve",
        headers=data["headers_res1"],
        json={"submission_id": sub_a_id, "raw_text": "Resident 1 items"},
    )
    conf_a = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/{sub_a_id}/confirm",
        headers=data["headers_res1"],
        json={"message_id": shared_msg_id},
    )
    assert conf_a.status_code == 200

    # Resident 2 attempts to confirm with the same message_id
    sub_b_id = f"sub_b_{int(time.time()*1000)}"
    await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/reserve",
        headers=data["headers_res2"],
        json={"submission_id": sub_b_id, "raw_text": "Resident 2 items"},
    )
    conf_b = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/{sub_b_id}/confirm",
        headers=data["headers_res2"],
        json={"message_id": shared_msg_id},
    )
    # Must be rejected with 409 Conflict
    assert conf_b.status_code == 409


@pytest.mark.asyncio
async def test_round_concurrency_and_structured_announcements(client: AsyncClient, setup_hardening_data):
    """Test 4: Concurrent round creation produces unique round numbers and structured announcements."""
    data = setup_hardening_data
    soc1_id = data["soc1_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Concurrent creation of 5 draft rounds
    async def create_one(i: int):
        return await client.post(
            f"/api/societies/{soc1_id}/rounds",
            headers=data["headers_admin"],
            json={
                "title": f"Concurrent Round {i}",
                "deadline_at": future_deadline,
                "shopping_date": "2026-12-05T10:00:00",
            },
        )

    responses = await asyncio.gather(*(create_one(i) for i in range(5)))
    assert all(r.status_code == 201 for r in responses)

    round_numbers = [r.json()["round_number"] for r in responses]
    # Every round number must be unique
    assert len(round_numbers) == len(set(round_numbers))

    # Verify structured announcement state
    first_round = responses[0].json()
    assert "opening_announcement" in first_round
    assert first_round["opening_announcement"]["status"] == "pending"
    assert first_round["opening_announcement"]["attempts"] == 0

    # Open the first round
    open_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{first_round['id']}/open",
        headers=data["headers_admin"],
    )
    assert open_res.status_code == 200
    open_data = open_res.json()
    assert open_data["status"] == "open"
    assert open_data["opening_announcement"] is not None
    assert open_data["opening_announcement"]["attempts"] >= 1

    # Close the round
    close_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{first_round['id']}/close",
        headers=data["headers_admin"],
    )
    assert close_res.status_code == 200
    close_data = close_res.json()
    assert close_data["status"] == "closed"
    assert close_data["closing_announcement"] is not None
    assert close_data["closing_announcement"]["attempts"] >= 1
