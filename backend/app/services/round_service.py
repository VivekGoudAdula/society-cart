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
    CreateRoundRequest,
    CreateSubmissionRequest,
    RoundResponse,
    RoundStatus,
    SubmissionResponse,
)
from app.services.nexconn_service import send_system_bot_message

logger = logging.getLogger(__name__)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime object is timezone-aware and set to UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _serialize_round(doc: Dict[str, Any], submissions_count: int = 0) -> RoundResponse:
    """Transform raw MongoDB round document into RoundResponse."""
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
        shopping_date=doc["shopping_date"],
        closed_at=_ensure_utc(doc.get("closed_at")),
        updated_at=_ensure_utc(doc.get("updated_at", datetime.now(timezone.utc))),
        submissions_count=submissions_count,
    )


def _serialize_submission(doc: Dict[str, Any]) -> SubmissionResponse:
    """Transform raw MongoDB submission document into SubmissionResponse."""
    return SubmissionResponse(
        id=str(doc["_id"]),
        society_id=str(doc["society_id"]),
        round_id=str(doc["round_id"]),
        round_number=int(doc["round_number"]),
        user_id=str(doc["user_id"]),
        flat_number=doc["flat_number"],
        user_name=doc.get("user_name", "Resident"),
        message_id=doc["message_id"],
        raw_text=doc["raw_text"],
        status=doc.get("status", "pending"),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
    )


async def _get_society_nexconn_group_id(society_id: str) -> Optional[str]:
    """Retrieve the Nexconn group channel identifier for an apartment society."""
    societies = get_societies_collection()
    soc = await societies.find_one({"_id": ObjectId(society_id)})
    if not soc:
        return None
    return soc.get("nexconn_group_id") or f"society_{soc['_id']}"


async def get_next_round_number(society_id: str) -> int:
    """Determine the next sequential round number for a given society."""
    rounds = get_order_rounds_collection()
    cursor = rounds.find({"society_id": society_id}).sort("round_number", -1).limit(1)
    results = await cursor.to_list(length=1)
    if not results:
        return 1
    return int(results[0].get("round_number", 0)) + 1


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

    round_number = await get_next_round_number(society_id)

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
        "opening_announcement_sent": False,
        "closing_announcement_sent": False,
    }

    rounds = get_order_rounds_collection()
    result = await rounds.insert_one(doc)
    doc["_id"] = result.inserted_id

    return _serialize_round(doc, submissions_count=0)


async def open_round(
    society_id: str,
    round_id: str,
    user_id: str,
) -> RoundResponse:
    """Transition a draft round to 'open' and broadcast the opening announcement.

    Args:
        society_id: Target society ID.
        round_id: Target round ID.
        user_id: Authorizing volunteer/admin user ID.

    Returns:
        RoundResponse: Updated open round.

    Raises:
        HTTPException: 404 Not Found, 400 Bad Request, or 409 Conflict.
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
    # Also trigger lazy expiry check on any existing open round
    existing_open = await rounds.find_one({"society_id": society_id, "status": "open"})
    if existing_open:
        if _ensure_utc(existing_open["deadline_at"]) <= now:
            # Auto-close the expired round first
            await close_round(society_id, str(existing_open["_id"]), is_automatic=True)
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another grocery round (#{existing_open['round_number']}) is currently active. Close it before opening a new one.",
            )

    try:
        updated = await rounds.find_one_and_update(
            {"_id": ObjectId(round_id), "status": "draft"},
            {
                "$set": {
                    "status": "open",
                    "opened_at": now,
                    "updated_at": now,
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
        sent = await send_system_bot_message(group_id, announcement_text, announcement_extra)
        if sent:
            await rounds.update_one({"_id": updated["_id"]}, {"$set": {"opening_announcement_sent": True}})

    submissions_count = await get_grocery_submissions_collection().count_documents({"round_id": str(updated["_id"])})
    return _serialize_round(updated, submissions_count=submissions_count)


async def close_round(
    society_id: str,
    round_id: str,
    user_id: Optional[str] = None,
    is_automatic: bool = False,
) -> RoundResponse:
    """Transition an active round to 'closed' and broadcast the closing announcement.

    Args:
        society_id: Target society ID.
        round_id: Target round ID.
        user_id: Optional volunteer user ID.
        is_automatic: True if invoked by the deadline scheduler.

    Returns:
        RoundResponse: Updated closed round.

    Raises:
        HTTPException: 404 Not Found, 400 Bad Request.
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
    updated = await rounds.find_one_and_update(
        {"_id": ObjectId(round_id), "status": {"$in": ["open", "draft"]}},
        {
            "$set": {
                "status": "closed",
                "closed_at": now,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not close round. It may have already been closed.",
        )

    # Dispatch Closing Announcement if round was active and closing announcement not yet sent
    if not updated.get("closing_announcement_sent", False):
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
            sent = await send_system_bot_message(group_id, announcement_text, announcement_extra)
            if sent:
                await rounds.update_one({"_id": updated["_id"]}, {"$set": {"closing_announcement_sent": True}})

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

    # Lazy deadline check
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

    # Trigger lazy check for any open round in this society
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

    # Lazy check if open but expired
    now = datetime.now(timezone.utc)
    if round_doc.get("status") == "open" and _ensure_utc(round_doc["deadline_at"]) <= now:
        round_doc = await close_round(society_id, str(round_doc["_id"]), is_automatic=True)
        return round_doc

    count = await get_grocery_submissions_collection().count_documents({"round_id": str(round_doc["_id"])})
    return _serialize_round(round_doc, submissions_count=count)


async def create_submission(
    society_id: str,
    user_id: str,
    flat_number: str,
    user_name: str,
    data: CreateSubmissionRequest,
) -> SubmissionResponse:
    """Associate a resident's grocery message with the active grocery round.

    Validates that the target round is strictly open and within its submission deadline.
    """
    rounds = get_order_rounds_collection()

    if data.round_id:
        round_doc = await rounds.find_one({"_id": ObjectId(data.round_id), "society_id": society_id})
    else:
        round_doc = await rounds.find_one({"society_id": society_id, "status": "open"})

    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is currently no active grocery round accepting submissions.",
        )

    # Check expiration
    now = datetime.now(timezone.utc)
    if round_doc["status"] == "open" and _ensure_utc(round_doc["deadline_at"]) <= now:
        await close_round(society_id, str(round_doc["_id"]), is_automatic=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The deadline for this grocery round has passed. No new submissions can be accepted.",
        )

    if round_doc["status"] != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit groceries to a round with status '{round_doc['status']}'. Ordering is closed.",
        )

    submissions = get_grocery_submissions_collection()
    doc = {
        "society_id": society_id,
        "round_id": str(round_doc["_id"]),
        "round_number": int(round_doc["round_number"]),
        "user_id": user_id,
        "flat_number": flat_number,
        "user_name": user_name,
        "message_id": data.message_id,
        "raw_text": data.raw_text,
        "status": "pending",
        "created_at": now,
    }

    result = await submissions.insert_one(doc)
    doc["_id"] = result.inserted_id

    return _serialize_submission(doc)


async def list_submissions(
    society_id: str,
    round_id: str,
) -> List[SubmissionResponse]:
    """Retrieve all grocery submissions associated with a specific round."""
    rounds = get_order_rounds_collection()
    round_doc = await rounds.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery round not found for this society.",
        )

    submissions = get_grocery_submissions_collection()
    cursor = submissions.find({"round_id": round_id, "society_id": society_id}).sort("created_at", 1)
    results = await cursor.to_list(length=500)
    return [_serialize_submission(doc) for doc in results]
