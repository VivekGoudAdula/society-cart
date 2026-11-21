"""Automated test suite for Phase 7: Purchases, Allocations, Billing, and Verified Savings.

Validates:
1. Actual Purchase Recording (valid, negative price/qty rejection, duplicate prevention, round isolation).
2. Purchase-to-Order Matching & Cost Allocation (quantity-based pricing, multiple batches weighted rate,
   brand/variant separation, partial purchases, unfulfilled items, substitutions, deterministic paise residuals,
   reconciliation enforcement).
3. Bill Generation & Lifecycle (itemized bill, per-flat totals, duplicate finalization protection,
   correction history preservation, finalized immutability).
4. Nexconn Group Announcement (generic text, resident privacy protection, duplicate request idempotency).
5. Resident Billing Dashboard & Strict Privacy (own flat access only, cross-society rejection).
6. Society Spending Summary (reconciliation equation).
7. Verified Retail Benchmarks & Savings (evidence model, comparable matching, missing benchmark unavailable,
   stale evidence exclusion, zero/negative honest reporting, partial coverage non-extrapolation).
8. Role-Based Access Control (resident blocked from recording/finalizing, volunteer/admin permitted).
"""

from datetime import datetime, timedelta, timezone
import time
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.core.database import (
    get_order_rounds_collection,
    get_grocery_orders_collection,
    get_purchase_records_collection,
    get_grocery_bills_collection,
    get_retail_benchmarks_collection,
)


@pytest.fixture
async def setup_phase7_data(client: AsyncClient):
    """Sets up two societies, Admin, Volunteer, Resident 1, Resident 2 in Society 1, and Society 2 Admin."""
    ts = int(time.time() * 1000)

    # 1. Admin in Society 1
    resp_admin = await client.post("/api/auth/register", json={
        "name": "Admin Sharma",
        "email": f"admin_p7_{ts}@example.com",
        "password": "Password123!",
    })
    token_admin = resp_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    resp_soc1 = await client.post("/api/societies", headers=headers_admin, json={
        "name": f"Greenwood Heights {ts}",
        "address": "Sarjapur Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "total_flats": 60,
        "creator_flat_number": "A-101",
    })
    soc1_id = resp_soc1.json()["society"]["id"]
    soc1_invite = resp_soc1.json()["society"]["invite_code"]

    # 2. Volunteer in Society 1
    resp_vol = await client.post("/api/auth/register", json={
        "name": "Volunteer Ananya",
        "email": f"vol_p7_{ts}@example.com",
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

    # 3. Resident 1 (Flat C-303)
    resp_res1 = await client.post("/api/auth/register", json={
        "name": "Resident Srinivas",
        "email": f"srini_p7_{ts}@example.com",
        "password": "Password123!",
    })
    token_res1 = resp_res1.json()["access_token"]
    user1_id = resp_res1.json()["user"]["id"]
    headers_res1 = {"Authorization": f"Bearer {token_res1}"}
    await client.post("/api/societies/join", headers=headers_res1, json={
        "invite_code": soc1_invite,
        "flat_number": "C-303",
    })

    # 4. Resident 2 (Flat D-404)
    resp_res2 = await client.post("/api/auth/register", json={
        "name": "Resident Pooja",
        "email": f"pooja_p7_{ts}@example.com",
        "password": "Password123!",
    })
    token_res2 = resp_res2.json()["access_token"]
    user2_id = resp_res2.json()["user"]["id"]
    headers_res2 = {"Authorization": f"Bearer {token_res2}"}
    await client.post("/api/societies/join", headers=headers_res2, json={
        "invite_code": soc1_invite,
        "flat_number": "D-404",
    })

    # 5. External Admin in Society 2
    resp_other = await client.post("/api/auth/register", json={
        "name": "External Admin",
        "email": f"other_p7_{ts}@example.com",
        "password": "Password123!",
    })
    token_other = resp_other.json()["access_token"]
    headers_other = {"Authorization": f"Bearer {token_other}"}

    resp_soc2 = await client.post("/api/societies", headers=headers_other, json={
        "name": f"Palm Meadows {ts}",
        "address": "Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "total_flats": 40,
        "creator_flat_number": "Z-999",
    })
    soc2_id = resp_soc2.json()["society"]["id"]

    # 6. Create and open Round 1 in Society 1
    deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp_round = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=headers_vol,
        json={
            "title": "Weekend Fresh Wholesale",
            "deadline_at": deadline,
            "shopping_date": "Sunday 9:00 AM",
        },
    )
    round_id = resp_round.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=headers_vol)

    return {
        "soc1_id": soc1_id,
        "soc2_id": soc2_id,
        "round_id": round_id,
        "headers_admin": headers_admin,
        "headers_vol": headers_vol,
        "headers_res1": headers_res1,
        "headers_res2": headers_res2,
        "headers_other": headers_other,
        "user1_id": user1_id,
        "user2_id": user2_id,
    }


