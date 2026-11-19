"""Automated test suite for Phase 4: Grocery Order Rounds.

Covers all 16 required test scenarios:
1. Admin creates a round.
2. Volunteer creates a round.
3. Resident cannot create a round.
4. Admin opens a round.
5. Volunteer opens a round.
6. Resident cannot open a round.
7. Only one round can be open per society.
8. Different societies can have separate open rounds.
9. Round closure works.
10. Closed rounds cannot be reopened incorrectly.
11. Expired rounds are automatically closed.
12. Duplicate closure announcements are prevented.
13. Cross-society access is rejected.
14. Closed rounds reject grocery submissions.
15. Active round API returns the correct round.
16. Round history is scoped to the society.
"""

from datetime import datetime, timedelta, timezone
import time
import pytest
from httpx import AsyncClient
from bson import ObjectId
from app.core.database import get_order_rounds_collection
from app.services.round_scheduler import check_expired_rounds_once


@pytest.fixture
async def setup_phase4_data(client: AsyncClient):
    """Sets up two societies, admin, volunteer, resident in society 1, and resident in society 2."""
    ts = int(time.time() * 1000)

    # 1. Admin in Society 1
    resp_admin = await client.post("/api/auth/register", json={
        "name": "Admin Sharma",
        "email": f"admin_{ts}@example.com",
        "password": "Password123!",
    })
    token_admin = resp_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # Society 1
    resp_soc1 = await client.post("/api/societies", headers=headers_admin, json={
        "name": f"Palm Grove Heights {ts}",
        "address": "Road 10, Banjara Hills",
        "city": "Hyderabad",
        "state": "Telangana",
        "total_flats": 50,
        "creator_flat_number": "A-101",
    })
    soc1_data = resp_soc1.json()
    soc1_id = soc1_data["society"]["id"]
    soc1_invite = soc1_data["society"]["invite_code"]

    # 2. Volunteer in Society 1
    resp_vol = await client.post("/api/auth/register", json={
        "name": "Volunteer Priya",
        "email": f"volunteer_{ts}@example.com",
        "password": "Password123!",
    })
    token_vol = resp_vol.json()["access_token"]
    headers_vol = {"Authorization": f"Bearer {token_vol}"}

    # Join Society 1
    join_vol = await client.post("/api/societies/join", headers=headers_vol, json={
        "invite_code": soc1_invite,
        "flat_number": "B-204",
    })
    vol_membership_id = join_vol.json()["membership"]["id"]

    # Admin promotes volunteer
    await client.patch(
        f"/api/societies/{soc1_id}/members/{vol_membership_id}/role",
        headers=headers_admin,
        json={"role": "volunteer"},
    )

    # 3. Ordinary Resident in Society 1
    resp_res = await client.post("/api/auth/register", json={
        "name": "Resident Rohan",
        "email": f"rohan_{ts}@example.com",
        "password": "Password123!",
    })
    token_res = resp_res.json()["access_token"]
    headers_res = {"Authorization": f"Bearer {token_res}"}

    # Join Society 1 as resident
    await client.post("/api/societies/join", headers=headers_res, json={
        "invite_code": soc1_invite,
        "flat_number": "C-305",
    })

    # 4. Separate Resident in Society 2
    resp_res2 = await client.post("/api/auth/register", json={
        "name": "Other Society Resident",
        "email": f"other_{ts}@example.com",
        "password": "Password123!",
    })
    token_res2 = resp_res2.json()["access_token"]
    headers_res2 = {"Authorization": f"Bearer {token_res2}"}

    resp_soc2 = await client.post("/api/societies", headers=headers_res2, json={
        "name": f"Green Valley Estates {ts}",
        "address": "Gachibowli",
        "city": "Hyderabad",
        "state": "Telangana",
        "total_flats": 40,
        "creator_flat_number": "GV-101",
    })
    soc2_id = resp_soc2.json()["society"]["id"]

    return {
        "soc1_id": soc1_id,
        "soc2_id": soc2_id,
        "headers_admin": headers_admin,
        "headers_vol": headers_vol,
        "headers_res": headers_res,
        "headers_res2": headers_res2,
    }


