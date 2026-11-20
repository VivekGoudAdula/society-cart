"""Pydantic schemas for Phase 7: Purchases, Allocations, Grocery Bills, Benchmarks, and Savings.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class BillStatus(str, Enum):
    """Lifecycle status of a grocery bill."""
    DRAFT = "draft"
    FINALIZED = "finalized"
    PUBLISHED = "published"
    CORRECTED = "corrected"
    CANCELLED = "cancelled"


class BenchmarkVerificationStatus(str, Enum):
    """Verification status of a retail benchmark price."""
    VERIFIED = "verified"
    PENDING = "pending"
    REJECTED = "rejected"


# ============================================================================
# Purchase Recording Schemas
# ============================================================================

class RecordPurchaseRequest(BaseModel):
    """Request payload to record an actual purchase made by a volunteer."""
    item_name: str = Field(..., min_length=1, max_length=120, description="Item name as purchased")
    category: str = Field(..., description="Canonical category (e.g. grains_rice, dairy_oil, etc.)")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name if specified")
    variant: Optional[str] = Field(None, max_length=100, description="Variant / specification (e.g. Full Cream, 1kg pack)")
    actual_quantity: float = Field(..., gt=0, description="Actual quantity bought (must be > 0)")
    unit: str = Field(..., min_length=1, max_length=30, description="Unit (e.g. kg, L, packet, piece)")
    total_price: float = Field(..., ge=0, description="Actual total cost in INR (must be >= 0)")
    shop_name: str = Field(..., min_length=1, max_length=150, description="Store / Vendor / Kirana name")
    purchase_date: Optional[datetime] = Field(None, description="Date of purchase")
    invoice_ref: Optional[str] = Field(None, max_length=100, description="Receipt / Bill / Invoice reference number")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes or physical store details")
    # Substitution mapping
    is_substitution: bool = Field(False, description="Whether this item substitutes for a requested item")
    substitute_for_item_name: Optional[str] = Field(None, description="Original item name being substituted")
    substitute_for_brand: Optional[str] = Field(None, description="Original brand being substituted")
    substitute_for_variant: Optional[str] = Field(None, description="Original variant being substituted")

    @field_validator("actual_quantity")
    @classmethod
    def validate_quantity_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Actual quantity must be strictly positive.")
        return round(v, 3)

    @field_validator("total_price")
    @classmethod
    def validate_price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Total purchase price cannot be negative.")
        return round(v, 2)


class UpdatePurchaseRequest(BaseModel):
    """Payload to update an unfinalized purchase record."""
    item_name: Optional[str] = Field(None, min_length=1, max_length=120)
    category: Optional[str] = None
    brand: Optional[str] = None
    variant: Optional[str] = None
    actual_quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = None
    total_price: Optional[float] = Field(None, ge=0)
    shop_name: Optional[str] = Field(None, min_length=1, max_length=150)
    invoice_ref: Optional[str] = None
    notes: Optional[str] = None
    is_substitution: Optional[bool] = None
    substitute_for_item_name: Optional[str] = None


class PurchaseRecordResponse(BaseModel):
    """Response representation of a recorded purchase."""
    id: str
    society_id: str
    round_id: str
    item_name: str
    normalized_name: str
    category: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    actual_quantity: float
    unit: str
    total_price: float
    unit_price: float
    shop_name: str
    purchase_date: datetime
    invoice_ref: Optional[str] = None
    notes: Optional[str] = None
    is_substitution: bool = False
    substitute_for_item_name: Optional[str] = None
    substitute_for_brand: Optional[str] = None
    substitute_for_variant: Optional[str] = None
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Allocation & Preview Schemas
# ============================================================================

class ItemAllocationDetail(BaseModel):
    """Per-flat allocation detail for a specific grocery line item."""
    item_name: str
    normalized_name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    category: str
    requested_quantity: float
    allocated_quantity: float
    unit: str
    unit_price: float
    item_total: float
    is_substituted: bool = False
    substitute_notes: Optional[str] = None
    is_unfulfilled: bool = False
    unfulfilled_quantity: float = 0.0


class FlatAllocationPreview(BaseModel):
    """Pre-bill allocation preview for a single apartment flat."""
    flat_number: str
    resident_name: str
    user_id: str
    order_id: str
    items: List[ItemAllocationDetail]
    items_subtotal: float
    shared_costs_allocated: float = 0.0
    rounding_adjustment: float = 0.0
    final_amount_payable: float


class PurchasedItemMatchingSummary(BaseModel):
    """Summary of purchase-to-order matching for a shopping list item."""
    item_key: str
    item_name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    category: str
    unit: str
    requested_quantity: float
    purchased_quantity: float
    fulfilled_quantity: float
    unfulfilled_quantity: float
    is_substituted: bool = False
    substitute_item_name: Optional[str] = None
    effective_unit_cost: float
    total_cost: float


class AllocationPreviewResponse(BaseModel):
    """Overall preview of cost allocation across all flats for a round."""
    society_id: str
    round_id: str
    round_number: int
    matching_summaries: List[PurchasedItemMatchingSummary]
    flat_allocations: List[FlatAllocationPreview]
    total_actual_purchase_cost: float
    total_allocated_flats_cost: float
    total_shared_costs: float = 0.0
    unallocated_cost: float = 0.0
    is_reconciled: bool
    reconciliation_message: str
    can_finalize: bool


# ============================================================================
# Bill Schemas
# ============================================================================

class SharedCostEntry(BaseModel):
    """Explicitly recorded shared cost item (e.g. delivery fee, packing material)."""
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., ge=0)
    notes: Optional[str] = None


class FinalizeBillsRequest(BaseModel):
    """Request to finalize individual bills for a round."""
    shared_costs: Optional[List[SharedCostEntry]] = Field(default_factory=list)
    rounding_policy: str = Field("deterministic_paise", description="Strategy for residual paise allocation")


class CorrectBillRequest(BaseModel):
    """Request to correct a finalized bill, generating a new version."""
    correction_notes: str = Field(..., min_length=5, max_length=500, description="Reason for bill correction")
    modified_items: Optional[List[ItemAllocationDetail]] = None


class GroceryBillResponse(BaseModel):
    """Full itemized grocery bill for a flat."""
    id: str
    society_id: str
    round_id: str
    round_number: int
    society_name: str
    user_id: str
    flat_number: str
    resident_name: str
    order_id: str
    status: BillStatus
    bill_version: int = 1
    items: List[ItemAllocationDetail]
    shared_costs: List[SharedCostEntry] = Field(default_factory=list)
    items_subtotal: float
    shared_costs_total: float
    rounding_adjustment: float
    total_amount: float
    is_reconciled: bool = True
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    previous_version_bill_id: Optional[str] = None
    correction_notes: Optional[str] = None


class PublishBillsAnnouncementResponse(BaseModel):
    """Result of publishing the group chat bill announcement."""
    society_id: str
    round_id: str
    round_number: int
    group_id: str
    message_text: str
    sent: bool
    delivery_status: str
    attempts: int
    published_at: datetime


# ============================================================================
# Spending Summary Schemas
# ============================================================================

class SocietySpendingSummaryResponse(BaseModel):
    """Society-wide expenditure and allocation audit summary."""
    society_id: str
    round_id: str
    round_number: int
    total_actual_purchase_cost: float
    total_allocated_bill_costs: float
    total_shared_costs: float
    total_unallocated_cost: float
    is_reconciled: bool
    reconciliation_equation: str
    total_purchased_items_count: int
    total_flats_billed: int
    total_finalized_bills: int
    total_unfulfilled_items_count: int
    total_substituted_items_count: int
    unresolved_discrepancies: List[str] = Field(default_factory=list)


# ============================================================================
# Retail Benchmark & Savings Schemas
# ============================================================================

class RecordBenchmarkRequest(BaseModel):
    """Request to record a verifiable individual retail benchmark price."""
    product_name: str = Field(..., min_length=1, max_length=120)
    brand: Optional[str] = Field(None, max_length=100)
    variant: Optional[str] = Field(None, max_length=100)
    package_size: float = Field(..., gt=0, description="Package quantity size (e.g. 1.0, 5.0, 0.5)")
    package_unit: str = Field(..., min_length=1, max_length=30, description="Package unit (e.g. kg, L, packet)")
    benchmark_price: float = Field(..., gt=0, description="Individual retail purchase price in INR")
    store_name: str = Field(..., min_length=1, max_length=150, description="Retailer or Kirana name")
    source_type: str = Field(..., description="Evidence type (e.g. receipt, quotation, price_listing)")
    evidence_ref: Optional[str] = Field(None, max_length=150, description="Receipt or invoice number")
    evidence_url: Optional[str] = Field(None, max_length=500, description="URL or reference to price proof")
    evidence_date: datetime = Field(..., description="Date price evidence was observed")
    location: str = Field(..., min_length=1, max_length=150, description="Market / locality (e.g. Kondapur, Hyderabad)")

    @field_validator("package_size")
    @classmethod
    def validate_pkg_size(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Package size must be positive.")
        return round(v, 3)

    @field_validator("benchmark_price")
    @classmethod
    def validate_benchmark_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Benchmark price must be positive.")
        return round(v, 2)


class RetailBenchmarkResponse(BaseModel):
    """Stored retail benchmark evidence."""
    id: str
    society_id: str
    product_name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    package_size: float
    package_unit: str
    benchmark_price: float
    benchmark_unit_price: float
    store_name: str
    source_type: str
    evidence_ref: Optional[str] = None
    evidence_url: Optional[str] = None
    evidence_date: datetime
    location: str
    verification_status: BenchmarkVerificationStatus
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime


class ItemSavingsDetail(BaseModel):
    """Item-level savings comparison against verifiable retail benchmark."""
    item_name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    quantity: float
    unit: str
    bulk_cost: float
    bulk_unit_price: float
    has_benchmark: bool
    benchmark_price: Optional[float] = None
    benchmark_unit_price: Optional[float] = None
    benchmark_store: Optional[str] = None
    benchmark_date: Optional[datetime] = None
    benchmark_cost: Optional[float] = None
    savings_amount: Optional[float] = None
    savings_percentage: Optional[float] = None
    status_label: str  # "Verified Savings" | "Benchmark Unavailable"
    unavailability_reason: Optional[str] = None


class SocietySavingsSummaryResponse(BaseModel):
    """Transparent, evidence-backed savings analysis."""
    society_id: str
    round_id: str
    round_number: int
    total_bulk_cost_comparable_items: float
    total_individual_benchmark_cost: float
    verified_savings_amount: float
    verified_savings_percentage: float
    total_items_evaluated: int
    items_with_verified_benchmarks: int
    items_excluded_count: int
    is_partial_coverage: bool
    label: str = "Verified Savings"
    items: List[ItemSavingsDetail]