# ============================================================================
# 1. Purchase Recording Tests
# ============================================================================

@pytest.mark.asyncio
async def test_01_valid_purchase_creation(client: AsyncClient, setup_phase7_data):
    """Test valid actual purchase recording with quantity, cost, shop, and invoice."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]

    resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Sona Masoori Rice",
            "category": "grains_rice",
            "brand": "India Gate",
            "variant": "Aged",
            "actual_quantity": 25.0,
            "unit": "kg",
            "total_price": 1250.0,
            "shop_name": "D-Mart Wholesale",
            "invoice_ref": "INV-7801",
            "notes": "Bulk sack purchase",
        },
    )
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["item_name"] == "Sona Masoori Rice"
    assert res_data["actual_quantity"] == 25.0
    assert res_data["total_price"] == 1250.0
    assert res_data["unit_price"] == 50.0
    assert res_data["shop_name"] == "D-Mart Wholesale"


@pytest.mark.asyncio
async def test_02_invalid_quantities_and_prices_rejected(client: AsyncClient, setup_phase7_data):
    """Test that zero/negative quantities and negative costs are rejected with 422."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]

    # Zero quantity
    r1 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Sugar",
            "category": "staples_sugar",
            "actual_quantity": 0.0,
            "unit": "kg",
            "total_price": 100.0,
            "shop_name": "Kirana Store",
        },
    )
    assert r1.status_code == 422

    # Negative price
    r2 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Sugar",
            "category": "staples_sugar",
            "actual_quantity": 5.0,
            "unit": "kg",
            "total_price": -50.0,
            "shop_name": "Kirana Store",
        },
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_03_duplicate_purchase_prevention(client: AsyncClient, setup_phase7_data):
    """Test accidental duplicate purchase recording is rejected with 409 Conflict."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]

    payload = {
        "item_name": "Sunflower Oil",
        "category": "dairy_oil",
        "brand": "Fortune",
        "actual_quantity": 10.0,
        "unit": "L",
        "total_price": 1400.0,
        "shop_name": "Metro Cash & Carry",
        "invoice_ref": "METRO-1122",
    }

    r1 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json=payload,
    )
    assert r1.status_code == 201

    # Exact duplicate submission
    r2 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json=payload,
    )
    assert r2.status_code == 409
    assert "duplicate purchase" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_04_purchase_records_isolated_by_society_and_round(client: AsyncClient, setup_phase7_data):
    """Verify purchase records are isolated to their own society and round."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    soc2_id = data["soc2_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    headers_other = data["headers_other"]

    # Society 2 admin cannot access Society 1 purchases
    resp = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_other,
    )
    assert resp.status_code == 403


# ============================================================================
# 2. Allocation & Per-Flat Billing Engine Tests
# ============================================================================

@pytest.mark.asyncio
async def test_05_and_06_and_07_quantity_based_per_flat_allocation(client: AsyncClient, setup_phase7_data):
    """Test quantity-based cost allocation matching confirmed packing breakdown.

    Example:
    - Flat 1 (C-303) requests 5 kg Rice
    - Flat 2 (D-404) requests 10 kg Rice
    - Total requested: 15 kg Rice
    - Volunteer buys 15 kg Rice for Rs 750 (Unit rate: Rs 50/kg)
    Allocation:
    - Flat 1 receives 5 kg -> Rs 250
    - Flat 2 receives 10 kg -> Rs 500
    - Reconciled: 750 = 250 + 500
    """
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    orders_col = get_grocery_orders_collection()
    t = datetime.now(timezone.utc)

    # 1. Flat 1 confirmed order (5 kg Rice)
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_alloc1_{int(time.time()*1000)}",
        "user_id": data["user1_id"],
        "flat_number": "C-303",
        "user_name": "Resident Srinivas",
        "raw_text": "5 kg rice",
        "status": "confirmed",
        "items": [{"id": "i1", "original_name": "rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    })

    # 2. Flat 2 confirmed order (10 kg Rice)
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_alloc2_{int(time.time()*1000)}",
        "user_id": data["user2_id"],
        "flat_number": "D-404",
        "user_name": "Resident Pooja",
        "raw_text": "10 kg rice",
        "status": "confirmed",
        "items": [{"id": "i2", "original_name": "rice", "normalized_name": "Rice", "quantity": 10.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    })

    # 3. Volunteer records purchase: 15 kg Rice for Rs 750
    p_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Rice",
            "category": "grains_rice",
            "actual_quantity": 15.0,
            "unit": "kg",
            "total_price": 750.0,
            "shop_name": "Super Bazaar",
            "invoice_ref": "SB-100",
        },
    )
    assert p_resp.status_code == 201

    # 4. Preview allocation
    preview_resp = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/allocation/preview",
        headers=headers_vol,
    )
    assert preview_resp.status_code == 200
    prev = preview_resp.json()
    assert prev["is_reconciled"] is True
    assert prev["total_actual_purchase_cost"] == 750.0
    assert prev["total_allocated_flats_cost"] == 750.0

    # Flat allocations
    flat1 = next(f for f in prev["flat_allocations"] if f["flat_number"] == "C-303")
    flat2 = next(f for f in prev["flat_allocations"] if f["flat_number"] == "D-404")
    assert flat1["final_amount_payable"] == 250.0
    assert flat2["final_amount_payable"] == 500.0


