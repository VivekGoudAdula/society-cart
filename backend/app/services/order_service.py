"""Service layer for AI grocery orders, clarifications, manual edits, and confirmations.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.core.config import get_settings
from app.core.database import (
    get_grocery_orders_collection,
    get_memberships_collection,
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
        recovery_attempts=int(doc.get("recovery_attempts", 0)),
    )


async def _verify_order_access(
    order: Dict[str, Any],
    caller_user_id: str,
    allow_volunteer: bool = False,
) -> str:
    """Verify caller membership and order authorization.

    Rules:
    - Caller must belong to the same society as the order.
    - Owner resident is always allowed.
    - Volunteers and admins are allowed only when allow_volunteer is True (viewing).
    - Volunteers and other residents cannot alter, clarify, confirm, or reject another resident's order.
    """
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

    if is_owner:
        return role

    if allow_volunteer and role in ("volunteer", "admin"):
        return role

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not authorized to access or modify this grocery order.",
    )


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

    Idempotent & Recoverable:
    - If order already exists in a completed or actionable state, returns existing.
    - If order exists in 'processing' or 'failed' (e.g. process was interrupted), resumes extraction.
    - Never publishes private resident items or flat numbers to the public chat.
    """
    orders_col = get_grocery_orders_collection()
    settings = get_settings()
    now = datetime.now(timezone.utc)

    # 1. Idempotency & Recovery Check
    existing = await orders_col.find_one({"submission_id": submission_id})
    if existing:
        completed_statuses = (
            "pending_review",
            "awaiting_confirmation",
            "needs_clarification",
            "confirmed",
            "rejected",
        )
        if existing.get("status") in completed_statuses:
            logger.info(
                "Order for submission %s already exists with status %s. Returning existing.",
                submission_id,
                existing.get("status"),
            )
            return _serialize_order(existing)

        # Existing record is in 'processing' or 'failed'; resume/recover
        order_doc = existing
    else:
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
            "recovery_attempts": 0,
        }

        try:
            res = await orders_col.insert_one(order_doc)
            order_doc["_id"] = res.inserted_id
        except Exception:
            # Handle potential concurrent insert race condition
            existing = await orders_col.find_one({"submission_id": submission_id})
            if existing:
                if existing.get("status") in (
                    "pending_review",
                    "awaiting_confirmation",
                    "needs_clarification",
                    "confirmed",
                    "rejected",
                ):
                    return _serialize_order(existing)
                order_doc = existing
            else:
                raise

    # 3. Call Groq AI service with bounded failure handling
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
                    "error_message": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return _serialize_order(updated)

    except Exception as ai_exc:
        logger.error("AI extraction error for submission %s: %s", submission_id, ai_exc)
        # Safe failure update: record failure without invalidating or corrupting original submission
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


