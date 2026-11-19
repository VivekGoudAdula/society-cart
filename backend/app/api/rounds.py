"""FastAPI router for society grocery order rounds and resident submissions.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import get_current_active_user
from app.dependencies.permissions import (
    require_society_member,
    require_society_volunteer_or_admin,
)
from app.schemas.round import (
    CreateRoundRequest,
    CreateSubmissionRequest,
    RoundListResponse,
    RoundResponse,
    SubmissionResponse,
)
from app.schemas.user import UserResponse
from app.services import round_service

router = APIRouter(
    prefix="/societies/{society_id}/rounds",
    tags=["Grocery Rounds"],
)


@router.post(
    "",
    response_model=RoundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new grocery round (Draft)",
)
async def create_round(
    society_id: str,
    payload: CreateRoundRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> RoundResponse:
    """Create a new grocery order round in draft status.

    Requires volunteer or administrator privileges.
    """
    return await round_service.create_round(
        society_id=society_id,
        user_id=current_user.id,
        data=payload,
    )


@router.post(
    "/{round_id}/open",
    response_model=RoundResponse,
    summary="Open an active grocery round and broadcast announcement",
)
async def open_round(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> RoundResponse:
    """Transition a draft round to open status and broadcast the Nexconn group announcement.

    Requires volunteer or administrator privileges.
    """
    return await round_service.open_round(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
    )


@router.post(
    "/{round_id}/close",
    response_model=RoundResponse,
    summary="Close an active grocery round and broadcast announcement",
)
async def close_round(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> RoundResponse:
    """Close an active grocery round, disallowing further resident submissions.

    Requires volunteer or administrator privileges.
    """
    return await round_service.close_round(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
        is_automatic=False,
    )


@router.get(
    "/active",
    response_model=Optional[RoundResponse],
    summary="Get current active open round for society",
)
async def get_active_round(
    society_id: str,
    membership: Dict[str, Any] = Depends(require_society_member),
) -> Optional[RoundResponse]:
    """Retrieve the currently open round for this apartment society, or null if none active.

    Performs automatic on-demand expiration check. Requires active membership in this society.
    """
    return await round_service.get_active_round(society_id)


@router.get(
    "",
    response_model=RoundListResponse,
    summary="List past and present rounds for society",
)
async def list_rounds(
    society_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    membership: Dict[str, Any] = Depends(require_society_member),
) -> RoundListResponse:
    """Retrieve round history for the society with pagination. Requires active membership."""
    items, total = await round_service.list_rounds(society_id, skip=skip, limit=limit)
    return RoundListResponse(items=items, total=total)


@router.get(
    "/{round_id}",
    response_model=RoundResponse,
    summary="Get round details",
)
async def get_round(
    society_id: str,
    round_id: str,
    membership: Dict[str, Any] = Depends(require_society_member),
) -> RoundResponse:
    """Retrieve details of a specific round. Requires active membership in this society."""
    return await round_service.get_round_by_id(society_id, round_id)


@router.post(
    "/{round_id}/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Associate a resident grocery message with the round",
)
async def submit_grocery_order(
    society_id: str,
    round_id: str,
    payload: CreateSubmissionRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_member),
) -> SubmissionResponse:
    """Submit a grocery order linked to a Nexconn message into the specified round.

    Validates that the round is currently open and has not passed its deadline.
    """
    payload.round_id = round_id
    return await round_service.create_submission(
        society_id=society_id,
        user_id=current_user.id,
        flat_number=membership.get("flat_number", "Unknown"),
        user_name=current_user.name,
        data=payload,
    )


@router.get(
    "/{round_id}/submissions",
    response_model=List[SubmissionResponse],
    summary="List all grocery submissions for a round",
)
async def list_round_submissions(
    society_id: str,
    round_id: str,
    membership: Dict[str, Any] = Depends(require_society_member),
) -> List[SubmissionResponse]:
    """Retrieve all submissions registered for a given round. Requires active membership."""
    return await round_service.list_submissions(society_id, round_id)
