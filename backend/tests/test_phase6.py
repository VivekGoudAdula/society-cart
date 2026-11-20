"""Automated test suite for Phase 6: Volunteer Shopping Dashboard, Aggregation & Packing Manifests.

Covers:
1. Aggregation Correctness (compatible unit normalization, brand/variant separation, incompatible unit separation).
2. Order Eligibility (only confirmed orders included; pending, clarification, processing, failed, and rejected excluded).
3. Individual Flat-wise Packing Breakdown (accurate grouping, brand/variant preservation).
4. Compilation Lifecycle (empty state, recompilation fresh calculation, version increment, concurrency safety).
5. Role-based Authorization and Cross-Society Isolation (resident blocked, volunteer/admin allowed, cross-society blocked).
6. CSV Export (consolidated bulk checklist and flat-wise packing breakdown).
"""

import asyncio
from datetime import datetime, timedelta, timezone
import time
import pytest
from httpx import AsyncClient

from app.core.database import get_grocery_orders_collection


@pytest.fixture
async def setup_phase6_data(client: AsyncClient):
    """Sets up two societies, Admin, Volunteer, Resident 1, Resident 2 in Society 1, and Society 2 Admin."""
    ts = int(time.time() * 1000)

    # 1. Admin in Society 1
    resp_admin = await client.post("/api/auth/register", json={
        "name": "Admin Sharma",
        "email": f"admin_p6_{ts}@example.com",
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
        "email": f"vol_p6_{ts}@example.com",
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
        "email": f"srini_p6_{ts}@example.com",
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
        "email": f"pooja_p6_{ts}@example.com",
        "password": "Password123!",
    })
    token_res2 = resp_res2.json()["access_token"]
    user2_id = resp_res2.json()["user"]["id"]
    headers_res2 = {"Authorization": f"Bearer {token_res2}"}
    await client.post("/api/societies/join", headers=headers_res2, json={
        "invite_code": soc1_invite,
        "flat_number": "D-404",
    })

    # 5. Admin & Society 2
    resp_other = await client.post("/api/auth/register", json={
        "name": "External Admin",
        "email": f"other_p6_{ts}@example.com",
        "password": "Password123!",
    })
    token_other = resp_other.json()["access_token"]
    headers_other = {"Authorization": f"Bearer {token_other}"}
    resp_soc2 = await client.post("/api/societies", headers=headers_other, json={
        "name": f"Palm Meadows {ts}",
        "address": "Koramangala",
        "city": "Bengaluru",
        "total_flats": 40,
        "creator_flat_number": "PM-1",
    })
    soc2_id = resp_soc2.json()["society"]["id"]

    # 6. Open Round 1 in Society 1
    resp_round = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=headers_vol,
        json={
            "title": "Weekend Community Bulk Order",
            "description": "Sunday wholesale procurement",
            "deadline_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "shopping_date": "Sunday 10:00 AM",
        },
    )
    round_id = resp_round.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=headers_vol)

    return {
        "soc1_id": soc1_id,
        "round_id": round_id,
        "soc2_id": soc2_id,
        "headers_admin": headers_admin,
        "headers_vol": headers_vol,
        "headers_res1": headers_res1,
        "headers_res2": headers_res2,
        "headers_other": headers_other,
        "user1_id": user1_id,
        "user2_id": user2_id,
    }


