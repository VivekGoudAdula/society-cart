"""Background scheduler for automatic deadline enforcement and announcement recovery.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument

from app.core.database import get_database, get_societies_collection
from app.services.nexconn_service import send_system_bot_message

logger = logging.getLogger(__name__)

_scheduler_task: Optional[asyncio.Task] = None


async def dispatch_opening_announcement(
    round_id: ObjectId,
    society_id: str,
    round_number: int,
    title: str,
    deadline_at: datetime,
    shopping_date: str,
    current_attempts: int = 0,
) -> bool:
    """Safely dispatch opening announcement and update structured delivery status."""
    try:
        db = get_database()
        rounds_col = db.order_rounds
        soc = await get_societies_collection().find_one({"_id": ObjectId(society_id)})
        group_id = soc.get("nexconn_group_id") if soc else f"society_{society_id}"

        deadline_str = deadline_at.strftime("%d %b %Y, %I:%M %p UTC") if hasattr(deadline_at, "strftime") else str(deadline_at)
        announcement_text = (
            f"🛒 Grocery Round #{round_number} is now OPEN!\n\n"
            f"Submit your grocery requirements before {deadline_str}.\n\n"
            f"Shopping date: {shopping_date}.\n\n"
            f"Please send your items in the society chat."
        )
        extra = {
            "type": "round_event",
            "action": "open",
            "round_id": str(round_id),
            "round_number": round_number,
            "title": title,
            "deadline_at": deadline_at.isoformat() if hasattr(deadline_at, "isoformat") else str(deadline_at),
            "shopping_date": shopping_date,
        }

        attempt_time = datetime.now(timezone.utc)
        attempts = current_attempts + 1

        sent = await send_system_bot_message(group_id, announcement_text, extra)
        if sent:
            await rounds_col.update_one(
                {"_id": round_id},
                {
                    "$set": {
                        "opening_announcement.status": "sent",
                        "opening_announcement.attempts": attempts,
                        "opening_announcement.last_attempt_at": attempt_time,
                        "opening_announcement.sent_at": attempt_time,
                        "opening_announcement.last_error": None,
                        "opening_announcement_sent": True,
                    }
                },
            )
            return True
        else:
            await rounds_col.update_one(
                {"_id": round_id},
                {
                    "$set": {
                        "opening_announcement.status": "failed",
                        "opening_announcement.attempts": attempts,
                        "opening_announcement.last_attempt_at": attempt_time,
                        "opening_announcement.last_error": "Nexconn returned unsuccessful response",
                        "opening_announcement_sent": False,
                    }
                },
            )
            return False
    except Exception as exc:
        logger.warning("Error dispatching opening announcement for round %s: %s", round_id, exc)
        try:
            db = get_database()
            await db.order_rounds.update_one(
                {"_id": round_id},
                {
                    "$set": {
                        "opening_announcement.status": "failed",
                        "opening_announcement.attempts": current_attempts + 1,
                        "opening_announcement.last_attempt_at": datetime.now(timezone.utc),
                        "opening_announcement.last_error": str(exc),
                        "opening_announcement_sent": False,
                    }
                },
            )
        except Exception:
            pass
        return False


async def dispatch_closing_announcement(
    round_id: ObjectId,
    society_id: str,
    round_number: int,
    closed_at: datetime,
    is_automatic: bool = True,
    current_attempts: int = 0,
) -> bool:
    """Safely dispatch closing announcement and update structured delivery status."""
    try:
        db = get_database()
        rounds_col = db.order_rounds
        soc = await get_societies_collection().find_one({"_id": ObjectId(society_id)})
        group_id = soc.get("nexconn_group_id") if soc else f"society_{society_id}"

        announcement_text = (
            f"🔒 Grocery Round #{round_number} is now CLOSED.\n\n"
            f"New grocery submissions are no longer accepted for this round.\n\n"
            f"The volunteer will now prepare the consolidated shopping list."
        )
        extra = {
            "type": "round_event",
            "action": "close",
            "round_id": str(round_id),
            "round_number": round_number,
            "closed_at": closed_at.isoformat() if hasattr(closed_at, "isoformat") else str(closed_at),
            "is_automatic": is_automatic,
        }

        attempt_time = datetime.now(timezone.utc)
        attempts = current_attempts + 1

        sent = await send_system_bot_message(group_id, announcement_text, extra)
        if sent:
            await rounds_col.update_one(
                {"_id": round_id},
                {
                    "$set": {
                        "closing_announcement.status": "sent",
                        "closing_announcement.attempts": attempts,
                        "closing_announcement.last_attempt_at": attempt_time,
                        "closing_announcement.sent_at": attempt_time,
                        "closing_announcement.last_error": None,
                        "closing_announcement_sent": True,
                    }
                },
            )
            return True
        else:
            await rounds_col.update_one(
                {"_id": round_id},
                {
                    "$set": {
                        "closing_announcement.status": "failed",
                        "closing_announcement.attempts": attempts,
                        "closing_announcement.last_attempt_at": attempt_time,
                        "closing_announcement.last_error": "Nexconn returned unsuccessful response",
                        "closing_announcement_sent": False,
                    }
                },
            )
            return False
    except Exception as exc:
        logger.warning("Error dispatching closing announcement for round %s: %s", round_id, exc)
        try:
            db = get_database()
            await db.order_rounds.update_one(
                {"_id": round_id},
                {
                    "$set": {
                        "closing_announcement.status": "failed",
                        "closing_announcement.attempts": current_attempts + 1,
                        "closing_announcement.last_attempt_at": datetime.now(timezone.utc),
                        "closing_announcement.last_error": str(exc),
                        "closing_announcement_sent": False,
                    }
                },
            )
        except Exception:
            pass
        return False


async def check_expired_rounds_once() -> int:
    """Find and automatically close open grocery rounds whose deadlines have expired.

    Also performs atomic recovery with bounded retries for pending or failed
    opening and closing announcements.

    Returns:
        int: Number of rounds transitioned to closed.
    """
    try:
        db = get_database()
    except Exception as exc:
        logger.debug("Database not yet connected for scheduler: %s", exc)
        return 0

    now = datetime.now(timezone.utc)
    rounds_col = db.order_rounds

    cursor = rounds_col.find({
        "status": "open",
        "deadline_at": {"$lte": now},
    })

    expired_rounds = await cursor.to_list(length=100)
    closed_count = 0

    pending_announcement = {
        "status": "pending",
        "attempts": 0,
        "last_attempt_at": None,
        "sent_at": None,
        "last_error": None,
    }

    for round_doc in expired_rounds:
        round_id = round_doc["_id"]
        society_id = round_doc["society_id"]
        round_number = round_doc.get("round_number", 1)

        # Atomic update strictly on status=open prevents duplicate closures or worker races
        updated = await rounds_col.find_one_and_update(
            {"_id": round_id, "status": "open"},
            {
                "$set": {
                    "status": "closed",
                    "closed_at": now,
                    "updated_at": now,
                    "closing_announcement": pending_announcement,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

        if updated:
            closed_count += 1
            logger.info(
                "Auto-closed expired grocery round #%s for society %s (Deadline was %s)",
                round_number,
                society_id,
                round_doc.get("deadline_at"),
            )

            # Publish Nexconn Closing Announcement
            await dispatch_closing_announcement(
                round_id=round_id,
                society_id=society_id,
                round_number=round_number,
                closed_at=now,
                is_automatic=True,
                current_attempts=0,
            )

    # 1. Recover pending or failed opening announcements on open rounds (bounded to 3 attempts)
    open_retry_cursor = rounds_col.find({
        "status": "open",
        "opening_announcement.status": {"$in": ["pending", "failed"]},
        "opening_announcement.attempts": {"$lt": 3},
    })
    open_retry_rounds = await open_retry_cursor.to_list(length=20)
    for o_doc in open_retry_rounds:
        o_id = o_doc["_id"]
        soc_id = o_doc["society_id"]
        o_num = o_doc.get("round_number", 1)
        o_title = o_doc.get("title", f"Round #{o_num}")
        o_deadline = o_doc.get("deadline_at")
        o_shop_date = str(o_doc.get("shopping_date", ""))
        o_attempts = int(o_doc.get("opening_announcement", {}).get("attempts", 0))

        # Atomic claim to prevent multi-worker duplicate retries
        claimed_open = await rounds_col.find_one_and_update(
            {
                "_id": o_id,
                "status": "open",
                "opening_announcement.status": {"$in": ["pending", "failed"]},
                "opening_announcement.attempts": o_attempts,
            },
            {
                "$set": {
                    "opening_announcement.status": "pending",
                    "opening_announcement.last_attempt_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if claimed_open:
            await dispatch_opening_announcement(
                round_id=o_id,
                society_id=soc_id,
                round_number=o_num,
                title=o_title,
                deadline_at=o_deadline,
                shopping_date=o_shop_date,
                current_attempts=o_attempts,
            )

    # 2. Recover pending or failed closing announcements on closed rounds (bounded to 3 attempts)
    retry_cursor = rounds_col.find({
        "status": "closed",
        "closing_announcement.status": {"$in": ["pending", "failed"]},
        "closing_announcement.attempts": {"$lt": 3},
    })
    retry_rounds = await retry_cursor.to_list(length=20)
    for r_doc in retry_rounds:
        r_id = r_doc["_id"]
        soc_id = r_doc["society_id"]
        r_num = r_doc.get("round_number", 1)
        r_closed = r_doc.get("closed_at", now)
        c_attempts = int(r_doc.get("closing_announcement", {}).get("attempts", 0))

        # Atomic claim to prevent multi-worker duplicate retries
        claimed = await rounds_col.find_one_and_update(
            {
                "_id": r_id,
                "closing_announcement.status": {"$in": ["pending", "failed"]},
                "closing_announcement.attempts": c_attempts,
            },
            {
                "$set": {
                    "closing_announcement.status": "pending",
                    "closing_announcement.last_attempt_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if claimed:
            await dispatch_closing_announcement(
                round_id=r_id,
                society_id=soc_id,
                round_number=r_num,
                closed_at=r_closed,
                is_automatic=True,
                current_attempts=c_attempts,
            )

    return closed_count


async def _run_scheduler_loop() -> None:
    """Continuous polling loop executing periodic expiration checks every 10 seconds."""
    logger.info("Started automatic round deadline scheduler loop.")
    while True:
        try:
            await check_expired_rounds_once()
        except asyncio.CancelledError:
            logger.info("Round deadline scheduler cancelled.")
            break
        except Exception as exc:
            logger.warning("Error in round deadline scheduler loop: %s", exc)

        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            break


def start_round_scheduler() -> Optional[asyncio.Task]:
    """Start the background scheduler task."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_run_scheduler_loop())
    return _scheduler_task


def stop_round_scheduler() -> None:
    """Stop and cancel the background scheduler task."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("Stopped round deadline scheduler.")