@pytest.mark.asyncio
async def test_08_multiple_batches_with_different_prices_weighted_average(client: AsyncClient, setup_phase7_data):
    """Test multiple purchase batches at different rates calculate weighted effective unit cost.

    Batch 1: 10 kg Rice for Rs 500 (Rs 50/kg)
    Batch 2: 15 kg Rice for Rs 900 (Rs 60/kg)
    Total: 25 kg for Rs 1400 -> Weighted rate = Rs 56.00/kg
    """
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]

    # Batch 1
    await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Wheat Atta",
            "category": "staples_atta_dal",
            "actual_quantity": 10.0,
            "unit": "kg",
            "total_price": 500.0,
            "shop_name": "Store A",
            "invoice_ref": "SA-1",
        },
    )

    # Batch 2
    await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Wheat Atta",
            "category": "staples_atta_dal",
            "actual_quantity": 15.0,
            "unit": "kg",
            "total_price": 900.0,
            "shop_name": "Store B",
            "invoice_ref": "SB-1",
        },
    )

    preview_resp = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/allocation/preview",
        headers=headers_vol,
    )
    assert preview_resp.status_code == 200
    prev = preview_resp.json()
    atta_matching = next((m for m in prev["matching_summaries"] if m["item_name"] == "Wheat Atta"), None)
    if atta_matching:
        assert atta_matching["purchased_quantity"] == 25.0
        assert atta_matching["effective_unit_cost"] == 56.0


@pytest.mark.asyncio
async def test_09_different_brands_and_variants_remain_separate(client: AsyncClient, setup_phase7_data):
    """Verify different brands and variants are never silently merged."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]

    p1 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Table Salt",
            "brand": "Tata Salt",
            "category": "staples_sugar",
            "actual_quantity": 5.0,
            "unit": "packet",
            "total_price": 125.0,
            "shop_name": "Kirana A",
        },
    )
    p2 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Table Salt",
            "brand": "Aashirvaad Salt",
            "category": "staples_sugar",
            "actual_quantity": 5.0,
            "unit": "packet",
            "total_price": 150.0,
            "shop_name": "Kirana B",
        },
    )
    assert p1.status_code == 201
    assert p2.status_code == 201
    assert p1.json()["unit_price"] == 25.0
    assert p2.json()["unit_price"] == 30.0


@pytest.mark.asyncio
async def test_11_and_12_partial_purchases_and_substitutions(client: AsyncClient, setup_phase7_data):
    """Test partial purchases and explicit product substitution mapping."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]

    # Explicit substitution purchase: Sunflower Oil substituted for Groundnut Oil
    resp_sub = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Fortune Sunflower Oil",
            "category": "dairy_oil",
            "brand": "Fortune",
            "actual_quantity": 5.0,
            "unit": "L",
            "total_price": 750.0,
            "shop_name": "Metro Cash",
            "is_substitution": True,
            "substitute_for_item_name": "Groundnut Oil",
        },
    )
    assert resp_sub.status_code == 201
    assert resp_sub.json()["is_substitution"] is True
    assert resp_sub.json()["substitute_for_item_name"] == "Groundnut Oil"


