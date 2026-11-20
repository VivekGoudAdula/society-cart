"""Pydantic schemas for Phase 6 Volunteer Shopping Dashboard and Aggregation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContributingFlat(BaseModel):
    """Details of an individual flat contributing to a consolidated item."""

    flat_number: str = Field(..., description="Apartment flat number, e.g. C-402")
    user_id: str = Field(..., description="Resident user ID")
    user_name: str = Field(..., description="Resident display name")
    order_id: str = Field(..., description="Associated grocery order ID")
    quantity: float = Field(..., description="Quantity requested by this flat (normalized)")
    unit: Optional[str] = Field(None, description="Unit of measurement, e.g. kg, L, packet")
    notes: Optional[str] = Field(None, description="Optional resident notes or original text")


class ConsolidatedItem(BaseModel):
    """Consolidated grocery item aggregated across all confirmed resident orders."""

    item_key: str = Field(..., description="Unique deterministic aggregation key")
    normalized_name: str = Field(..., description="Standardized English grocery item name, e.g. Rice")
    brand: Optional[str] = Field(None, description="Brand name if specified, e.g. Sona Masoori, Aashirvaad")
    variant: Optional[str] = Field(None, description="Product variant, e.g. Sunflower, Whole Wheat")
    category: str = Field(..., description="Canonical category identifier, e.g. grains_rice")
    total_quantity: float = Field(..., description="Sum of quantities across contributing flats")
    unit: str = Field(..., description="Standardized measurement unit, e.g. kg, L, packet")
    contributing_flats: List[ContributingFlat] = Field(default_factory=list, description="Flats requesting this item")
    contributing_flats_count: int = Field(0, description="Number of distinct flats requesting this item")
    original_names: List[str] = Field(default_factory=list, description="Original item descriptions for traceability")
    is_purchased: bool = Field(False, description="Whether volunteer marked this item as purchased")


class CategoryGroup(BaseModel):
    """Category-wise group of consolidated shopping items."""

    category: str = Field(..., description="Canonical category identifier, e.g. grains_rice")
    category_name: str = Field(..., description="Human-readable category title, e.g. Rice & Grains")
    items: List[ConsolidatedItem] = Field(default_factory=list, description="Consolidated items in this category")
    item_count: int = Field(0, description="Total distinct consolidated items in this category")


class PackingFlatItem(BaseModel):
    """Item row in a flat-wise packing breakdown."""

    item_id: str = Field(..., description="Item ID")
    original_name: str = Field(..., description="Original item name requested by resident")
    normalized_name: str = Field(..., description="Normalized English item name")
    brand: Optional[str] = Field(None, description="Brand name")
    variant: Optional[str] = Field(None, description="Variant name")
    quantity: Optional[float] = Field(None, description="Requested quantity")
    unit: Optional[str] = Field(None, description="Measurement unit")
    category: str = Field(..., description="Canonical category identifier")


class FlatPackingBreakdown(BaseModel):
    """Flat-wise packing breakdown for grocery distribution."""

    flat_number: str = Field(..., description="Apartment flat number")
    user_id: str = Field(..., description="Resident user ID")
    user_name: str = Field(..., description="Resident display name")
    order_id: str = Field(..., description="Confirmed grocery order ID")
    items: List[PackingFlatItem] = Field(default_factory=list, description="Confirmed items for this flat")
    total_items: int = Field(0, description="Total confirmed items for this flat")


class UnresolvedOrderInfo(BaseModel):
    """Information regarding orders that have not yet been confirmed by residents."""

    order_id: str = Field(..., description="Order ID")
    flat_number: str = Field(..., description="Apartment flat number")
    user_id: str = Field(..., description="Resident user ID")
    user_name: str = Field(..., description="Resident display name")
    status: str = Field(..., description="Order status: pending_review, needs_clarification, processing, failed")
    clarification_prompt: Optional[str] = Field(None, description="Clarification requested from resident")
    error_message: Optional[str] = Field(None, description="Processing error message if failed")
    raw_text: str = Field(..., description="Original submission text")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ShoppingListSummary(BaseModel):
    """Compilation summary statistics."""

    total_confirmed_flats: int = Field(0, description="Distinct flats with confirmed orders")
    total_confirmed_orders: int = Field(0, description="Total confirmed orders included")
    total_distinct_items: int = Field(0, description="Total distinct consolidated items across all categories")
    total_items_count: int = Field(0, description="Total individual item rows across all confirmed orders")
    total_unresolved_flats: int = Field(0, description="Distinct flats with unconfirmed or pending orders")
    total_unresolved_orders: int = Field(0, description="Total unconfirmed or pending orders excluded")
    has_unresolved_orders: bool = Field(False, description="True if any unresolved orders exist")
    rejected_orders_count: int = Field(0, description="Total rejected orders excluded")


class CompiledShoppingListResponse(BaseModel):
    """Full compiled society shopping manifest response."""

    id: str = Field(..., description="Shopping list document ID")
    society_id: str = Field(..., description="Apartment society ID")
    round_id: str = Field(..., description="Grocery order round ID")
    round_number: int = Field(..., description="Sequential round number")
    round_title: Optional[str] = Field(None, description="Order round title")
    shopping_date: Optional[str] = Field(None, description="Expected shop visit date")
    version: int = Field(1, description="Compilation version incremented on each recompile")
    compiled_at: datetime = Field(..., description="Compilation timestamp")
    compiled_by_user_id: str = Field(..., description="Volunteer/admin user ID who compiled the list")
    summary: ShoppingListSummary = Field(..., description="High-level summary statistics")
    categories: List[CategoryGroup] = Field(default_factory=list, description="Consolidated items by category")
    packing_breakdown: List[FlatPackingBreakdown] = Field(default_factory=list, description="Flat-wise packing list")
    unresolved_orders: List[UnresolvedOrderInfo] = Field(default_factory=list, description="Unconfirmed orders list")