async def recover_stale_processing_orders(
    timeout_seconds: int = 120,
    max_recovery_attempts: int = 3,
) -> int:
    """Scan and recover orders stuck in 'processing' status beyond timeout_seconds.

    Atomic claim:
    - Identifies orders where status == 'processing' and updated_at <= cutoff.
    - Atomically increments recovery_attempts and updates updated_at.
    - If recovery_attempts exceeds max_recovery_attempts, atomically marks as 'failed'.
    - Otherwise re-runs Groq extraction and transitions to 'pending_review' or 'needs_clarification'.
    - Preserves submission and prevents duplicate order creation.
    """
    orders_col = get_grocery_orders_collection()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=timeout_seconds)

    cursor = orders_col.find({
        "status": "processing",
        "updated_at": {"$lte": cutoff},
    })
    candidate_orders = await cursor.to_list(length=100)
    recovered_count = 0

    for candidate in candidate_orders:
        order_id = candidate["_id"]
        attempts = int(candidate.get("recovery_attempts", 0))

        if attempts >= max_recovery_attempts:
            await orders_col.update_one(
                {"_id": order_id, "status": "processing"},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": f"Processing timed out after {attempts} attempts following backend restart.",
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            continue

        # Atomic claim: only claim if status is STILL 'processing'
        claimed = await orders_col.find_one_and_update(
            {
                "_id": order_id,
                "status": "processing",
            },
            {
                "$inc": {"recovery_attempts": 1},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )

        if not claimed:
            continue

        try:
            raw_text = claimed.get("raw_text", "")
            ai_output = await groq_service.extract_grocery_items(raw_text)

            await orders_col.find_one_and_update(
                {
                    "_id": order_id,
                    "status": "processing",
                },
                {
                    "$set": {
                        "detected_language": ai_output.detected_language,
                        "items": [it.model_dump() for it in ai_output.items],
                        "status": ai_output.overall_status,
                        "clarification_prompt": ai_output.clarification_prompt,
                        "error_message": None,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            recovered_count += 1
            logger.info("Successfully recovered stale order %s to status %s", order_id, ai_output.overall_status)
        except Exception as exc:
            logger.error("Failed to recover stale order %s: %s", order_id, exc)
            if attempts + 1 >= max_recovery_attempts:
                await orders_col.update_one(
                    {"_id": order_id, "status": "processing"},
                    {
                        "$set": {
                            "status": "failed",
                            "error_message": f"Extraction failed during recovery: {exc}",
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )

    return recovered_count


async def retry_ai_extraction(
    order_id: str,
    caller_user_id: str,
) -> GroceryOrderResponse:
    """Manually retry AI extraction for an order that failed or was interrupted."""
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery order not found.",
        )

    # Only owner resident can retry their order
    await _verify_order_access(order, caller_user_id, allow_volunteer=False)

    if order.get("status") in ("confirmed", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry extraction for an order in '{order['status']}' state.",
        )

    # Mark as processing
    await orders_col.update_one(
        {"_id": order["_id"]},
        {"$set": {"status": "processing", "updated_at": datetime.now(timezone.utc)}},
    )

    try:
        raw_text = order.get("raw_text", "")
        ai_output: AIExtractionOutput = await groq_service.extract_grocery_items(raw_text)

        updated = await orders_col.find_one_and_update(
            {"_id": order["_id"]},
            {
                "$set": {
                    "detected_language": ai_output.detected_language,
                    "items": [it.model_dump() for it in ai_output.items],
                    "status": ai_output.overall_status,
                    "clarification_prompt": ai_output.clarification_prompt,
                    "error_message": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return _serialize_order(updated)

    except Exception as exc:
        logger.error("Retry extraction failed for order %s: %s", order_id, exc)
        failed = await orders_col.find_one_and_update(
            {"_id": order["_id"]},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(exc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return _serialize_order(failed)


async def get_order_by_id(
    order_id: str,
    caller_user_id: str,
    caller_role: str = "resident",
    society_id: Optional[str] = None,
) -> GroceryOrderResponse:
    """Retrieve an individual grocery order enforcing resident privacy and RBAC.

    - The resident who created the order can view it.
    - Volunteers and Admins belonging to the SAME society can view it.
    - Other residents cannot view it (403 Forbidden).
    - Cross-society callers cannot access it (403 Forbidden).
    """
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery order not found.",
        )

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
    """Process resident clarification response for ambiguous items.

    Enforces:
    - Only the resident owner can clarify their order (allow_volunteer=False).
    - Cannot clarify already confirmed, rejected, or currently processing orders.
    """
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    await _verify_order_access(order, caller_user_id, allow_volunteer=False)

    current_status = order.get("status")
    if current_status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot clarify an already confirmed order.",
        )
    if current_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot clarify a rejected order.",
        )
    if current_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot clarify an order that is currently processing.",
        )

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
    """Manually update grocery items (edit, add, remove) by the resident owner.

    Enforces:
    - Only the resident owner can modify their items (allow_volunteer=False).
    - Cannot modify already confirmed, rejected, or processing orders.
    """
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    await _verify_order_access(order, caller_user_id, allow_volunteer=False)

    current_status = order.get("status")
    if current_status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an already confirmed order.",
        )
    if current_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify a rejected order.",
        )
    if current_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an order that is currently processing.",
        )

    now = datetime.now(timezone.utc)
    updated = await orders_col.find_one_and_update(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "items": [it.model_dump() for it in items],
                "status": "pending_review",
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
    """Resident explicitly confirms the AI interpretation of their order.

    Enforces:
    - Only the resident owner can confirm their order (allow_volunteer=False).
    - Cannot confirm a rejected order or currently processing order.
    - Cannot confirm an empty grocery order.
    - Confirmation is idempotent.
    - Does NOT broadcast private details to public society chat.
    """
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    await _verify_order_access(order, caller_user_id, allow_volunteer=False)

    current_status = order.get("status")
    if current_status == "confirmed":
        return _serialize_order(order)
    if current_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot confirm a rejected order.",
        )
    if current_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot confirm an order that is currently processing.",
        )

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

    return _serialize_order(updated)


async def reject_order(
    order_id: str,
    caller_user_id: str,
    caller_role: str,
) -> GroceryOrderResponse:
    """Resident explicitly rejects the AI interpretation.

    Enforces:
    - Only the resident owner can reject their order (allow_volunteer=False).
    - Cannot reject an already confirmed order.
    - Rejection is idempotent.
    """
    orders_col = get_grocery_orders_collection()
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    await _verify_order_access(order, caller_user_id, allow_volunteer=False)

    current_status = order.get("status")
    if current_status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject an already confirmed order.",
        )
    if current_status == "rejected":
        return _serialize_order(order)
    if current_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject an order that is currently processing.",
        )

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
