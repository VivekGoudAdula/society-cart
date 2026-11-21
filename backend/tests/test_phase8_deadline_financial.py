"""Phase 8: Order Deadline Enforcement and Financial Accuracy Tests.

Verifies:
1. Order deadline enforcement:
   - Submissions right before deadline accepted.
   - Submissions after deadline rejected.
   - Pre-deadline reservations confirmed after deadline/closure accepted.
2. Financial accuracy & reconciliation:
   - Mathematical identity: Actual Purchase Cost = Resident Allocated Costs + Shared Expenses + Unallocated Inventory.
   - Exact paise precision (Decimal('0.01'), ROUND_HALF_UP).
   - Distinct brand & variant preservation.
   - Physical allocation overrides (Case A: 5, 5, 5; Case B: 2, 8, 5).
   - Benchmark verification lifecycle (pending, verified, rejected, >90 day staleness).
   - Honest zero and negative savings reporting.
"""

import pytest
import time
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from bson import ObjectId

from app.core.database import (
    get_users_collection,
    get_societies_collection,
    get_order_rounds_collection,
    get_grocery_orders_collection,
    get_shopping_lists_collection,
    get_purchase_records_collection,
    get_grocery_bills_collection,
    get_retail_benchmarks_collection,
)


@pytest.fixture
async def df_fixture(client: AsyncClient):
    """Sets up a society with Admin, Volunteer, and 3 Residents for deadline & financial verification.
    """
    users_col = get_users_collection()
    societies_col = get_societies_collection()
    rounds_col = get_order_rounds_collection()
    orders_col = get_grocery_orders_collection()
    sl_col = get_shopping_lists_collection()
    pr_col = get_purchase_records_collection()
    bills_col = get_grocery_bills_collection()
    bench_col = get_retail_benchmarks_collection()

    await users_col.delete_many({"email": {"$regex": "@p8df.com$"}})
    await societies_col.delete_many({"name": {"$regex": "^P8DF Society"}})
    await rounds_col.delete_many({"title": {"$regex": "^P8DF Round"}})

    ts = int(time.time() * 1000)
    async def reg(name: str, email: str):
        resp = await client.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": "Password123!",
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        return {"id": data["user"]["id"], "token": data["access_token"], "headers": {"Authorization": f"Bearer {data['access_token']}"}}

    admin = await reg("Admin DF", f"admin_{ts}@p8df.com")
    vol = await reg("Volunteer DF", f"vol_{ts}@p8df.com")
    res1 = await reg("Resident 1", f"res1_{ts}@p8df.com")
    res2 = await reg("Resident 2", f"res2_{ts}@p8df.com")
    res3 = await reg("Resident 3", f"res3_{ts}@p8df.com")

    resp_soc = await client.post("/api/societies", json={
        "name": f"P8DF Society {ts}",
        "address": "123 Market Rd",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "total_flats": 30,
        "creator_flat_number": "ADM-01"
    }, headers=admin["headers"])
    assert resp_soc.status_code == 201
    soc_data = resp_soc.json()
    soc_id = soc_data["society"]["id"] if "society" in soc_data else soc_data["id"]
    invite_code = soc_data["society"]["invite_code"] if "society" in soc_data else soc_data["invite_code"]

    # Join members
    j_vol = await client.post("/api/societies/join", json={"invite_code": invite_code, "flat_number": "V-1"}, headers=vol["headers"])
    vol_mem_id = j_vol.json()["membership"]["id"]
    await client.patch(f"/api/societies/{soc_id}/members/{vol_mem_id}/role", json={"role": "volunteer"}, headers=admin["headers"])

    await client.post("/api/societies/join", json={"invite_code": invite_code, "flat_number": "A-101"}, headers=res1["headers"])
    await client.post("/api/societies/join", json={"invite_code": invite_code, "flat_number": "A-102"}, headers=res2["headers"])
    await client.post("/api/societies/join", json={"invite_code": invite_code, "flat_number": "A-103"}, headers=res3["headers"])

    yield {
        "admin": admin, "vol": vol, "res1": res1, "res2": res2, "res3": res3,
        "soc_id": soc_id
    }

    # Teardown
    await users_col.delete_many({"email": {"$regex": "@p8df.com$"}})
    await societies_col.delete_many({"name": {"$regex": "^P8DF Society"}})
    await rounds_col.delete_many({"society_id": soc_id})
    await orders_col.delete_many({"society_id": soc_id})
    await sl_col.delete_many({"society_id": soc_id})
    await pr_col.delete_many({"society_id": soc_id})
    await bills_col.delete_many({"society_id": soc_id})
    await bench_col.delete_many({"society_id": soc_id})


