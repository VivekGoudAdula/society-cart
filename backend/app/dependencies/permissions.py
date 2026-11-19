"""Role-based access control (RBAC) dependencies for society operations.
"""

from typing import Any, Dict
from fastapi import Depends, HTTPException, Path, status
from app.dependencies.auth import get_current_active_user
from app.schemas.user import UserResponse
from app.services.membership_service import get_active_membership


async def require_society_member(
    society_id: str = Path(..., description="Target apartment society ID"),
    current_user: UserResponse = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Verify that the current authenticated user is an active member of the society.

    Args:
        society_id: Target society ID from URL path.
        current_user: Resolved authenticated user.

    Returns:
        Dict[str, Any]: Membership document.

    Raises:
        HTTPException: 403 Forbidden if user is not a member of this society.
    """
    membership = await get_active_membership(current_user.id, society_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this apartment society.",
        )
    return membership


async def require_society_admin(
    society_id: str = Path(..., description="Target apartment society ID"),
    current_user: UserResponse = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Verify that the current authenticated user is an active administrator of the society.

    Args:
        society_id: Target society ID from URL path.
        current_user: Resolved authenticated user.

    Returns:
        Dict[str, Any]: Admin membership document.

    Raises:
        HTTPException: 403 Forbidden if user is not an administrator.
    """
    membership = await get_active_membership(current_user.id, society_id)
    if not membership or membership.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Society administrator privileges are required for this action.",
        )
    return membership