@pytest.mark.asyncio
async def test_01_aggregation_and_unit_normalization(client: AsyncClient, setup_phase6_data):
    """Verify safe quantity aggregation, compatible unit normalization, and separation rules."""
    data = setup_phase6_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    orders_col = get_grocery_orders_collection()
    now = datetime.now(timezone.utc)

    # Flat C-303 confirmed items:
    # 1. Sona Masoori Rice: 5 kg (grains_rice)
    # 2. Aashirvaad Atta: 500 g (grains_rice) -> converts to 0.5 kg
    # 3. Sunflower Oil: 500 ml (cooking_oils) -> converts to 0.5 L
    # 4. Tomato: 1 kg (vegetables)
    # 5. Packaged Rice: 2 packet (grains_rice) -> incompatible unit with kg
    order_c303 = {
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_c303_{int(time.time()*1000)}",
        "message_id": "msg_c303",
        "user_id": data["user1_id"],
        "flat_number": "C-303",
        "user_name": "Resident Srinivas",
        "raw_text": "Rice, Atta, Oil, Tomato",
        "detected_language": "en",
        "status": "confirmed",
        "items": [
            {"id": "c1", "original_name": "sona masoori rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "brand": "Sona Masoori", "category": "grains_rice", "confidence": 1.0},
            {"id": "c2", "original_name": "aashirvaad atta", "normalized_name": "Atta", "quantity": 500.0, "unit": "g", "brand": "Aashirvaad", "category": "grains_rice", "confidence": 1.0},
            {"id": "c3", "original_name": "sunflower oil", "normalized_name": "Sunflower Oil", "quantity": 500.0, "unit": "ml", "brand": None, "category": "cooking_oils", "confidence": 1.0},
            {"id": "c4", "original_name": "tomatoes", "normalized_name": "Tomato", "quantity": 1.0, "unit": "kg", "category": "vegetables", "confidence": 1.0},
            {"id": "c5", "original_name": "rice packet", "normalized_name": "Rice", "quantity": 2.0, "unit": "packet", "brand": "Sona Masoori", "category": "grains_rice", "confidence": 1.0},
        ],
        "created_at": now,
        "updated_at": now,
        "confirmed_at": now,
    }
    await orders_col.insert_one(order_c303)

    # Flat D-404 confirmed items:
    # 1. Sona Masoori Rice: 10 kg (grains_rice) -> sums with C-303 (5 + 10 = 15 kg)
    # 2. Aashirvaad Atta: 1 kg (grains_rice) -> sums with C-303 (0.5 + 1 = 1.5 kg)
    # 3. Pillsbury Atta: 2 kg (grains_rice) -> separate entry due to different brand!
    # 4. Sunflower Oil: 1 L (cooking_oils) -> sums with C-303 (0.5 + 1 = 1.5 L)
    # 5. Groundnut Oil: 1 L (cooking_oils) -> separate entry due to different variant!
    order_d404 = {
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_d404_{int(time.time()*1000)}",
        "message_id": "msg_d404",
        "user_id": data["user2_id"],
        "flat_number": "D-404",
        "user_name": "Resident Pooja",
        "raw_text": "Rice, Atta, Oils",
        "detected_language": "en",
        "status": "confirmed",
        "items": [
            {"id": "d1", "original_name": "sona masoori rice", "normalized_name": "Rice", "quantity": 10.0, "unit": "kg", "brand": "Sona Masoori", "category": "grains_rice", "confidence": 1.0},
            {"id": "d2", "original_name": "aashirvaad atta", "normalized_name": "Atta", "quantity": 1.0, "unit": "kg", "brand": "Aashirvaad", "category": "grains_rice", "confidence": 1.0},
            {"id": "d3", "original_name": "pillsbury atta", "normalized_name": "Atta", "quantity": 2.0, "unit": "kg", "brand": "Pillsbury", "category": "grains_rice", "confidence": 1.0},
            {"id": "d4", "original_name": "sunflower oil", "normalized_name": "Sunflower Oil", "quantity": 1.0, "unit": "L", "brand": None, "category": "cooking_oils", "confidence": 1.0},
            {"id": "d5", "original_name": "groundnut oil", "normalized_name": "Groundnut Oil", "quantity": 1.0, "unit": "L", "brand": None, "category": "cooking_oils", "confidence": 1.0},
        ],
        "created_at": now,
        "updated_at": now,
        "confirmed_at": now,
    }
    await orders_col.insert_one(order_d404)

    # Trigger compilation via Volunteer API
    res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_vol,
    )
    assert res.status_code == 200
    manifest = res.json()

    # 1. Summary checks
    assert manifest["summary"]["total_confirmed_flats"] == 2
    assert manifest["summary"]["total_confirmed_orders"] == 2
    assert manifest["summary"]["total_unresolved_orders"] == 0

    # 2. Category Grains & Rice checks
    grains_group = next(cg for cg in manifest["categories"] if cg["category"] == "grains_rice")
    # Expected items in grains_rice:
    # - Rice (Sona Masoori, kg) -> total 15.0 kg
    # - Rice (Sona Masoori, packet) -> total 2.0 packet (incompatible unit separate)
    # - Atta (Aashirvaad, kg) -> total 1.5 kg (normalized from 500g + 1kg)
    # - Atta (Pillsbury, kg) -> total 2.0 kg (different brand separate)
    assert len(grains_group["items"]) == 4

    rice_kg = next(it for it in grains_group["items"] if it["normalized_name"] == "Rice" and it["unit"] == "kg")
    assert rice_kg["total_quantity"] == 15.0
    assert rice_kg["contributing_flats_count"] == 2

    rice_pkt = next(it for it in grains_group["items"] if it["normalized_name"] == "Rice" and it["unit"] == "packet")
    assert rice_pkt["total_quantity"] == 2.0
    assert rice_pkt["contributing_flats_count"] == 1

    atta_aashirvaad = next(it for it in grains_group["items"] if it["normalized_name"] == "Atta" and it["brand"] == "Aashirvaad")
    assert atta_aashirvaad["total_quantity"] == 1.5
    assert atta_aashirvaad["unit"] == "kg"

    atta_pillsbury = next(it for it in grains_group["items"] if it["normalized_name"] == "Atta" and it["brand"] == "Pillsbury")
    assert atta_pillsbury["total_quantity"] == 2.0

    # 3. Category Cooking Oils checks
    oils_group = next(cg for cg in manifest["categories"] if cg["category"] == "cooking_oils")
    # Expected: Sunflower Oil (1.5 L, normalized 500ml + 1L) and Groundnut Oil (1.0 L)
    assert len(oils_group["items"]) == 2
    sunflower = next(it for it in oils_group["items"] if it["normalized_name"] == "Sunflower Oil")
    assert sunflower["total_quantity"] == 1.5
    assert sunflower["unit"] == "L"

    groundnut = next(it for it in oils_group["items"] if it["normalized_name"] == "Groundnut Oil")
    assert groundnut["total_quantity"] == 1.0


