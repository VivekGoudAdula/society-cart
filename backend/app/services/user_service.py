"""User service for profile queries and updates.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from bson import ObjectId
from app.core.database import get_users_collection
from app.schemas.user import UserResponse, UserUpdateRequest


def _serialize_user(doc: Dict[str, Any]) -> UserResponse:
    """Format raw MongoDB user document to public UserResponse schema."""
    return UserResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        phone=doc.get("phone"),
        is_active=doc.get("is_active", True),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
    )


async def get_user_by_id(user_id: str) -> Optional[UserResponse]:
    """Retrieve an active user by their document ID.

    Args:
        user_id: User document ID.

    Returns:
        Optional[UserResponse]: User if found and active, None otherwise.
    """
    col = get_users_collection()
    query = {"is_active": True}
    if ObjectId.is_valid(user_id):
        query["_id"] = ObjectId(user_id)
    else:
        query["_id"] = user_id

    doc = await col.find_one(query)
    return _serialize_user(doc) if doc else None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve raw user document by normalized email (includes password_hash).

    Args:
        email: Raw email string.

    Returns:
        Optional[Dict[str, Any]]: Full user document or None.
    """
    col = get_users_collection()
    normalized = email.strip().lower()
    return await col.find_one({"email": normalized})


async def update_user_profile(user_id: str, updates: UserUpdateRequest) -> Optional[UserResponse]:
    """Update non-sensitive user profile fields (name, phone).

    Args:
        user_id: Target user ID.
        updates: Permitted update fields.

    Returns:
        Optional[UserResponse]: Updated user profile.
    """
    col = get_users_collection()
    update_data: Dict[str, Any] = {}
    if updates.name is not None:
        update_data["name"] = updates.name.strip()
    if updates.phone is not None:
        update_data["phone"] = updates.phone.strip()

    if not update_data:
        return await get_user_by_id(user_id)

    update_data["updated_at"] = datetime.now(timezone.utc)
    query = {"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id}

    await col.update_one(query, {"$set": update_data})
    return await get_user_by_id(user_id)
