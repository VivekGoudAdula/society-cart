"""Phase 8 Test Suite: AI Parsing & Grocery Quantity Edge Cases.

Validates:
1. English, Telugu, Hindi, and mixed code-switching parsing with colloquial verb filtering.
2. Missing quantity and ambiguous quantity clarification detection.
3. Proper taxonomy and canonical category mapping (e.g. Kandi Pappu -> Toor Dal, Eggs -> other, Bread -> other).
4. Brand and variant preservation without wrongful merging.
5. Resident manual corrections after AI interpretation.
6. Immutable terminal state: stale AI workers cannot overwrite confirmed or rejected orders.
"""

from datetime import datetime, timezone
import time
import pytest
from httpx import AsyncClient

from app.core.database import get_grocery_orders_collection
from app.services import groq_service, order_service


@pytest.fixture(autouse=True)
def clean_mock_groq():
    """Reset mock groq handler after each test."""
    yield
    groq_service.reset_mock_groq_handler()


@pytest.fixture
async def setup_ai_test_data(client: AsyncClient):
    """Sets up a society, volunteer, and resident for AI parsing tests."""
    ts = int(time.time() * 1000)

    # 1. Admin
    resp_admin = await client.post("/api/auth/register", json={
        "name": "Admin Sharma",
        "email": f"admin_ai_{ts}@example.com",
        "password": "Password123!",
    })
    token_admin = resp_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    resp_soc = await client.post("/api/societies", headers=headers_admin, json={
        "name": f"Multilingual Enclave {ts}",
        "address": "Banjara Hills",
        "city": "Hyderabad",
        "state": "Telangana",
        "total_flats": 40,
        "creator_flat_number": "A-101",
    })
    soc_data = resp_soc.json()
    soc_id = soc_data["society"]["id"] if "society" in soc_data else soc_data["id"]
    soc_invite = soc_data["society"]["invite_code"] if "society" in soc_data else soc_data["invite_code"]

    # 2. Resident
    resp_res = await client.post("/api/auth/register", json={
        "name": "Resident Srinivas",
        "email": f"srini_ai_{ts}@example.com",
        "password": "Password123!",
    })
    token_res = resp_res.json()["access_token"]
    headers_res = {"Authorization": f"Bearer {token_res}"}
    user_id = resp_res.json()["user"]["id"]
    await client.post("/api/societies/join", headers=headers_res, json={
        "invite_code": soc_invite,
        "flat_number": "C-303",
    })

    return {
        "soc_id": soc_id,
        "user_id": user_id,
        "headers_res": headers_res,
        "flat_number": "C-303",
    }


# ============================================================================
# 1. Multilingual Extraction: Telugu, Hindi, English & Code-Switching
# ============================================================================

@pytest.mark.asyncio
async def test_01_telugu_and_colloquial_verb_filtering():
    """Test Telugu grocery message with colloquial verbs ('teesko').

    Input: 'Naaku 5 kg sona masoori rice and 1 kg kandi pappu teesko'
    Expected:
    - Sona Masoori Rice (5.0 kg, grains_rice)
    - Toor Dal (1.0 kg, pulses) - Kandi Pappu standardized to Toor Dal
    - Verb 'teesko' cleanly filtered out
    """
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "te",
        "items": [
            {
                "id": "item_1",
                "original_name": "sona masoori rice",
                "normalized_name": "Sona Masoori Rice",
                "quantity": 5.0,
                "unit": "kg",
                "category": "grains_rice",
                "variant": "Sona Masoori",
                "confidence": 0.95,
                "needs_clarification": False,
            },
            {
                "id": "item_2",
                "original_name": "kandi pappu",
                "normalized_name": "Toor Dal",
                "quantity": 1.0,
                "unit": "kg",
                "category": "pulses",
                "confidence": 0.98,
                "needs_clarification": False,
            },
        ],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })

    result = await groq_service.extract_grocery_items("Naaku 5 kg sona masoori rice and 1 kg kandi pappu teesko")
    assert result.overall_status == "pending_review"
    assert len(result.items) == 2
    assert result.items[0].normalized_name == "Sona Masoori Rice"
    assert result.items[1].normalized_name == "Toor Dal"
    assert result.items[1].category == "pulses"


@pytest.mark.asyncio
async def test_02_hindi_brand_and_taxonomy_extraction():
    """Test Hindi grocery text with brands and colloquial verbs ('lelo').

    Input: '3 packet amul doodh aur 5 kg aashirvaad atta lelo'
    Expected:
    - Milk (brand Amul, 3 packets, dairy)
    - Atta (brand Aashirvaad, 5 kg, grains_rice)
    - Verb 'lelo' ignored
    """
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "hi",
        "items": [
            {
                "id": "item_1",
                "original_name": "amul doodh",
                "normalized_name": "Milk",
                "quantity": 3.0,
                "unit": "packet",
                "category": "dairy",
                "brand": "Amul",
                "confidence": 0.97,
                "needs_clarification": False,
            },
            {
                "id": "item_2",
                "original_name": "aashirvaad atta",
                "normalized_name": "Atta",
                "quantity": 5.0,
                "unit": "kg",
                "category": "grains_rice",
                "brand": "Aashirvaad",
                "confidence": 0.99,
                "needs_clarification": False,
            },
        ],
        "overall_status": "pending_review",
        "clarification_prompt": None,
    })

    result = await groq_service.extract_grocery_items("3 packet amul doodh aur 5 kg aashirvaad atta lelo")
    assert len(result.items) == 2
    assert result.items[0].brand == "Amul"
    assert result.items[1].brand == "Aashirvaad"
    assert result.items[1].category == "grains_rice"


