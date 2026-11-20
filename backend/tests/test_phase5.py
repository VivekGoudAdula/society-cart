"""Automated test suite for Phase 5: AI-Powered Multilingual Grocery Understanding.

Covers:
1. Multilingual Groq Extraction (English, Telugu, Hindi, Mixed code-switching).
2. Ambiguous item & missing quantity clarification detection.
3. Invalid model output and Groq failure / timeout resilience.
4. End-to-end confirmed submission to structured order workflow.
5. Idempotent AI processing (duplicate triggers return existing order).
6. Resident review, manual item editing, clarification, confirmation, and rejection.
7. Strict resident-level authorization and society isolation.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import time
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

    # 1. English
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [
            {"id": "item_1", "original_name": "rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_and_rice", "confidence": 0.98},
            {"id": "item_2", "original_name": "sugar", "normalized_name": "Sugar", "quantity": 2.0, "unit": "packet", "category": "spices", "confidence": 0.95},
        ],
        "overall_status": "awaiting_confirmation",
        "clarification_prompt": None,
    })
    res_en = await groq_service.extract_grocery_items("Need 5 kg rice and 2 packets of sugar.")
    assert res_en.detected_language == "en"
    assert len(res_en.items) == 2
    assert res_en.items[0].normalized_name == "Rice"
    assert res_en.items[0].quantity == 5.0
    assert res_en.items[0].unit == "kg"
    assert res_en.overall_status == "awaiting_confirmation"

    # 2. Telugu
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "te",
        "items": [
            {"id": "item_1", "original_name": "ఉల్లిపాయలు", "normalized_name": "Onion", "quantity": 2.0, "unit": "kg", "category": "vegetables", "confidence": 0.96},
        ],
        "overall_status": "awaiting_confirmation",
        "clarification_prompt": None,
    })
    res_te = await groq_service.extract_grocery_items("నాకు 2 కిలోల ఉల్లిపాయలు కావాలి")
    assert res_te.detected_language == "te"
    assert res_te.items[0].original_name == "ఉల్లిపాయలు"
    assert res_te.items[0].normalized_name == "Onion"
    assert res_te.items[0].quantity == 2.0

    # 3. Hindi
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "hi",
        "items": [
            {"id": "item_1", "original_name": "आलू", "normalized_name": "Potato", "quantity": 3.0, "unit": "kg", "category": "vegetables", "confidence": 0.97},
            {"id": "item_2", "original_name": "तेल", "normalized_name": "Cooking Oil", "quantity": 1.0, "unit": "L", "category": "cooking_oils", "confidence": 0.92},
        ],
        "overall_status": "awaiting_confirmation",
        "clarification_prompt": None,
    })
    res_hi = await groq_service.extract_grocery_items("मुझे 3 किलो आलू और 1 लीटर तेल चाहिए")
    assert res_hi.detected_language == "hi"
    assert res_hi.items[0].normalized_name == "Potato"
    assert res_hi.items[1].quantity == 1.0
    assert res_hi.items[1].unit == "L"

    # 4. Mixed code-switching
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "mixed",
        "items": [
            {"id": "item_1", "original_name": "onions", "normalized_name": "Onion", "quantity": 2.0, "unit": "kg", "category": "vegetables", "confidence": 0.95},
            {"id": "item_2", "original_name": "atta", "normalized_name": "Whole Wheat Atta", "quantity": 1.0, "unit": "packet", "category": "grains_and_rice", "confidence": 0.94},
        ],
        "overall_status": "awaiting_confirmation",
        "clarification_prompt": None,
    })
    res_mix = await groq_service.extract_grocery_items("2 kg onions aur 1 packet atta add karo")
    assert res_mix.detected_language == "mixed"
    assert len(res_mix.items) == 2


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
# 2. WORKFLOW & INTEGRATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_04_e2e_submission_to_ai_order_lifecycle(client: AsyncClient, setup_phase5_data):
    """End-to-end workflow: Confirmed submission -> AI extraction -> Idempotent -> Clarify -> Edit -> Confirm."""
    data = setup_phase5_data
    soc1_id = data["soc1_id"]
    round_id = data["round_id"]
    headers_res1 = data["headers_res1"]

    # Mock extraction: initially needs clarification on oil
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

    # Step 2: Confirm reservation (triggers background AI extraction)
    msg_id = f"nexconn_msg_p5_{int(time.time()*1000)}"
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

    # Step 4: Idempotency Check - re-triggering does not create duplicates
    idem_order = await order_service.trigger_ai_extraction(
        society_id=soc1_id,
        round_id=round_id,
        round_number=1,
        submission_id=sub_id,
        message_id=msg_id,
        user_id=data["user1_id"],
        flat_number="C-303",
        user_name="Resident Srinivas",
        raw_text="5 kg బియ్యం and some నూనె",
    )
    assert idem_order.id == order_id

    # Step 5: Clarification response by resident
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "te",
        "items": [
            {"id": "item_1", "original_name": "బియ్యం", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_and_rice", "confidence": 0.98, "needs_clarification": False},
            {"id": "item_2", "original_name": "నూనె", "normalized_name": "Sunflower Oil", "quantity": 2.0, "unit": "L", "category": "cooking_oils", "variant": "Sunflower", "confidence": 0.95, "needs_clarification": False},
        ],
        "overall_status": "awaiting_confirmation",
        "clarification_prompt": None,
    })

    clar_resp = await client.post(
        f"/api/orders/{order_id}/clarify",
        headers=headers_res1,
        json={"clarification_text": "2 litres sunflower oil"},
    )
    assert clar_resp.status_code == 200
    clarified = clar_resp.json()
    assert clarified["status"] == "awaiting_confirmation"
    assert clarified["items"][1]["quantity"] == 2.0
    assert len(clarified["clarification_history"]) == 1

    # Step 6: Manual item edit by resident (change Rice to 10 kg)
    updated_items = clarified["items"]
    updated_items[0]["quantity"] = 10.0
    patch_res = await client.patch(
        f"/api/orders/{order_id}/items",
        headers=headers_res1,
        json={"items": updated_items},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["items"][0]["quantity"] == 10.0
    # Raw text must remain immutable
    assert patch_res.json()["raw_text"] == "5 kg బియ్యం and some నూనె"

    # Step 7: Resident confirms order
    cnf_res = await client.post(f"/api/orders/{order_id}/confirm", headers=headers_res1)
    assert cnf_res.status_code == 200
    assert cnf_res.json()["status"] == "confirmed"
    assert cnf_res.json()["confirmed_at"] is not None

    # Step 8: Idempotent confirmation
    re_cnf = await client.post(f"/api/orders/{order_id}/confirm", headers=headers_res1)
    assert re_cnf.status_code == 200
    assert re_cnf.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_05_rejection_and_authorization_isolation(client: AsyncClient, setup_phase5_data):
    """Verify rejection flow, resident ownership privacy, volunteer/admin RBAC, and cross-society isolation."""
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
        "overall_status": "awaiting_confirmation",
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
    assert r1_view.json()["id"] == order1.id

    # 2. Resident 2 CANNOT view Resident 1's order -> 403 Forbidden
    r2_view = await client.get(f"/api/orders/{order1.id}", headers=headers_res2)
    assert r2_view.status_code == 403

    # 3. Resident 2 CANNOT confirm or reject Resident 1's order -> 403 Forbidden
    r2_hack_cnf = await client.post(f"/api/orders/{order1.id}/confirm", headers=headers_res2)
    assert r2_hack_cnf.status_code == 403

    r2_hack_rej = await client.post(f"/api/orders/{order1.id}/reject", headers=headers_res2)
    assert r2_hack_rej.status_code == 403

    # 4. Volunteer in same society CAN view order
    vol_view = await client.get(f"/api/orders/{order1.id}", headers=headers_vol)
    assert vol_view.status_code == 200

    # 5. Admin in same society CAN view order
    admin_view = await client.get(f"/api/orders/{order1.id}", headers=headers_admin)
    assert admin_view.status_code == 200

    # 6. User from Society 2 CANNOT list or access Society 1 orders -> 403 Forbidden
    cross_list = await client.get(
        f"/api/societies/{soc1_id}/rounds/{round_id}/orders",
        headers=headers_other,
    )
    assert cross_list.status_code == 403

    cross_view = await client.get(
        f"/api/orders/{order1.id}",
        headers=headers_other,
    )
    assert cross_view.status_code == 403

    # 7. Resident 1 rejects order
    rej_res = await client.post(f"/api/orders/{order1.id}/reject", headers=headers_res1)
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"
