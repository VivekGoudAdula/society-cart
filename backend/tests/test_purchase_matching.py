"""Test suite for Purchase-to-Order Fulfillment Matching and Cost Allocation.

Validates the exact production scenario:
Resident Requests:
- Aashirvaad Atta – 2 packets (Flat 202)
- Sona Masoori Rice – 5 kg (Flat C-402)
- Sunflower Oil – 2 L (Flat C-402)

Recorded Actual Purchases:
- Sona Masoori Rice – 5 kg – ₹500 – D-Mart
- Ashirvad Aata – 2 packets – ₹200 – D-Mart
- Sun flower oil – 2 L – ₹200 – D-Mart
Total expenditure: ₹900.

Assertions:
1. Matching engine recognizes transliteration and compound spelling variations:
   - Ashirvad Aata ↔ Aashirvaad Atta
   - Sun flower oil ↔ Sunflower Oil
   - Sona Masoori Rice ↔ Sona Masoori Rice
2. Matching summary reflects:
   - Purchased Qty = 2 packets, 5 kg, 2 L
   - Fulfilled Qty = 2 packets, 5 kg, 2 L
   - Unfulfilled Qty = 0 across all items
   - Effective rates = ₹100/packet, ₹100/kg, ₹100/L
3. Per-flat allocations sum exactly to ₹900:
   - Flat 202 = ₹200.00
   - Flat C-402 = ₹700.00
   - Unallocated = ₹0.00
   - Reconciliation diff = ₹0.00
"""

import time
import pytest
from httpx import AsyncClient

from app.services.billing_service import (
    are_units_compatible,
    extract_product_tokens,
    compute_product_match_score,
    _match_all_purchases_to_manifest,
)
from app.schemas.shopping_list import ConsolidatedItem


def test_unit_compatibility_and_normalization():
    """Verify compatible units and conversion factors."""
    compat, factor = are_units_compatible("packet", "packets")
    assert compat is True and factor == 1.0

    compat, factor = are_units_compatible("kg", "kgs")
    assert compat is True and factor == 1.0

    compat, factor = are_units_compatible("L", "litres")
    assert compat is True and factor == 1.0

    compat, factor = are_units_compatible("kg", "g")
    assert compat is True and factor == 0.001

    compat, factor = are_units_compatible("L", "ml")
    assert compat is True and factor == 0.001

    compat, _ = are_units_compatible("kg", "packet")
    assert compat is False


def test_product_tokens_and_similarity():
    """Verify transliteration and compound phrase normalization."""
    tokens_req_atta = extract_product_tokens("Aashirvaad Atta")
    tokens_pur_atta = extract_product_tokens("Ashirvad Aata")
    score_atta = compute_product_match_score(tokens_req_atta, tokens_pur_atta)
    assert score_atta >= 0.80

    tokens_req_oil = extract_product_tokens("Sunflower Oil")
    tokens_pur_oil = extract_product_tokens("Sun flower oil")
    score_oil = compute_product_match_score(tokens_req_oil, tokens_pur_oil)
    assert score_oil >= 0.80

    tokens_req_rice = extract_product_tokens("Sona Masoori Rice")
    tokens_pur_rice = extract_product_tokens("Sona Masoori Rice")
    score_rice = compute_product_match_score(tokens_req_rice, tokens_pur_rice)
    assert score_rice >= 0.90


