"""Service layer for grocery order rounds and resident grocery submissions.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.database import (
    get_order_rounds_collection,
    get_grocery_submissions_collection,
    get_societies_collection,
)
from app.schemas.round import (
    AnnouncementDeliveryState,
    CreateRoundRequest,
    CreateSubmissionRequest,
    RoundResponse,
    RoundStatus,
    SubmissionConfirmationRequest,
    SubmissionFailureRequest,
    SubmissionReservationRequest,
    SubmissionResponse,
)
from app.services.nexconn_service import send_system_bot_message

logger = logging.getLogger(__name__)


def _ensure_utc(dt: Any) -> Optional[datetime]:
    """Ensure a datetime object is timezone-aware and set to UTC."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _serialize_round(doc: Dict[str, Any], submissions_count: int = 0) -> RoundResponse:
    """Transform raw MongoDB round document into RoundResponse."""
    open_ann = doc.get("opening_announcement")
    if open_ann and isinstance(open_ann, dict):
        opening_ann_model = AnnouncementDeliveryState(
            status=open_ann.get("status", "pending"),
            attempts=int(open_ann.get("attempts", 0)),
            last_attempt_at=_ensure_utc(open_ann.get("last_attempt_at")),
            sent_at=_ensure_utc(open_ann.get("sent_at")),
            last_error=open_ann.get("last_error"),
        )
    else:
        was_sent = bool(doc.get("opening_announcement_sent", False))
        opening_ann_model = AnnouncementDeliveryState(
            status="sent" if was_sent else "pending",
            attempts=1 if was_sent else 0,
            sent_at=_ensure_utc(doc.get("opened_at")) if was_sent else None,
        )

    close_ann = doc.get("closing_announcement")
    if close_ann and isinstance(close_ann, dict):
        closing_ann_model = AnnouncementDeliveryState(
            status=close_ann.get("status", "pending"),
            attempts=int(close_ann.get("attempts", 0)),
            last_attempt_at=_ensure_utc(close_ann.get("last_attempt_at")),
            sent_at=_ensure_utc(close_ann.get("sent_at")),
            last_error=close_ann.get("last_error"),
        )
    else:
        was_sent = bool(doc.get("closing_announcement_sent", False))
        closing_ann_model = AnnouncementDeliveryState(
            status="sent" if was_sent else "pending",
            attempts=1 if was_sent else 0,
            sent_at=_ensure_utc(doc.get("closed_at")) if was_sent else None,
        )

    return RoundResponse(
        id=str(doc["_id"]),
        society_id=str(doc["society_id"]),
        round_number=int(doc["round_number"]),
        title=doc["title"],
        description=doc.get("description"),
        status=doc["status"],
        created_by=str(doc["created_by"]),
        created_at=_ensure_utc(doc.get("created_at", datetime.now(timezone.utc))),
        opened_at=_ensure_utc(doc.get("opened_at")),
        deadline_at=_ensure_utc(doc["deadline_at"]),
        shopping_date=str(doc["shopping_date"]),
        closed_at=_ensure_utc(doc.get("closed_at")),
        updated_at=_ensure_utc(doc.get("updated_at", datetime.now(timezone.utc))),
        submissions_count=submissions_count,
        opening_announcement=opening_ann_model,
        closing_announcement=closing_ann_model,
        opening_announcement_sent=bool(doc.get("opening_announcement_sent", opening_ann_model.status == "sent")),
        closing_announcement_sent=bool(doc.get("closing_announcement_sent", closing_ann_model.status == "sent")),
    )


def _serialize_submission(doc: Dict[str, Any]) -> SubmissionResponse:
    """Transform raw MongoDB submission document into SubmissionResponse."""
    sub_id = doc.get("submission_id") or str(doc["_id"])
    return SubmissionResponse(
        id=str(doc["_id"]),
        submission_id=sub_id,
        society_id=str(doc["society_id"]),
        round_id=str(doc["round_id"]),
        round_number=int(doc["round_number"]),
        user_id=str(doc["user_id"]),
        flat_number=doc["flat_number"],
        user_name=doc.get("user_name", "Resident"),
        message_id=doc.get("message_id"),
        raw_text=doc["raw_text"],
        status=doc.get("status", "reserved"),
        reserved_at=_ensure_utc(doc.get("reserved_at")),
        confirmed_at=_ensure_utc(doc.get("confirmed_at")),
        created_at=_ensure_utc(doc.get("created_at", datetime.now(timezone.utc))),
    )


