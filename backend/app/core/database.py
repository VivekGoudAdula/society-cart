"""Database connection and index management using PyMongo Async API.
"""

import asyncio
import logging
from typing import Optional
from pymongo import AsyncMongoClient, ASCENDING
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_mongo_client: Optional[AsyncMongoClient] = None
_client_loop: Optional[asyncio.AbstractEventLoop] = None


async def get_or_create_client() -> Optional[AsyncMongoClient]:
    """Get or create the AsyncMongoClient bound to the current running asyncio loop.

    Avoids cross-loop errors during automated testing.
    """
    global _mongo_client, _client_loop
    if not settings.mongodb_uri:
        logger.warning("MONGODB_URI is not set. Database connection skipped.")
        return None

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _mongo_client is None or (_client_loop is not None and current_loop != _client_loop):
        if _mongo_client is not None:
            try:
                await _mongo_client.close()
            except Exception:
                pass
        _mongo_client = AsyncMongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
        )
        _client_loop = current_loop
        logger.info("Initialized AsyncMongoClient bound to active event loop.")

    return _mongo_client


async def connect_to_mongo() -> Optional[AsyncDatabase]:
    """Initialize the asynchronous MongoDB client and configure indexes.

    Returns:
        Optional[AsyncDatabase]: Connected database instance or None.
    """
    client = await get_or_create_client()
    if client is None:
        return None

    db = client[settings.mongodb_database]
    await init_db_indexes(db)
    return db


async def close_mongo_connection() -> None:
    """Close the active MongoDB client connection on application shutdown."""
    global _mongo_client, _client_loop
    if _mongo_client is not None:
        try:
            await _mongo_client.close()
        except Exception:
            pass
        _mongo_client = None
        _client_loop = None
        logger.info("Closed MongoDB connection.")


async def init_db_indexes(db: AsyncDatabase) -> None:
    """Create essential unique and query indexes across core collections.

    Args:
        db: Active AsyncDatabase instance.
    """
    try:
        # Users Collection: Unique normalized email
        await db.users.create_index(
            [("email", ASCENDING)],
            unique=True,
            name="idx_users_email_unique",
        )

        # Societies Collection: Unique invite code
        await db.societies.create_index(
            [("invite_code", ASCENDING)],
            unique=True,
            name="idx_societies_invite_code_unique",
        )

        # Memberships Collection:
        # 1. Prevent duplicate active memberships for a user in the same society
        await db.memberships.create_index(
            [("user_id", ASCENDING), ("society_id", ASCENDING)],
            unique=True,
            partialFilterExpression={"is_active": True},
            name="idx_memberships_user_society_active_unique",
        )

        # 2. Prevent duplicate active residents in the same flat in the same society
        await db.memberships.create_index(
            [("society_id", ASCENDING), ("flat_number", ASCENDING)],
            unique=True,
            partialFilterExpression={"is_active": True},
            name="idx_memberships_society_flat_active_unique",
        )

        # 3. Fast lookup indexes for society and user queries
        await db.memberships.create_index(
            [("society_id", ASCENDING)],
            name="idx_memberships_society_id",
        )
        await db.memberships.create_index(
            [("user_id", ASCENDING)],
            name="idx_memberships_user_id",
        )

        # Order Rounds Collection:
        # 1. Partial unique index: strictly prevent multiple simultaneous OPEN rounds per society
        await db.order_rounds.create_index(
            [("society_id", ASCENDING)],
            unique=True,
            partialFilterExpression={"status": "open"},
            name="idx_order_rounds_society_open_unique",
        )

        # 2. Strict unique index: prevent duplicate round numbers within a society under concurrency
        await db.order_rounds.create_index(
            [("society_id", ASCENDING), ("round_number", ASCENDING)],
            unique=True,
            name="idx_order_rounds_society_round_unique",
        )

        # 3. Sequential round numbering and society lookup
        await db.order_rounds.create_index(
            [("society_id", ASCENDING), ("round_number", -1)],
            name="idx_order_rounds_society_number",
        )

        # 4. Fast expired round detection for automatic scheduler
        await db.order_rounds.create_index(
            [("status", ASCENDING), ("deadline_at", ASCENDING)],
            name="idx_order_rounds_status_deadline",
        )

        # Grocery Submissions Collection:
        # 1. Scope submissions by society and round
        await db.grocery_submissions.create_index(
            [("society_id", ASCENDING), ("round_id", ASCENDING)],
            name="idx_submissions_society_round",
        )

        # 2. User submission lookup for privacy filtering
        await db.grocery_submissions.create_index(
            [("round_id", ASCENDING), ("user_id", ASCENDING)],
            name="idx_submissions_round_user",
        )

        # 3. Flat lookup within round
        await db.grocery_submissions.create_index(
            [("round_id", ASCENDING), ("flat_number", ASCENDING)],
            name="idx_submissions_round_flat",
        )

        # 4. Client submission ID unique constraint for race-safe reservation
        await db.grocery_submissions.create_index(
            [("submission_id", ASCENDING)],
            unique=True,
            sparse=True,
            name="idx_submissions_client_id_unique",
        )

        # 5. Link by real Nexconn message ID - partial unique index on non-null message_id
        await db.grocery_submissions.create_index(
            [("message_id", ASCENDING)],
            unique=True,
            partialFilterExpression={"message_id": {"$type": "string"}},
            name="idx_submissions_message_id_unique",
        )

        # Grocery Orders Collection (Structured AI Interpretations):
        # 1. Strict 1:1 mapping between submission and structured order - prevents duplicate AI processing
        await db.grocery_orders.create_index(
            [("submission_id", ASCENDING)],
            unique=True,
            name="idx_orders_submission_unique",
        )

        # 2. Scope orders by society and round
        await db.grocery_orders.create_index(
            [("society_id", ASCENDING), ("round_id", ASCENDING)],
            name="idx_orders_society_round",
        )

        # 3. Fast resident lookup within round
        await db.grocery_orders.create_index(
            [("round_id", ASCENDING), ("user_id", ASCENDING)],
            name="idx_orders_round_user",
        )

        # 4. Status lookup for pending confirmations
        await db.grocery_orders.create_index(
            [("user_id", ASCENDING), ("status", ASCENDING)],
            name="idx_orders_user_status",
        )
    except Exception as exc:
        logger.warning("Database index check: %s", exc)


def get_database() -> AsyncDatabase:
    """Return the active database instance.

    Returns:
        AsyncDatabase: Application database.

    Raises:
        RuntimeError: If database is not connected.
    """
    global _mongo_client, _client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _mongo_client is None or (_client_loop is not None and current_loop != _client_loop):
        if not settings.mongodb_uri:
            raise RuntimeError("MONGODB_URI is not set. Database is unavailable.")
        _mongo_client = AsyncMongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
        )
        _client_loop = current_loop

    return _mongo_client[settings.mongodb_database]


def get_users_collection() -> AsyncCollection:
    """Return the users collection."""
    return get_database().users


def get_societies_collection() -> AsyncCollection:
    """Return the societies collection."""
    return get_database().societies


def get_memberships_collection() -> AsyncCollection:
    """Return the memberships collection."""
    return get_database().memberships


def get_order_rounds_collection() -> AsyncCollection:
    """Return the order_rounds collection."""
    return get_database().order_rounds


def get_grocery_submissions_collection() -> AsyncCollection:
    """Return the grocery_submissions collection."""
    return get_database().grocery_submissions


def get_grocery_orders_collection() -> AsyncCollection:
    """Return the grocery_orders collection for structured AI interpretations."""
    return get_database().grocery_orders