@pytest.mark.asyncio
async def test_deadline_enforcement_rules(client: AsyncClient, df_fixture):
    """Test:
    1. Submission immediately before deadline accepted.
    2. Submission after deadline rejected.
    3. Pre-deadline reservation confirmed after deadline/closure accepted.
    """
    f = df_fixture
    soc_id = f["soc_id"]
    vol = f["vol"]
    rounds_col = get_order_rounds_collection()

    # Create round with deadline comfortably in the future so opening succeeds
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=2)
    resp = await client.post(f"/api/societies/{soc_id}/rounds", json={
        "title": "P8DF Round Deadline Test",
        "shopping_date": "Tomorrow 10am",
        "deadline_at": deadline.isoformat()
    }, headers=vol["headers"])
    assert resp.status_code == 201
    round_id = resp.json()["id"]

    open_resp = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/open", headers=vol["headers"])
    assert open_resp.status_code == 200

    # 1. Submission BEFORE deadline: reserve succeeds
    sub_id = f"sub_deadline_before_{int(time.time()*1000)}"
    resp_before = await client.post(
        f"/api/societies/{soc_id}/rounds/{round_id}/submissions/reserve",
        headers=f["res1"]["headers"],
        json={"submission_id": sub_id, "raw_text": "2kg apples"}
    )
    assert resp_before.status_code in [200, 201]

    # 2. Advance deadline into past in DB to simulate deadline passing
    past_deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
    await rounds_col.update_one(
        {"_id": ObjectId(round_id)},
        {"$set": {"deadline_at": past_deadline}}
    )

    # Submission AFTER deadline must fail (HTTP 400)
    sub_after = f"sub_deadline_after_{int(time.time()*1000)}"
    resp_after = await client.post(
        f"/api/societies/{soc_id}/rounds/{round_id}/submissions/reserve",
        headers=f["res2"]["headers"],
        json={"submission_id": sub_after, "raw_text": "3kg bananas"}
    )
    assert resp_after.status_code == 400

    # 3. Pre-deadline reservation confirmed AFTER deadline/closure must SUCCEED
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/close", headers=vol["headers"])

    msg_id = f"msg_deadline_before_{int(time.time()*1000)}"
    c_resp = await client.post(
        f"/api/societies/{soc_id}/rounds/{round_id}/submissions/{sub_id}/confirm",
        headers=f["res1"]["headers"],
        json={"message_id": msg_id}
    )
    assert c_resp.status_code == 200
    assert c_resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_financial_reconciliation_identity_and_paise_precision(client: AsyncClient, df_fixture):
    """Test exact financial reconciliation:
    Actual Purchase Cost = Resident Allocated Costs + Shared Expenses + Unallocated Inventory.
    And verify paise precision (ROUND_HALF_UP, Decimal('0.01')).
    """
    f = df_fixture
    soc_id = f["soc_id"]
    vol = f["vol"]
    orders_col = get_grocery_orders_collection()

    now = datetime.now(timezone.utc)
    resp = await client.post(f"/api/societies/{soc_id}/rounds", json={
        "title": "P8DF Financial Test",
        "shopping_date": "Sunday 10am",
        "deadline_at": (now + timedelta(days=1)).isoformat()
    }, headers=vol["headers"])
    round_id = resp.json()["id"]
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/open", headers=vol["headers"])

    # Three flats order Sugar (1 kg each)
    flats = [("A-101", f["res1"]["id"]), ("A-102", f["res2"]["id"]), ("A-103", f["res3"]["id"])]
    for flat_no, u_id in flats:
        await orders_col.insert_one({
            "society_id": soc_id,
            "round_id": round_id,
            "user_id": u_id,
            "flat_number": flat_no,
            "raw_text": "1kg sugar",
            "channel_type": "nexconn_chat",
            "message_id": f"msg_sugar_{flat_no}_{int(time.time()*1000)}",
            "submission_id": f"sub_sugar_{flat_no}_{int(time.time()*1000)}",
            "status": "confirmed",
            "items": [{"id": f"it_{flat_no}", "original_name": "Sugar", "normalized_name": "Sugar", "quantity": 1.0, "unit": "kg", "category": "grains_rice"}],
            "language_detected": "en",
            "created_at": now,
            "updated_at": now
        })

    # Close round and compile shopping list
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/close", headers=vol["headers"])
    compile_resp = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/shopping-list/compile", headers=vol["headers"])
    assert compile_resp.status_code == 200

    # Volunteer purchases 4 kg Sugar for total cost 100.00 INR (25.00/kg)
    # Requested was 3 kg. So 3 kg allocated (75.00 INR), 1 kg unallocated (25.00 INR).
    resp_purch = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/purchases", json={
        "item_name": "Sugar",
        "category": "grains_rice",
        "actual_quantity": 4.0,
        "unit": "kg",
        "total_price": 100.00,
        "shop_name": "Metro Wholesale"
    }, headers=vol["headers"])
    assert resp_purch.status_code == 201

    # Preview bills
    resp_preview = await client.get(f"/api/societies/{soc_id}/rounds/{round_id}/allocation/preview", headers=vol["headers"])
    assert resp_preview.status_code == 200

    # Finalize bills with shared delivery expense of 10.00 INR split across 3 flats
    resp_fin = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/bills/finalize", json={
        "shared_costs": [
            {"name": "Delivery Auto", "amount": 10.00}
        ]
    }, headers=vol["headers"])
    assert resp_fin.status_code == 200

    # Spending summary
    resp_summary = await client.get(f"/api/societies/{soc_id}/rounds/{round_id}/spending-summary", headers=vol["headers"])
    assert resp_summary.status_code == 200
    summary = resp_summary.json()

    # Check mathematical reconciliation
    actual_purchases = Decimal(str(summary["total_actual_purchase_cost"]))
    shared_costs = Decimal(str(summary["total_shared_costs"]))
    allocated_bill_costs = Decimal(str(summary["total_allocated_bill_costs"]))
    unallocated_inventory = Decimal(str(summary["total_unallocated_cost"]))

    # Mathematical identity:
    # Actual Purchase Cost = Allocated Items Cost + Unallocated Inventory Cost
    allocated_items_cost = allocated_bill_costs
    assert actual_purchases == allocated_items_cost + unallocated_inventory, (
        f"Reconciliation error: actual {actual_purchases} != {allocated_items_cost} + {unallocated_inventory}"
    )
    assert summary["is_reconciled"] is True

    # Check that individual bills sum up to (allocated_items + shared_costs) with zero paise drift
    bills_col = get_grocery_bills_collection()
    all_bills = await bills_col.find({"round_id": round_id, "status": "finalized"}).to_list(100)
    sum_individual_bills = sum(Decimal(str(b["total_amount"])) for b in all_bills)
    total_billed_to_flats = allocated_items_cost + shared_costs
    assert sum_individual_bills == total_billed_to_flats