async def _get_society_nexconn_group_id(society_id: str) -> Optional[str]:
    """Retrieve the Nexconn group channel identifier for an apartment society."""
    societies = get_societies_collection()
    soc = await societies.find_one({"_id": ObjectId(society_id)})
    if not soc:
        return None
    return soc.get("nexconn_group_id") or f"society_{soc['_id']}"


async def allocate_round_number(society_id: str) -> int:
    """Atomically allocate the next sequential round number for a society.

    Uses an atomic counter on the society document to prevent race conditions.
    """
    societies = get_societies_collection()
    rounds = get_order_rounds_collection()

    soc = await societies.find_one({"_id": ObjectId(society_id)})
    if not soc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apartment society not found.",
        )

    # Initialize counter if not present
    if "round_counter" not in soc:
        last_round = await rounds.find_one({"society_id": society_id}, sort=[("round_number", -1)])
        current_max = int(last_round["round_number"]) if last_round else 0
        await societies.update_one(
            {"_id": ObjectId(society_id), "round_counter": {"$exists": False}},
            {"$set": {"round_counter": current_max}},
        )

    updated_soc = await societies.find_one_and_update(
        {"_id": ObjectId(society_id)},
        {"$inc": {"round_counter": 1}},
        return_document=ReturnDocument.AFTER,
    )
    return int(updated_soc["round_counter"])


async def create_round(
    society_id: str,
    user_id: str,
    data: CreateRoundRequest,
) -> RoundResponse:
    """Create a new grocery order round in 'draft' status.

    Args:
        society_id: Society ID.
        user_id: Creator user ID.
        data: Round parameters.

    Returns:
        RoundResponse: Created draft round.

    Raises:
        HTTPException: 400 Bad Request if deadline is in the past or society invalid.
    """
    societies = get_societies_collection()
    soc = await societies.find_one({"_id": ObjectId(society_id), "is_active": True})
    if not soc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apartment society not found or inactive.",
        )

    now = datetime.now(timezone.utc)
    if data.deadline_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order round deadline must be in the future.",
        )

    round_number = await allocate_round_number(society_id)

    initial_delivery_state = {
        "status": "pending",
        "attempts": 0,
        "last_attempt_at": None,
        "sent_at": None,
        "last_error": None,
    }

    doc = {
        "society_id": society_id,
        "round_number": round_number,
        "title": data.title,
        "description": data.description,
        "status": "draft",
        "created_by": user_id,
        "created_at": now,
        "opened_at": None,
        "deadline_at": data.deadline_at,
        "shopping_date": data.shopping_date,
        "closed_at": None,
        "updated_at": now,
        "opening_announcement": initial_delivery_state.copy(),
        "closing_announcement": initial_delivery_state.copy(),
        "opening_announcement_sent": False,
        "closing_announcement_sent": False,
    }

    rounds = get_order_rounds_collection()
    try:
        result = await rounds.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Round number {round_number} already exists for this society.",
        )

    doc["_id"] = result.inserted_id
    return _serialize_round(doc, submissions_count=0)


