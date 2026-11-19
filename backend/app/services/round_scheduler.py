"""Background scheduler for automatic deadline enforcement on active grocery rounds.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional
from pymongo import ReturnDocument

from app.core.database import get_database, get_societies_collection
from app.services.nexconn_service import send_system_bot_message

logger = logging.getLogger(__name__)

_scheduler_task: Optional[asyncio.Task] = None


async def check_expired_rounds_once() -> int:
    """Find and automatically close any open grocery rounds whose deadlines have expired.

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

    for round_doc in expired_rounds:
        round_id = round_doc["_id"]
        society_id = round_doc["society_id"]
        round_number = round_doc.get("round_number", 1)

        # Atomic update to prevent duplicate closures or races
        updated = await rounds_col.find_one_and_update(
            {"_id": round_id, "status": "open"},
            {
                "$set": {
                    "status": "closed",
                    "closed_at": now,
                    "updated_at": now,
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

            # Publish Nexconn Closing Announcement if not sent yet
            if not updated.get("closing_announcement_sent", False):
                try:
                    soc = await get_societies_collection().find_one({"_id": society_id})
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
                        "closed_at": now.isoformat(),
                        "is_automatic": True,
                    }
                    sent = await send_system_bot_message(group_id, announcement_text, extra)
                    if sent:
                        await rounds_col.update_one(
                            {"_id": round_id},
                            {"$set": {"closing_announcement_sent": True}},
                        )
                except Exception as ann_exc:
                    logger.warning("Error publishing auto-close announcement: %s", ann_exc)

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