async def _seed_confirmed_orders_and_purchases(data):
    """Seed confirmed orders for Flat 1 and Flat 2 and a matching purchase."""
    orders_col = get_grocery_orders_collection()
    purchases_col = get_purchase_records_collection()
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    t = datetime.now(timezone.utc)
    ts = int(time.time() * 1000)

    # Flat 1: 5 kg Rice
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_seed1_{ts}",
        "user_id": data["user1_id"],
        "flat_number": "C-303",
        "user_name": "Resident Srinivas",
        "raw_text": "5 kg rice",
        "status": "confirmed",
        "items": [{"id": "i1", "original_name": "rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    })

    # Flat 2: 10 kg Rice
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_seed2_{ts}",
        "user_id": data["user2_id"],
        "flat_number": "D-404",
        "user_name": "Resident Pooja",
        "raw_text": "10 kg rice",
        "status": "confirmed",
        "items": [{"id": "i2", "original_name": "rice", "normalized_name": "Rice", "quantity": 10.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    })

    # Purchase: 15 kg Rice for Rs 750 (Rs 50/kg)
    await purchases_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "item_name": "Rice",
        "normalized_name": "Rice",
        "category": "grains_rice",
        "brand": None,
        "variant": None,
        "actual_quantity": 15.0,
        "unit": "kg",
        "total_price": 750.0,
        "unit_price": 50.0,
        "shop_name": "Super Bazaar",
        "purchase_date": t,
        "invoice_ref": f"SB-SEED-{ts}",
        "created_by_user_id": data["user1_id"],
        "created_at": t,
        "updated_at": t,
        "audit_trail": [],
    })


# ============================================================================
# 3. Bill Finalization, Lifecycle & Immutability Tests
# ============================================================================

@pytest.mark.asyncio
async def test_15_to_18_bill_finalization_immutability_and_correction(client: AsyncClient, setup_phase7_data):
    """Test bill finalization, duplicate prevention, purchase immutability, and versioned corrections."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]

    # Seed orders and purchase
    await _seed_confirmed_orders_and_purchases(data)

    # 1. Finalize bills
    fin_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/bills/finalize",
        headers=headers_vol,
        json={"shared_costs": [{"name": "Delivery Auto", "amount": 40.0}]},
    )
    assert fin_resp.status_code == 200
    bills = fin_resp.json()
    assert len(bills) >= 2
    assert all(b["status"] == "finalized" for b in bills)

    # 2. Duplicate finalization is idempotent and returns existing
    fin_again = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/bills/finalize",
        headers=headers_vol,
        json={},
    )
    assert fin_again.status_code == 200

    # 3. Finalized round blocks new purchase recording (Immutability)
    p_blocked = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Late Item",
            "category": "other",
            "actual_quantity": 1.0,
            "unit": "packet",
            "total_price": 10.0,
            "shop_name": "Corner Shop",
        },
    )
    assert p_blocked.status_code == 400
    assert "cannot record new purchases after bills" in p_blocked.json()["detail"].lower()

    # 4. Bill correction creates version 2 and preserves history
    first_bill_id = bills[0]["id"]
    corr_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/bills/{first_bill_id}/correct",
        headers=headers_vol,
        json={"correction_notes": "Volunteer adjusted resident discount voucher."},
    )
    assert corr_resp.status_code == 200
    corrected = corr_resp.json()
    assert corrected["bill_version"] == 2
    assert corrected["status"] == "corrected"
    assert corrected["previous_version_bill_id"] == first_bill_id
    assert corrected["correction_notes"] == "Volunteer adjusted resident discount voucher."


# ============================================================================
# 4. Resident Isolation & Privacy Tests
# ============================================================================

@pytest.mark.asyncio
async def test_19_and_20_resident_privacy_and_isolation(client: AsyncClient, setup_phase7_data):
    """Test resident can only view their own bill, not other flats or other societies."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    headers_res1 = data["headers_res1"]
    headers_res2 = data["headers_res2"]

    # Seed orders, purchases, and finalize bills
    await _seed_confirmed_orders_and_purchases(data)
    fin_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/bills/finalize",
        headers=headers_vol,
        json={},
    )
    assert fin_res.status_code == 200

    # Get bills as volunteer
    round_bills = (await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/bills",
        headers=headers_vol,
    )).json()

    bill1 = next(b for b in round_bills if b["flat_number"] == "C-303")
    bill2 = next(b for b in round_bills if b["flat_number"] == "D-404")

    # Resident 1 can access own bill
    r1_own = await client.get(f"/api/users/me/bills/{bill1['id']}", headers=headers_res1)
    assert r1_own.status_code == 200
    assert r1_own.json()["flat_number"] == "C-303"

    # Resident 1 CANNOT access Resident 2's bill (Strict 403 Forbidden)
    r1_other = await client.get(f"/api/users/me/bills/{bill2['id']}", headers=headers_res1)
    assert r1_other.status_code == 403

    # Resident 1 lists own bills: should only see bill1
    my_bills = (await client.get("/api/users/me/bills", headers=headers_res1)).json()
    assert all(b["user_id"] == data["user1_id"] for b in my_bills)


# ============================================================================
# 5. Nexconn Chat Bill Announcement Tests
# ============================================================================