def test_matching_all_purchases_to_manifest_items():
    """Direct unit test of _match_all_purchases_to_manifest with the 3 confirmed purchases."""
    manifest_items = [
        ConsolidatedItem(
            item_key="staples_atta_dal__aashirvaad atta____packet",
            normalized_name="Aashirvaad Atta",
            brand="Aashirvaad",
            variant=None,
            category="staples_atta_dal",
            unit="packet",
            total_quantity=2.0,
            contributing_flats_count=1,
            original_names=["Aashirvaad Atta", "atta"],
        ),
        ConsolidatedItem(
            item_key="grains_rice__sona masoori rice____kg",
            normalized_name="Sona Masoori Rice",
            brand=None,
            variant="Sona Masoori",
            category="grains_rice",
            unit="kg",
            total_quantity=5.0,
            contributing_flats_count=1,
            original_names=["Sona Masoori Rice"],
        ),
        ConsolidatedItem(
            item_key="cooking_oils__sunflower oil____l",
            normalized_name="Sunflower Oil",
            brand=None,
            variant="Sunflower",
            category="cooking_oils",
            unit="L",
            total_quantity=2.0,
            contributing_flats_count=1,
            original_names=["Sunflower Oil"],
        ),
    ]

    recorded_purchases = [
        {
            "_id": "p_rice_1",
            "item_name": "Sona Masoori Rice",
            "actual_quantity": 5.0,
            "unit": "kg",
            "total_price": 500.0,
            "category": "grains_rice",
            "brand": None,
            "variant": None,
        },
        {
            "_id": "p_atta_1",
            "item_name": "Ashirvad Aata",
            "actual_quantity": 2.0,
            "unit": "packet",
            "total_price": 200.0,
            "category": "staples_atta_dal",
            "brand": "Ashirvad",
            "variant": None,
        },
        {
            "_id": "p_oil_1",
            "item_name": "Sun flower oil",
            "actual_quantity": 2.0,
            "unit": "L",
            "total_price": 200.0,
            "category": "dairy_oil",
            "brand": None,
            "variant": None,
        },
    ]

    match_map = _match_all_purchases_to_manifest(manifest_items, recorded_purchases)

    # All three items must have exactly one matched purchase
    assert len(match_map["staples_atta_dal__aashirvaad atta____packet"]) == 1
    assert len(match_map["grains_rice__sona masoori rice____kg"]) == 1
    assert len(match_map["cooking_oils__sunflower oil____l"]) == 1

    atta_match = match_map["staples_atta_dal__aashirvaad atta____packet"][0]
    assert atta_match[0]["item_name"] == "Ashirvad Aata"
    assert atta_match[0]["actual_quantity"] == 2.0
    assert atta_match[0]["total_price"] == 200.0

    rice_match = match_map["grains_rice__sona masoori rice____kg"][0]
    assert rice_match[0]["item_name"] == "Sona Masoori Rice"
    assert rice_match[0]["actual_quantity"] == 5.0
    assert rice_match[0]["total_price"] == 500.0

    oil_match = match_map["cooking_oils__sunflower oil____l"][0]
    assert oil_match[0]["item_name"] == "Sun flower oil"
    assert oil_match[0]["actual_quantity"] == 2.0
    assert oil_match[0]["total_price"] == 200.0