@pytest.mark.asyncio
async def test_scenarios_1_to_3_round_creation_permissions(client: AsyncClient, setup_phase4_data):
    """Scenario 1: Admin creates round.
    Scenario 2: Volunteer creates round.
    Scenario 3: Resident cannot create round (403).
    """
    data = setup_phase4_data
    soc1_id = data["soc1_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # 1. Admin creates round
    resp_admin_create = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={
            "title": "Admin Round #1",
            "description": "Weekly grocery run",
            "deadline_at": future_deadline,
            "shopping_date": "Saturday 10:00 AM",
        },
    )
    assert resp_admin_create.status_code == 201
    res_data = resp_admin_create.json()
    assert res_data["title"] == "Admin Round #1"
    assert res_data["status"] == "draft"
    assert res_data["round_number"] == 1

    # 2. Volunteer creates round
    resp_vol_create = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_vol"],
        json={
            "title": "Volunteer Round #2",
            "description": "Mid-week run",
            "deadline_at": future_deadline,
            "shopping_date": "Sunday 4:00 PM",
        },
    )
    assert resp_vol_create.status_code == 201
    assert resp_vol_create.json()["round_number"] == 2
    assert resp_vol_create.json()["status"] == "draft"

    # 3. Resident cannot create round
    resp_res_create = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_res"],
        json={
            "title": "Resident Illegal Round",
            "deadline_at": future_deadline,
            "shopping_date": "Tomorrow",
        },
    )
    assert resp_res_create.status_code == 403


@pytest.mark.asyncio
async def test_scenarios_4_to_6_round_opening_permissions(client: AsyncClient, setup_phase4_data):
    """Scenario 4: Admin opens a round.
    Scenario 5: Volunteer opens a round.
    Scenario 6: Resident cannot open a round (403).
    """
    data = setup_phase4_data
    soc1_id = data["soc1_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Create draft round
    create_res = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={
            "title": "Opening Test Round",
            "deadline_at": future_deadline,
            "shopping_date": "Saturday",
        },
    )
    round_id = create_res.json()["id"]

    # 6. Resident cannot open
    resp_res_open = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/open",
        headers=data["headers_res"],
    )
    assert resp_res_open.status_code == 403

    # 4. Admin opens round
    resp_admin_open = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/open",
        headers=data["headers_admin"],
    )
    assert resp_admin_open.status_code == 200
    assert resp_admin_open.json()["status"] == "open"
    assert resp_admin_open.json()["opened_at"] is not None

    # Close it so volunteer can test opening another round
    await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/close",
        headers=data["headers_admin"],
    )

    # 5. Volunteer opens another round
    round2 = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_vol"],
        json={
            "title": "Volunteer Open Test",
            "deadline_at": future_deadline,
            "shopping_date": "Sunday",
        },
    )
    round2_id = round2.json()["id"]

    resp_vol_open = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round2_id}/open",
        headers=data["headers_vol"],
    )
    assert resp_vol_open.status_code == 200
    assert resp_vol_open.json()["status"] == "open"


@pytest.mark.asyncio
async def test_scenarios_7_and_8_simultaneous_open_rounds_and_multi_society(client: AsyncClient, setup_phase4_data):
    """Scenario 7: Only one round can be open per society (409 Conflict).
    Scenario 8: Different societies can have separate open rounds simultaneously.
    """
    data = setup_phase4_data
    soc1_id = data["soc1_id"]
    soc2_id = data["soc2_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Create two rounds in Society 1
    r1 = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={"title": "Soc1 Round A", "deadline_at": future_deadline, "shopping_date": "Sat"},
    )
    r1_id = r1.json()["id"]

    r2 = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={"title": "Soc1 Round B", "deadline_at": future_deadline, "shopping_date": "Sun"},
    )
    r2_id = r2.json()["id"]

    # Open Round A in Society 1
    open_r1 = await client.post(f"/api/societies/{soc1_id}/rounds/{r1_id}/open", headers=data["headers_admin"])
    assert open_r1.status_code == 200

    # 7. Attempting to open Round B in Society 1 must fail with 409 Conflict
    open_r2 = await client.post(f"/api/societies/{soc1_id}/rounds/{r2_id}/open", headers=data["headers_admin"])
    assert open_r2.status_code == 409

    # 8. Society 2 can open its own round simultaneously
    r_soc2 = await client.post(
        f"/api/societies/{soc2_id}/rounds",
        headers=data["headers_res2"],  # Creator is admin of Soc2
        json={"title": "Soc2 Round Alpha", "deadline_at": future_deadline, "shopping_date": "Friday"},
    )
    r_soc2_id = r_soc2.json()["id"]
    open_soc2 = await client.post(f"/api/societies/{soc2_id}/rounds/{r_soc2_id}/open", headers=data["headers_res2"])
    assert open_soc2.status_code == 200
    assert open_soc2.json()["status"] == "open"


@pytest.mark.asyncio
async def test_scenarios_9_and_10_round_closure_and_reopen_prevention(client: AsyncClient, setup_phase4_data):
    """Scenario 9: Round closure works.
    Scenario 10: Closed rounds cannot be closed again or reopened incorrectly.
    """
    data = setup_phase4_data
    soc1_id = data["soc1_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    r = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={"title": "Closure Test", "deadline_at": future_deadline, "shopping_date": "Sat"},
    )
    round_id = r.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=data["headers_admin"])

    # 9. Close round
    close_resp = await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/close", headers=data["headers_admin"])
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"
    assert close_resp.json()["closed_at"] is not None

    # 10. Cannot close an already closed round
    reclose_resp = await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/close", headers=data["headers_admin"])
    assert reclose_resp.status_code == 400

    # Cannot reopen closed round
    reopen_resp = await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=data["headers_admin"])
    assert reopen_resp.status_code == 400