@pytest.mark.asyncio
async def test_02_order_eligibility_and_unconfirmed_exclusion(client: AsyncClient, setup_phase6_data):
    """Verify that unconfirmed/pending/failed orders are excluded from the shopping list and flagged with warnings."""
    data = setup_phase6_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    orders_col = get_grocery_orders_collection()
    now = datetime.now(timezone.utc)

    # 1. Confirmed Order -> INCLUDED
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_conf_{int(time.time()*1000)}",
        "message_id": "msg_conf",
        "user_id": data["user1_id"],
        "flat_number": "C-303",
        "user_name": "Resident Srinivas",
        "raw_text": "2 kg sugar",
        "status": "confirmed",
        "items": [{"id": "i1", "original_name": "sugar", "normalized_name": "Sugar", "quantity": 2.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": now,
        "updated_at": now,
    })

    # 2. Pending Review -> EXCLUDED from manifest, INCLUDED in unresolved
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_pen_{int(time.time()*1000)}",
        "message_id": "msg_pen",
        "user_id": data["user2_id"],
        "flat_number": "D-404",
        "user_name": "Resident Pooja",
        "raw_text": "5 kg wheat flour",
        "status": "pending_review",
        "items": [{"id": "i2", "original_name": "wheat flour", "normalized_name": "Atta", "quantity": 5.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": now,
        "updated_at": now,
    })

    # 3. Needs Clarification -> EXCLUDED from manifest, INCLUDED in unresolved
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_clar_{int(time.time()*1000)}",
        "message_id": "msg_clar",
        "user_id": "user_clar_id",
        "flat_number": "E-505",
        "user_name": "Resident Rajesh",
        "raw_text": "some coriander",
        "status": "needs_clarification",
        "clarification_prompt": "Please specify quantity of coriander",
        "items": [{"id": "i3", "original_name": "coriander", "normalized_name": "Coriander", "quantity": None, "unit": None, "category": "vegetables"}],
        "created_at": now,
        "updated_at": now,
    })

    # 4. Processing -> EXCLUDED from manifest, INCLUDED in unresolved
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_proc_{int(time.time()*1000)}",
        "message_id": "msg_proc",
        "user_id": "user_proc_id",
        "flat_number": "F-606",
        "user_name": "Resident Divya",
        "raw_text": "1 packet butter",
        "status": "processing",
        "items": [],
        "created_at": now,
        "updated_at": now,
    })

    # 5. Failed -> EXCLUDED from manifest, INCLUDED in unresolved
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_fail_{int(time.time()*1000)}",
        "message_id": "msg_fail",
        "user_id": "user_fail_id",
        "flat_number": "G-707",
        "user_name": "Resident Anita",
        "raw_text": "gibberish text",
        "status": "failed",
        "error_message": "LLM parsing timeout",
        "items": [],
        "created_at": now,
        "updated_at": now,
    })

    # 6. Rejected -> EXCLUDED from manifest, counted separately (not pending confirmation)
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_rej_{int(time.time()*1000)}",
        "message_id": "msg_rej",
        "user_id": "user_rej_id",
        "flat_number": "H-808",
        "user_name": "Resident Vikram",
        "raw_text": "2 kg apples",
        "status": "rejected",
        "items": [{"id": "i6", "original_name": "apples", "normalized_name": "Apple", "quantity": 2.0, "unit": "kg", "category": "fruits"}],
        "created_at": now,
        "updated_at": now,
    })

    # Compile shopping list
    res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_vol,
    )
    assert res.status_code == 200
    manifest = res.json()

    # Confirmed counts
    assert manifest["summary"]["total_confirmed_flats"] == 1
    assert manifest["summary"]["total_confirmed_orders"] == 1

    # Unresolved counts
    assert manifest["summary"]["total_unresolved_flats"] == 4
    assert manifest["summary"]["total_unresolved_orders"] == 4
    assert manifest["summary"]["has_unresolved_orders"] is True
    assert manifest["summary"]["rejected_orders_count"] == 1

    # Unresolved orders list length
    assert len(manifest["unresolved_orders"]) == 4
    unresolved_statuses = set(uo["status"] for uo in manifest["unresolved_orders"])
    assert unresolved_statuses == {"pending_review", "needs_clarification", "processing", "failed"}

    # Verified items in shopping list MUST ONLY contain Sugar (2 kg)
    all_items = [it for cg in manifest["categories"] for it in cg["items"]]
    assert len(all_items) == 1
    assert all_items[0]["normalized_name"] == "Sugar"
    assert all_items[0]["total_quantity"] == 2.0


