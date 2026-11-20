"""FastAPI router for structured AI grocery orders, clarifications, and confirmations.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_active_user
from app.dependencies.permissions import require_society_member
from app.schemas.order import (
    ClarifyOrderRequest,
    GroceryOrderResponse,
    UpdateOrderItemsRequest,
)
from app.schemas.user import UserResponse
from app.services import order_service

router = APIRouter(tags=["Grocery Orders"])


@router.get(
    "/societies/{society_id}/rounds/{round_id}/orders",
    response_model=List[GroceryOrderResponse],
    summary="List structured grocery orders for a round",
)
async def list_round_orders(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_member),
) -> List[GroceryOrderResponse]:
    """Retrieve structured grocery orders for an apartment round.

    Privacy Enforcement:
    - Residents see only their own orders.
    - Volunteers and Admins see all orders in the society round.
    """
    return await order_service.list_orders_for_round(
        society_id=society_id,
        round_id=round_id,
        caller_user_id=current_user.id,
        caller_role=membership.get("role", "resident"),
    )


@router.get(
    "/orders/{order_id}",
    response_model=GroceryOrderResponse,
    summary="Get single grocery order details",
)
async def get_order(
    order_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
) -> GroceryOrderResponse:
    """Retrieve details of a specific grocery order.

    Requires authentication and order ownership or volunteer/admin privileges.
    """
    return await order_service.get_order_by_id(
        order_id=order_id,
        caller_user_id=current_user.id,
        caller_role="resident",  # Base check; service layer looks up membership if needed
    )


@router.post(
    "/orders/{order_id}/clarify",
    response_model=GroceryOrderResponse,
    summary="Submit resident clarification for ambiguous items",
)
async def clarify_order(
    order_id: str,
    payload: ClarifyOrderRequest,
    current_user: UserResponse = Depends(get_current_active_user),
) -> GroceryOrderResponse:
    """Submit resident clarification response (e.g. specifying missing quantity or brand)."""
    return await order_service.clarify_order(
        order_id=order_id,
        caller_user_id=current_user.id,
        caller_role="resident",
        clarification_text=payload.clarification_text,
    )


@router.patch(
    "/orders/{order_id}/items",
    response_model=GroceryOrderResponse,
    summary="Manually adjust or correct grocery order items",
)
async def update_order_items(
    order_id: str,
    payload: UpdateOrderItemsRequest,
    current_user: UserResponse = Depends(get_current_active_user),
) -> GroceryOrderResponse:
    """Allow residents to edit quantities, units, item names, or add/remove items."""
    return await order_service.update_order_items(
        order_id=order_id,
        caller_user_id=current_user.id,
        caller_role="resident",
        items=payload.items,
    )


@router.post(
    "/orders/{order_id}/confirm",
    response_model=GroceryOrderResponse,
    summary="Resident explicitly confirms structured grocery order",
)
async def confirm_order(
    order_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
) -> GroceryOrderResponse:
    """Resident confirms that the AI interpretation of their order is accurate."""
    return await order_service.confirm_order(
        order_id=order_id,
        caller_user_id=current_user.id,
        caller_role="resident",
    )


@router.post(
    "/orders/{order_id}/reject",
    response_model=GroceryOrderResponse,
    summary="Resident explicitly rejects structured grocery order",
)
async def reject_order(
    order_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
) -> GroceryOrderResponse:
    """Resident rejects the interpretation (cancels the extracted order)."""
    return await order_service.reject_order(
        order_id=order_id,
        caller_user_id=current_user.id,
        caller_role="resident",
    )


@router.post(
    "/orders/{order_id}/retry",
    response_model=GroceryOrderResponse,
    summary="Retry AI extraction for a failed or interrupted order",
)
async def retry_order(
    order_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
) -> GroceryOrderResponse:
    """Allow resident owner to retry AI extraction."""
    return await order_service.retry_ai_extraction(
        order_id=order_id,
        caller_user_id=current_user.id,
    )