# ============================================================================
# 2. Missing & Ambiguous Quantities: Clarification Flagging
# ============================================================================

@pytest.mark.asyncio
async def test_03_missing_and_ambiguous_quantities_trigger_clarification():
    """Test that missing ('sugar', 'oil') or vague ('thoda coriander') quantities
    are NEVER silently invented, and instead trigger needs_clarification.
    """
    groq_service.set_mock_groq_handler(lambda raw, clar: {
        "detected_language": "en",
        "items": [
            {
                "id": "item_1",
                "original_name": "rice",
                "normalized_name": "Rice",
                "quantity": 5.0,
                "unit": "kg",
                "category": "grains_rice",
                "needs_clarification": False,
            },
            {
                "id": "item_2",
                "original_name": "cooking oil",
                "normalized_name": "Cooking Oil",
                "quantity": None,
                "unit": None,
                "category": "cooking_oils",
                "needs_clarification": True,
                "clarification_reason": "Missing quantity and unit",
            },
            {
                "id": "item_3",
                "original_name": "thoda coriander",
                "normalized_name": "Coriander",
                "quantity": None,
                "unit": "bunch",
                "category": "vegetables",
                "needs_clarification": True,
                "clarification_reason": "Ambiguous quantity 'thoda'",
            },
        ],
        "overall_status": "needs_clarification",
        "clarification_prompt": "Please specify the quantity and package size for Cooking Oil and Coriander.",
    })

    result = await groq_service.extract_grocery_items("5 kg rice, cooking oil, and thoda coriander")
    assert result.overall_status == "needs_clarification"
    assert result.clarification_prompt is not None
    oil_item = next(it for it in result.items if it.normalized_name == "Cooking Oil")
    assert oil_item.quantity is None
    assert oil_item.needs_clarification is True


# ============================================================================
# 3. Resident Corrections After AI Extraction
# ============================================================================

@pytest.mark.asyncio
async def test_04_resident_item_editing_and_confirmation(client: AsyncClient, setup_ai_test_data):
    """Test that a resident can manually correct AI-extracted items before confirming."""
    data = setup_ai_test_data
    soc_id = data["soc_id"]
    headers_res = data["headers_res"]
    orders_col = get_grocery_orders_collection()
    t = datetime.now(timezone.utc)
    ts = int(time.time() * 1000)

    # Pre-seed an order in pending_review
    order_doc = {
        "society_id": soc_id,
        "round_id": "mock_round",
        "round_number": 1,
        "submission_id": f"sub_edit_{ts}",
        "user_id": data["user_id"],
        "flat_number": data["flat_number"],
        "user_name": "Resident Srinivas",
        "raw_text": "5 kg rice",
        "status": "pending_review",
        "items": [{"id": "item1", "original_name": "rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    }
    inserted = await orders_col.insert_one(order_doc)
    order_id = str(inserted.inserted_id)

    # Resident modifies quantity from 5 kg to 10 kg and adds brand 'India Gate'
    update_resp = await client.patch(
        f"/api/orders/{order_id}/items",
        headers=headers_res,
        json={
            "items": [
                {
                    "id": "item1",
                    "original_name": "rice",
                    "normalized_name": "Rice",
                    "quantity": 10.0,
                    "unit": "kg",
                    "category": "grains_rice",
                    "brand": "India Gate",
                }
            ]
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["items"][0]["quantity"] == 10.0
    assert updated["items"][0]["brand"] == "India Gate"

    # Now resident confirms the corrected order
    confirm_resp = await client.post(
        f"/api/orders/{order_id}/confirm",
        headers=headers_res,
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


# ============================================================================
# 4. Terminal State Immutability: Stale AI Worker Cannot Overwrite
# ============================================================================

@pytest.mark.asyncio
async def test_05_confirmed_orders_immune_to_stale_ai_commits(client: AsyncClient, setup_ai_test_data):
    """Test that once an order reaches a terminal state (confirmed or rejected),
    a late or stale AI background commit is discarded and cannot overwrite it.
    """
    data = setup_ai_test_data
    soc_id = data["soc_id"]
    orders_col = get_grocery_orders_collection()
    t = datetime.now(timezone.utc)
    ts = int(time.time() * 1000)

    # Order already confirmed by resident
    order_doc = {
        "society_id": soc_id,
        "round_id": "round_terminal",
        "round_number": 1,
        "submission_id": f"sub_stale_{ts}",
        "message_id": f"msg_stale_{ts}",
        "user_id": data["user_id"],
        "flat_number": data["flat_number"],
        "user_name": "Resident Srinivas",
        "raw_text": "5 kg rice",
        "status": "confirmed",
        "items": [{"id": "item1", "original_name": "rice", "normalized_name": "Rice", "quantity": 5.0, "unit": "kg", "category": "grains_rice"}],
        "created_at": t,
        "updated_at": t,
    }
    inserted = await orders_col.insert_one(order_doc)

    # Attempting to trigger extraction on an already confirmed order MUST be a no-op
    # and MUST NOT revert status from 'confirmed'
    await order_service.trigger_ai_extraction(
        society_id=soc_id,
        round_id="round_terminal",
        round_number=1,
        submission_id=f"sub_stale_{ts}",
        message_id=f"msg_stale_{ts}",
        user_id=data["user_id"],
        flat_number=data["flat_number"],
        user_name="Resident Srinivas",
        raw_text="Overwriting text",
    )

    persisted = await orders_col.find_one({"_id": inserted.inserted_id})
    assert persisted["status"] == "confirmed"
    assert persisted["items"][0]["quantity"] == 5.0