@pytest.mark.asyncio
async def test_scenarios_11_and_12_automatic_expiry_and_duplicate_announcements(client: AsyncClient, setup_phase4_data):
    """Scenario 11: Expired rounds are automatically closed.
    Scenario 12: Duplicate closure announcements are prevented.
    """
    data = setup_phase4_data
    soc1_id = data["soc1_id"]
    rounds_col = get_order_rounds_collection()

    # Insert an open round whose deadline has already elapsed (simulating elapsed time)
    expired_deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
    doc = {
        "society_id": soc1_id,
        "round_number": 99,
        "title": "Expired Round Test",
        "status": "open",
        "created_by": "test",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "opened_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "deadline_at": expired_deadline,
        "shopping_date": "Today",
        "closed_at": None,
        "updated_at": datetime.now(timezone.utc),
        "opening_announcement_sent": True,
        "closing_announcement_sent": False,
    }
    insert_res = await rounds_col.insert_one(doc)
    round_id = str(insert_res.inserted_id)

    # 11. Run scheduler check
    closed_count = await check_expired_rounds_once()
    assert closed_count >= 1

    # Verify document is closed
    updated_doc = await rounds_col.find_one({"_id": ObjectId(round_id)})
    assert updated_doc["status"] == "closed"
    assert updated_doc["closed_at"] is not None

    # 12. Run scheduler again: it must not close it again or duplicate announcements
    second_run_count = await check_expired_rounds_once()
    assert second_run_count == 0


@pytest.mark.asyncio
async def test_scenario_13_cross_society_rejection(client: AsyncClient, setup_phase4_data):
    """Scenario 13: Cross-society access is rejected with 403 Forbidden."""
    data = setup_phase4_data
    soc1_id = data["soc1_id"]
    headers_res2 = data["headers_res2"]  # Resident from Society 2

    # Resident 2 tries to access Society 1 rounds
    resp = await client.get(f"/api/societies/{soc1_id}/rounds", headers=headers_res2)
    assert resp.status_code == 403

    # Resident 2 tries to get active round of Society 1
    resp_active = await client.get(f"/api/societies/{soc1_id}/rounds/active", headers=headers_res2)
    assert resp_active.status_code == 403


@pytest.mark.asyncio
async def test_scenarios_14_to_16_submissions_active_and_history(client: AsyncClient, setup_phase4_data):
    """Scenario 14: Closed rounds reject grocery submissions.
    Scenario 15: Active round API returns the correct round.
    Scenario 16: Round history is scoped to the society.
    """
    data = setup_phase4_data
    soc1_id = data["soc1_id"]
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Create & open a round
    create_res = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=data["headers_admin"],
        json={"title": "Active Drive 2026", "deadline_at": future_deadline, "shopping_date": "Sunday"},
    )
    round_id = create_res.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=data["headers_admin"])

    # 15. Active round API returns this round
    resp_active = await client.get(f"/api/societies/{soc1_id}/rounds/active", headers=data["headers_res"])
    assert resp_active.status_code == 200
    assert resp_active.json() is not None
    assert resp_active.json()["id"] == round_id
    assert resp_active.json()["status"] == "open"

    # Resident submits grocery items while round is open
    sub_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_res"],
        json={
            "message_id": "nexconn_msg_101",
            "raw_text": "5 kg rice and 2L oil",
        },
    )
    assert sub_res.status_code == 201
    assert sub_res.json()["flat_number"] == "C-305"
    assert sub_res.json()["round_id"] == round_id

    # Close the round
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/close", headers=data["headers_admin"])

    # 14. Submissions are rejected after closure
    sub_fail = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions",
        headers=data["headers_res"],
        json={
            "message_id": "nexconn_msg_102",
            "raw_text": "1 packet bread",
        },
    )
    assert sub_fail.status_code == 400

    # Active round is now None/null
    resp_active_closed = await client.get(f"/api/societies/{soc1_id}/rounds/active", headers=data["headers_res"])
    assert resp_active_closed.status_code == 200
    assert resp_active_closed.json() is None

    # 16. Round history is scoped to society and sorted descending
    history_res = await client.get(f"/api/societies/{soc1_id}/rounds", headers=data["headers_res"])
    assert history_res.status_code == 200
    items = history_res.json()["items"]
    assert len(items) >= 1
    # Check that every item in history belongs to soc1_id
    for item in items:
        assert item["society_id"] == soc1_id