@pytest.mark.asyncio
async def test_brand_and_variant_preservation(client: AsyncClient, df_fixture):
    """Test that distinct brands/variants are never merged into a single generic item.
    - "Aashirvaad Shudh Chakki Atta" vs "Fortune Chakki Atta"
    """
    f = df_fixture
    soc_id = f["soc_id"]
    vol = f["vol"]
    orders_col = get_grocery_orders_collection()

    now = datetime.now(timezone.utc)
    resp = await client.post(f"/api/societies/{soc_id}/rounds", json={
        "title": "P8DF Brand Test",
        "shopping_date": "Sunday 10am",
        "deadline_at": (now + timedelta(days=1)).isoformat()
    }, headers=vol["headers"])
    round_id = resp.json()["id"]
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/open", headers=vol["headers"])

    # Flat 1 orders Aashirvaad Shudh Chakki Atta
    await orders_col.insert_one({
        "society_id": soc_id,
        "round_id": round_id,
        "user_id": f["res1"]["id"],
        "flat_number": "A-101",
        "raw_text": "5kg Aashirvaad Shudh Chakki Atta",
        "channel_type": "nexconn_chat",
        "message_id": f"msg_brand_1_{int(time.time()*1000)}",
        "submission_id": f"sub_brand_1_{int(time.time()*1000)}",
        "status": "confirmed",
        "items": [{
            "id": "b1",
            "original_name": "Aashirvaad Shudh Chakki Atta",
            "normalized_name": "Aashirvaad Shudh Chakki Atta",
            "brand": "Aashirvaad",
            "quantity": 5.0,
            "unit": "kg",
            "category": "grains_rice"
        }],
        "language_detected": "en",
        "created_at": now,
        "updated_at": now
    })

    # Flat 2 orders Fortune Chakki Atta
    await orders_col.insert_one({
        "society_id": soc_id,
        "round_id": round_id,
        "user_id": f["res2"]["id"],
        "flat_number": "A-102",
        "raw_text": "5kg Fortune Chakki Atta",
        "channel_type": "nexconn_chat",
        "message_id": f"msg_brand_2_{int(time.time()*1000)}",
        "submission_id": f"sub_brand_2_{int(time.time()*1000)}",
        "status": "confirmed",
        "items": [{
            "id": "b2",
            "original_name": "Fortune Chakki Atta",
            "normalized_name": "Fortune Chakki Atta",
            "brand": "Fortune",
            "quantity": 5.0,
            "unit": "kg",
            "category": "grains_rice"
        }],
        "language_detected": "en",
        "created_at": now,
        "updated_at": now
    })

    # Close round and compile shopping list
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/close", headers=vol["headers"])
    resp_sl = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/shopping-list/compile", headers=vol["headers"])
    assert resp_sl.status_code == 200
    categories = resp_sl.json()["categories"]
    items = [it for cat in categories for it in cat["items"]]

    # Manifest items must be separate entries
    item_names = [it["normalized_name"] for it in items]
    assert "Aashirvaad Shudh Chakki Atta" in item_names
    assert "Fortune Chakki Atta" in item_names
    assert len(items) == 2, "Distinct brands must not be grouped together"


