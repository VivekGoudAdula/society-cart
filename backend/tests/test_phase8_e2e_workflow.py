"""
Phase 8: End-to-End 15-Stage Workflow Verification.

Verifies the full lifecycle of a bulk grocery ordering cycle strictly through API endpoints
and official service interfaces without manual database edits:
1. Admin registers and creates society
2. Residents & Volunteer register and join society
3. Volunteer opens grocery order round
4. Residents reserve grocery order submissions (simulating Nexconn group chat)
5. Background AI extraction processes grocery messages (using deterministic mock Groq handler)
6. Submissions confirmed into pending_review orders
7. Residents review, adjust quantities, and confirm orders
8. Volunteer closes order round
9. Volunteer compiles consolidated shopping list & packing breakdown
10. Volunteer records actual purchases & shared expenses
11. Volunteer previews cost allocation and finalizes bills
12. Residents retrieve and verify their individual bills
13. Volunteer creates and verifies retail benchmark evidence
14. Society savings summary is calculated against verified benchmarks
15. Volunteer publishes privacy-safe announcement to Nexconn group chat
"""

import pytest
import time
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.services import groq_service, order_service
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


@pytest.mark.asyncio
async def test_full_15_stage_e2e_workflow(client: AsyncClient):
    """
    Execute full end-to-end multi-resident, volunteer, and admin workflow across all 15 stages.
    """
    ts = int(time.time() * 1000)

    # -------------------------------------------------------------------------
    # Stage 1: Admin registers and creates society
    # -------------------------------------------------------------------------
    admin_reg_resp = await client.post("/api/auth/register", json={
        "name": f"Admin Sharma {ts}",
        "email": f"admin_e2e_{ts}@society.com",
        "password": "SecurePassword123!",
        "role": "admin"
    })
    assert admin_reg_resp.status_code == 201, admin_reg_resp.text
    admin_token = admin_reg_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    soc_resp = await client.post("/api/societies", json={
        "name": f"Prestige Lakeside {ts}",
        "address": "Varthur Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560087",
        "total_flats": 100,
        "creator_flat_number": "PH-01"
    }, headers=admin_headers)
    assert soc_resp.status_code == 201, soc_resp.text
    soc_data = soc_resp.json()
    society_id = soc_data["society"]["id"] if "society" in soc_data else soc_data["id"]
    invite_code = soc_data["society"]["invite_code"] if "society" in soc_data else soc_data["invite_code"]

    # -------------------------------------------------------------------------
    # Stage 2: Residents & Volunteer register and join society
    # -------------------------------------------------------------------------
    async def register_member(name: str, email: str, flat: str, role: str = "resident"):
        reg = await client.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": "SecurePassword123!",
            "role": role
        })
        assert reg.status_code == 201, reg.text
        t = reg.json()["access_token"]
        uid = reg.json()["user"]["id"]
        h = {"Authorization": f"Bearer {t}"}
        join = await client.post("/api/societies/join", json={
            "invite_code": invite_code,
            "flat_number": flat
        }, headers=h)
        assert join.status_code == 200, join.text
        mem_id = join.json()["membership"]["id"]
        return {"id": uid, "headers": h, "flat": flat, "membership_id": mem_id}

    vol = await register_member(f"Volunteer Priya {ts}", f"vol_e2e_{ts}@society.com", "V-101", "volunteer")
    await client.patch(
        f"/api/societies/{society_id}/members/{vol['membership_id']}/role",
        headers=admin_headers,
        json={"role": "volunteer"},
    )
    res1 = await register_member(f"Resident Amit {ts}", f"amit_e2e_{ts}@society.com", "A-201", "resident")
    res2 = await register_member(f"Resident Divya {ts}", f"divya_e2e_{ts}@society.com", "B-302", "resident")

    # -------------------------------------------------------------------------
    # Stage 3: Volunteer opens grocery order round
    # -------------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    round_create_resp = await client.post(f"/api/societies/{society_id}/rounds", json={
        "title": f"Weekend Organic Wholesale {ts}",
        "shopping_date": "Sunday Morning",
        "delivery_date": (now + timedelta(days=2)).date().isoformat(),
        "deadline_at": (now + timedelta(days=1)).isoformat()
    }, headers=vol["headers"])
    assert round_create_resp.status_code == 201, round_create_resp.text
    round_id = round_create_resp.json()["id"]

    round_open_resp = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/open", headers=vol["headers"])
    assert round_open_resp.status_code == 200, round_open_resp.text
    assert round_open_resp.json()["status"] == "open"

    # -------------------------------------------------------------------------
    # Stage 4: Residents reserve grocery order submissions
    # -------------------------------------------------------------------------
    sub1_resp = await client.post(
        f"/api/societies/{society_id}/rounds/{round_id}/submissions/reserve",
        headers=res1["headers"],
        json={"submission_id": f"sub_e2e_1_{ts}", "raw_text": "5kg Aashirvaad Atta, 2kg Sugar"}
    )
    assert sub1_resp.status_code in [200, 201]

    sub2_resp = await client.post(
        f"/api/societies/{society_id}/rounds/{round_id}/submissions/reserve",
        headers=res2["headers"],
        json={"submission_id": f"sub_e2e_2_{ts}", "raw_text": "5kg Aashirvaad Atta, 1L Sunflower Oil"}
    )
    assert sub2_resp.status_code in [200, 201]

    # -------------------------------------------------------------------------
    # Stage 5 & 6: Pre-set AI extraction mock & Bot confirmation into pending_review
    # -------------------------------------------------------------------------
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [
            {"id": "item_1", "original_name": "Aashirvaad Atta", "normalized_name": "Aashirvaad Atta", "brand": "Aashirvaad", "quantity": 5.0, "unit": "kg", "category": "grains_rice", "confidence": 0.98},
            {"id": "item_2", "original_name": "Sugar", "normalized_name": "Sugar", "brand": None, "quantity": 2.0, "unit": "kg", "category": "grains_rice", "confidence": 0.95} if "sugar" in raw.lower() else {"id": "item_2", "original_name": "Sunflower Oil", "normalized_name": "Sunflower Oil", "brand": None, "quantity": 1.0, "unit": "l", "category": "cooking_oils", "confidence": 0.95},
        ],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })

    c1_resp = await client.post(
        f"/api/societies/{society_id}/rounds/{round_id}/submissions/{sub1_resp.json()['submission_id']}/confirm",
        headers=res1["headers"],
        json={"message_id": f"msg_e2e_1_{ts}"}
    )
    assert c1_resp.status_code == 200

    c2_resp = await client.post(
        f"/api/societies/{society_id}/rounds/{round_id}/submissions/{sub2_resp.json()['submission_id']}/confirm",
        headers=res2["headers"],
        json={"message_id": f"msg_e2e_2_{ts}"}
    )
    assert c2_resp.status_code == 200

    order1 = await order_service.trigger_ai_extraction(
        society_id=society_id,
        round_id=round_id,
        round_number=1,
        submission_id=f"sub_e2e_1_{ts}",
        message_id=f"msg_e2e_1_{ts}",
        user_id=res1["id"],
        flat_number=res1["flat"],
        user_name="Resident Amit",
        raw_text="5kg Aashirvaad Atta, 2kg Sugar",
    )
    order1_id = order1.id

    order2 = await order_service.trigger_ai_extraction(
        society_id=society_id,
        round_id=round_id,
        round_number=1,
        submission_id=f"sub_e2e_2_{ts}",
        message_id=f"msg_e2e_2_{ts}",
        user_id=res2["id"],
        flat_number=res2["flat"],
        user_name="Resident Divya",
        raw_text="5kg Aashirvaad Atta, 1L Sunflower Oil",
    )
    order2_id = order2.id

    # -------------------------------------------------------------------------
    # Stage 7: Residents review, modify, and confirm orders
    # -------------------------------------------------------------------------
    # Resident 1 adjusts Sugar quantity from 2kg to 3kg
    adj_resp = await client.patch(f"/api/orders/{order1_id}/items", json={
        "items": [
            {"id": "item_1", "original_name": "Aashirvaad Atta", "normalized_name": "Aashirvaad Atta", "brand": "Aashirvaad", "quantity": 5.0, "unit": "kg", "category": "grains_rice"},
            {"id": "item_2", "original_name": "Sugar", "normalized_name": "Sugar", "brand": None, "quantity": 3.0, "unit": "kg", "category": "grains_rice"}
        ]
    }, headers=res1["headers"])
    assert adj_resp.status_code == 200, adj_resp.text
    assert adj_resp.json()["items"][1]["quantity"] == 3.0

    # Resident 1 confirms order
    conf1 = await client.post(f"/api/orders/{order1_id}/confirm", headers=res1["headers"])
    assert conf1.status_code == 200, conf1.text
    assert conf1.json()["status"] == "confirmed"

    # Resident 2 confirms order directly
    conf2 = await client.post(f"/api/orders/{order2_id}/confirm", headers=res2["headers"])
    assert conf2.status_code == 200, conf2.text
    assert conf2.json()["status"] == "confirmed"

    # -------------------------------------------------------------------------
    # Stage 8: Volunteer closes order round
    # -------------------------------------------------------------------------
    close_resp = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/close", headers=vol["headers"])
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json()["status"] == "closed"

    # -------------------------------------------------------------------------
    # Stage 9: Volunteer compiles consolidated shopping list
    # -------------------------------------------------------------------------
    compile_resp = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/shopping-list/compile", headers=vol["headers"])
    assert compile_resp.status_code == 200, compile_resp.text
    categories = compile_resp.json()["categories"]
    items = [it for cat in categories for it in cat["items"]]
    manifest_map = {}
    for it in items:
        manifest_map[it["normalized_name"]] = manifest_map.get(it["normalized_name"], 0.0) + it["total_quantity"]
    assert manifest_map["Aashirvaad Atta"] == 10.0
    assert manifest_map["Sugar"] == 3.0
    assert manifest_map["Sunflower Oil"] == 1.0

    # -------------------------------------------------------------------------
    # Stage 10: Volunteer records actual purchases & shared expenses
    # -------------------------------------------------------------------------
    # Atta: 10kg for 450.00 INR (45/kg)
    # Sugar: 3kg for 120.00 INR (40/kg)
    # Oil: 1L for 140.00 INR (140/L)
    # Total purchases = 450 + 120 + 140 = 710.00 INR
    # Shared auto tempo expense = 50.00 INR (split equally across 2 flats: 25.00 each)
    p1 = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/purchases", json={
        "item_name": "Aashirvaad Atta",
        "brand": "Aashirvaad",
        "category": "grains_rice",
        "actual_quantity": 10.0,
        "unit": "kg",
        "total_price": 450.00,
        "shop_name": "Metro Wholesale"
    }, headers=vol["headers"])
    assert p1.status_code == 201, p1.text

    p2 = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/purchases", json={
        "item_name": "Sugar",
        "category": "grains_rice",
        "actual_quantity": 3.0,
        "unit": "kg",
        "total_price": 120.00,
        "shop_name": "Metro Wholesale"
    }, headers=vol["headers"])
    assert p2.status_code == 201, p2.text

    p3 = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/purchases", json={
        "item_name": "Sunflower Oil",
        "category": "cooking_oils",
        "actual_quantity": 1.0,
        "unit": "l",
        "total_price": 140.00,
        "shop_name": "Metro Wholesale"
    }, headers=vol["headers"])
    assert p3.status_code == 201, p3.text

    # -------------------------------------------------------------------------
    # Stage 11: Volunteer previews cost allocation and finalizes bills
    # -------------------------------------------------------------------------
    preview_resp = await client.get(f"/api/societies/{society_id}/rounds/{round_id}/allocation/preview", headers=vol["headers"])
    assert preview_resp.status_code == 200, preview_resp.text
    preview_data = preview_resp.json()
    assert preview_data["total_actual_purchase_cost"] == 710.00

    # Finalize bills with shared costs
    fin_resp = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/bills/finalize", json={
        "shared_costs": [{"name": "Delivery Tempo", "amount": 50.00}]
    }, headers=vol["headers"])
    assert fin_resp.status_code == 200, fin_resp.text
    bills_list = fin_resp.json()
    assert len(bills_list) == 2

    # -------------------------------------------------------------------------
    # Stage 12: Residents retrieve and verify their individual bills
    # -------------------------------------------------------------------------
    # Flat A-201: 5kg Atta (225) + 3kg Sugar (120) + 25 shared = 370.00 INR
    res1_bills_resp = await client.get("/api/users/me/bills", headers=res1["headers"])
    assert res1_bills_resp.status_code == 200, res1_bills_resp.text
    res1_bills = res1_bills_resp.json()
    assert len(res1_bills) >= 1
    my_bill1 = next(b for b in res1_bills if b["round_id"] == round_id)
    assert Decimal(str(my_bill1["total_amount"])) == Decimal("370.00")
    assert Decimal(str(my_bill1["shared_costs_total"])) == Decimal("25.00")

    # Flat B-302: 5kg Atta (225) + 1L Oil (140) + 25 shared = 390.00 INR
    res2_bills_resp = await client.get("/api/users/me/bills", headers=res2["headers"])
    assert res2_bills_resp.status_code == 200, res2_bills_resp.text
    res2_bills = res2_bills_resp.json()
    my_bill2 = next(b for b in res2_bills if b["round_id"] == round_id)
    assert Decimal(str(my_bill2["total_amount"])) == Decimal("390.00")

    # Total billed to flats: 370.00 + 390.00 = 760.00 INR (710 purchases + 50 shared)
    assert Decimal(str(my_bill1["total_amount"])) + Decimal(str(my_bill2["total_amount"])) == Decimal("760.00")

    # -------------------------------------------------------------------------
    # Stage 13: Volunteer creates and verifies retail benchmark evidence
    # -------------------------------------------------------------------------
    # Zepto benchmark: Atta = 55.00/kg (bulk was 45/kg), Sugar = 50.00/kg (bulk was 40/kg)
    now_dt = datetime.now(timezone.utc)
    b_atta_resp = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/benchmarks", json={
        "product_name": "Aashirvaad Atta",
        "brand": "Aashirvaad",
        "package_size": 1.0,
        "package_unit": "kg",
        "benchmark_price": 55.00,
        "store_name": "Zepto Quick",
        "source_type": "price_listing",
        "evidence_date": now_dt.isoformat(),
        "location": "Bengaluru",
    }, headers=vol["headers"])
    assert b_atta_resp.status_code == 201, b_atta_resp.text
    b_atta_id = b_atta_resp.json()["id"]

    v_atta_resp = await client.patch(
        f"/api/societies/{society_id}/rounds/{round_id}/benchmarks/{b_atta_id}/verify",
        json={"status": "verified", "notes": "Verified against Zepto app catalog"},
        headers=vol["headers"]
    )
    assert v_atta_resp.status_code == 200, v_atta_resp.text
    assert v_atta_resp.json()["verification_status"] == "verified"

    # -------------------------------------------------------------------------
    # Stage 14: Society savings summary is calculated against verified benchmarks
    # -------------------------------------------------------------------------
    savings_resp = await client.get(f"/api/societies/{society_id}/rounds/{round_id}/savings", headers=vol["headers"])
    assert savings_resp.status_code == 200, savings_resp.text
    savings_data = savings_resp.json()
    assert "verified_savings_amount" in savings_data

    # -------------------------------------------------------------------------
    # Stage 15: Volunteer publishes privacy-safe announcement to Nexconn group chat
    # -------------------------------------------------------------------------
    pub_resp = await client.post(f"/api/societies/{society_id}/rounds/{round_id}/bills/publish", headers=vol["headers"])
    assert pub_resp.status_code == 200, pub_resp.text
    pub_data = pub_resp.json()
    assert pub_data["sent"] is True
    # Verify strict privacy: message never leaks flat numbers or individual costs
    announcement_msg = pub_data.get("message_text", "")
    assert "A-201" not in announcement_msg
    assert "B-302" not in announcement_msg
    assert "370" not in announcement_msg
    assert "390" not in announcement_msg

    # Teardown
    users_col = get_users_collection()
    societies_col = get_societies_collection()
    rounds_col = get_order_rounds_collection()
    orders_col = get_grocery_orders_collection()
    sl_col = get_shopping_lists_collection()
    pr_col = get_purchase_records_collection()
    bills_col = get_grocery_bills_collection()
    bench_col = get_retail_benchmarks_collection()

    await users_col.delete_many({"email": {"$regex": f"_{ts}@society.com$"}})
    await societies_col.delete_many({"name": f"Prestige Lakeside {ts}"})
    await rounds_col.delete_many({"society_id": society_id})
    await orders_col.delete_many({"society_id": society_id})
    await sl_col.delete_many({"society_id": society_id})
    await pr_col.delete_many({"society_id": society_id})
    await bills_col.delete_many({"society_id": society_id})
    await bench_col.delete_many({"society_id": society_id})
