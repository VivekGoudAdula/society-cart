"""Service layer for AI grocery orders, clarifications, manual edits, and confirmations.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.core.config import get_settings
from app.core.database import (
    get_grocery_orders_collection,
    get_societies_collection,
)
from app.schemas.order import (
    AIExtractionOutput,
    ClarificationHistoryEntry,
    GroceryItemSchema,
    GroceryOrderResponse,
    OrderStatus,
)
from app.services import groq_service
from app.services.nexconn_service import send_system_bot_message

logger = logging.getLogger(__name__)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime object is timezone-aware and set to UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _serialize_order(doc: Dict[str, Any]) -> GroceryOrderResponse:
    """Transform raw MongoDB grocery order document into GroceryOrderResponse."""
    items = [
        GroceryItemSchema.model_validate(it) for it in doc.get("items", [])
    ]
    history = [
        ClarificationHistoryEntry(
            prompt=h.get("prompt", ""),
            resident_response=h.get("resident_response", ""),
            timestamp=_ensure_utc(h.get("timestamp", datetime.now(timezone.utc))),
        )
        for h in doc.get("clarification_history", [])
    ]

    return GroceryOrderResponse(
        id=str(doc["_id"]),
        society_id=str(doc["society_id"]),
        round_id=str(doc["round_id"]),
        round_number=int(doc.get("round_number", 1)),
        submission_id=str(doc["submission_id"]),
        message_id=str(doc.get("message_id", "")),
        user_id=str(doc["user_id"]),
        flat_number=str(doc.get("flat_number", "")),
        user_name=str(doc.get("user_name", "Resident")),
        raw_text=doc.get("raw_text", ""),
        detected_language=doc.get("detected_language", "en"),
        items=items,
        status=doc.get("status", "processing"),
        clarification_prompt=doc.get("clarification_prompt"),
        clarification_history=history,
        ai_model=doc.get("ai_model", get_settings().groq_model),
        prompt_version=doc.get("prompt_version", "v1.0"),
        created_at=_ensure_utc(doc.get("created_at", datetime.now(timezone.utc))),
        updated_at=_ensure_utc(doc.get("updated_at", datetime.now(timezone.utc))),
        confirmed_at=_ensure_utc(doc.get("confirmed_at")),
    )


async def _get_society_nexconn_group_id(society_id: str) -> Optional[str]:
    """Retrieve the Nexconn group channel identifier for an apartment society."""
    societies = get_societies_collection()
    soc = await societies.find_one({"_id": ObjectId(society_id)})
    if not soc:
        return None
    return soc.get("nexconn_group_id") or f"society_{soc['_id']}"


async def trigger_ai_extraction(
    society_id: str,
    round_id: str,
    round_number: int,
    submission_id: str,
    message_id: str,
    user_id: str,
    flat_number: str,
    user_name: str,
    raw_text: str,
) -> GroceryOrderResponse:
    """Execute AI extraction on confirmed resident grocery submission.

    Idempotent: If an order already exists for this submission, returns existing record.
    """
    orders_col = get_grocery_orders_collection()

    # 1. Idempotency Check: Avoid duplicate processing
    existing = await orders_col.find_one({"submission_id": submission_id})
    if existing:
        logger.info("Order for submission %s already exists. Returning existing.", submission_id)
        return _serialize_order(existing)

    settings = get_settings()
    now = datetime.now(timezone.utc)

    # 2. Persist initial 'processing' record
    order_doc = {
        "society_id": society_id,
        "round_id": round_id,
        "round_number": round_number,
        "submission_id": submission_id,
        "message_id": message_id,
        "user_id": user_id,
        "flat_number": flat_number,
        "user_name": user_name,
        "raw_text": raw_text,
        "detected_language": "en",
        "items": [],
        "status": "processing",
        "clarification_prompt": None,
        "clarification_history": [],
        "ai_model": settings.groq_model,
        "prompt_version": "v1.0",
        "created_at": now,
        "updated_at": now,
        "confirmed_at": None,
    }

    try:
        res = await orders_col.insert_one(order_doc)
        order_doc["_id"] = res.inserted_id
    except Exception as exc:
        # Race condition catch if duplicate concurrent request arrived
        existing = await orders_col.find_one({"submission_id": submission_id})
        if existing:
            return _serialize_order(existing)
        raise exc

    # 3. Call Groq AI service
    try:
        ai_output: AIExtractionOutput = await groq_service.extract_grocery_items(raw_text)

        updated = await orders_col.find_one_and_update(
            {"_id": order_doc["_id"]},
            {
                "$set": {
                    "detected_language": ai_output.detected_language,
                    "items": [it.model_dump() for it in ai_output.items],
                    "status": ai_output.overall_status,
                    "clarification_prompt": ai_output.clarification_prompt,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )

        # Notify society group channel
        group_id = await _get_society_nexconn_group_id(society_id)
        if group_id:
            status_msg = (
                f"🤖 [Society Cart AI] Grocery list from Flat {flat_number} has been processed "
                f"and is awaiting resident review."
            )
            extra = {
                "type": "ai_order_event",
                "action": "extracted",
                "order_id": str(updated["_id"]),
                "flat_number": flat_number,
                "status": ai_output.overall_status,
            }
            await send_system_bot_message(group_id, status_msg, extra)

        return _serialize_order(updated)

    except Exception as ai_exc:
        logger.error("AI extraction error for submission %s: %s", submission_id, ai_exc)
        # Bounded failure update without invalidating original submission
        failed = await orders_col.find_one_and_update(
            {"_id": order_doc["_id"]},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(ai_exc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return _serialize_order(failed)


async def _verify_order_access(
    order: Dict[str, Any],
    caller_user_id: str,
    allow_volunteer: bool = True,
) -> str:
    """Verify caller's membership in society and ownership or authorized role."""
    from app.core.database import get_memberships_collection
    mem = await get_memberships_collection().find_one({
        "user_id": caller_user_id,
        "society_id": order["society_id"],
        "is_active": True,
    })
    if not mem:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this apartment society.",
        )

    role = mem.get("role", "resident")
    is_owner = str(order["user_id"]) == caller_user_id
    if is_owner or (allow_volunteer and role in ("volunteer", "admin")):
        return role

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not authorized to view or modify another resident's grocery order.",
    )


