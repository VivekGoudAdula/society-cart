"""Membership service for listing society members and administrative role assignment.
"""

from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_memberships_collection, get_users_collection, get_societies_collection
from app.schemas.membership import MembershipResponse
from app.services.society_service import _serialize_membership
from app.services.nexconn_service import remove_resident_from_group


async def get_active_membership(user_id: str, society_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an active membership for a specific user and society.

    Args:
        user_id: User document ID.
        society_id: Society document ID.

    Returns:
        Optional[Dict[str, Any]]: Raw membership document if found and active.
    """
    col = get_memberships_collection()
    return await col.find_one({
        "user_id": user_id,
        "society_id": society_id,
        "is_active": True,
    })


async def list_society_members(society_id: str) -> List[MembershipResponse]:
    """Retrieve all active members of a society with user profile names.

    Args:
        society_id: Society document ID.

    Returns:
        List[MembershipResponse]: Formatted membership list with user metadata.
    """
    memberships_col = get_memberships_collection()
    users_col = get_users_collection()

    cursor = memberships_col.find({"society_id": society_id, "is_active": True})
    members = await cursor.to_list()

    results: List[MembershipResponse] = []
    for mem in members:
        uid = mem["user_id"]
        uq = {"_id": ObjectId(uid) if ObjectId.is_valid(uid) else uid}
        user_doc = await users_col.find_one(uq)
        name = user_doc.get("name") if user_doc else "Neighbor"
        email = user_doc.get("email") if user_doc else None
        results.append(_serialize_membership(mem, user_name=name, user_email=email))

    return results


async def assign_member_role(
    admin_user_id: str,
    society_id: str,
    target_membership_id: str,
    new_role: str,
) -> MembershipResponse:
    """Assign or revoke volunteer privileges. Admin-only operation.

    Args:
        admin_user_id: User executing the change.
        society_id: Society ID.
        target_membership_id: Target membership ID.
        new_role: 'volunteer' or 'resident'.

    Returns:
        MembershipResponse: Updated membership.

    Raises:
        HTTPException: 403 if requester is not admin; 404 if member not found.
    """
    admin_mem = await get_active_membership(admin_user_id, society_id)
    if not admin_mem or admin_mem.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only society administrators can assign volunteer roles.",
        )

    col = get_memberships_collection()
    mq = {
        "_id": ObjectId(target_membership_id) if ObjectId.is_valid(target_membership_id) else target_membership_id,
        "society_id": society_id,
        "is_active": True,
    }

    target_mem = await col.find_one(mq)
    if not target_mem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society member not found.",
        )

    if target_mem.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reassign the society administrator role.",
        )

    await col.update_one(mq, {"$set": {"role": new_role}})
    updated_doc = await col.find_one(mq)
    return _serialize_membership(updated_doc)


async def deactivate_membership(
    admin_user_id: str,
    society_id: str,
    target_membership_id: str,
) -> None:
    """Deactivate a society membership. Admin-only operation.

    Args:
        admin_user_id: Admin user ID.
        society_id: Society ID.
        target_membership_id: Target membership ID.

    Raises:
        HTTPException: 403 if not admin; 400 if trying to deactivate self or admin.
    """
    admin_mem = await get_active_membership(admin_user_id, society_id)
    if not admin_mem or admin_mem.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only society administrators can remove members.",
        )

    col = get_memberships_collection()
    mq = {
        "_id": ObjectId(target_membership_id) if ObjectId.is_valid(target_membership_id) else target_membership_id,
        "society_id": society_id,
        "is_active": True,
    }

    target_mem = await col.find_one(mq)
    if not target_mem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society member not found.",
        )

    if target_mem["user_id"] == admin_user_id or target_mem.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own membership.",
        )

    await col.update_one(mq, {"$set": {"is_active": False}})

    # Synchronize group membership revocation with Nexconn
    societies_col = get_societies_collection()
    society_oid = ObjectId(society_id) if ObjectId.is_valid(society_id) else society_id
    society_doc = await societies_col.find_one({"_id": society_oid})
    group_id = (society_doc or {}).get("nexconn_group_id") or f"society_{society_id}"
    await remove_resident_from_group(target_mem["user_id"], group_id)
