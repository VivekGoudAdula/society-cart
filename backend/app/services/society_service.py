"""Society service for community creation, joining, and membership querying.
"""

from datetime import datetime, timezone
import random
import string
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError
from app.core.database import get_societies_collection, get_memberships_collection
from app.schemas.society import (
    SocietyCreateRequest,
    SocietyJoinRequest,
    SocietyResponse,
    UserSocietyMembershipResponse,
)
from app.schemas.membership import MembershipResponse
from app.services.nexconn_service import create_nexconn_group, add_resident_to_group


def _serialize_society(doc: Dict[str, Any]) -> SocietyResponse:
    """Format raw MongoDB society document into SocietyResponse schema."""
    return SocietyResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        address=doc["address"],
        city=doc["city"],
        state=doc.get("state"),
        country=doc.get("country", "India"),
        invite_code=doc["invite_code"],
        created_by=str(doc["created_by"]),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
        is_active=doc.get("is_active", True),
        total_flats=doc.get("total_flats"),
        nexconn_group_id=doc.get("nexconn_group_id"),
    )


def _serialize_membership(doc: Dict[str, Any], user_name: Optional[str] = None, user_email: Optional[str] = None) -> MembershipResponse:
    """Format raw MongoDB membership document into MembershipResponse schema."""
    return MembershipResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        society_id=str(doc["society_id"]),
        flat_number=doc["flat_number"],
        role=doc["role"],
        joined_at=doc.get("joined_at", datetime.now(timezone.utc)),
        is_active=doc.get("is_active", True),
        user_name=user_name,
        user_email=user_email,
    )


async def generate_unique_invite_code(society_name: str) -> str:
    """Generate a clean, readable, unique 8-character society invite code.

    Format: ABC-1234 (based on society name initials + random digits).
    """
    col = get_societies_collection()
    initials = "".join([w[0].upper() for w in society_name.split() if w.isalnum()])[:3]
    if len(initials) < 2:
        initials = "SC"

    for _ in range(20):
        random_suffix = "".join(random.choices(string.digits + string.ascii_uppercase, k=4))
        candidate = f"{initials}-{random_suffix}"
        existing = await col.find_one({"invite_code": candidate})
        if not existing:
            return candidate

    fallback = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"SC-{fallback}"


async def create_society(
    user_id: str,
    request: SocietyCreateRequest,
) -> UserSocietyMembershipResponse:
    """Create a new apartment society and grant admin role to the creator.

    Args:
        user_id: Authenticated user ID creating the society.
        request: Validated society creation parameters.

    Returns:
        UserSocietyMembershipResponse: Created society and creator's admin membership.
    """
    societies_col = get_societies_collection()
    memberships_col = get_memberships_collection()

    invite_code = await generate_unique_invite_code(request.name)
    now = datetime.now(timezone.utc)

    society_oid = ObjectId()
    society_id_str = str(society_oid)
    nexconn_group_id = f"society_{society_id_str}"

    society_doc = {
        "_id": society_oid,
        "name": request.name.strip(),
        "address": request.address.strip(),
        "city": request.city.strip(),
        "state": request.state.strip() if request.state else None,
        "country": request.country.strip(),
        "total_flats": request.total_flats,
        "invite_code": invite_code,
        "created_by": user_id,
        "created_at": now,
        "is_active": True,
        "nexconn_group_id": nexconn_group_id,
    }

    await societies_col.insert_one(society_doc)

    # Provision private group channel on Nexconn network
    await create_nexconn_group(
        group_id=nexconn_group_id,
        group_name=society_doc["name"],
        creator_user_id=user_id,
    )

    # Create admin membership for the creator
    normalized_flat = request.creator_flat_number.strip().upper()
    membership_doc = {
        "user_id": user_id,
        "society_id": society_id_str,
        "flat_number": normalized_flat,
        "role": "admin",
        "joined_at": now,
        "is_active": True,
    }

    res_mem = await memberships_col.insert_one(membership_doc)
    membership_doc["_id"] = res_mem.inserted_id

    # Synchronize user to society Nexconn group channel
    group_id = society_doc.get("nexconn_group_id") or f"society_{society_id_str}"
    await add_resident_to_group(user_id, group_id, society_doc["name"])

    return UserSocietyMembershipResponse(
        society=_serialize_society(society_doc),
        membership=_serialize_membership(membership_doc),
    )