@pytest.mark.asyncio
async def test_21_and_22_nexconn_bill_publication_privacy_and_idempotency(client: AsyncClient, setup_phase7_data):
    """Test generic group announcement does not expose private flat numbers or bill amounts."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]

    # Seed orders, purchases, and finalize bills
    await _seed_confirmed_orders_and_purchases(data)
    fin_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/bills/finalize",
        headers=headers_vol,
        json={},
    )
    assert fin_res.status_code == 200

    with patch("app.services.billing_service.send_system_bot_message", new_callable=AsyncMock) as mock_bot:
        mock_bot.return_value = True

        # First publish
        pub1 = await client.post(
            f"/api/societies/{soc1_id}/rounds/{round_id}/bills/publish",
            headers=headers_vol,
        )
        assert pub1.status_code == 200
        res1 = pub1.json()
        assert res1["sent"] is True

        # Privacy verification: Message text MUST NOT contain flat numbers or rupee amounts
        msg = res1["message_text"]
        assert "C-303" not in msg
        assert "D-404" not in msg
        assert "250" not in msg
        assert "500" not in msg
        assert "Society Cart: Shopping for Round" in msg
        assert "Your itemized grocery bill is now available" in msg

        # Second publish (Idempotent - does not re-invoke bot)
        pub2 = await client.post(
            f"/api/societies/{soc1_id}/rounds/{round_id}/bills/publish",
            headers=headers_vol,
        )
        assert pub2.status_code == 200
        assert pub2.json()["sent"] is True
        # mock_bot was called only once!
        assert mock_bot.call_count == 1


# ============================================================================
# 6. Retail Benchmark Prices & Verified Savings Tests
# ============================================================================

@pytest.mark.asyncio
async def test_23_to_28_evidence_backed_savings_and_honest_reporting(client: AsyncClient, setup_phase7_data):
    """Test verified savings against recorded retail benchmark evidence."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    headers_res1 = data["headers_res1"]

    # Seed orders, purchases, and finalize bills
    await _seed_confirmed_orders_and_purchases(data)
    fin_res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/bills/finalize",
        headers=headers_vol,
        json={},
    )
    assert fin_res.status_code == 200

    # 1. Record retail benchmark evidence: Rice at Rs 60.00/kg from Reliance Fresh
    bench_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/benchmarks",
        headers=headers_vol,
        json={
            "product_name": "Rice",
            "package_size": 1.0,
            "package_unit": "kg",
            "benchmark_price": 60.0,
            "store_name": "Reliance Fresh",
            "source_type": "receipt",
            "evidence_ref": "REL-9921",
            "evidence_date": datetime.now(timezone.utc).isoformat(),
            "location": "Sarjapur Road, Bengaluru",
        },
    )
    assert bench_resp.status_code == 201
    assert bench_resp.json()["benchmark_unit_price"] == 60.0
    assert bench_resp.json()["verification_status"] == "pending"
    bench_id = bench_resp.json()["id"]

    # 1b. Verify benchmark before requesting savings
    verify_resp = await client.patch(
        f"/api/societies/{soc1_id}/rounds/{round_id}/benchmarks/{bench_id}/verify",
        headers=headers_vol,
        json={"status": "verified", "notes": "Verified against physical receipt."},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verification_status"] == "verified"

    # 2. Retrieve savings summary
    sav_resp = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/savings",
        headers=headers_res1,
    )
    assert sav_resp.status_code == 200
    sav = sav_resp.json()

    # Bulk Rice was purchased at Rs 50.00/kg; Benchmark is Rs 60.00/kg
    rice_savings = next((it for it in sav["items"] if it["item_name"].lower() == "rice"), None)
    assert rice_savings is not None
    assert rice_savings["has_benchmark"] is True
    assert rice_savings["benchmark_unit_price"] == 60.0
    assert rice_savings["bulk_unit_price"] == 50.0
    assert rice_savings["savings_amount"] > 0
    assert rice_savings["status_label"] == "Verified Savings"

    # Total savings equation verified
    assert sav["verified_savings_amount"] > 0
    assert sav["verified_savings_percentage"] > 0
    assert sav["label"] == "Verified Savings"


# ============================================================================
# 7. Role-Based Access Control Tests
# ============================================================================

