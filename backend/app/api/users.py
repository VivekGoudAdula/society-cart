"""Resident profile endpoints.
"""

from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_active_user
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.user_service import update_user_profile

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserResponse:
    """Retrieve the authenticated user's profile information."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    updates: UserUpdateRequest,
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserResponse:
    """Update allowed profile attributes (name, phone).

    Protected fields like password hash, roles, and IDs cannot be changed through this endpoint.
    """
    updated_user = await update_user_profile(current_user.id, updates)
    return updated_user or current_user
