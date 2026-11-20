"""FastAPI router for society volunteer shopping dashboard, compilation, and CSV export.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.dependencies.auth import get_current_active_user
from app.dependencies.permissions import require_society_volunteer_or_admin
from app.schemas.shopping_list import (
    CompiledShoppingListResponse,
    UnresolvedOrderInfo,
)
from app.schemas.user import UserResponse
from app.services import shopping_list_service

router = APIRouter(
    prefix="/societies/{society_id}/rounds/{round_id}/shopping-list",
    tags=["Volunteer Shopping Dashboard"],
)


@router.post(
    "/compile",
    response_model=CompiledShoppingListResponse,
    summary="Compile or recompile the consolidated shopping list",
)
async def compile_shopping_list(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> CompiledShoppingListResponse:
    """Compile or recompile the consolidated shopping manifest for a society grocery round.

    Rules:
    - Only confirmed orders from this society and round are aggregated.
    - Safe unit normalization and strict category grouping.
    - Generates flat-wise packing breakdown.
    - Requires volunteer or administrator privileges.
    """
    return await shopping_list_service.compile_shopping_list(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
    )


@router.get(
    "",
    response_model=CompiledShoppingListResponse,
    summary="Retrieve the compiled shopping list",
)
async def get_shopping_list(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> CompiledShoppingListResponse:
    """Retrieve the current compiled shopping list and packing breakdown for a round.

    Requires volunteer or administrator privileges.
    """
    shopping_list = await shopping_list_service.get_shopping_list(
        society_id=society_id,
        round_id=round_id,
    )
    if not shopping_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list has not been compiled yet for this round.",
        )
    return shopping_list


@router.get(
    "/unresolved",
    response_model=List[UnresolvedOrderInfo],
    summary="List unresolved or unconfirmed resident orders for a round",
)
async def get_unresolved_orders(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> List[UnresolvedOrderInfo]:
    """Retrieve list of orders still in pending_review, needs_clarification, processing, or failed state.

    Requires volunteer or administrator privileges.
    """
    return await shopping_list_service.get_unresolved_orders(
        society_id=society_id,
        round_id=round_id,
    )


@router.get(
    "/export",
    summary="Export shopping list or packing breakdown as CSV",
)
async def export_shopping_list(
    society_id: str,
    round_id: str,
    type: str = Query("consolidated", pattern="^(consolidated|packing)$", description="Export type: consolidated or packing"),
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> Response:
    """Download RFC 4180 compliant CSV of the compiled bulk shopping list or flat-wise packing manifest.

    Requires volunteer or administrator privileges.
    """
    shopping_list = await shopping_list_service.get_shopping_list(
        society_id=society_id,
        round_id=round_id,
    )
    if not shopping_list:
        # Auto-compile if not yet compiled for convenience on export
        shopping_list = await shopping_list_service.compile_shopping_list(
            society_id=society_id,
            round_id=round_id,
            user_id=current_user.id,
        )

    csv_data = shopping_list_service.export_shopping_list_csv(
        shopping_list=shopping_list,
        export_type=type,
    )

    filename = f"shopping_list_round_{shopping_list.round_number}_{type}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