async def open_round(
    society_id: str,
    round_id: str,
    user_id: str,
) -> RoundResponse:
    """Transition a draft round to 'open' and broadcast the opening announcement.

    Does not roll back round state if announcement delivery encounters an error.
    """
    rounds = get_order_rounds_collection()
    round_doc = await rounds.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery round not found for this society.",
        )

    current_status = round_doc.get("status")
    if current_status == "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This grocery round is already open.",
        )
    if current_status in ("closed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot open a {current_status} grocery round.",
        )

    now = datetime.now(timezone.utc)
    if _ensure_utc(round_doc["deadline_at"]) <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot open round because its submission deadline has already passed.",
        )

    # Check for another currently open round in this society
    existing_open = await rounds.find_one({"society_id": society_id, "status": "open"})
    if existing_open:
        if _ensure_utc(existing_open["deadline_at"]) <= now:
            await close_round(society_id, str(existing_open["_id"]), is_automatic=True)
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another grocery round (#{existing_open['round_number']}) is currently active. Close it before opening a new one.",
            )

    pending_announcement = {
        "status": "pending",
        "attempts": 0,
        "last_attempt_at": None,
        "sent_at": None,
        "last_error": None,
    }

    try:
        updated = await rounds.find_one_and_update(
            {"_id": ObjectId(round_id), "status": "draft"},
            {
                "$set": {
                    "status": "open",
                    "opened_at": now,
                    "updated_at": now,
                    "opening_announcement": pending_announcement,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A concurrent request has already opened an active round for this society.",
        )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to open round. It may have already been opened or modified.",
        )

    # Dispatch Real Nexconn Group Announcement
    group_id = await _get_society_nexconn_group_id(society_id)
    if group_id:
        deadline_str = updated["deadline_at"].strftime("%d %b %Y, %I:%M %p UTC")
        announcement_text = (
            f"🛒 Grocery Round #{updated['round_number']} is now OPEN!\n\n"
            f"Submit your grocery requirements before {deadline_str}.\n\n"
            f"Shopping date: {updated['shopping_date']}.\n\n"
            f"Please send your items in the society chat."
        )
        announcement_extra = {
            "type": "round_event",
            "action": "open",
            "round_id": str(updated["_id"]),
            "round_number": updated["round_number"],
            "title": updated["title"],
            "deadline_at": updated["deadline_at"].isoformat(),
            "shopping_date": updated["shopping_date"],
        }

        attempt_time = datetime.now(timezone.utc)
        try:
            sent = await send_system_bot_message(group_id, announcement_text, announcement_extra)
            if sent:
                updated = await rounds.find_one_and_update(
                    {"_id": updated["_id"]},
                    {
                        "$set": {
                            "opening_announcement.status": "sent",
                            "opening_announcement.attempts": 1,
                            "opening_announcement.last_attempt_at": attempt_time,
                            "opening_announcement.sent_at": attempt_time,
                            "opening_announcement.last_error": None,
                            "opening_announcement_sent": True,
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                )
            else:
                updated = await rounds.find_one_and_update(
                    {"_id": updated["_id"]},
                    {
                        "$set": {
                            "opening_announcement.status": "failed",
                            "opening_announcement.attempts": 1,
                            "opening_announcement.last_attempt_at": attempt_time,
                            "opening_announcement.last_error": "Nexconn message dispatch was unsuccessful.",
                            "opening_announcement_sent": False,
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                )
        except Exception as exc:
            logger.warning("Opening announcement delivery exception: %s", exc)
            updated = await rounds.find_one_and_update(
                {"_id": updated["_id"]},
                {
                    "$set": {
                        "opening_announcement.status": "failed",
                        "opening_announcement.attempts": 1,
                        "opening_announcement.last_attempt_at": attempt_time,
                        "opening_announcement.last_error": str(exc),
                        "opening_announcement_sent": False,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )

    submissions_count = await get_grocery_submissions_collection().count_documents({"round_id": str(updated["_id"])})
    return _serialize_round(updated, submissions_count=submissions_count)


async def close_round(
    society_id: str,
    round_id: str,
    user_id: Optional[str] = None,
    is_automatic: bool = False,
) -> RoundResponse:
    """Transition an active round to 'closed' and broadcast the closing announcement.

    Does not roll back round state if announcement delivery encounters an error.
    """
    rounds = get_order_rounds_collection()
    round_doc = await rounds.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery round not found for this society.",
        )

    current_status = round_doc.get("status")
    if current_status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An already closed round must not be closed again.",
        )
    if current_status not in ("open", "draft"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot close a round with status '{current_status}'.",
        )

    now = datetime.now(timezone.utc)
    pending_closing_announcement = {
        "status": "pending",
        "attempts": 0,
        "last_attempt_at": None,
        "sent_at": None,
        "last_error": None,
    }

    updated = await rounds.find_one_and_update(
        {"_id": ObjectId(round_id), "status": {"$in": ["open", "draft"]}},
        {
            "$set": {
                "status": "closed",
                "closed_at": now,
                "updated_at": now,
                "closing_announcement": pending_closing_announcement,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not close round. It may have already been closed.",
        )

    # Dispatch Closing Announcement
    group_id = await _get_society_nexconn_group_id(society_id)
    if group_id:
        announcement_text = (
            f"🔒 Grocery Round #{updated['round_number']} is now CLOSED.\n\n"
            f"New grocery submissions are no longer accepted for this round.\n\n"
            f"The volunteer will now prepare the consolidated shopping list."
        )
        announcement_extra = {
            "type": "round_event",
            "action": "close",
            "round_id": str(updated["_id"]),
            "round_number": updated["round_number"],
            "closed_at": now.isoformat(),
            "is_automatic": is_automatic,
        }

        attempt_time = datetime.now(timezone.utc)
        try:
            sent = await send_system_bot_message(group_id, announcement_text, announcement_extra)
            if sent:
                updated = await rounds.find_one_and_update(
                    {"_id": updated["_id"]},
                    {
                        "$set": {
                            "closing_announcement.status": "sent",
                            "closing_announcement.attempts": 1,
                            "closing_announcement.last_attempt_at": attempt_time,
                            "closing_announcement.sent_at": attempt_time,
                            "closing_announcement.last_error": None,
                            "closing_announcement_sent": True,
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                )
            else:
                updated = await rounds.find_one_and_update(
                    {"_id": updated["_id"]},
                    {
                        "$set": {
                            "closing_announcement.status": "failed",
                            "closing_announcement.attempts": 1,
                            "closing_announcement.last_attempt_at": attempt_time,
                            "closing_announcement.last_error": "Nexconn closing message dispatch was unsuccessful.",
                            "closing_announcement_sent": False,
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                )
        except Exception as exc:
            logger.warning("Closing announcement delivery exception: %s", exc)
            updated = await rounds.find_one_and_update(
                {"_id": updated["_id"]},
                {
                    "$set": {
                        "closing_announcement.status": "failed",
                        "closing_announcement.attempts": 1,
                        "closing_announcement.last_attempt_at": attempt_time,
                        "closing_announcement.last_error": str(exc),
                        "closing_announcement_sent": False,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )

    submissions_count = await get_grocery_submissions_collection().count_documents({"round_id": str(updated["_id"])})
    return _serialize_round(updated, submissions_count=submissions_count)


async def get_active_round(society_id: str) -> Optional[RoundResponse]:
    """Retrieve the currently active open grocery round for an apartment society.

    Performs an on-demand deadline check to ensure expired rounds are closed immediately.
    """
    rounds = get_order_rounds_collection()
    round_doc = await rounds.find_one({"society_id": society_id, "status": "open"})
    if not round_doc:
        return None

    now = datetime.now(timezone.utc)
    if _ensure_utc(round_doc["deadline_at"]) <= now:
        logger.info(
            "Active round #%s in society %s has expired (deadline: %s). Auto-closing.",
            round_doc.get("round_number"),
            society_id,
            round_doc["deadline_at"],
        )
        await close_round(society_id, str(round_doc["_id"]), is_automatic=True)
        return None

    submissions_count = await get_grocery_submissions_collection().count_documents({"round_id": str(round_doc["_id"])})
    return _serialize_round(round_doc, submissions_count=submissions_count)


async def list_rounds(
    society_id: str,
    skip: int = 0,
    limit: int = 20,
) -> Tuple[List[RoundResponse], int]:
    """Retrieve paginated round history for a society in descending order."""
    rounds = get_order_rounds_collection()
    submissions = get_grocery_submissions_collection()

    now = datetime.now(timezone.utc)
    open_round_doc = await rounds.find_one({"society_id": society_id, "status": "open"})
    if open_round_doc and _ensure_utc(open_round_doc["deadline_at"]) <= now:
        await close_round(society_id, str(open_round_doc["_id"]), is_automatic=True)

    query = {"society_id": society_id}
    total = await rounds.count_documents(query)

    cursor = rounds.find(query).sort("round_number", -1).skip(skip).limit(limit)
    raw_rounds = await cursor.to_list(length=limit)

    results: List[RoundResponse] = []
    for doc in raw_rounds:
        count = await submissions.count_documents({"round_id": str(doc["_id"])})
        results.append(_serialize_round(doc, submissions_count=count))

    return results, total


async def get_round_by_id(society_id: str, round_id: str) -> RoundResponse:
    """Retrieve specific round details verifying society ownership."""
    rounds = get_order_rounds_collection()
    round_doc = await rounds.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery round not found for this society.",
        )

    now = datetime.now(timezone.utc)
    if round_doc.get("status") == "open" and _ensure_utc(round_doc["deadline_at"]) <= now:
        return await close_round(society_id, str(round_doc["_id"]), is_automatic=True)

    count = await get_grocery_submissions_collection().count_documents({"round_id": str(round_doc["_id"])})
    return _serialize_round(round_doc, submissions_count=count)


async def reserve_submission(
    society_id: str,
    round_id: str,
    user_id: str,
    flat_number: str,
    user_name: str,
    data: SubmissionReservationRequest,
) -> SubmissionResponse:
    """Pre-register a resident grocery submission before dispatching to Nexconn chat.

    Validates that the round is strictly open and before its deadline. Records the
    acceptance timestamp `reserved_at` which authorizes timely submission even if
    the round subsequently closes prior to confirmation.
    """
    rounds = get_order_rounds_collection()
    round_doc = await rounds.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery round not found for this society.",
        )

    now = datetime.now(timezone.utc)
    if round_doc.get("status") == "open" and _ensure_utc(round_doc["deadline_at"]) <= now:
        await close_round(society_id, str(round_doc["_id"]), is_automatic=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The deadline for this grocery round has passed. No new reservations can be accepted.",
        )

    if round_doc.get("status") != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reserve grocery submission. Round status is '{round_doc.get('status')}'.",
        )

    submissions = get_grocery_submissions_collection()

    # Check for existing reservation with identical submission_id
    existing = await submissions.find_one({"submission_id": data.submission_id})
    if existing:
        if str(existing.get("user_id")) == user_id and str(existing.get("round_id")) == round_id:
            return _serialize_submission(existing)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A submission with this ID already exists for another user or round.",
        )

    doc = {
        "submission_id": data.submission_id,
        "society_id": society_id,
        "round_id": str(round_doc["_id"]),
        "round_number": int(round_doc["round_number"]),
        "user_id": user_id,
        "flat_number": flat_number,
        "user_name": user_name,
        "message_id": None,
        "raw_text": data.raw_text,
        "status": "reserved",
        "reserved_at": now,
        "confirmed_at": None,
        "created_at": now,
    }

    try:
        result = await submissions.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submission reservation ID conflict. Please generate a unique submission ID.",
        )

    doc["_id"] = result.inserted_id
    return _serialize_submission(doc)


async def confirm_submission(
    society_id: str,
    round_id: str,
    submission_id: str,
    user_id: str,
    user_role: str,
    data: SubmissionConfirmationRequest,
) -> SubmissionResponse:
    """Confirm a reserved grocery submission by linking the delivered Nexconn message ID.

    Authoritative timeliness rule: A reservation accepted before deadline remains
    confirmable even if the round is now closed.
    """
    submissions = get_grocery_submissions_collection()
    query = {"submission_id": submission_id, "society_id": society_id, "round_id": round_id}
    sub_doc = await submissions.find_one(query)

    if not sub_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserved grocery submission not found.",
        )

    # Enforce ownership
    if user_role not in ("volunteer", "admin") and str(sub_doc.get("user_id")) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to confirm another resident's submission reservation.",
        )

    # Idempotent confirmation if already confirmed with identical message_id
    if sub_doc.get("status") == "confirmed":
        if sub_doc.get("message_id") == data.message_id:
            return _serialize_submission(sub_doc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reservation has already been confirmed with a different message ID.",
        )

    if sub_doc.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot confirm a reservation that has been marked as failed.",
        )

    # Enforce single message_id constraint across submissions
    existing_message = await submissions.find_one({
        "message_id": data.message_id,
        "submission_id": {"$ne": submission_id},
    })
    if existing_message:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Nexconn message ID is already associated with another grocery submission.",
        )

    now = datetime.now(timezone.utc)
    try:
        updated = await submissions.find_one_and_update(
            {"_id": sub_doc["_id"], "status": "reserved"},
            {
                "$set": {
                    "message_id": data.message_id,
                    "status": "confirmed",
                    "confirmed_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate message ID detected. This Nexconn message is already linked.",
        )

    if not updated:
        # Race condition fallback check
        current = await submissions.find_one({"_id": sub_doc["_id"]})
        if current and current.get("status") == "confirmed" and current.get("message_id") == data.message_id:
            return _serialize_submission(current)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to confirm reservation. Current status may not be 'reserved'.",
        )

    # Phase 5: Trigger asynchronous background AI grocery extraction
    try:
        import asyncio
        from app.services import order_service
        asyncio.create_task(
            order_service.trigger_ai_extraction(
                society_id=society_id,
                round_id=round_id,
                round_number=int(updated.get("round_number", 1)),
                submission_id=submission_id,
                message_id=data.message_id,
                user_id=str(updated["user_id"]),
                flat_number=str(updated.get("flat_number", "")),
                user_name=str(updated.get("user_name", "Resident")),
                raw_text=str(updated["raw_text"]),
            )
        )
    except Exception as bg_exc:
        logger.warning("Could not launch background AI extraction task: %s", bg_exc)

    return _serialize_submission(updated)


async def fail_submission(
    society_id: str,
    round_id: str,
    submission_id: str,
    user_id: str,
    user_role: str,
    data: Optional[SubmissionFailureRequest] = None,
) -> SubmissionResponse:
    """Mark a submission reservation as failed when message dispatch fails."""
    submissions = get_grocery_submissions_collection()
    query = {"submission_id": submission_id, "society_id": society_id, "round_id": round_id}
    sub_doc = await submissions.find_one(query)

    if not sub_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery submission reservation not found.",
        )

    if user_role not in ("volunteer", "admin") and str(sub_doc.get("user_id")) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update another resident's submission reservation.",
        )

    if sub_doc.get("status") == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark an already confirmed submission as failed.",
        )

    reason = data.reason if data else "Nexconn message delivery failed"
    updated = await submissions.find_one_and_update(
        {"_id": sub_doc["_id"]},
        {"$set": {"status": "failed", "fail_reason": reason}},
        return_document=ReturnDocument.AFTER,
    )
    return _serialize_submission(updated)


async def create_submission(
    society_id: str,
    user_id: str,
    flat_number: str,
    user_name: str,
    data: CreateSubmissionRequest,
) -> SubmissionResponse:
    """Direct submission endpoint preserving backward compatibility.

    Chains race-safe reservation and confirmation steps atomically.
    """
    round_id = data.round_id
    if not round_id:
        active = await get_active_round(society_id)
        if not active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="There is currently no active grocery round accepting submissions.",
            )
        round_id = active.id

    client_sub_id = f"sub_{data.message_id}_{int(datetime.now(timezone.utc).timestamp())}"
    reserve_req = SubmissionReservationRequest(
        submission_id=client_sub_id,
        raw_text=data.raw_text,
    )

    reservation = await reserve_submission(
        society_id=society_id,
        round_id=round_id,
        user_id=user_id,
        flat_number=flat_number,
        user_name=user_name,
        data=reserve_req,
    )

    confirm_req = SubmissionConfirmationRequest(message_id=data.message_id)
    return await confirm_submission(
        society_id=society_id,
        round_id=round_id,
        submission_id=reservation.submission_id,
        user_id=user_id,
        user_role="resident",
        data=confirm_req,
    )


async def list_submissions(
    society_id: str,
    round_id: str,
    caller_user_id: str,
    caller_role: str,
) -> List[SubmissionResponse]:
    """Retrieve grocery submissions associated with a round respecting privacy boundaries.

    Authorization Rules:
    - Residents can only retrieve their own submissions.
    - Volunteers and Admins can retrieve all submissions for their authorized society.
    - Access to submissions in a different society is forbidden.
    """
    rounds = get_order_rounds_collection()
    round_doc = await rounds.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery round not found for this society.",
        )

    submissions = get_grocery_submissions_collection()

    query: Dict[str, Any] = {
        "round_id": round_id,
        "society_id": society_id,
        "status": {"$ne": "failed"},
    }

    # Privacy enforcement
    if caller_role in ("volunteer", "admin"):
        # Authorized coordinators see all resident orders in this society
        pass
    else:
        # Residents only see their own orders
        query["user_id"] = caller_user_id

    cursor = submissions.find(query).sort("created_at", 1)
    results = await cursor.to_list(length=1000)
    return [_serialize_submission(doc) for doc in results]
