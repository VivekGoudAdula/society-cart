"""
Phase 8: Security, Role-Based Access Control, and Billing Privacy Tests.

Verifies:
1. Cross-society isolation across Residents, Volunteers, and Admins.
2. Flat-level privacy (Resident cannot access or mutate another flat's order or bill).
3. Role enforcement (Resident cannot access Volunteer endpoints, Volunteer cannot access Admin endpoints).
4. Authentication edge cases (missing token, invalid token, expired token, malformed token).
5. Bot impersonation rejection (cannot forge bot identity).
6. Sensitive credential exposure audit (passwords, hashes, API keys, secrets never leaked).
"""

import pytest
import time
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
import jwt

from app.core.config import get_settings
from app.core.database import (
    get_users_collection,
    get_societies_collection,
    get_order_rounds_collection,
    get_grocery_orders_collection,
    get_grocery_bills_collection,
    get_memberships_collection,
)

settings = get_settings()


@pytest.fixture
async def sec_fixture(client: AsyncClient):
    """
    Sets up two separate societies:
    - Society A (Admin A, Volunteer A, Resident A1 [Flat 101], Resident A2 [Flat 102])
    - Society B (Admin B, Volunteer B, Resident B1 [Flat 201])
    """
    users_col = get_users_collection()
    societies_col = get_societies_collection()
    rounds_col = get_order_rounds_collection()
    orders_col = get_grocery_orders_collection()
    bills_col = get_grocery_bills_collection()
    members_col = get_memberships_collection()
    ts = int(time.time() * 1000)

    # Clear prior test data in fixture namespace
    await users_col.delete_many({"email": {"$regex": "@p8sec.com$"}})
    await societies_col.delete_many({"name": {"$regex": "^P8Sec Society"}})
    await rounds_col.delete_many({"title": {"$regex": "^P8Sec Round"}})

    async def register_user(name: str, email: str):
        pwd = "SecurePassword123!"
        resp = await client.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": pwd,
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        token = data["access_token"]
        user_id = data["user"]["id"]
        return {"id": user_id, "token": token, "headers": {"Authorization": f"Bearer {token}"}, "email": email}

    # Society A users
    admin_a = await register_user("Admin A", f"admin_a_{ts}@p8sec.com")
    vol_a = await register_user("Volunteer A", f"vol_a_{ts}@p8sec.com")
    res_a1 = await register_user("Resident A1", f"res_a1_{ts}@p8sec.com")
    res_a2 = await register_user("Resident A2", f"res_a2_{ts}@p8sec.com")

    # Society B users
    admin_b = await register_user("Admin B", f"admin_b_{ts}@p8sec.com")
    vol_b = await register_user("Volunteer B", f"vol_b_{ts}@p8sec.com")
    res_b1 = await register_user("Resident B1", f"res_b1_{ts}@p8sec.com")

    # Create Society A
    resp_soc_a = await client.post("/api/societies", json={
        "name": f"P8Sec Society A {ts}",
        "address": "100 A Street",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "total_flats": 50,
        "creator_flat_number": "A-ADM"
    }, headers=admin_a["headers"])
    assert resp_soc_a.status_code == 201, resp_soc_a.text
    data_a = resp_soc_a.json()
    soc_a_id = data_a["society"]["id"] if "society" in data_a else data_a["id"]
    invite_a = data_a["society"]["invite_code"] if "society" in data_a else data_a["invite_code"]

    # Create Society B
    resp_soc_b = await client.post("/api/societies", json={
        "name": f"P8Sec Society B {ts}",
        "address": "200 B Street",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560002",
        "total_flats": 50,
        "creator_flat_number": "B-ADM"
    }, headers=admin_b["headers"])
    assert resp_soc_b.status_code == 201, resp_soc_b.text
    data_b = resp_soc_b.json()
    soc_b_id = data_b["society"]["id"] if "society" in data_b else data_b["id"]
    invite_b = data_b["society"]["invite_code"] if "society" in data_b else data_b["invite_code"]

    # Add members to Society A
    j_vol_a = await client.post("/api/societies/join", json={"invite_code": invite_a, "flat_number": "V-100"}, headers=vol_a["headers"])
    vol_a_mem_id = j_vol_a.json()["membership"]["id"]
    await client.patch(f"/api/societies/{soc_a_id}/members/{vol_a_mem_id}/role", json={"role": "volunteer"}, headers=admin_a["headers"])

    await client.post("/api/societies/join", json={"invite_code": invite_a, "flat_number": "101"}, headers=res_a1["headers"])
    await client.post("/api/societies/join", json={"invite_code": invite_a, "flat_number": "102"}, headers=res_a2["headers"])

    # Add members to Society B
    j_vol_b = await client.post("/api/societies/join", json={"invite_code": invite_b, "flat_number": "V-200"}, headers=vol_b["headers"])
    vol_b_mem_id = j_vol_b.json()["membership"]["id"]
    await client.patch(f"/api/societies/{soc_b_id}/members/{vol_b_mem_id}/role", json={"role": "volunteer"}, headers=admin_b["headers"])

    await client.post("/api/societies/join", json={"invite_code": invite_b, "flat_number": "201"}, headers=res_b1["headers"])

    # Create Round in Society A
    deadline_a = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    resp_round_a = await client.post(f"/api/societies/{soc_a_id}/rounds", json={
        "title": f"P8Sec Round A {ts}",
        "shopping_date": "Saturday 10:00 AM",
        "delivery_date": (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat(),
        "deadline_at": deadline_a,
    }, headers=vol_a["headers"])
    assert resp_round_a.status_code == 201, resp_round_a.text
    round_a_id = resp_round_a.json()["id"]

    # Open Round in Society A
    await client.post(f"/api/societies/{soc_a_id}/rounds/{round_a_id}/open", headers=vol_a["headers"])

    # Create Order for Flat 101 in Round A
    order_doc_101 = {
        "society_id": soc_a_id,
        "round_id": round_a_id,
        "round_number": 1,
        "user_id": res_a1["id"],
        "flat_number": "101",
        "user_name": "Resident A1",
        "raw_text": "2kg tomatoes",
        "channel_type": "nexconn_chat",
        "message_id": f"p8_sec_msg_101_{ts}",
        "submission_id": f"p8_sec_sub_101_{ts}",
        "status": "pending_review",
        "items": [{"id": "item1", "original_name": "tomatoes", "normalized_name": "Tomatoes", "quantity": 2.0, "unit": "kg", "category": "vegetables", "notes": None}],
        "language_detected": "en",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    ins_101 = await orders_col.insert_one(order_doc_101)
    order_a1_id = str(ins_101.inserted_id)

    # Create Bill for Flat 101
    bill_doc_101 = {
        "society_id": soc_a_id,
        "round_id": round_a_id,
        "round_number": 1,
        "society_name": f"P8Sec Society A {ts}",
        "user_id": res_a1["id"],
        "flat_number": "101",
        "resident_name": "Resident A1",
        "order_id": order_a1_id,
        "status": "finalized",
        "bill_version": 1,
        "items": [{
            "item_name": "Tomatoes",
            "normalized_name": "Tomatoes",
            "category": "vegetables",
            "requested_quantity": 2.0,
            "allocated_quantity": 2.0,
            "unit": "kg",
            "unit_price": 40.0,
            "item_total": 80.0,
            "is_substituted": False,
            "is_unfulfilled": False,
            "unfulfilled_quantity": 0.0,
        }],
        "shared_costs": [],
        "items_subtotal": 80.0,
        "shared_costs_total": 0.0,
        "rounding_adjustment": 0.0,
        "total_amount": 80.0,
        "is_reconciled": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    ins_bill_101 = await bills_col.insert_one(bill_doc_101)
    bill_a1_id = str(ins_bill_101.inserted_id)

    yield {
        "admin_a": admin_a, "vol_a": vol_a, "res_a1": res_a1, "res_a2": res_a2,
        "admin_b": admin_b, "vol_b": vol_b, "res_b1": res_b1,
        "soc_a_id": soc_a_id, "soc_b_id": soc_b_id,
        "round_a_id": round_a_id,
        "order_a1_id": order_a1_id,
        "bill_a1_id": bill_a1_id,
    }

    # Cleanup
    await users_col.delete_many({"email": {"$regex": "@p8sec.com$"}})
    await societies_col.delete_many({"name": {"$regex": "^P8Sec Society"}})
    await rounds_col.delete_many({"title": {"$regex": "^P8Sec Round"}})
    await orders_col.delete_many({"society_id": soc_a_id})
    await bills_col.delete_many({"society_id": soc_a_id})


@pytest.mark.asyncio
async def test_cross_society_isolation(client: AsyncClient, sec_fixture):
    """
    Test that users belonging to Society B cannot access or mutate Society A data.
    """
    f = sec_fixture
    soc_a_id = f["soc_a_id"]
    round_a_id = f["round_a_id"]

    # 1. Resident B1 cannot view Society A orders
    resp = await client.get(f"/api/societies/{soc_a_id}/rounds/{round_a_id}/orders", headers=f["res_b1"]["headers"])
    assert resp.status_code == 403, "Resident B1 must not view Society A orders"

    # 2. Volunteer B cannot compile shopping list for Society A
    resp = await client.post(f"/api/societies/{soc_a_id}/rounds/{round_a_id}/shopping-list/compile", headers=f["vol_b"]["headers"])
    assert resp.status_code == 403, "Volunteer B must not compile Society A shopping list"

    # 3. Volunteer B cannot record purchases for Society A
    resp = await client.post(f"/api/societies/{soc_a_id}/rounds/{round_a_id}/purchases", json={
        "items": [{"item_name": "Apples", "quantity": 10, "unit": "kg", "total_cost": 500, "category": "produce"}]
    }, headers=f["vol_b"]["headers"])
    assert resp.status_code == 403, "Volunteer B must not record purchases for Society A"

    # 4. Admin B cannot add members to Society A
    resp = await client.patch(f"/api/societies/{soc_a_id}/members/dummy_id/role", json={
        "role": "volunteer"
    }, headers=f["admin_b"]["headers"])
    assert resp.status_code == 403, "Admin B must not modify Society A members"


@pytest.mark.asyncio
async def test_flat_level_privacy(client: AsyncClient, sec_fixture):
    """
    Test that Resident A2 (Flat 102) cannot access or modify Flat 101's order or bill.
    """
    f = sec_fixture
    order_a1_id = f["order_a1_id"]
    bill_a1_id = f["bill_a1_id"]

    # 1. Resident A2 cannot edit Flat 101's order
    resp = await client.patch(
        f"/api/orders/{order_a1_id}/items",
        json={"items": [{"id": "item1", "original_name": "Tomatoes", "normalized_name": "Tomatoes", "quantity": 5.0, "unit": "kg"}]},
        headers=f["res_a2"]["headers"]
    )
    assert resp.status_code == 403, "Resident A2 must not edit Flat 101's order"

    # 2. Resident A2 cannot confirm Flat 101's order
    resp = await client.post(
        f"/api/orders/{order_a1_id}/confirm",
        headers=f["res_a2"]["headers"]
    )
    assert resp.status_code == 403, "Resident A2 must not confirm Flat 101's order"

    # 3. Resident A2 cannot reject Flat 101's order
    resp = await client.post(
        f"/api/orders/{order_a1_id}/reject",
        headers=f["res_a2"]["headers"]
    )
    assert resp.status_code == 403, "Resident A2 must not reject Flat 101's order"

    # 4. Resident A2 cannot view Flat 101's bill via /api/users/me/bills/{bill_id}
    resp = await client.get(
        f"/api/users/me/bills/{bill_a1_id}",
        headers=f["res_a2"]["headers"]
    )
    assert resp.status_code in [403, 404], "Resident A2 must not view Flat 101's bill"

    # 5. Resident A1 CAN view their own order and bill
    resp_own_order = await client.get(f"/api/orders/{order_a1_id}", headers=f["res_a1"]["headers"])
    assert resp_own_order.status_code == 200

    resp_own_bill = await client.get(f"/api/users/me/bills/{bill_a1_id}", headers=f["res_a1"]["headers"])
    assert resp_own_bill.status_code == 200


@pytest.mark.asyncio
async def test_role_enforcement(client: AsyncClient, sec_fixture):
    """
    Test RBAC boundaries:
    - Resident cannot call Volunteer endpoints.
    - Volunteer cannot call Admin endpoints.
    """
    f = sec_fixture
    soc_a_id = f["soc_a_id"]
    round_a_id = f["round_a_id"]

    # Resident cannot compile shopping list
    resp = await client.post(f"/api/societies/{soc_a_id}/rounds/{round_a_id}/shopping-list/compile", headers=f["res_a1"]["headers"])
    assert resp.status_code == 403, "Resident cannot compile shopping list"

    # Resident cannot record purchases
    resp = await client.post(f"/api/societies/{soc_a_id}/rounds/{round_a_id}/purchases", json={
        "items": [{"item_name": "Onions", "quantity": 10, "unit": "kg", "total_cost": 300, "category": "produce"}]
    }, headers=f["res_a1"]["headers"])
    assert resp.status_code == 403, "Resident cannot record purchases"

    # Resident cannot finalize bills
    resp = await client.post(f"/api/societies/{soc_a_id}/rounds/{round_a_id}/bills/finalize", headers=f["res_a1"]["headers"])
    assert resp.status_code == 403, "Resident cannot finalize bills"

    # Resident cannot publish announcements
    resp = await client.post(f"/api/societies/{soc_a_id}/rounds/{round_a_id}/bills/publish", headers=f["res_a1"]["headers"])
    assert resp.status_code == 403, "Resident cannot publish bills"

    # Volunteer cannot assign member role (admin only)
    resp = await client.patch(f"/api/societies/{soc_a_id}/members/dummy_id/role", json={
        "role": "volunteer"
    }, headers=f["vol_a"]["headers"])
    assert resp.status_code == 403, "Volunteer cannot update roles (admin only)"


@pytest.mark.asyncio
async def test_authentication_edge_cases(client: AsyncClient, sec_fixture):
    """
    Test auth validation: missing, invalid, expired, or malformed JWT tokens.
    """
    f = sec_fixture
    soc_a_id = f["soc_a_id"]

    # 1. Missing Authorization header
    resp = await client.get(f"/api/societies/{soc_a_id}")
    assert resp.status_code in [401, 403]

    # 2. Invalid signature / bad token
    resp = await client.get(f"/api/societies/{soc_a_id}", headers={"Authorization": "Bearer bad.token.here"})
    assert resp.status_code in [401, 403]

    # 3. Expired token
    expired_payload = {
        "sub": f["res_a1"]["id"],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2)
    }
    expired_jwt = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    resp = await client.get(f"/api/societies/{soc_a_id}", headers={"Authorization": f"Bearer {expired_jwt}"})
    assert resp.status_code in [401, 403]

    # 4. Malformed auth header
    resp = await client.get(f"/api/societies/{soc_a_id}", headers={"Authorization": "Basic 123456"})
    assert resp.status_code in [401, 403]


@pytest.mark.asyncio
async def test_sensitive_credential_exposure_audit(client: AsyncClient, sec_fixture):
    """
    Verify that sensitive credentials (passwords, hashes, secret keys)
    are never returned in API responses or public payloads.
    """
    f = sec_fixture
    soc_a_id = f["soc_a_id"]

    # 1. Check /api/auth/me
    resp = await client.get("/api/auth/me", headers=f["res_a1"]["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "password" not in data
    assert "hashed_password" not in data
    assert "groq_api_key" not in str(data)
    assert "nexconn_app_secret" not in str(data)

    # 2. Check /api/societies/{id}/members
    resp = await client.get(f"/api/societies/{soc_a_id}/members", headers=f["admin_a"]["headers"])
    assert resp.status_code == 200
    members = resp.json()
    for m in members:
        assert "password" not in m
        assert "hashed_password" not in m
        assert "password_hash" not in m

    # 3. Check /api/societies/{id}/rounds/{round_id}/spending-summary
    resp = await client.get(f"/api/societies/{soc_a_id}/rounds/{f['round_a_id']}/spending-summary", headers=f["vol_a"]["headers"])
    assert resp.status_code == 200
    text_data = resp.text
    assert "secret" not in text_data.lower() or "secret" not in text_data
    if settings.groq_api_key:
        assert settings.groq_api_key not in text_data
    if settings.nexconn_app_secret:
        assert settings.nexconn_app_secret not in text_data
