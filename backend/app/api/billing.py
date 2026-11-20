"""FastAPI router for Phase 7: Purchases, Allocations, Grocery Bills, and Savings.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_current_active_user
from app.dependencies.permissions import (
    require_society_member,
    require_society_volunteer_or_admin,
)
from app.schemas.billing import (
    AllocationPreviewResponse,
    CorrectBillRequest,
    FinalizeBillsRequest,
    GroceryBillResponse,
    PublishBillsAnnouncementResponse,
    PurchaseRecordResponse,
    RecordBenchmarkRequest,
    RecordPurchaseRequest,
    RetailBenchmarkResponse,
    SocietySavingsSummaryResponse,
    SocietySpendingSummaryResponse,
    UpdatePurchaseRequest,
)
from app.schemas.user import UserResponse
from app.services import billing_service

router = APIRouter(tags=["Billing & Savings"])


# ============================================================================
# Volunteer / Admin: Purchase Recording
# ============================================================================

@router.post(
    "/societies/{society_id}/rounds/{round_id}/purchases",
    response_model=PurchaseRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an actual grocery purchase",
)
async def record_purchase(
    society_id: str,
    round_id: str,
    req: RecordPurchaseRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> PurchaseRecordResponse:
    """Record an actual grocery purchase made by a volunteer."""
    return await billing_service.record_purchase(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
        req=req,
    )


@router.get(
    "/societies/{society_id}/rounds/{round_id}/purchases",
    response_model=List[PurchaseRecordResponse],
    summary="List all recorded purchases for a round",
)
async def list_purchases(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> List[PurchaseRecordResponse]:
    """List all purchases recorded for this grocery round."""
    return await billing_service.list_purchases(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
    )


@router.patch(
    "/societies/{society_id}/rounds/{round_id}/purchases/{purchase_id}",
    response_model=PurchaseRecordResponse,
    summary="Update an unfinalized purchase record",
)
async def update_purchase(
    society_id: str,
    round_id: str,
    purchase_id: str,
    req: UpdatePurchaseRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> PurchaseRecordResponse:
    """Update an unfinalized purchase record before bills are finalized."""
    return await billing_service.update_purchase(
        society_id=society_id,
        round_id=round_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
        req=req,
    )


@router.delete(
    "/societies/{society_id}/rounds/{round_id}/purchases/{purchase_id}",
    summary="Delete an unfinalized purchase record",
)
async def delete_purchase(
    society_id: str,
    round_id: str,
    purchase_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> Dict[str, str]:
    """Delete an unfinalized purchase record."""
    return await billing_service.delete_purchase(
        society_id=society_id,
        round_id=round_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
    )


# ============================================================================
# Volunteer / Admin: Allocation Preview & Bill Finalization
# ============================================================================

@router.get(
    "/societies/{society_id}/rounds/{round_id}/allocation/preview",
    response_model=AllocationPreviewResponse,
    summary="Preview per-flat cost allocation and purchase reconciliation",
)
async def get_allocation_preview(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> AllocationPreviewResponse:
    """Calculate and preview per-flat cost allocation and purchase reconciliation."""
    return await billing_service.calculate_allocation(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
    )


@router.post(
    "/societies/{society_id}/rounds/{round_id}/bills/finalize",
    response_model=List[GroceryBillResponse],
    summary="Finalize and create immutable bills for all flats",
)
async def finalize_bills(
    society_id: str,
    round_id: str,
    req: FinalizeBillsRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> List[GroceryBillResponse]:
    """Finalize all bills for the round. Requires purchase-cost reconciliation."""
    return await billing_service.finalize_bills(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
        req=req,
    )


@router.get(
    "/societies/{society_id}/rounds/{round_id}/bills",
    response_model=List[GroceryBillResponse],
    summary="List all finalized bills for a round",
)
async def get_round_bills(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> List[GroceryBillResponse]:
    """Retrieve all finalized bills for the round."""
    return await billing_service.get_round_bills(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
    )


@router.post(
    "/societies/{society_id}/rounds/{round_id}/bills/{bill_id}/correct",
    response_model=GroceryBillResponse,
    summary="Create a corrected version of a finalized bill",
)
async def correct_bill(
    society_id: str,
    round_id: str,
    bill_id: str,
    req: CorrectBillRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> GroceryBillResponse:
    """Create a corrected version of an existing bill, preserving audit history."""
    return await billing_service.correct_bill(
        society_id=society_id,
        round_id=round_id,
        bill_id=bill_id,
        user_id=current_user.id,
        correction_notes=req.correction_notes,
    )


@router.post(
    "/societies/{society_id}/rounds/{round_id}/bills/publish",
    response_model=PublishBillsAnnouncementResponse,
    summary="Publish privacy-safe bills available announcement to Nexconn group chat",
)
async def publish_bills_announcement(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> PublishBillsAnnouncementResponse:
    """Publish a generic privacy-safe announcement to the society's Nexconn group chat.

    STRICT PRIVACY: Never publishes flat numbers, resident names, or amounts!
    Idempotent: Duplicate calls will not re-send duplicate messages.
    """
    return await billing_service.publish_bills_announcement(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
    )


# ============================================================================
# Volunteer / Admin: Society Spending Summary
# ============================================================================

@router.get(
    "/societies/{society_id}/rounds/{round_id}/spending-summary",
    response_model=SocietySpendingSummaryResponse,
    summary="Retrieve society spending and allocation audit summary",
)
async def get_society_spending_summary(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> SocietySpendingSummaryResponse:
    """Retrieve full society-wide expenditure, flat allocation, and reconciliation breakdown."""
    return await billing_service.get_society_spending_summary(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
    )


# ============================================================================
# Volunteer / Admin / Resident: Retail Benchmarks & Savings
# ============================================================================

@router.post(
    "/societies/{society_id}/rounds/{round_id}/benchmarks",
    response_model=RetailBenchmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record verifiable retail benchmark price evidence",
)
async def record_benchmark(
    society_id: str,
    round_id: str,
    req: RecordBenchmarkRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_volunteer_or_admin),
) -> RetailBenchmarkResponse:
    """Record verified retail benchmark price evidence with source documentation."""
    return await billing_service.record_retail_benchmark(
        society_id=society_id,
        user_id=current_user.id,
        req=req,
    )


@router.get(
    "/societies/{society_id}/rounds/{round_id}/benchmarks",
    response_model=List[RetailBenchmarkResponse],
    summary="List retail benchmark prices recorded for society",
)
async def list_benchmarks(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_member),
) -> List[RetailBenchmarkResponse]:
    """List all retail benchmark prices recorded for this society."""
    return await billing_service.list_retail_benchmarks(
        society_id=society_id,
        user_id=current_user.id,
    )


@router.get(
    "/societies/{society_id}/rounds/{round_id}/savings",
    response_model=SocietySavingsSummaryResponse,
    summary="Calculate evidence-backed verified bulk savings",
)
async def get_savings_summary(
    society_id: str,
    round_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    membership: Dict[str, Any] = Depends(require_society_member),
) -> SocietySavingsSummaryResponse:
    """Calculate verified bulk savings against verified retail benchmark evidence."""
    return await billing_service.calculate_society_savings(
        society_id=society_id,
        round_id=round_id,
        user_id=current_user.id,
    )


# ============================================================================
# Resident: My Bills Access (Strict Resident Isolation)
# ============================================================================

@router.get(
    "/users/me/bills",
    response_model=List[GroceryBillResponse],
    summary="List all grocery bills for current resident",
)
async def get_my_bills(
    current_user: UserResponse = Depends(get_current_active_user),
) -> List[GroceryBillResponse]:
    """Retrieve all grocery bills belonging strictly to the authenticated resident."""
    return await billing_service.get_my_bills(user_id=current_user.id)


@router.get(
    "/users/me/bills/{bill_id}",
    response_model=GroceryBillResponse,
    summary="Retrieve a specific grocery bill for current resident",
)
async def get_my_bill_by_id(
    bill_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
) -> GroceryBillResponse:
    """Retrieve an itemized grocery bill.

    Strictly enforced: Residents can only access bills belonging to their own flat.
    """
    return await billing_service.get_my_bill_by_id(
        user_id=current_user.id,
        bill_id=bill_id,
    )