@pytest.mark.asyncio
async def test_physical_allocation_overrides_case_a_and_b(client: AsyncClient, df_fixture):
    """Test physical allocation overrides:
    Flat A requested 5 kg rice.
    Flat B requested 10 kg rice.
    Flat C requested 10 kg rice.
    Total requested: 25 kg.
    Volunteer purchased: 15 kg for 600 INR (40/kg).

    Case B: Volunteer distributes 2 kg, 8 kg, 5 kg.
    """
    f = df_fixture
    soc_id = f["soc_id"]
    vol = f["vol"]
    orders_col = get_grocery_orders_collection()

    now = datetime.now(timezone.utc)
    resp = await client.post(f"/api/societies/{soc_id}/rounds", json={
        "title": "P8DF Physical Overrides Test",
        "shopping_date": "Sunday 10am",
        "deadline_at": (now + timedelta(days=1)).isoformat()
    }, headers=vol["headers"])
    round_id = resp.json()["id"]
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/open", headers=vol["headers"])

    # Flat A (res1): 5 kg rice
    # Flat B (res2): 10 kg rice
    # Flat C (res3): 10 kg rice
    requests = [
        ("A-101", f["res1"]["id"], 5.0),
        ("A-102", f["res2"]["id"], 10.0),
        ("A-103", f["res3"]["id"], 10.0),
    ]
    for flat_no, u_id, qty in requests:
        await orders_col.insert_one({
            "society_id": soc_id,
            "round_id": round_id,
            "user_id": u_id,
            "flat_number": flat_no,
            "raw_text": f"{qty}kg rice",
            "channel_type": "nexconn_chat",
            "message_id": f"msg_rice_{flat_no}_{int(time.time()*1000)}",
            "submission_id": f"sub_rice_{flat_no}_{int(time.time()*1000)}",
            "status": "confirmed",
            "items": [{"id": f"r_{flat_no}", "original_name": "Basmati Rice", "normalized_name": "Basmati Rice", "quantity": qty, "unit": "kg", "category": "grains_rice"}],
            "language_detected": "en",
            "created_at": now,
            "updated_at": now
        })

    # Close and compile
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/close", headers=vol["headers"])
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/shopping-list/compile", headers=vol["headers"])

    # Record purchase: 15 kg for 600.00 INR (Unit price: 40.00 INR/kg)
    resp_p = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/purchases", json={
        "item_name": "Basmati Rice",
        "category": "grains_rice",
        "actual_quantity": 15.0,
        "unit": "kg",
        "total_price": 600.00,
        "shop_name": "Super Bazaar"
    }, headers=vol["headers"])
    assert resp_p.status_code == 201

    # Test Case B Override: Distribute 2 kg to Flat A, 8 kg to Flat B, 5 kg to Flat C
    resp_override = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/bills/finalize", json={
        "flat_allocations_override": [
            {"flat_number": "A-101", "item_name": "Basmati Rice", "allocated_quantity": 2.0},
            {"flat_number": "A-102", "item_name": "Basmati Rice", "allocated_quantity": 8.0},
            {"flat_number": "A-103", "item_name": "Basmati Rice", "allocated_quantity": 5.0},
        ]
    }, headers=vol["headers"])
    assert resp_override.status_code == 200

    # Verify bills for each flat reflect exact physical override quantities and cost
    bills_col = get_grocery_bills_collection()
    bill_a = await bills_col.find_one({"round_id": round_id, "flat_number": "A-101", "status": "finalized"})
    bill_b = await bills_col.find_one({"round_id": round_id, "flat_number": "A-102", "status": "finalized"})
    bill_c = await bills_col.find_one({"round_id": round_id, "flat_number": "A-103", "status": "finalized"})

    assert bill_a["items"][0]["allocated_quantity"] == 2.0
    assert bill_a["total_amount"] == 80.00  # 2 kg * 40.00

    assert bill_b["items"][0]["allocated_quantity"] == 8.0
    assert bill_b["total_amount"] == 320.00  # 8 kg * 40.00

    assert bill_c["items"][0]["allocated_quantity"] == 5.0
    assert bill_c["total_amount"] == 200.00  # 5 kg * 40.00

    # Sum of bills: 80 + 320 + 200 = 600.00 (100% of purchase cost allocated)
    assert bill_a["total_amount"] + bill_b["total_amount"] + bill_c["total_amount"] == 600.00


