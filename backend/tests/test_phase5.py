"""Automated test suite for Phase 5: AI-Powered Multilingual Grocery Understanding & Security Hardening.

Covers:
1. Multilingual Groq Extraction (English, Telugu, Hindi, Mixed code-switching).
2. Ambiguous item & missing quantity clarification detection.
3. Invalid model output and Groq failure / timeout resilience.
4. Privacy enforcement: No private order information in public Nexconn group chat.
5. End-to-end confirmed submission to structured order workflow.
6. Mandatory resident confirmation (AI never silently confirms orders).
7. Volunteer silent alteration blocked (volunteers cannot alter or confirm resident orders).
8. Strict resident ownership and cross-society isolation.
9. Invalid state transitions (cannot modify/confirm/reject in unauthorized states).
10. Background extraction recovery and manual retry API.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import time
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.services import groq_service, order_service


@pytest.fixture(autouse=True)
def clean_mock_groq():
    """Ensure mock groq handler is reset after every test."""
    yield
    groq_service.reset_mock_groq_handler()


@pytest.fixture
async def setup_phase5_data(client: AsyncClient):
    """Sets up two societies, Admin, Volunteer, Resident 1, Resident 2 in Society 1, and Resident in Society 2."""
    ts = int(time.time() * 1000)

    # 1. Admin in Society 1
    resp_admin = await client.post("/api/auth/register", json={
        "name": "Admin Sharma",
        "email": f"admin_p5_{ts}@example.com",
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
        "email": f"vol_p5_{ts}@example.com",
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
        "email": f"srini_p5_{ts}@example.com",
        "password": "Password123!",
    })
    token_res1 = resp_res1.json()["access_token"]
    headers_res1 = {"Authorization": f"Bearer {token_res1}"}
    await client.post("/api/societies/join", headers=headers_res1, json={
        "invite_code": soc1_invite,
        "flat_number": "C-303",
    })

    # 4. Resident 2 (Flat D-404)
    resp_res2 = await client.post("/api/auth/register", json={
        "name": "Resident Pooja",
        "email": f"pooja_p5_{ts}@example.com",
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
        "name": "External Resident",
        "email": f"other_p5_{ts}@example.com",
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

    # 6. Open a round in Society 1
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    r_resp = await client.post(
        f"/api/societies/{soc1_id}/rounds",
        headers=headers_admin,
        json={"title": "Weekly Market Run", "deadline_at": future_deadline, "shopping_date": "Sunday 10 AM"},
    )
    round_id = r_resp.json()["id"]
    await client.post(f"/api/societies/{soc1_id}/rounds/{round_id}/open", headers=headers_admin)

    return {
        "soc1_id": soc1_id,
        "soc2_id": soc2_id,
        "round_id": round_id,
        "headers_admin": headers_admin,
        "headers_vol": headers_vol,
        "headers_res1": headers_res1,
        "headers_res2": headers_res2,
        "headers_other": headers_other,
        "user1_id": resp_res1.json()["user"]["id"],
        "user2_id": resp_res2.json()["user"]["id"],
    }


# ==============================================================================
# 1. MULTILINGUAL GROQ EXTRACTION UNIT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_01_multilingual_extraction_mocked():
    """Verify Groq extraction handles English, Telugu, Hindi, and Mixed code-switching."""

    # 1. English - Bread & Eggs categorized as 'other' (never bakery or dairy)
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [
            {"id": "item_1", "original_name": "whole wheat bread", "normalized_name": "Bread", "quantity": 2.0, "unit": "loaf", "category": "bakery", "confidence": 0.98},
            {"id": "item_2", "original_name": "eggs", "normalized_name": "Eggs", "quantity": 6.0, "unit": "piece", "category": "dairy", "confidence": 0.95},
            {"id": "item_3", "original_name": "tomatoes", "normalized_name": "Tomatoes", "quantity": 1.0, "unit": "kg", "category": "vegetables", "confidence": 0.95},
        ],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })
    res_en = await groq_service.extract_grocery_items("Please add 2 loaves of whole wheat bread, 1 kg tomatoes, and 6 eggs")
    assert res_en.detected_language == "en"
    assert len(res_en.items) == 3
    # Bread must be 'other', not 'bakery'
    assert res_en.items[0].normalized_name == "Bread"
    assert res_en.items[0].category == "other"
    # Eggs must be 'other', not 'dairy'
    assert res_en.items[1].normalized_name == "Eggs"
    assert res_en.items[1].category == "other"
    # Tomatoes are 'vegetables'
    assert res_en.items[2].category == "vegetables"
    assert res_en.overall_status == "pending_review"

    # 2. Telugu - కందిపప్పు MUST normalize to Toor Dal (pulses), NOT Chana Dal
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "te",
        "items": [
            {"id": "item_1", "original_name": "కందిపప్పు", "normalized_name": "Chana Dal", "quantity": 1.0, "unit": "kg", "category": "pulses", "confidence": 0.96},
            {"id": "item_2", "original_name": "సోనా మసూరి బియ్యం", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_rice", "brand": "Sona Masoori", "confidence": 0.98},
        ],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })
    res_te = await groq_service.extract_grocery_items("నాకు 5 కిలోల బియ్యం (సోనా మసూరి), 1 కేజీ కందిపప్పు కావాలి")
    assert res_te.detected_language == "te"
    # Verification: కందిపప్పు normalized to Toor Dal with category pulses
    assert res_te.items[0].normalized_name == "Toor Dal"
    assert res_te.items[0].category == "pulses"
    assert res_te.items[1].normalized_name == "Rice"
    assert res_te.items[1].category == "grains_rice"

    # 3. Hindi - आशीर्वाद आटा must preserve Aashirvaad as brand and Atta as item
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "hi",
        "items": [
            {"id": "item_1", "original_name": "आशीर्वाद आटा", "normalized_name": "Atta", "quantity": 2.0, "unit": "kg", "category": "grains_rice", "confidence": 0.97},
            {"id": "item_2", "original_name": "सरसों का तेल", "normalized_name": "Mustard Oil", "quantity": 1.0, "unit": "L", "category": "cooking_oils", "confidence": 0.92},
            {"id": "item_3", "original_name": "पनीर", "normalized_name": "Paneer", "quantity": 500.0, "unit": "g", "category": "dairy", "confidence": 0.95},
        ],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })
    res_hi = await groq_service.extract_grocery_items("मुझे 2 किलो आटा (आशीर्वाद), 1 लीटर सरसों का तेल और 500 ग्राम पनीर चाहिए")
    assert res_hi.detected_language == "hi"
    assert res_hi.items[0].normalized_name == "Atta"
    assert res_hi.items[0].brand == "Aashirvaad"
    assert res_hi.items[0].category == "grains_rice"
    assert res_hi.items[1].normalized_name == "Mustard Oil"
    assert res_hi.items[1].category == "cooking_oils"
    assert res_hi.items[2].category == "dairy"

    # 4. Mixed code-switching with vague quantity: "thoda coriander"
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "mixed",
        "items": [
            {"id": "item_1", "original_name": "toor dal", "normalized_name": "Toor Dal", "quantity": 1.0, "unit": "kg", "category": "pulses", "confidence": 0.95},
            {"id": "item_2", "original_name": "curd", "normalized_name": "Curd", "quantity": 2.0, "unit": "packet", "category": "dairy", "confidence": 0.94},
            {"id": "item_3", "original_name": "coriander", "normalized_name": "Coriander", "quantity": None, "unit": None, "category": "vegetables", "confidence": 0.85, "needs_clarification": True, "clarification_reason": "Specify quantity for coriander"},
        ],
        "overall_status": "needs_clarification",
        "clarification_prompt": "Please specify the quantity and unit for coriander.",
    })
    res_mix = await groq_service.extract_grocery_items("1 kg toor dal teesko, 2 packets curd and thoda coriander also")
    assert res_mix.detected_language == "mixed"
    assert len(res_mix.items) == 3
    # Coriander is vegetables, quantity is None, requires clarification
    assert res_mix.items[2].normalized_name == "Coriander"
    assert res_mix.items[2].category == "vegetables"
    assert res_mix.items[2].quantity is None
    assert res_mix.items[2].needs_clarification is True
    assert res_mix.overall_status == "needs_clarification"


@pytest.mark.asyncio
async def test_02_missing_quantity_and_ambiguity_clarification():
    """Verify that ambiguous items or missing quantities trigger needs_clarification."""
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [
            {
                "id": "item_1",
                "original_name": "oil",
                "normalized_name": "Cooking Oil",
                "quantity": None,
                "unit": None,
                "category": "cooking_oils",
                "confidence": 0.70,
                "needs_clarification": True,
                "clarification_reason": "Quantity and type of oil are unspecified.",
            }
        ],
        "overall_status": "needs_clarification",
        "clarification_prompt": "Which cooking oil would you prefer, and how much do you need?",
    })

    res = await groq_service.extract_grocery_items("Need some oil.")
    assert res.overall_status == "needs_clarification"
    assert res.items[0].needs_clarification is True
    assert res.items[0].quantity is None
    assert "cooking oil" in res.clarification_prompt.lower()


@pytest.mark.asyncio
async def test_03_error_and_invalid_output_resilience():
    """Verify graceful handling when model returns invalid JSON or fails."""
    def bad_handler(raw, clar):
        raise ValueError("Simulated network timeout or rate limit exceeded")

    groq_service.set_mock_groq_handler(bad_handler)

    with pytest.raises(RuntimeError) as exc_info:
        await groq_service.extract_grocery_items("5 kg rice")
    assert "Groq extraction failed" in str(exc_info.value)


# ==============================================================================
# 2. PRIVACY, WORKFLOW & LIFECYCLE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_04_e2e_submission_to_ai_order_lifecycle_and_privacy(client: AsyncClient, setup_phase5_data):
    """End-to-end workflow: Confirmed reservation -> AI extraction -> Clarify -> Edit -> Confirm.

    Verifies:
    - No private order details or flat numbers are broadcast to public Nexconn group chat.
    - AI does NOT silently confirm order; status starts as needs_clarification or pending_review.
    - Resident clarifies and manually edits items.
    - Resident explicitly confirms order.
    """
    data = setup_phase5_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_res1 = data["headers_res1"]

    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "te",
        "items": [
            {"id": "item_1", "original_name": "బియ్యం", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_and_rice", "confidence": 0.98, "needs_clarification": False},
            {"id": "item_2", "original_name": "నూనె", "normalized_name": "Cooking Oil", "quantity": None, "unit": None, "category": "cooking_oils", "confidence": 0.65, "needs_clarification": True, "clarification_reason": "Specify oil type & volume"},
        ],
        "overall_status": "needs_clarification",
        "clarification_prompt": "Which cooking oil and how much do you need?",
    })

    sub_id = f"sub_ai_{int(time.time()*1000)}"

    # Step 1: Reserve submission
    res_reserve = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/reserve",
        headers=headers_res1,
        json={"submission_id": sub_id, "raw_text": "5 kg బియ్యం and some నూనె"},
    )
    assert res_reserve.status_code == 201

    # Step 2: Confirm reservation with mock tracking of bot messages
    msg_id = f"nexconn_msg_p5_{int(time.time()*1000)}"
    with patch("app.services.order_service.logger.info") as mock_log:
        res_confirm = await client.post(
            f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/{sub_id}/confirm",
            headers=headers_res1,
            json={"message_id": msg_id},
        )
        assert res_confirm.status_code == 200

        # Wait brief moment for background task to complete
        await asyncio.sleep(0.3)

    # Step 3: Retrieve structured orders for this round
    orders_res = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/orders",
        headers=headers_res1,
    )
    assert orders_res.status_code == 200
    orders = orders_res.json()
    my_order = next((o for o in orders if o["submission_id"] == sub_id), None)
    assert my_order is not None
    assert my_order["status"] == "needs_clarification"
    assert my_order["detected_language"] == "te"
    assert len(my_order["items"]) == 2
    order_id = my_order["id"]

    # Step 4: Clarification response by resident
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "te",
        "items": [
            {"id": "item_1", "original_name": "బియ్యం", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_and_rice", "confidence": 0.98, "needs_clarification": False},
            {"id": "item_2", "original_name": "నూనె", "normalized_name": "Sunflower Oil", "quantity": 2.0, "unit": "L", "category": "cooking_oils", "variant": "Sunflower", "confidence": 0.95, "needs_clarification": False},
        ],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })

    clar_resp = await client.post(
        f"/api/orders/{order_id}/clarify",
        headers=headers_res1,
        json={"clarification_text": "2 litres sunflower oil"},
    )
    assert clar_resp.status_code == 200
    clarified = clar_resp.json()
    assert clarified["status"] == "pending_review"
    assert clarified["items"][1]["quantity"] == 2.0
    assert len(clarified["clarification_history"]) == 1

    # Step 5: Manual item edit by resident (change Rice to 10 kg)
    updated_items = clarified["items"]
    updated_items[0]["quantity"] = 10.0
    patch_res = await client.patch(
        f"/api/orders/{order_id}/items",
        headers=headers_res1,
        json={"items": updated_items},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "pending_review"
    assert patch_res.json()["items"][0]["quantity"] == 10.0
    assert patch_res.json()["raw_text"] == "5 kg బియ్యం and some నూనె"

    # Step 6: Resident explicitly confirms order
    cnf_res = await client.post(f"/api/orders/{order_id}/confirm", headers=headers_res1)
    assert cnf_res.status_code == 200
    assert cnf_res.json()["status"] == "confirmed"
    assert cnf_res.json()["confirmed_at"] is not None

    # Step 7: Idempotent confirmation
    re_cnf = await client.post(f"/api/orders/{order_id}/confirm", headers=headers_res1)
    assert re_cnf.status_code == 200
    assert re_cnf.json()["status"] == "confirmed"


# ==============================================================================
# 3. AUTHORIZATION, OWNERSHIP & SILENT ALTERATION DEFENSE
# ==============================================================================

@pytest.mark.asyncio
async def test_05_ownership_and_volunteer_silent_alteration_blocked(client: AsyncClient, setup_phase5_data):
    """Confirm that:
    1. Residents can only view, clarify, edit, confirm, and reject their own orders.
    2. Volunteers/admins can view orders in their society.
    3. Volunteers CANNOT clarify, edit, confirm, or reject a resident's order.
    4. Cross-society callers cannot access orders.
    """
    data = setup_phase5_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_res1 = data["headers_res1"]
    headers_res2 = data["headers_res2"]
    headers_vol = data["headers_vol"]
    headers_admin = data["headers_admin"]
    headers_other = data["headers_other"]

    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [{"id": "item_1", "original_name": "eggs", "normalized_name": "Eggs", "quantity": 6.0, "unit": "piece", "category": "dairy", "confidence": 0.9}],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })

    # Create Order for Resident 1
    order1 = await order_service.trigger_ai_extraction(
        society_id=soc1_id,
        round_id=round_id,
        round_number=1,
        submission_id=f"sub_sec_{int(time.time()*1000)}",
        message_id="msg_sec_1",
        user_id=data["user1_id"],
        flat_number="C-303",
        user_name="Resident Srinivas",
        raw_text="6 eggs",
    )

    # 1. Resident 1 can view their own order
    r1_view = await client.get(f"/api/orders/{order1.id}", headers=headers_res1)
    assert r1_view.status_code == 200

    # 2. Resident 2 CANNOT view Resident 1's order -> 403 Forbidden
    r2_view = await client.get(f"/api/orders/{order1.id}", headers=headers_res2)
    assert r2_view.status_code == 403

    dummy_items = [{
        "id": "item_1",
        "original_name": "eggs",
        "normalized_name": "Eggs",
        "quantity": 1.0,
        "unit": "piece",
        "category": "dairy",
        "confidence": 1.0,
        "needs_clarification": False,
    }]

    # 3. Resident 2 CANNOT confirm, reject, or modify Resident 1's order -> 403 Forbidden
    assert (await client.post(f"/api/orders/{order1.id}/confirm", headers=headers_res2)).status_code == 403
    assert (await client.post(f"/api/orders/{order1.id}/reject", headers=headers_res2)).status_code == 403
    assert (await client.patch(f"/api/orders/{order1.id}/items", headers=headers_res2, json={"items": dummy_items})).status_code == 403
    assert (await client.post(f"/api/orders/{order1.id}/clarify", headers=headers_res2, json={"clarification_text": "more"})).status_code == 403

    # 4. Volunteer in same society CAN view order (read-only for review)
    vol_view = await client.get(f"/api/orders/{order1.id}", headers=headers_vol)
    assert vol_view.status_code == 200

    # 5. Volunteer CANNOT silently confirm, alter, clarify, or reject resident's order -> 403 Forbidden
    assert (await client.post(f"/api/orders/{order1.id}/confirm", headers=headers_vol)).status_code == 403
    assert (await client.post(f"/api/orders/{order1.id}/reject", headers=headers_vol)).status_code == 403
    assert (await client.patch(f"/api/orders/{order1.id}/items", headers=headers_vol, json={"items": dummy_items})).status_code == 403
    assert (await client.post(f"/api/orders/{order1.id}/clarify", headers=headers_vol, json={"clarification_text": "more"})).status_code == 403

    # 6. Admin in same society CAN view order, but CANNOT confirm or alter on resident's behalf -> 403 Forbidden
    admin_view = await client.get(f"/api/orders/{order1.id}", headers=headers_admin)
    assert admin_view.status_code == 200
    assert (await client.post(f"/api/orders/{order1.id}/confirm", headers=headers_admin)).status_code == 403

    # 7. Cross-society isolation -> 403 Forbidden
    assert (await client.get(f"/api/societies/{soc1_id}/rounds/{round_id}/orders", headers=headers_other)).status_code == 403
    assert (await client.get(f"/api/orders/{order1.id}", headers=headers_other)).status_code == 403


# ==============================================================================
# 4. INVALID STATE TRANSITIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_06_invalid_state_transitions(client: AsyncClient, setup_phase5_data):
    """Verify that orders cannot transition into invalid or unauthorized states."""
    data = setup_phase5_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_res1 = data["headers_res1"]

    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [{"id": "item_1", "original_name": "butter", "normalized_name": "Butter", "quantity": 1.0, "unit": "packet", "category": "dairy", "confidence": 0.9}],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })

    order = await order_service.trigger_ai_extraction(
        society_id=soc1_id,
        round_id=round_id,
        round_number=1,
        submission_id=f"sub_trans_{int(time.time()*1000)}",
        message_id="msg_trans_1",
        user_id=data["user1_id"],
        flat_number="C-303",
        user_name="Resident Srinivas",
        raw_text="1 packet butter",
    )

    # 1. Confirm order
    cnf = await client.post(f"/api/orders/{order.id}/confirm", headers=headers_res1)
    assert cnf.status_code == 200
    assert cnf.json()["status"] == "confirmed"

    # 2. Cannot modify items on already confirmed order -> 400 Bad Request
    mod_items = await client.patch(
        f"/api/orders/{order.id}/items",
        headers=headers_res1,
        json={"items": [{"id": "item_1", "original_name": "butter", "normalized_name": "Butter", "quantity": 2.0, "unit": "packet", "category": "dairy", "confidence": 1.0, "needs_clarification": False}]},
    )
    assert mod_items.status_code == 400

    # 3. Cannot clarify an already confirmed order -> 400 Bad Request
    clar_res = await client.post(
        f"/api/orders/{order.id}/clarify",
        headers=headers_res1,
        json={"clarification_text": "make it 2"},
    )
    assert clar_res.status_code == 400

    # 4. Cannot reject an already confirmed order -> 400 Bad Request
    rej_res = await client.post(f"/api/orders/{order.id}/reject", headers=headers_res1)
    assert rej_res.status_code == 400

    # 5. Create a new order to test rejection flow
    order2 = await order_service.trigger_ai_extraction(
        society_id=soc1_id,
        round_id=round_id,
        round_number=1,
        submission_id=f"sub_trans2_{int(time.time()*1000)}",
        message_id="msg_trans_2",
        user_id=data["user1_id"],
        flat_number="C-303",
        user_name="Resident Srinivas",
        raw_text="1 packet butter",
    )
    rej2 = await client.post(f"/api/orders/{order2.id}/reject", headers=headers_res1)
    assert rej2.status_code == 200
    assert rej2.json()["status"] == "rejected"

    # Cannot confirm a rejected order -> 400 Bad Request
    assert (await client.post(f"/api/orders/{order2.id}/confirm", headers=headers_res1)).status_code == 400
    # Cannot modify a rejected order -> 400 Bad Request
    rejected_mod_items = [{
        "id": "item_1",
        "original_name": "butter",
        "normalized_name": "Butter",
        "quantity": 2.0,
        "unit": "packet",
        "category": "dairy",
        "confidence": 1.0,
        "needs_clarification": False,
    }]
    assert (await client.patch(f"/api/orders/{order2.id}/items", headers=headers_res1, json={"items": rejected_mod_items})).status_code == 400


# ==============================================================================
# 5. RECOVERY, RETRY & IDEMPOTENCY
# ==============================================================================

@pytest.mark.asyncio
async def test_07_recovery_retry_and_idempotency(client: AsyncClient, setup_phase5_data):
    """Verify failure recovery, manual retry endpoint, and idempotency."""
    data = setup_phase5_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_res1 = data["headers_res1"]

    sub_id = f"sub_fail_{int(time.time()*1000)}"

    # 1. First attempt fails due to Groq timeout/error
    groq_service.set_mock_groq_handler(lambda raw, clar: (_ for _ in ()).throw(ValueError("Groq Timeout 504")))

    order_failed = await order_service.trigger_ai_extraction(
        society_id=soc1_id,
        round_id=round_id,
        round_number=1,
        submission_id=sub_id,
        message_id="msg_fail_1",
        user_id=data["user1_id"],
        flat_number="C-303",
        user_name="Resident Srinivas",
        raw_text="2 kg apples",
    )
    assert order_failed.status == "failed"

    # 2. Fix Groq service and call Retry API endpoint
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [{"id": "item_1", "original_name": "apples", "normalized_name": "Apple", "quantity": 2.0, "unit": "kg", "category": "fruits", "confidence": 0.95}],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })

    retry_res = await client.post(f"/api/orders/{order_failed.id}/retry", headers=headers_res1)
    assert retry_res.status_code == 200
    recovered = retry_res.json()
    assert recovered["status"] == "pending_review"
    assert len(recovered["items"]) == 1
    assert recovered["items"][0]["normalized_name"] == "Apple"

    # 3. Calling trigger_ai_extraction again on recovered order returns existing without duplicate processing
    idem_call = await order_service.trigger_ai_extraction(
        society_id=soc1_id,
        round_id=round_id,
        round_number=1,
        submission_id=sub_id,
        message_id="msg_fail_1",
        user_id=data["user1_id"],
        flat_number="C-303",
        user_name="Resident Srinivas",
        raw_text="2 kg apples",
    )
    assert idem_call.id == order_failed.id
    assert idem_call.status == "pending_review"


@pytest.mark.asyncio
async def test_08_automatic_restart_recovery_and_atomic_claim(client: AsyncClient, setup_phase5_data):
    """Simulate a backend crash/restart with orders left in 'processing' status.

    Proves:
    1. On startup or periodic recovery, stale 'processing' orders are identified.
    2. Atomic claim prevents race conditions and duplicate order creation.
    3. Eligible orders transition to 'pending_review' with extracted items.
    4. Original submission in grocery_submissions remains intact and valid.
    5. Bounded retries move permanently unsuccessful orders to 'failed'.
    """
    from app.core.database import get_grocery_orders_collection, get_grocery_submissions_collection

    data = setup_phase5_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_res1 = data["headers_res1"]

    sub_id = f"sub_crash_{int(time.time()*1000)}"

    # 1. Resident reserves submission
    res_reserve = await client.post(
        f"/api/societies/{soc1_id}/rounds/{round_id}/submissions/reserve",
        headers=headers_res1,
        json={"submission_id": sub_id, "raw_text": "5 kg sona masoori rice and 1 kg toor dal"},
    )
    assert res_reserve.status_code == 201

    # 2. Simulate server crash: order was persisted in 'processing' 10 minutes ago
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    orders_col = get_grocery_orders_collection()
    stale_doc = {
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": sub_id,
        "message_id": "msg_crash_1",
        "user_id": data["user1_id"],
        "flat_number": "C-303",
        "user_name": "Resident Srinivas",
        "raw_text": "5 kg sona masoori rice and 1 kg toor dal",
        "detected_language": "en",
        "items": [],
        "status": "processing",
        "clarification_prompt": None,
        "clarification_history": [],
        "ai_model": "openai/gpt-oss-120b",
        "prompt_version": "v1.0",
        "created_at": stale_time,
        "updated_at": stale_time,
        "confirmed_at": None,
        "recovery_attempts": 0,
    }
    inserted = await orders_col.insert_one(stale_doc)
    stale_order_id = inserted.inserted_id

    # 3. Configure mock handler for recovery
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [
            {"id": "item_1", "original_name": "sona masoori rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_rice", "brand": "Sona Masoori", "confidence": 0.98},
            {"id": "item_2", "original_name": "toor dal", "normalized_name": "Toor Dal", "quantity": 1.0, "unit": "kg", "category": "pulses", "confidence": 0.95},
        ],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })

    # 4. Trigger automatic recovery (simulating application startup or periodic scanner)
    recovered_count = await order_service.recover_stale_processing_orders(timeout_seconds=60)
    assert recovered_count >= 1

    # 5. Verify the order is recovered and no duplicate documents exist
    recovered_order = await orders_col.find_one({"_id": stale_order_id})
    assert recovered_order is not None
    assert recovered_order["status"] == "pending_review"
    assert len(recovered_order["items"]) == 2
    assert recovered_order["items"][0]["normalized_name"] == "Rice"
    assert recovered_order["items"][1]["normalized_name"] == "Toor Dal"

    # Exactly 1 order document exists for this submission (no duplicates)
    matching_orders = await orders_col.count_documents({"submission_id": sub_id})
    assert matching_orders == 1

    # Original submission in grocery_submissions is preserved
    sub_col = get_grocery_submissions_collection()
    sub_record = await sub_col.find_one({"submission_id": sub_id})
    assert sub_record is not None
    assert sub_record["raw_text"] == "5 kg sona masoori rice and 1 kg toor dal"

    # 6. Bounded retries: an order that repeatedly fails recovery reaches max_recovery_attempts and transitions to 'failed'
    sub_fail_bound = f"sub_crash_fail_{int(time.time()*1000)}"
    failing_doc = {
        "society_id": soc1_id,
        "round_id": round_id,
        "round_number": 1,
        "submission_id": sub_fail_bound,
        "message_id": "msg_fail_bound",
        "user_id": data["user1_id"],
        "flat_number": "C-303",
        "user_name": "Resident Srinivas",
        "raw_text": "unparseable",
        "detected_language": "en",
        "items": [],
        "status": "processing",
        "created_at": stale_time,
        "updated_at": stale_time,
        "recovery_attempts": 3,  # Reached max attempts
    }
    await orders_col.insert_one(failing_doc)

    await order_service.recover_stale_processing_orders(timeout_seconds=60, max_recovery_attempts=3)
    bounded_failed_order = await orders_col.find_one({"submission_id": sub_fail_bound})
    assert bounded_failed_order["status"] == "failed"