async def get_order_by_id(
    order_id: str,
    caller_user_id: str,
    caller_role: str = "resident",
    society_id: Optional[str] = None,
) -> GroceryOrderResponse:
    """Retrieve an individual grocery order enforcing resident privacy and RBAC."""
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery order not found.",
        )

    # Society scoping check
    if society_id and order["society_id"] != society_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to another apartment society's grocery order is forbidden.",
        )

    await _verify_order_access(order, caller_user_id, allow_volunteer=True)
    return _serialize_order(order)


async def list_orders_for_round(
    society_id: str,
    round_id: str,
    caller_user_id: str,
    caller_role: str,
) -> List[GroceryOrderResponse]:
    """List grocery orders for a round respecting privacy boundaries.

    - Volunteers and Admins see all orders in the society round.
    - Residents see only their own orders.
    """
    orders_col = get_grocery_orders_collection()
    query: Dict[str, Any] = {
        "society_id": society_id,
        "round_id": round_id,
    }

    if caller_role not in ("volunteer", "admin"):
        query["user_id"] = caller_user_id

    cursor = orders_col.find(query).sort("created_at", 1)
    results = await cursor.to_list(length=500)
    return [_serialize_order(doc) for doc in results]


async def clarify_order(
    order_id: str,
    caller_user_id: str,
    caller_role: str,
    clarification_text: str,
) -> GroceryOrderResponse:
    """Process resident's clarification response for ambiguous items."""
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    await _verify_order_access(order, caller_user_id, allow_volunteer=True)

    if order["status"] == "confirmed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot clarify an already confirmed order.")

    # Re-evaluate with Groq service
    raw_text = order["raw_text"]
    current_items = order.get("items", [])
    history = order.get("clarification_history", [])

    ai_output = await groq_service.reparse_with_clarification(
        raw_text=raw_text,
        current_items=current_items,
        clarification_text=clarification_text,
        history=history,
    )

    new_history_entry = {
        "prompt": order.get("clarification_prompt") or "Clarification requested",
        "resident_response": clarification_text,
        "timestamp": datetime.now(timezone.utc),
    }

    updated = await orders_col.find_one_and_update(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "items": [it.model_dump() for it in ai_output.items],
                "status": ai_output.overall_status,
                "clarification_prompt": ai_output.clarification_prompt,
                "updated_at": datetime.now(timezone.utc),
            },
            "$push": {"clarification_history": new_history_entry},
        },
        return_document=ReturnDocument.AFTER,
    )

    return _serialize_order(updated)


async def update_order_items(
    order_id: str,
    caller_user_id: str,
    caller_role: str,
    items: List[GroceryItemSchema],
) -> GroceryOrderResponse:
    """Manually update grocery items (edit, add, remove) by the resident."""
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    await _verify_order_access(order, caller_user_id, allow_volunteer=True)

    if order["status"] == "confirmed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify an already confirmed order.")

    now = datetime.now(timezone.utc)
    updated = await orders_col.find_one_and_update(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "items": [it.model_dump() for it in items],
                "status": "awaiting_confirmation",
                "clarification_prompt": None,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    return _serialize_order(updated)


async def confirm_order(
    order_id: str,
    caller_user_id: str,
    caller_role: str,
) -> GroceryOrderResponse:
    """Resident explicitly confirms the AI interpretation of their order."""
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    await _verify_order_access(order, caller_user_id, allow_volunteer=True)

    if order["status"] == "confirmed":
        return _serialize_order(order)

    if not order.get("items"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot confirm an empty grocery order.",
        )

    now = datetime.now(timezone.utc)
    updated = await orders_col.find_one_and_update(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "status": "confirmed",
                "confirmed_at": now,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    # Optional channel announcement
    group_id = await _get_society_nexconn_group_id(order["society_id"])
    if group_id:
        msg = f"✅ Flat {order.get('flat_number', '')}'s grocery order has been confirmed."
        await send_system_bot_message(
            group_id,
            msg,
            {"type": "ai_order_event", "action": "confirmed", "order_id": order_id},
        )

    return _serialize_order(updated)


async def reject_order(
    order_id: str,
    caller_user_id: str,
    caller_role: str,
) -> GroceryOrderResponse:
    """Resident explicitly rejects the AI interpretation."""
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    await _verify_order_access(order, caller_user_id, allow_volunteer=True)

    now = datetime.now(timezone.utc)
    updated = await orders_col.find_one_and_update(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "status": "rejected",
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    return _serialize_order(updated)
