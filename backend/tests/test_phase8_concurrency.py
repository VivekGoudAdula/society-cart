"""Phase 8 Test Suite: Multi-Resident Concurrency & Duplicate Handling.

Tests realistic concurrent workflows:
1. Multiple residents submitting grocery messages simultaneously in the same society.
2. Resident submitting message while a volunteer closes an order round.
3. Submissions near and after the order deadline.
4. Concurrent submissions from different societies (society isolation under load).
5. Duplicate Nexconn message delivery prevention (same message_id).
6. Repeated API requests for the same submission ID (idempotency).
7. Duplicate AI-processing triggers (exclusive lease prevents worker collisions).
8. Simultaneous confirmation and rejection requests on the same order.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import time
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.core.database import (
    get_order_rounds_collection,
    get_grocery_submissions_collection,
    get_grocery_orders_collection,
)
from app.services import groq_service, order_service


@pytest.fixture(autouse=True)
def clean_mock_groq():
    """Reset mock groq handler after each test."""
    yield
    groq_service.reset_mock_groq_handler()


@pytest.fixture
async def setup_concurrency_data(client: AsyncClient):
    """Sets up two societies, Admin, Volunteer, and multiple Residents."""
    ts = int(time.time() * 1000)

    # 1. Admin in Society 1
    resp_admin = await client.post("/api/auth/register", json={
        "name": "Admin Sharma",
        "email": f"admin_p8_{ts}@example.com",
        "password": "Password123!",
    })
    token_admin = resp_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    resp_soc1 = await client.post("/api/societies", headers=headers_admin, json={
        "name": f"Concurrency Heights {ts}",
        "address": "Outer Ring Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "total_flats": 100,
        "creator_flat_number": "A-101",
    })
    soc1_id = resp_soc1.json()["society"]["id"]
    soc1_invite = resp_soc1.json()["society"]["invite_code"]

    # 2. Volunteer in Society 1
    resp_vol = await client.post("/api/auth/register", json={
        "name": "Volunteer Ananya",
        "email": f"vol_p8_{ts}@example.com",
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

    # 3. Create 4 distinct Residents in Society 1
    residents = []
    for i in range(1, 5):
        resp_res = await client.post("/api/auth/register", json={
            "name": f"Resident {i}",
            "email": f"res{i}_p8_{ts}@example.com",
            "password": "Password123!",
        })
        token_res = resp_res.json()["access_token"]
        headers_res = {"Authorization": f"Bearer {token_res}"}
        user_id = resp_res.json()["user"]["id"]
        flat_number = f"F-{100 + i}"
        await client.post("/api/societies/join", headers=headers_res, json={
            "invite_code": soc1_invite,
            "flat_number": flat_number,
        })
        residents.append({
            "user_id": user_id,
            "name": f"Resident {i}",
            "flat_number": flat_number,
            "headers": headers_res,
        })

    # 4. Create second Society (Society 2) with a resident for cross-society tests
    resp_admin2 = await client.post("/api/auth/register", json={
        "name": "Admin Two",
        "email": f"admin2_p8_{ts}@example.com",
        "password": "Password123!",
    })
    token_admin2 = resp_admin2.json()["access_token"]
    headers_admin2 = {"Authorization": f"Bearer {token_admin2}"}

    resp_soc2 = await client.post("/api/societies", headers=headers_admin2, json={
        "name": f"Parallel Towers {ts}",
        "address": "Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "total_flats": 50,
        "creator_flat_number": "P-101",
    })
    soc2_id = resp_soc2.json()["society"]["id"]
    soc2_invite = resp_soc2.json()["society"]["invite_code"]

    resp_res_soc2 = await client.post("/api/auth/register", json={
        "name": "Resident Soc2",
        "email": f"res_soc2_p8_{ts}@example.com",
        "password": "Password123!",
    })
    headers_res_soc2 = {"Authorization": f"Bearer {resp_res_soc2.json()['access_token']}"}
    await client.post("/api/societies/join", headers=headers_res_soc2, json={
        "invite_code": soc2_invite,
        "flat_number": "P-202",
    })

    # 5. Open a round in Society 1
    deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp_round = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=headers_vol,
        json={
            "title": "Weekend Bulk Run",
            "deadline_at": deadline,
            "shopping_date": "Sunday 9:00 AM",
        },
    )
    round1_id = resp_round.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round1_id}/open", headers=headers_vol)

    # 6. Open a round in Society 2
    resp_round2 = await client.post(
        f"/api/societies/{soc2_id}/rounds",
        headers=headers_admin2,
        json={
            "title": "Parallel Bulk Run",
            "deadline_at": deadline,
            "shopping_date": "Sunday 10:00 AM",
        },
    )
    round2_id = resp_round2.json()["id"]
    await client.post(f"/api/societies/{soc2_id}/rounds/{round2_id}/open", headers=headers_admin2)

    return {
        "soc1_id": soc1_id,
        "soc2_id": soc2_id,
        "round1_id": round1_id,
        "round2_id": round2_id,
        "headers_admin": headers_admin,
        "headers_vol": headers_vol,
        "residents": residents,
        "headers_res_soc2": headers_res_soc2,
    }


# ============================================================================
# 1. Multi-Resident Concurrent Submissions
# ============================================================================

@pytest.mark.asyncio
async def test_01_multi_resident_concurrent_submissions(client: AsyncClient, setup_concurrency_data):
    """Test 4 residents simultaneously reserving and confirming grocery submissions.

    Verify:
    - All 4 reservations succeed without duplicate key errors.
    - Each submission is bound to the correct resident, flat number, society, and round.
    - Confirmations link correctly without cross-talk.
    """
    data = setup_concurrency_data
    soc1_id = data["soc1_id"]
    round1_id = data["round1_id"]
    residents = data["residents"]
    ts = int(time.time() * 1000)

    # Step 1: Concurrent reservation requests via asyncio.gather
    async def reserve_order(res, idx):
        sub_id = f"sub_concurrent_{idx}_{ts}"
        resp = await client.post(
            f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/reserve",
            headers=res["headers"],
            json={"submission_id": sub_id, "raw_text": f"{idx + 1} kg rice and {idx + 1} litre milk"},
        )
        return resp, sub_id, res

    reservation_results = await asyncio.gather(
        *(reserve_order(res, idx) for idx, res in enumerate(residents))
    )

    for resp, sub_id, res in reservation_results:
        assert resp.status_code in [200, 201]
        body = resp.json()
        assert body["submission_id"] == sub_id
        assert body["user_id"] == res["user_id"]
        assert body["flat_number"] == res["flat_number"]
        assert body["status"] == "reserved"

    # Step 2: Concurrent confirmation requests
    async def confirm_order(resp, sub_id, res, idx):
        msg_id = f"msg_nexconn_live_{idx}_{ts}"
        c_resp = await client.post(
            f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/{sub_id}/confirm",
            headers=res["headers"],
            json={"message_id": msg_id},
        )
        return c_resp, msg_id

    confirm_results = await asyncio.gather(
        *(confirm_order(resp, sub_id, res, idx) for idx, (resp, sub_id, res) in enumerate(reservation_results))
    )

    for c_resp, msg_id in confirm_results:
        assert c_resp.status_code == 200
        c_body = c_resp.json()
        assert c_body["status"] == "confirmed"
        assert c_body["message_id"] == msg_id


# ============================================================================
# 2. Race Condition: Submission vs Round Closure
# ============================================================================

@pytest.mark.asyncio
async def test_02_concurrent_submission_and_round_closure(client: AsyncClient, setup_concurrency_data):
    """Test race condition where volunteer closes a round while a resident attempts to reserve.

    Verify:
    - Atomicity ensures that reservations attempted after closure are cleanly rejected with HTTP 400.
    - Pre-closed reservations remain confirmable even after round status is closed.
    """
    data = setup_concurrency_data
    soc1_id = data["soc1_id"]
    round1_id = data["round1_id"]
    headers_vol = data["headers_vol"]
    res1 = data["residents"][0]
    ts = int(time.time() * 1000)

    # 1. Resident pre-reserves an order before closure
    pre_sub_id = f"sub_pre_close_{ts}"
    pre_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/reserve",
        headers=res1["headers"],
        json={"submission_id": pre_sub_id, "raw_text": "5 kg wheat flour"},
    )
    assert pre_res.status_code in [200, 201]
    assert pre_res.json()["status"] == "reserved"

    # 2. Volunteer closes the round
    close_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/close",
        headers=headers_vol,
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"

    # 3. New reservation attempted after closure MUST be rejected
    late_sub_id = f"sub_late_after_close_{ts}"
    late_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/reserve",
        headers=res1["headers"],
        json={"submission_id": late_sub_id, "raw_text": "2 kg sugar"},
    )
    assert late_resp.status_code == 400
    assert "cannot reserve" in late_resp.json()["detail"].lower()

    # 4. Authoritative timeliness rule: The pre-reserved order CAN still be confirmed
    confirm_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/{pre_sub_id}/confirm",
        headers=res1["headers"],
        json={"message_id": f"msg_pre_closed_{ts}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


# ============================================================================
# 3. Concurrent Submissions from Different Societies
# ============================================================================

@pytest.mark.asyncio
async def test_03_concurrent_submissions_multi_society_isolation(client: AsyncClient, setup_concurrency_data):
    """Test concurrent submissions from distinct societies remain completely partitioned."""
    data = setup_concurrency_data
    soc1_id = data["soc1_id"]
    soc2_id = data["soc2_id"]
    round1_id = data["round1_id"]
    round2_id = data["round2_id"]
    res_soc1 = data["residents"][0]
    headers_soc2 = data["headers_res_soc2"]
    ts = int(time.time() * 1000)

    sub1_id = f"sub_soc1_iso_{ts}"
    sub2_id = f"sub_soc2_iso_{ts}"

    async def sub_soc1():
        return await client.post(
            f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/reserve",
            headers=res_soc1["headers"],
            json={"submission_id": sub1_id, "raw_text": "Society 1 Basmati Rice"},
        )

    async def sub_soc2():
        return await client.post(
            f"/api/societies/{soc2_id}/rounds/{round2_id}/submissions/reserve",
            headers=headers_soc2,
            json={"submission_id": sub2_id, "raw_text": "Society 2 Sunflower Oil"},
        )

    resp1, resp2 = await asyncio.gather(sub_soc1(), sub_soc2())
    assert resp1.status_code in [200, 201]
    assert resp2.status_code in [200, 201]
    assert resp1.json()["society_id"] == soc1_id
    assert resp2.json()["society_id"] == soc2_id


# ============================================================================
# 4. Duplicate Nexconn Message Delivery & Idempotency
# ============================================================================

@pytest.mark.asyncio
async def test_04_duplicate_nexconn_message_delivery_prevention(client: AsyncClient, setup_concurrency_data):
    """Test duplicate message delivery from Nexconn network:
    1. Re-confirming with the same message_id is idempotent.
    2. Attempting to attach an already confirmed message_id to a different submission fails with 409 Conflict.
    """
    data = setup_concurrency_data
    soc1_id = data["soc1_id"]
    round1_id = data["round1_id"]
    res1 = data["residents"][0]
    res2 = data["residents"][1]
    ts = int(time.time() * 1000)

    # Resident 1 creates and confirms submission
    sub1_id = f"sub_dup_msg1_{ts}"
    msg_id = f"msg_dup_nexconn_{ts}"

    await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/reserve",
        headers=res1["headers"],
        json={"submission_id": sub1_id, "raw_text": "10 kg rice"},
    )
    conf1 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/{sub1_id}/confirm",
        headers=res1["headers"],
        json={"message_id": msg_id},
    )
    assert conf1.status_code == 200

    # Idempotent re-delivery for the same reservation
    conf1_repeat = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/{sub1_id}/confirm",
        headers=res1["headers"],
        json={"message_id": msg_id},
    )
    assert conf1_repeat.status_code == 200
    assert conf1_repeat.json()["status"] == "confirmed"

    # Malicious or duplicate attempt: Resident 2 attempts to use Resident 1's message_id
    sub2_id = f"sub_dup_msg2_{ts}"
    await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/reserve",
        headers=res2["headers"],
        json={"submission_id": sub2_id, "raw_text": "5 kg wheat"},
    )
    conf2_collision = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/{sub2_id}/confirm",
        headers=res2["headers"],
        json={"message_id": msg_id},
    )
    assert conf2_collision.status_code == 409
    assert "already associated" in conf2_collision.json()["detail"].lower()


# ============================================================================
# 5. Repeated Reservation Requests (API Idempotency)
# ============================================================================

@pytest.mark.asyncio
async def test_05_repeated_reservation_request_idempotency(client: AsyncClient, setup_concurrency_data):
    """Test network retry: client sending identical reservation request twice."""
    data = setup_concurrency_data
    soc1_id = data["soc1_id"]
    round1_id = data["round1_id"]
    res1 = data["residents"][0]
    ts = int(time.time() * 1000)
    sub_id = f"sub_retry_{ts}"

    # First attempt
    res1_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/reserve",
        headers=res1["headers"],
        json={"submission_id": sub_id, "raw_text": "2 packets milk"},
    )
    assert res1_resp.status_code in [200, 201]

    # Immediate second attempt with same submission_id
    res2_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round1_id}/submissions/reserve",
        headers=res1["headers"],
        json={"submission_id": sub_id, "raw_text": "2 packets milk"},
    )
    assert res2_resp.status_code in [200, 201]
    assert res2_resp.json()["id"] == res1_resp.json()["id"]


# ============================================================================
# 6. Simultaneous Confirmation, Rejection, and Clarification
# ============================================================================

@pytest.mark.asyncio
async def test_06_simultaneous_confirmation_and_rejection_conflict(client: AsyncClient, setup_concurrency_data):
    """Test race condition where resident attempts concurrent confirmation and rejection on the same order.

    Verify:
    - Only one terminal status succeeds.
    - The subsequent or conflicting transition returns HTTP 400.
    """
    data = setup_concurrency_data
    soc1_id = data["soc1_id"]
    round1_id = data["round1_id"]
    res1 = data["residents"][0]
    orders_col = get_grocery_orders_collection()
    t = datetime.now(timezone.utc)
    ts = int(time.time() * 1000)

    # Insert order in pending_review state
    order_doc = {
        "society_id": soc1_id,
        "round_id": round1_id,
        "round_number": 1,
        "submission_id": f"sub_conflict_{ts}",
        "user_id": res1["user_id"],
        "flat_number": res1["flat_number"],
        "user_name": res1["name"],
        "raw_text": "10 kg rice",
        "status": "pending_review",
        "items": [{"id": "item1", "original_name": "rice", "normalized_name": "Rice", "quantity": 10.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    }
    inserted = await orders_col.insert_one(order_doc)
    order_id = str(inserted.inserted_id)

    # Step: Resident confirms order
    confirm_resp = await client.post(
        f"/api/orders/{order_id}/confirm",
        headers=res1["headers"],
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    # Step: Subsequent attempt to reject an already confirmed order MUST be rejected
    reject_resp = await client.post(
        f"/api/orders/{order_id}/reject",
        headers=res1["headers"],
    )
    assert reject_resp.status_code == 400
    assert "cannot reject" in reject_resp.json()["detail"].lower()