async def join_society(
    user_id: str,
    request: SocietyJoinRequest,
) -> UserSocietyMembershipResponse:
    """Join an apartment society using a valid invite code.

    Args:
        user_id: Authenticated user ID.
        request: Invite code and flat number.

    Returns:
        UserSocietyMembershipResponse: Joined society and resident membership.

    Raises:
        HTTPException: 404 if invite code is invalid; 409 if already member or flat occupied.
    """
    societies_col = get_societies_collection()
    memberships_col = get_memberships_collection()

    clean_code = request.invite_code.strip().upper()
    society_doc = await societies_col.find_one({"invite_code": clean_code, "is_active": True})

    if not society_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid society invitation code. Please check and try again.",
        )

    society_id_str = str(society_doc["_id"])
    normalized_flat = request.flat_number.strip().upper()

    # 1. Check if user is already an active member of this society
    existing_user_membership = await memberships_col.find_one({
        "user_id": user_id,
        "society_id": society_id_str,
        "is_active": True,
    })
    if existing_user_membership:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already an active member of this society.",
        )

    # 2. Check if flat number is already occupied by an active resident in this society
    occupied_flat = await memberships_col.find_one({
        "society_id": society_id_str,
        "flat_number": normalized_flat,
        "is_active": True,
    })
    if occupied_flat:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Flat {normalized_flat} is already registered by another resident in this society.",
        )

    # 3. Validate requested role and enforce single active volunteer rule
    requested_role = (request.role or "resident").strip().lower()
    if requested_role not in ("resident", "volunteer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. You can only join as 'resident' or 'volunteer'.",
        )

    if requested_role == "volunteer":
        existing_volunteer = await memberships_col.find_one({
            "society_id": society_id_str,
            "role": "volunteer",
            "is_active": True,
        })
        if existing_volunteer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This society already has an active volunteer. You can join as a resident.",
            )

    now = datetime.now(timezone.utc)
    membership_doc = {
        "user_id": user_id,
        "society_id": society_id_str,
        "flat_number": normalized_flat,
        "role": requested_role,
        "joined_at": now,
        "is_active": True,
    }

    try:
        res_mem = await memberships_col.insert_one(membership_doc)
        membership_doc["_id"] = res_mem.inserted_id
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Membership conflict. Either you already belong to this society or the flat is occupied.",
        )

    # Synchronize user to society Nexconn group channel
    group_id = society_doc.get("nexconn_group_id") or f"society_{society_id_str}"
    await add_resident_to_group(user_id, group_id, society_doc["name"])

    return UserSocietyMembershipResponse(
        society=_serialize_society(society_doc),
        membership=_serialize_membership(membership_doc),
    )


async def get_user_societies(user_id: str) -> List[UserSocietyMembershipResponse]:
    """Retrieve all societies where the user has an active membership.

    Args:
        user_id: Authenticated user ID.

    Returns:
        List[UserSocietyMembershipResponse]: List of societies paired with membership.
    """
    memberships_col = get_memberships_collection()
    societies_col = get_societies_collection()

    cursor = memberships_col.find({"user_id": user_id, "is_active": True})
    active_memberships = await cursor.to_list()

    results: List[UserSocietyMembershipResponse] = []
    for mem in active_memberships:
        soc_id = mem["society_id"]
        q = {"_id": ObjectId(soc_id) if ObjectId.is_valid(soc_id) else soc_id, "is_active": True}
        soc_doc = await societies_col.find_one(q)
        if soc_doc:
            results.append(
                UserSocietyMembershipResponse(
                    society=_serialize_society(soc_doc),
                    membership=_serialize_membership(mem),
                )
            )

    return results


async def get_society_by_id(society_id: str) -> Optional[SocietyResponse]:
    """Find an active society by its document ID.

    Args:
        society_id: Society ID string.

    Returns:
        Optional[SocietyResponse]: Society details if found.
    """
    col = get_societies_collection()
    q = {"is_active": True}
    if ObjectId.is_valid(society_id):
        q["_id"] = ObjectId(society_id)
    else:
        q["_id"] = society_id

    doc = await col.find_one(q)
    return _serialize_society(doc) if doc else None