@pytest.mark.asyncio
async def test_full_purchase_fulfillment_and_allocation_workflow(client: AsyncClient):
    """End-to-end integration test creating the exact 3 requests and 3 recorded purchases."""
    from datetime import datetime, timezone, timedelta
    from app.core.database import get_grocery_orders_collection

    ts = int(time.time() * 1000)

    # 1. Register Admin and Create Society
    resp_admin = await client.post("/api/auth/register", json={
        "name": "Admin Sharma",
        "email": f"admin_match_{ts}@example.com",
        "password": "Password123!",
    })
    token_admin = resp_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    resp_soc = await client.post("/api/societies", headers=headers_admin, json={
        "name": f"Palm Meadows {ts}",
        "address": "Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "total_flats": 50,
        "creator_flat_number": "A-101",
    })
    soc_id = resp_soc.json()["society"]["id"]
    invite_code = resp_soc.json()["society"]["invite_code"]

    # 2. Register Volunteer
    resp_vol = await client.post("/api/auth/register", json={
        "name": "Volunteer Ramesh",
        "email": f"vol_match_{ts}@example.com",
        "password": "Password123!",
    })
    token_vol = resp_vol.json()["access_token"]
    headers_vol = {"Authorization": f"Bearer {token_vol}"}
    join_vol = await client.post("/api/societies/join", headers=headers_vol, json={
        "invite_code": invite_code,
        "flat_number": "V-001",
    })
    vol_mem_id = join_vol.json()["membership"]["id"]
    await client.patch(
        f"/api/societies/{soc_id}/members/{vol_mem_id}/role",
        headers=headers_admin,
        json={"role": "volunteer"},
    )

    # 3. Register Resident 1 (Flat 202)
    resp_res1 = await client.post("/api/auth/register", json={
        "name": "Geeta Sharma",
        "email": f"geeta_{ts}@example.com",
        "password": "Password123!",
    })
    user1_id = resp_res1.json()["user"]["id"]
    token_res1 = resp_res1.json()["access_token"]
    headers_res1 = {"Authorization": f"Bearer {token_res1}"}
    await client.post("/api/societies/join", headers=headers_res1, json={
        "invite_code": invite_code,
        "flat_number": "202",
    })

    # 4. Register Resident 2 (Flat C-402)
    resp_res2 = await client.post("/api/auth/register", json={
        "name": "Praveen Rao",
        "email": f"praveen_{ts}@example.com",
        "password": "Password123!",
    })
    user2_id = resp_res2.json()["user"]["id"]
    token_res2 = resp_res2.json()["access_token"]
    headers_res2 = {"Authorization": f"Bearer {token_res2}"}
    await client.post("/api/societies/join", headers=headers_res2, json={
        "invite_code": invite_code,
        "flat_number": "C-402",
    })

    # 5. Create Order Round & Open
    deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp_round = await client.post(
        f"/api/societies/{soc_id}/rounds",
        headers=headers_vol,
        json={
            "title": "Weekend Fresh Wholesale",
            "deadline_at": deadline,
            "shopping_date": "Sunday 9:00 AM",
        },
    )
    round_id = resp_round.json()["id"]
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/open", headers=headers_vol)

    # 6. Place Confirmed Resident Orders in DB:
    # Resident 1 (Flat 202): Aashirvaad Atta – 2 packets
    orders_col = get_grocery_orders_collection()
    now_dt = datetime.now(timezone.utc)
    await orders_col.insert_one({
        "society_id": soc_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_match1_{ts}",
        "user_id": user1_id,
        "flat_number": "202",
        "user_name": "Geeta Sharma",
        "raw_text": "2 packets Aashirvaad Atta",
        "status": "confirmed",
        "items": [
            {
                "id": f"item_atta_{ts}",
                "original_name": "Aashirvaad Atta",
                "normalized_name": "Aashirvaad Atta",
                "quantity": 2.0,
                "unit": "packet",
                "category": "staples_atta_dal",
                "brand": "Aashirvaad",
                "variant": None,
            }
        ],
        "created_at": now_dt,
        "updated_at": now_dt,
    })

    # Resident 2 (Flat C-402): Sona Masoori Rice 5 kg, Sunflower Oil 2 L
    await orders_col.insert_one({
        "society_id": soc_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": f"sub_match2_{ts}",
        "user_id": user2_id,
        "flat_number": "C-402",
        "user_name": "Praveen Rao",
        "raw_text": "5 kg Sona Masoori Rice and 2 L Sunflower Oil",
        "status": "confirmed",
        "items": [
            {
                "id": f"item_rice_{ts}",
                "original_name": "Sona Masoori Rice",
                "normalized_name": "Sona Masoori Rice",
                "quantity": 5.0,
                "unit": "kg",
                "category": "grains_rice",
                "brand": None,
                "variant": "Sona Masoori",
            },
            {
                "id": f"item_oil_{ts}",
                "original_name": "Sunflower Oil",
                "normalized_name": "Sunflower Oil",
                "quantity": 2.0,
                "unit": "L",
                "category": "cooking_oils",
                "brand": None,
                "variant": "Sunflower",
            },
        ],
        "created_at": now_dt,
        "updated_at": now_dt,
    })

    # 7. Close Round & Compile Shopping List
    await client.post(f"/api/societies/{soc_id}/rounds/{round_id}/close", headers=headers_vol)
    resp_compile = await client.post(
        f"/api/societies/{soc_id}/rounds/{round_id}/shopping-list/compile",
        headers=headers_vol,
    )
    assert resp_compile.status_code == 200

    # 8. Volunteer Records Actual Purchases:
    # - Sona Masoori Rice – 5 kg – ₹500 – D-Mart
    resp_p1 = await client.post(
        f"/api/societies/{soc_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Sona Masoori Rice",
            "actual_quantity": 5.0,
            "unit": "kg",
            "total_price": 500.0,
            "shop_name": "D-Mart",
            "category": "grains_rice",
        },
    )
    assert resp_p1.status_code == 201

    # - Ashirvad Aata – 2 packets – ₹200 – D-Mart (spelling variation)
    resp_p2 = await client.post(
        f"/api/societies/{soc_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Ashirvad Aata",
            "actual_quantity": 2.0,
            "unit": "packet",
            "total_price": 200.0,
            "shop_name": "D-Mart",
            "category": "staples_atta_dal",
        },
    )
    assert resp_p2.status_code == 201

    # - Sun flower oil – 2 L – ₹200 – D-Mart (compound space variation)
    resp_p3 = await client.post(
        f"/api/societies/{soc_id}/rounds/{round_id}/purchases",
        headers=headers_vol,
        json={
            "item_name": "Sun flower oil",
            "actual_quantity": 2.0,
            "unit": "L",
            "total_price": 200.0,
            "shop_name": "D-Mart",
            "category": "dairy_oil",
        },
    )
    assert resp_p3.status_code == 201

    # 9. Get Allocation Preview
    resp_preview = await client.get(
        f"/api/societies/{soc_id}/rounds/{round_id}/allocation/preview",
        headers=headers_vol,
    )
    assert resp_preview.status_code == 200
    preview_data = resp_preview.json()

    # --- VERIFY MATCHING SUMMARIES ---
    summaries = preview_data["matching_summaries"]
    assert len(summaries) == 3

    # Map by canonical name lowercase
    summary_by_name = {s["item_name"].lower(): s for s in summaries}

    # Verify Atta matching
    atta_summary = next(s for k, s in summary_by_name.items() if "atta" in k)
    assert atta_summary["requested_quantity"] == 2.0
    assert atta_summary["purchased_quantity"] == 2.0
    assert atta_summary["fulfilled_quantity"] == 2.0
    assert atta_summary["unfulfilled_quantity"] == 0.0
    assert atta_summary["effective_unit_cost"] == 100.0
    assert atta_summary["total_cost"] == 200.0

    # Verify Rice matching
    rice_summary = next(s for k, s in summary_by_name.items() if "rice" in k)
    assert rice_summary["requested_quantity"] == 5.0
    assert rice_summary["purchased_quantity"] == 5.0
    assert rice_summary["fulfilled_quantity"] == 5.0
    assert rice_summary["unfulfilled_quantity"] == 0.0
    assert rice_summary["effective_unit_cost"] == 100.0
    assert rice_summary["total_cost"] == 500.0

    # Verify Oil matching
    oil_summary = next(s for k, s in summary_by_name.items() if "oil" in k)
    assert oil_summary["requested_quantity"] == 2.0
    assert oil_summary["purchased_quantity"] == 2.0
    assert oil_summary["fulfilled_quantity"] == 2.0
    assert oil_summary["unfulfilled_quantity"] == 0.0
    assert oil_summary["effective_unit_cost"] == 100.0
    assert oil_summary["total_cost"] == 200.0

    # --- VERIFY PER-FLAT ALLOCATIONS ---
    flat_allocs = preview_data["flat_allocations"]
    assert len(flat_allocs) == 2

    flat_by_num = {f["flat_number"]: f for f in flat_allocs}

    # Flat 202: 2 packets Atta = ₹200.00
    assert flat_by_num["202"]["items_subtotal"] == 200.00
    assert flat_by_num["202"]["final_amount_payable"] == 200.00

    # Flat C-402: 5 kg Rice (₹500) + 2 L Oil (₹200) = ₹700.00
    assert flat_by_num["C-402"]["items_subtotal"] == 700.00
    assert flat_by_num["C-402"]["final_amount_payable"] == 700.00

    # Total allocated = 200 + 700 = ₹900.00
    assert preview_data["total_actual_purchase_cost"] == 900.00
    assert preview_data["total_allocated_flats_cost"] == 900.00
    assert preview_data["unallocated_cost"] == 0.00
    assert preview_data["is_reconciled"] is True
    assert preview_data["can_finalize"] is True

    # 10. Finalize Bills and verify persistence
    resp_finalize = await client.post(
        f"/api/societies/{soc_id}/rounds/{round_id}/bills/finalize",
        headers=headers_vol,
        json={"shared_costs": []},
    )
    assert resp_finalize.status_code == 200
    finalized = resp_finalize.json()
    assert len(finalized) == 2

    finalized_by_flat = {b["flat_number"]: b for b in finalized}
    assert finalized_by_flat["202"]["total_amount"] == 200.00
    assert finalized_by_flat["C-402"]["total_amount"] == 700.00
