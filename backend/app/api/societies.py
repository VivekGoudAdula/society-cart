"""Society and membership management endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies.auth import get_current_active_user
from app.dependencies.permissions import require_society_member, require_society_admin
from app.schemas.membership import AssignRoleRequest, MembershipResponse
from app.schemas.society import (
    SocietyCreateRequest,
    SocietyJoinRequest,
    SocietyResponse,
    UserSocietyMembershipResponse,
)
from app.schemas.user import UserResponse
from app.services.membership_service import (
    assign_member_role,
    deactivate_membership,
    list_society_members,
)
from app.services.society_service import (
    create_society,
    get_society_by_id,
    get_user_societies,
    join_society,
)

router = APIRouter(prefix="/societies", tags=["Societies"])


@router.post("", response_model=UserSocietyMembershipResponse, status_code=status.HTTP_201_CREATED)
async def create_new_society(
    request: SocietyCreateRequest,
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserSocietyMembershipResponse:
    """Create a new apartment society. The creator automatically receives the admin role."""
    return await create_society(current_user.id, request)


@router.post("/join", response_model=UserSocietyMembershipResponse)
async def join_existing_society(
    request: SocietyJoinRequest,
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserSocietyMembershipResponse:
    """Join an apartment society as a resident using a valid invite code."""
    return await join_society(current_user.id, request)


@router.get("/my", response_model=List[UserSocietyMembershipResponse])
async def get_my_societies(
    current_user: UserResponse = Depends(get_current_active_user),
) -> List[UserSocietyMembershipResponse]:
    """Retrieve all societies the authenticated user belongs to with flat and role details."""
    return await get_user_societies(current_user.id)


@router.get("/{society_id}", response_model=SocietyResponse)
async def get_society_details(
    society_id: str,
    _membership=Depends(require_society_member),
) -> SocietyResponse:
    """Retrieve details of a society. User must be an active member of the society."""
    society = await get_society_by_id(society_id)
    if not society:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society not found.",
        )
    return society


@router.get("/{society_id}/members", response_model=List[MembershipResponse])
async def get_society_members(
    society_id: str,
    _membership=Depends(require_society_member),
) -> List[MembershipResponse]:
    """List all active members of the society."""
    return await list_society_members(society_id)


@router.patch("/{society_id}/members/{membership_id}/role", response_model=MembershipResponse)
async def update_member_role(
    society_id: str,
    membership_id: str,
    request: AssignRoleRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    _admin_check=Depends(require_society_admin),
) -> MembershipResponse:
    """Assign or revoke the volunteer role for a society member. Only admins can execute this."""
    return await assign_member_role(
        admin_user_id=current_user.id,
        society_id=society_id,
        target_membership_id=membership_id,
        new_role=request.role,
    )


@router.delete("/{society_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_society_member(
    society_id: str,
    membership_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    _admin_check=Depends(require_society_admin),
) -> None:
    """Deactivate a society member. Only administrators can execute this."""
    await deactivate_membership(
        admin_user_id=current_user.id,
        society_id=society_id,
        target_membership_id=membership_id,
    )