@pytest.mark.asyncio
async def test_03_flat_wise_packing_breakdown(client: AsyncClient, setup_phase6_data):
    """Verify that flat-wise packing breakdown groups items accurately by flat and preserves details."""
    data = setup_phase6_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    orders_col = get_grocery_orders_collection()
    now = datetime.now(timezone.utc)

    # Flat A-101 Order
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_a101_{int(time.time()*1000)}",
        "message_id": "msg_a101",
        "user_id": data["user1_id"],
        "flat_number": "A-101",
        "user_name": "Resident Srinivas",
        "raw_text": "5 kg rice, 1 L milk",
        "status": "confirmed",
        "items": [
            {"id": "it1", "original_name": "rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "brand": "India Gate", "category": "grains_rice"},
            {"id": "it2", "original_name": "milk", "normalized_name": "Milk", "quantity": 1.0, "unit": "L", "brand": "Amul", "category": "dairy"},
        ],
        "created_at": now,
        "updated_at": now,
    })

    # Flat B-202 Order
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_b202_{int(time.time()*1000)}",
        "message_id": "msg_b202",
        "user_id": data["user2_id"],
        "flat_number": "B-202",
        "user_name": "Resident Pooja",
        "raw_text": "2 packets bread, 6 eggs",
        "status": "confirmed",
        "items": [
            {"id": "it3", "original_name": "bread", "normalized_name": "Bread", "quantity": 2.0, "unit": "packet", "category": "other"},
            {"id": "it4", "original_name": "eggs", "normalized_name": "Eggs", "quantity": 6.0, "unit": "piece", "category": "other"},
        ],
        "created_at": now,
        "updated_at": now,
    })

    res = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_vol,
    )
    assert res.status_code == 200
    manifest = res.json()

    packing = manifest["packing_breakdown"]
    assert len(packing) == 2

    # Alphabetically sorted by flat
    flat_a = packing[0]
    assert flat_a["flat_number"] == "A-101"
    assert flat_a["user_name"] == "Resident Srinivas"
    assert len(flat_a["items"]) == 2
    assert flat_a["items"][0]["brand"] == "India Gate"
    assert flat_a["items"][1]["brand"] == "Amul"

    flat_b = packing[1]
    assert flat_b["flat_number"] == "B-202"
    assert flat_b["user_name"] == "Resident Pooja"
    assert len(flat_b["items"]) == 2
    assert flat_b["items"][0]["normalized_name"] == "Bread"
    assert flat_b["items"][1]["normalized_name"] == "Eggs"