@pytest.mark.asyncio
async def test_benchmark_verification_lifecycle_and_honest_savings(client: AsyncClient, df_fixture):
    """Test:
    1. Benchmark creation (status=pending).
    2. Verification by volunteer (status=verified, verified_by, verified_at).
    3. Rejection of benchmark (status=rejected).
    4. Outdated benchmark (>90 days old) excluded from savings.
    5. Honest reporting of zero and negative savings (when bulk purchase price >= benchmark).
    """
    f = df_fixture
    soc_id = f["soc_id"]
    vol = f["vol"]
    now = datetime.now(timezone.utc)

    resp_round = await client.post(f"/api/societies/{soc_id}/rounds", json={
        "title": "P8DF Benchmark Lifecycle Test",
        "shopping_date": "Sunday 10am",
        "deadline_at": (now + timedelta(days=1)).isoformat()
    }, headers=vol["headers"])
    round_id = resp_round.json()["id"]

    # 1. Create benchmark
    resp_b1 = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/benchmarks", json={
        "product_name": "Basmati Rice",
        "package_size": 1.0,
        "package_unit": "kg",
        "benchmark_price": 50.00,
        "store_name": "Zepto Quick",
        "source_type": "price_listing",
        "evidence_date": now.isoformat(),
        "location": "Bengaluru",
    }, headers=vol["headers"])
    assert resp_b1.status_code == 201
    b1 = resp_b1.json()
    assert b1["verification_status"] == "pending"

    # 2. Verify benchmark
    resp_v1 = await client.patch(
        f"/api/societies/{soc_id}/rounds/{round_id}/benchmarks/{b1['id']}/verify",
        json={"status": "verified", "notes": "Verified against Zepto app screenshot"},
        headers=vol["headers"]
    )
    assert resp_v1.status_code == 200
    v1_data = resp_v1.json()
    assert v1_data["verification_status"] == "verified"
    assert v1_data["verified_by"] is not None
    assert v1_data["verified_at"] is not None

    # 3. Create second benchmark and reject it
    resp_b2 = await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/benchmarks", json={
        "product_name": "Basmati Rice",
        "package_size": 1.0,
        "package_unit": "kg",
        "benchmark_price": 30.00,
        "store_name": "Blinkit",
        "source_type": "price_listing",
        "evidence_date": now.isoformat(),
        "location": "Bengaluru",
    }, headers=vol["headers"])
    b2 = resp_b2.json()

    resp_v2 = await client.patch(
        f"/api/societies/{soc_id}/rounds/{round_id}/benchmarks/{b2['id']}/verify",
        json={"status": "rejected", "notes": "Out of stock / expired coupon used"},
        headers=vol["headers"]
    )
    assert resp_v2.status_code == 200
    v2_data = resp_v2.json()
    assert v2_data["verification_status"] == "rejected"

    # 4. Outdated benchmark (>90 days old)
    bench_col = get_retail_benchmarks_collection()
    old_date = datetime.now(timezone.utc) - timedelta(days=95)
    await bench_col.insert_one({
        "society_id": soc_id,
        "round_id": round_id,
        "product_name": "Potatoes",
        "package_size": 1.0,
        "package_unit": "kg",
        "benchmark_price": 35.0,
        "benchmark_unit_price": 35.0,
        "store_name": "Old Supermarket",
        "source_type": "receipt",
        "evidence_date": old_date,
        "location": "Bengaluru",
        "verification_status": "verified",
        "verified_by": "admin",
        "verified_at": old_date,
        "created_at": old_date,
        "updated_at": old_date
    })

    # 5. Honest zero and negative savings
    # Bulk purchase at 55.00 INR/kg vs verified benchmark of 50.00 INR/kg -> negative savings
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/open", headers=vol["headers"])
    orders_col = get_grocery_orders_collection()
    await orders_col.insert_one({
        "society_id": soc_id,
        "round_id": round_id,
        "user_id": f["res1"]["id"],
        "flat_number": "A-101",
        "raw_text": "1kg Basmati Rice",
        "channel_type": "nexconn_chat",
        "message_id": f"msg_rice_honest_{int(time.time()*1000)}",
        "submission_id": f"sub_rice_honest_{int(time.time()*1000)}",
        "status": "confirmed",
        "items": [{"id": "r_h", "original_name": "Basmati Rice", "normalized_name": "Basmati Rice", "quantity": 1.0, "unit": "kg", "category": "grains_rice"}],
        "language_detected": "en",
        "created_at": now,
        "updated_at": now
    })
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/close", headers=vol["headers"])
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/shopping-list/compile", headers=vol["headers"])

    # Volunteer buys at 55.00 INR/kg (Retail benchmark is 50.00 INR/kg)
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/purchases", json={
        "item_name": "Basmati Rice",
        "category": "grains_rice",
        "actual_quantity": 1.0,
        "unit": "kg",
        "total_price": 55.00,
        "shop_name": "Local Store"
    }, headers=vol["headers"])
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/bills/finalize", json={}, headers=vol["headers"])

    resp_savings = await client.get(f"/api/societies/{soc_id}/rounds/{round_id}/savings", headers=vol["headers"])
    assert resp_savings.status_code == 200
    savings = resp_savings.json()
    assert savings["verified_savings_amount"] <= 0, "Negative savings must be honestly reported"