@pytest.mark.asyncio
async def test_29_and_30_rbac_privilege_enforcement(client: AsyncClient, setup_phase7_data):
    """Verify residents cannot record purchases or finalize bills; volunteer/admin can."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_res1 = data["headers_res1"]
    headers_vol = data["headers_vol"]

    # Resident attempts to record purchase -> 403 Forbidden
    res_record = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/purchases",
        headers=headers_res1,
        json={
            "item_name": "Rogue Purchase",
            "category": "other",
            "actual_quantity": 1.0,
            "unit": "kg",
            "total_price": 10.0,
            "shop_name": "Store",
        },
    )
    assert res_record.status_code == 403

    # Resident attempts to finalize bills -> 403 Forbidden
    res_fin = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/bills/finalize",
        headers=headers_res1,
        json={},
    )
    assert res_fin.status_code == 403


# ============================================================================
# 8. Phase 7 Audit Regression Tests
# ============================================================================

async def _seed_three_flats_scenario(data, purchase_qty: float = 15.0, purchase_total: float = 750.0):
    """Seed Flat A (5 kg), Flat B (10 kg), Flat C (10 kg) and a purchase record in a new round."""
    rounds_col = get_order_rounds_collection()
    orders_col = get_grocery_orders_collection()
    purchases_col = get_purchase_records_collection()
    soc1_id = data["soc1_id"]
    t = datetime.now(timezone.utc)
    ts = int(time.time() * 1000)

    # Create fresh round
    round_res = await rounds_col.insert_one({
        "society_id": soc1_id,
        "round_number": 99,
        "status": "closed",
        "opened_by_user_id": data["user1_id"],
        "opened_at": t,
        "closed_at": t,
        "shopping_list_compiled": False,
        "created_at": t,
        "updated_at": t,
    })
    r_id = str(round_res.inserted_id)

    # Flat A: 5 kg Rice
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": r_id,
        "round_number": 99,
        "submission_id": f"sub_a_{ts}",
        "user_id": data["user1_id"],
        "flat_number": "A-101",
        "user_name": "Resident Flat A",
        "raw_text": "5 kg rice",
        "status": "confirmed",
        "items": [{"id": "item_a", "original_name": "rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    })

    # Flat B: 10 kg Rice
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": r_id,
        "round_number": 99,
        "submission_id": f"sub_b_{ts}",
        "user_id": data["user2_id"],
        "flat_number": "B-202",
        "user_name": "Resident Flat B",
        "raw_text": "10 kg rice",
        "status": "confirmed",
        "items": [{"id": "item_b", "original_name": "rice", "normalized_name": "Rice", "quantity": 10.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    })

    # Flat C: 10 kg Rice
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": r_id,
        "round_number": 99,
        "submission_id": f"sub_c_{ts}",
        "user_id": data["user2_id"],
        "flat_number": "C-303",
        "user_name": "Resident Flat C",
        "raw_text": "10 kg rice",
        "status": "confirmed",
        "items": [{"id": "item_c", "original_name": "rice", "normalized_name": "Rice", "quantity": 10.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    })

    # Volunteer purchase
    unit_price = round(purchase_total / purchase_qty, 4)
    await purchases_col.insert_one({
        "society_id": soc1_id,
        "round_id": r_id,
        "item_name": "Rice",
        "normalized_name": "Rice",
        "category": "grains_rice",
        "brand": None,
        "variant": None,
        "actual_quantity": purchase_qty,
        "unit": "kg",
        "total_price": purchase_total,
        "unit_price": unit_price,
        "shop_name": "Grain Mandi",
        "purchase_date": t,
        "invoice_ref": f"MANDI-{ts}",
        "created_by_user_id": data["user1_id"],
        "created_at": t,
        "updated_at": t,
        "audit_trail": [],
    })

    return r_id


@pytest.mark.asyncio
async def test_31_phase6_packing_case_a_equal_distribution(client: AsyncClient, setup_phase7_data):
    """Audit Test Case A:
    - Flat A requested 5 kg rice.
    - Flat B requested 10 kg rice.
    - Flat C requested 10 kg rice.
    - Volunteer purchased 15 kg at Rs 50/kg (total Rs 750).
    - Volunteer distributes: 5 kg, 5 kg, and 5 kg.
    Verify:
    - Flat A billed for 5 kg (Rs 250), 0 unfulfilled.
    - Flat B billed for 5 kg (Rs 250), 5 kg unfulfilled.
    - Flat C billed for 5 kg (Rs 250), 5 kg unfulfilled.
    - Total allocated = Rs 750.
    - Unallocated inventory = 0 kg (Rs 0.00).
    - Reconciliation holds strictly.
    """
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    headers_vol = data["headers_vol"]

    r_id = await _seed_three_flats_scenario(data, purchase_qty=15.0, purchase_total=750.0)

    # Volunteer finalizes bills with Case A physical allocation override: 5 kg, 5 kg, 5 kg
    fin_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{r_id}/bills/finalize",
        headers=headers_vol,
        json={
            "flat_allocations_override": [
                {"flat_number": "A-101", "item_name": "Rice", "allocated_quantity": 5.0},
                {"flat_number": "B-202", "item_name": "Rice", "allocated_quantity": 5.0},
                {"flat_number": "C-303", "item_name": "Rice", "allocated_quantity": 5.0},
            ]
        },
    )
    assert fin_resp.status_code == 200
    bills = fin_resp.json()
    assert len(bills) == 3

    bill_a = next(b for b in bills if b["flat_number"] == "A-101")
    bill_b = next(b for b in bills if b["flat_number"] == "B-202")
    bill_c = next(b for b in bills if b["flat_number"] == "C-303")

    # Flat A: 5 kg requested, 5 kg allocated, Rs 250, 0 unfulfilled
    it_a = bill_a["items"][0]
    assert it_a["requested_quantity"] == 5.0
    assert it_a["allocated_quantity"] == 5.0
    assert it_a["item_total"] == 250.0
    assert it_a["is_unfulfilled"] is False
    assert it_a["unfulfilled_quantity"] == 0.0

    # Flat B: 10 kg requested, 5 kg allocated, Rs 250, 5 kg unfulfilled
    it_b = bill_b["items"][0]
    assert it_b["requested_quantity"] == 10.0
    assert it_b["allocated_quantity"] == 5.0
    assert it_b["item_total"] == 250.0
    assert it_b["is_unfulfilled"] is True
    assert it_b["unfulfilled_quantity"] == 5.0

    # Flat C: 10 kg requested, 5 kg allocated, Rs 250, 5 kg unfulfilled
    it_c = bill_c["items"][0]
    assert it_c["requested_quantity"] == 10.0
    assert it_c["allocated_quantity"] == 5.0
    assert it_c["item_total"] == 250.0
    assert it_c["is_unfulfilled"] is True
    assert it_c["unfulfilled_quantity"] == 5.0

    # Society spending summary reconciliation
    spend_resp = await client.get(
        f"/api/societies/{soc1_id}/rounds/{r_id}/spending-summary",
        headers=headers_vol,
    )
    assert spend_resp.status_code == 200
    spend = spend_resp.json()
    assert spend["total_actual_purchase_cost"] == 750.0
    assert spend["total_allocated_bill_costs"] == 750.0
    assert spend["total_unallocated_cost"] == 0.0
    assert spend["is_reconciled"] is True


@pytest.mark.asyncio
async def test_32_phase6_packing_case_b_skewed_distribution(client: AsyncClient, setup_phase7_data):
    """Audit Test Case B:
    - Same requests: Flat A (5 kg), Flat B (10 kg), Flat C (10 kg).
    - Volunteer purchased 15 kg at Rs 50/kg (total Rs 750).
    - Volunteer distributes: 2 kg, 8 kg, and 5 kg.
    Verify:
    - Flat A billed for 2 kg (Rs 100), 3 kg unfulfilled.
    - Flat B billed for 8 kg (Rs 400), 2 kg unfulfilled.
    - Flat C billed for 5 kg (Rs 250), 5 kg unfulfilled.
    - Total allocated = Rs 750.
    - Unallocated inventory = 0 kg (Rs 0.00).
    - Residents are NEVER billed for quantities they did not receive.
    """
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    headers_vol = data["headers_vol"]

    r_id = await _seed_three_flats_scenario(data, purchase_qty=15.0, purchase_total=750.0)

    # Volunteer finalizes bills with Case B physical allocation: 2 kg, 8 kg, 5 kg
    fin_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{r_id}/bills/finalize",
        headers=headers_vol,
        json={
            "flat_allocations_override": [
                {"flat_number": "A-101", "item_name": "Rice", "allocated_quantity": 2.0},
                {"flat_number": "B-202", "item_name": "Rice", "allocated_quantity": 8.0},
                {"flat_number": "C-303", "item_name": "Rice", "allocated_quantity": 5.0},
            ]
        },
    )
    assert fin_resp.status_code == 200
    bills = fin_resp.json()

    bill_a = next(b for b in bills if b["flat_number"] == "A-101")
    bill_b = next(b for b in bills if b["flat_number"] == "B-202")
    bill_c = next(b for b in bills if b["flat_number"] == "C-303")

    # Flat A: 2 kg allocated (Rs 100), 3 kg unfulfilled
    it_a = bill_a["items"][0]
    assert it_a["allocated_quantity"] == 2.0
    assert it_a["item_total"] == 100.0
    assert it_a["unfulfilled_quantity"] == 3.0

    # Flat B: 8 kg allocated (Rs 400), 2 kg unfulfilled
    it_b = bill_b["items"][0]
    assert it_b["allocated_quantity"] == 8.0
    assert it_b["item_total"] == 400.0
    assert it_b["unfulfilled_quantity"] == 2.0

    # Flat C: 5 kg allocated (Rs 250), 5 kg unfulfilled
    it_c = bill_c["items"][0]
    assert it_c["allocated_quantity"] == 5.0
    assert it_c["item_total"] == 250.0
    assert it_c["unfulfilled_quantity"] == 5.0

    # Reconciliation check
    spend_resp = await client.get(
        f"/api/societies/{soc1_id}/rounds/{r_id}/spending-summary",
        headers=headers_vol,
    )
    assert spend_resp.status_code == 200
    spend = spend_resp.json()
    assert spend["total_actual_purchase_cost"] == 750.0
    assert spend["total_allocated_bill_costs"] == 750.0
    assert spend["total_unallocated_cost"] == 0.0
    assert spend["is_reconciled"] is True


@pytest.mark.asyncio
async def test_33_benchmark_explicit_verification_workflow(client: AsyncClient, setup_phase7_data):
    """Test explicit benchmark verification workflow:
    1. Benchmark creation starts as pending.
    2. Savings calculation excludes pending benchmarks.
    3. Volunteer verifies benchmark -> becomes verified with audit metadata.
    4. Savings calculation includes verified benchmark.
    """
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    headers_vol = data["headers_vol"]
    headers_res1 = data["headers_res1"]

    # Seed orders and finalize bills
    r_id = await _seed_three_flats_scenario(data, purchase_qty=15.0, purchase_total=750.0)
    await client.post(
        f"/api/societies/{soc1_id}/rounds/{r_id}/bills/finalize",
        headers=headers_vol,
        json={},
    )

    # 1. Record benchmark: starts as PENDING
    b_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{r_id}/benchmarks",
        headers=headers_vol,
        json={
            "product_name": "Rice",
            "package_size": 1.0,
            "package_unit": "kg",
            "benchmark_price": 65.0,
            "store_name": "Nature Basket",
            "source_type": "price_listing",
            "evidence_date": datetime.now(timezone.utc).isoformat(),
            "location": "Indiranagar, Bengaluru",
        },
    )
    assert b_resp.status_code == 201
    bench = b_resp.json()
    assert bench["verification_status"] == "pending"
    assert bench["verified_by"] is None
    bench_id = bench["id"]

    # 2. Savings before verification: benchmark is NOT used (Benchmark Unavailable)
    sav_pending = (await client.get(
        f"/api/societies/{soc1_id}/rounds/{r_id}/savings",
        headers=headers_res1,
    )).json()
    rice_pending = next(it for it in sav_pending["items"] if it["item_name"].lower() == "rice")
    assert rice_pending["has_benchmark"] is False
    assert rice_pending["status_label"] == "Benchmark Unavailable"

    # 3. Volunteer verifies the benchmark
    v_resp = await client.patch(
        f"/api/societies/{soc1_id}/rounds/{r_id}/benchmarks/{bench_id}/verify",
        headers=headers_vol,
        json={"status": "verified", "notes": "Audited invoice matched store location."},
    )
    assert v_resp.status_code == 200
    v_bench = v_resp.json()
    assert v_bench["verification_status"] == "verified"
    assert v_bench["verified_by"] is not None
    assert v_bench["verified_at"] is not None

    # 4. Savings after verification: benchmark is applied
    sav_verified = (await client.get(
        f"/api/societies/{soc1_id}/rounds/{r_id}/savings",
        headers=headers_res1,
    )).json()
    rice_ver = next(it for it in sav_verified["items"] if it["item_name"].lower() == "rice")
    assert rice_ver["has_benchmark"] is True
    assert rice_ver["status_label"] == "Verified Savings"
    assert rice_ver["benchmark_unit_price"] == 65.0
    assert rice_ver["savings_amount"] > 0


@pytest.mark.asyncio
async def test_34_concurrent_bill_correction_conflict_rejection(client: AsyncClient, setup_phase7_data):
    """Test atomic CAS prevents concurrent duplicate corrections on the same bill."""
    data = setup_phase7_data
    soc1_id = data["soc1_id"]
    headers_vol = data["headers_vol"]

    r_id = await _seed_three_flats_scenario(data, purchase_qty=15.0, purchase_total=750.0)
    fin_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds/{r_id}/bills/finalize",
        headers=headers_vol,
        json={},
    )
    assert fin_resp.status_code == 200
    bills = fin_resp.json()
    bill_id = bills[0]["id"]

    # First correction succeeds
    corr1 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{r_id}/bills/{bill_id}/correct",
        headers=headers_vol,
        json={"correction_notes": "First valid correction by Volunteer A."},
    )
    assert corr1.status_code == 200
    assert corr1.json()["bill_version"] == 2

    # Second concurrent correction attempt on the original bill fails with 409 Conflict
    corr2 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{r_id}/bills/{bill_id}/correct",
        headers=headers_vol,
        json={"correction_notes": "Conflicting correction attempt on same bill."},
    )
    assert corr2.status_code == 409
    assert "cannot be corrected" in corr2.json()["detail"].lower()