@pytest.mark.asyncio
async def test_04_compilation_lifecycle_and_recompilation(client: AsyncClient, setup_phase6_data):
    """Verify empty round state, recompilation reflecting new orders, and zero double-counting."""
    data = setup_phase6_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    orders_col = get_grocery_orders_collection()
    now = datetime.now(timezone.utc)

    # 1. Compile on empty round
    res_empty = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_vol,
    )
    assert res_empty.status_code == 200
    manifest_empty = res_empty.json()
    assert manifest_empty["version"] == 1
    assert manifest_empty["summary"]["total_confirmed_flats"] == 0
    assert manifest_empty["summary"]["total_distinct_items"] == 0

    # 2. Add first confirmed order (5 kg Rice) and recompile
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_order1_{int(time.time()*1000)}",
        "user_id": data["user1_id"],
        "flat_number": "C-303",
        "user_name": "Resident Srinivas",
        "raw_text": "5 kg rice",
        "status": "confirmed",
        "items": [{"id": "i1", "original_name": "rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": now,
        "updated_at": now,
    })

    res_v2 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_vol,
    )
    assert res_v2.status_code == 200
    manifest_v2 = res_v2.json()
    assert manifest_v2["version"] == 2
    assert manifest_v2["summary"]["total_distinct_items"] == 1

    grains_v2 = next(cg for cg in manifest_v2["categories"] if cg["category"] == "grains_rice")
    assert grains_v2["items"][0]["total_quantity"] == 5.0

    # 3. Add second confirmed order (10 kg Rice) and recompile
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_order2_{int(time.time()*1000)}",
        "user_id": data["user2_id"],
        "flat_number": "D-404",
        "user_name": "Resident Pooja",
        "raw_text": "10 kg rice",
        "status": "confirmed",
        "items": [{"id": "i2", "original_name": "rice", "normalized_name": "Rice", "quantity": 10.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": now,
        "updated_at": now,
    })

    res_v3 = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_vol,
    )
    assert res_v3.status_code == 200
    manifest_v3 = res_v3.json()
    assert manifest_v3["version"] == 3

    # Must recalculate from source orders without double-counting (5 + 10 = 15, NOT 5 + 5 + 10 = 20)
    grains_v3 = next(cg for cg in manifest_v3["categories"] if cg["category"] == "grains_rice")
    assert grains_v3["items"][0]["total_quantity"] == 15.0

    # 4. Concurrent recompilation requests
    r1, r2 = await asyncio.gather(
        client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile", headers=headers_vol),
        client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile", headers=headers_vol),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["summary"]["total_confirmed_flats"] == 2
    assert r2.json()["summary"]["total_confirmed_flats"] == 2


@pytest.mark.asyncio
async def test_05_authorization_and_cross_society_isolation(client: AsyncClient, setup_phase6_data):
    """Verify that residents and external societies cannot compile or view shopping lists."""
    data = setup_phase6_data
    soc1_id = data["soc1_id"]
    soc2_id = data["soc2_id"]
    round_id = data["round_id"]
    headers_res1 = data["headers_res1"]
    headers_vol = data["headers_vol"]
    headers_admin = data["headers_admin"]
    headers_other = data["headers_other"]

    # 1. Resident cannot compile shopping list -> 403 Forbidden
    res_compile = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_res1,
    )
    assert res_compile.status_code == 403

    # 2. Resident cannot retrieve shopping list -> 403 Forbidden
    res_get = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list",
        headers=headers_res1,
    )
    assert res_get.status_code == 403

    # 3. Volunteer can compile and retrieve -> 200 OK
    assert (await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile", headers=headers_vol)).status_code == 200
    assert (await client.get(f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list", headers=headers_vol)).status_code == 200

    # 4. Admin can compile and retrieve -> 200 OK
    assert (await client.get(f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list", headers=headers_admin)).status_code == 200

    # 5. External society admin cannot compile or view Society 1 shopping list -> 403 Forbidden
    cross_compile = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_other,
    )
    assert cross_compile.status_code == 403

    cross_get = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list",
        headers=headers_other,
    )
    assert cross_get.status_code == 403


@pytest.mark.asyncio
async def test_06_csv_export(client: AsyncClient, setup_phase6_data):
    """Verify RFC 4180 compliant CSV export for consolidated shopping list and packing breakdown."""
    data = setup_phase6_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_vol = data["headers_vol"]
    headers_res1 = data["headers_res1"]
    headers_other = data["headers_other"]
    orders_col = get_grocery_orders_collection()
    now = datetime.now(timezone.utc)

    # Insert confirmed order
    await orders_col.insert_one({
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_csv_{int(time.time()*1000)}",
        "user_id": data["user1_id"],
        "flat_number": "C-303",
        "user_name": "Resident Srinivas",
        "raw_text": "5 kg toor dal",
        "status": "confirmed",
        "items": [{"id": "it_csv", "original_name": "toor dal", "normalized_name": "Toor Dal", "quantity": 5.0, "unit": "kg", "brand": "Tata Sampann", "category": "pulses"}],
        "created_at": now,
        "updated_at": now,
    })

    # 1. Consolidated CSV Export
    resp_csv = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/export?type=consolidated",
        headers=headers_vol,
    )
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "attachment" in resp_csv.headers["content-disposition"]
    csv_text = resp_csv.text
    assert "Category,Item Name,Brand,Variant,Total Quantity,Unit,Contributing Flats Count,Contributing Flats" in csv_text
    assert "Pulses,Toor Dal,Tata Sampann,,5.0,kg,1,C-303" in csv_text

    # 2. Packing Breakdown CSV Export
    resp_pack_csv = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/export?type=packing",
        headers=headers_vol,
    )
    assert resp_pack_csv.status_code == 200
    pack_text = resp_pack_csv.text
    assert "Flat Number,Resident Name,Category,Item Name,Brand,Variant,Quantity,Unit" in pack_text
    assert "C-303,Resident Srinivas,Pulses,Toor Dal,Tata Sampann,,5.0,kg" in pack_text

    # 3. Resident or cross-society blocked from CSV export -> 403 Forbidden
    assert (await client.get(f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/export", headers=headers_res1)).status_code == 403
    assert (await client.get(f"/api/societies/{soc1_id}/rounds/{round_id}/shopping-list/export", headers=headers_other)).status_code == 403
