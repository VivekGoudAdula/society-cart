"""Billing & Savings Service for Society Cart (Phase 7).

Manages actual purchase recording, canonical matching, per-flat cost allocation,
immutable bill generation, privacy-safe Nexconn chat announcement,
verified retail benchmark evidence, and transparent savings analysis.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import (
    get_purchase_records_collection,
    get_grocery_bills_collection,
    get_retail_benchmarks_collection,
    get_order_rounds_collection,
    get_societies_collection,
)
from app.schemas.billing import (
    BenchmarkVerificationStatus,
    BillStatus,
    FinalizeBillsRequest,
    FlatAllocationPreview,
    FlatItemAllocationOverride,
    GroceryBillResponse,
    ItemAllocationDetail,
    ItemSavingsDetail,
    PublishBillsAnnouncementResponse,
    PurchaseRecordResponse,
    PurchasedItemMatchingSummary,
    AllocationPreviewResponse,
    RecordBenchmarkRequest,
    RecordPurchaseRequest,
    RetailBenchmarkResponse,
    SharedCostEntry,
    SocietySavingsSummaryResponse,
    SocietySpendingSummaryResponse,
    UpdatePurchaseRequest,
    VerifyBenchmarkRequest,
)
from app.services import membership_service, shopping_list_service
from app.services.nexconn_service import send_system_bot_message
from app.services.shopping_list_service import normalize_unit_and_quantity, _build_aggregation_key

logger = logging.getLogger(__name__)


# ============================================================================
# Helpers
# ============================================================================

def _to_decimal(val: Any) -> Decimal:
    """Convert float, int, or string safely to Decimal."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _quantize_paise(d: Any) -> Decimal:
    """Round to 2 decimal places (paise) using ROUND_HALF_UP."""
    dec = _to_decimal(d)
    return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quantize_unit_cost(d: Any) -> Decimal:
    """Round unit costs to 4 decimal places using ROUND_HALF_UP."""
    dec = _to_decimal(d)
    return dec.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

def _ensure_utc(dt: Optional[datetime]) -> datetime:
    """Ensure datetime has timezone.utc."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _serialize_purchase(doc: Dict[str, Any]) -> PurchaseRecordResponse:
    """Serialize a MongoDB purchase record document into PurchaseRecordResponse."""
    return PurchaseRecordResponse(
        id=str(doc["_id"]),
        society_id=str(doc["society_id"]),
        round_id=str(doc["round_id"]),
        item_name=doc["item_name"],
        normalized_name=doc.get("normalized_name", doc["item_name"]),
        category=doc.get("category", "other"),
        brand=doc.get("brand"),
        variant=doc.get("variant"),
        actual_quantity=float(doc["actual_quantity"]),
        unit=doc["unit"],
        total_price=float(doc["total_price"]),
        unit_price=float(doc.get("unit_price", 0.0)),
        shop_name=doc.get("shop_name", "Local Store"),
        purchase_date=_ensure_utc(doc.get("purchase_date")),
        invoice_ref=doc.get("invoice_ref"),
        notes=doc.get("notes"),
        is_substitution=bool(doc.get("is_substitution", False)),
        substitute_for_item_name=doc.get("substitute_for_item_name"),
        substitute_for_brand=doc.get("substitute_for_brand"),
        substitute_for_variant=doc.get("substitute_for_variant"),
        created_by_user_id=str(doc.get("created_by_user_id", "")),
        created_at=_ensure_utc(doc.get("created_at")),
        updated_at=_ensure_utc(doc.get("updated_at")),
    )


def _serialize_bill(doc: Dict[str, Any]) -> GroceryBillResponse:
    """Serialize a MongoDB grocery bill document into GroceryBillResponse."""
    items = [
        ItemAllocationDetail(**it) for it in doc.get("items", [])
    ]
    shared = [
        SharedCostEntry(**sc) for sc in doc.get("shared_costs", [])
    ]
    return GroceryBillResponse(
        id=str(doc["_id"]),
        society_id=str(doc["society_id"]),
        round_id=str(doc["round_id"]),
        round_number=int(doc.get("round_number", 1)),
        society_name=doc.get("society_name", "Society"),
        user_id=str(doc["user_id"]),
        flat_number=str(doc["flat_number"]),
        resident_name=str(doc.get("resident_name", "Resident")),
        order_id=str(doc["order_id"]),
        status=BillStatus(doc.get("status", "draft")),
        bill_version=int(doc.get("bill_version", 1)),
        items=items,
        shared_costs=shared,
        items_subtotal=float(doc.get("items_subtotal", 0.0)),
        shared_costs_total=float(doc.get("shared_costs_total", 0.0)),
        rounding_adjustment=float(doc.get("rounding_adjustment", 0.0)),
        total_amount=float(doc.get("total_amount", 0.0)),
        is_reconciled=bool(doc.get("is_reconciled", True)),
        created_at=_ensure_utc(doc.get("created_at")),
        updated_at=_ensure_utc(doc.get("updated_at")),
        finalized_at=_ensure_utc(doc["finalized_at"]) if doc.get("finalized_at") else None,
        published_at=_ensure_utc(doc["published_at"]) if doc.get("published_at") else None,
        previous_version_bill_id=doc.get("previous_version_bill_id"),
        correction_notes=doc.get("correction_notes"),
    )


def _serialize_benchmark(doc: Dict[str, Any]) -> RetailBenchmarkResponse:
    """Serialize a MongoDB benchmark document into RetailBenchmarkResponse."""
    return RetailBenchmarkResponse(
        id=str(doc["_id"]),
        society_id=str(doc["society_id"]),
        product_name=doc["product_name"],
        brand=doc.get("brand"),
        variant=doc.get("variant"),
        package_size=float(doc["package_size"]),
        package_unit=doc["package_unit"],
        benchmark_price=float(doc["benchmark_price"]),
        benchmark_unit_price=float(doc.get("benchmark_unit_price", 0.0)),
        store_name=doc["store_name"],
        source_type=doc["source_type"],
        evidence_ref=doc.get("evidence_ref"),
        evidence_url=doc.get("evidence_url"),
        evidence_date=_ensure_utc(doc.get("evidence_date")),
        location=doc["location"],
        verification_status=BenchmarkVerificationStatus(doc.get("verification_status", "verified")),
        verified_by=doc.get("verified_by"),
        verified_at=_ensure_utc(doc["verified_at"]) if doc.get("verified_at") else None,
        created_at=_ensure_utc(doc.get("created_at")),
    )


# ============================================================================
# 1. Purchase Recording
# ============================================================================

async def record_purchase(
    society_id: str,
    round_id: str,
    user_id: str,
    req: RecordPurchaseRequest,
) -> PurchaseRecordResponse:
    """Record an actual grocery purchase for a society round."""
    # 1. Verify volunteer/admin role
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    # 2. Verify round existence and society binding
    rounds_col = get_order_rounds_collection()
    round_doc = await rounds_col.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery round not found in this society.",
        )

    # 3. Check if bills are already finalized for this round
    bills_col = get_grocery_bills_collection()
    finalized_bill = await bills_col.find_one({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$in": [BillStatus.FINALIZED.value, BillStatus.PUBLISHED.value]},
    })
    if finalized_bill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record new purchases after bills for this round have been finalized.",
        )

    # 4. Normalize quantity and unit
    norm_qty, norm_unit = normalize_unit_and_quantity(req.actual_quantity, req.unit)
    if norm_qty is None or norm_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Purchased quantity must be positive.",
        )

    if req.total_price < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Purchase total price cannot be negative.",
        )

    unit_price = round(req.total_price / norm_qty, 4)

    # 5. Duplicate prevention check
    purchases_col = get_purchase_records_collection()
    dup_query = {
        "society_id": society_id,
        "round_id": round_id,
        "item_name": req.item_name.strip(),
        "brand": (req.brand or "").strip() or None,
        "variant": (req.variant or "").strip() or None,
        "unit": norm_unit,
        "shop_name": req.shop_name.strip(),
    }
    if req.invoice_ref:
        dup_query["invoice_ref"] = req.invoice_ref.strip()

    existing_dup = await purchases_col.find_one(dup_query)
    if existing_dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A duplicate purchase entry already exists for '{req.item_name}' at '{req.shop_name}' in this round.",
        )

    now = datetime.now(timezone.utc)
    purchase_date = _ensure_utc(req.purchase_date) if req.purchase_date else now

    doc = {
        "society_id": society_id,
        "round_id": round_id,
        "item_name": req.item_name.strip(),
        "normalized_name": req.item_name.strip().title(),
        "category": req.category.strip().lower(),
        "brand": (req.brand.strip() if req.brand else None),
        "variant": (req.variant.strip() if req.variant else None),
        "actual_quantity": norm_qty,
        "unit": norm_unit,
        "total_price": round(req.total_price, 2),
        "unit_price": unit_price,
        "shop_name": req.shop_name.strip(),
        "purchase_date": purchase_date,
        "invoice_ref": req.invoice_ref.strip() if req.invoice_ref else None,
        "notes": req.notes.strip() if req.notes else None,
        "is_substitution": req.is_substitution,
        "substitute_for_item_name": req.substitute_for_item_name.strip() if req.substitute_for_item_name else None,
        "substitute_for_brand": req.substitute_for_brand.strip() if req.substitute_for_brand else None,
        "substitute_for_variant": req.substitute_for_variant.strip() if req.substitute_for_variant else None,
        "created_by_user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "audit_trail": [
            {
                "action": "created",
                "user_id": user_id,
                "timestamp": now,
                "quantity": norm_qty,
                "total_price": round(req.total_price, 2),
            }
        ],
    }

    res = await purchases_col.insert_one(doc)
    doc["_id"] = res.inserted_id
    logger.info("Recorded purchase %s for round %s (Rs %s)", res.inserted_id, round_id, req.total_price)
    return _serialize_purchase(doc)


async def list_purchases(
    society_id: str,
    round_id: str,
    user_id: str,
) -> List[PurchaseRecordResponse]:
    """List all recorded purchases for a round."""
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )
    purchases_col = get_purchase_records_collection()
    cursor = purchases_col.find({"society_id": society_id, "round_id": round_id}).sort("created_at", 1)
    results = []
    async for doc in cursor:
        results.append(_serialize_purchase(doc))
    return results


async def update_purchase(
    society_id: str,
    round_id: str,
    purchase_id: str,
    user_id: str,
    req: UpdatePurchaseRequest,
) -> PurchaseRecordResponse:
    """Update an unfinalized purchase record with audit trail tracking."""
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    bills_col = get_grocery_bills_collection()
    finalized_bill = await bills_col.find_one({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$in": [BillStatus.FINALIZED.value, BillStatus.PUBLISHED.value]},
    })
    if finalized_bill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify purchases after bills have been finalized.",
        )

    purchases_col = get_purchase_records_collection()
    existing = await purchases_col.find_one({
        "_id": ObjectId(purchase_id),
        "society_id": society_id,
        "round_id": round_id,
    })
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase record not found.")

    update_fields: Dict[str, Any] = {}
    if req.item_name is not None:
        update_fields["item_name"] = req.item_name.strip()
        update_fields["normalized_name"] = req.item_name.strip().title()
    if req.category is not None:
        update_fields["category"] = req.category.strip().lower()
    if req.brand is not None:
        update_fields["brand"] = req.brand.strip() or None
    if req.variant is not None:
        update_fields["variant"] = req.variant.strip() or None
    if req.shop_name is not None:
        update_fields["shop_name"] = req.shop_name.strip()
    if req.invoice_ref is not None:
        update_fields["invoice_ref"] = req.invoice_ref.strip() or None
    if req.notes is not None:
        update_fields["notes"] = req.notes.strip() or None
    if req.is_substitution is not None:
        update_fields["is_substitution"] = req.is_substitution
    if req.substitute_for_item_name is not None:
        update_fields["substitute_for_item_name"] = req.substitute_for_item_name.strip() or None

    current_qty = update_fields.get("actual_quantity", existing["actual_quantity"])
    current_unit = update_fields.get("unit", existing["unit"])
    if req.actual_quantity is not None or req.unit is not None:
        raw_qty = req.actual_quantity if req.actual_quantity is not None else existing["actual_quantity"]
        raw_unit = req.unit if req.unit is not None else existing["unit"]
        norm_qty, norm_unit = normalize_unit_and_quantity(raw_qty, raw_unit)
        if norm_qty is None or norm_qty <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Quantity must be positive.")
        update_fields["actual_quantity"] = norm_qty
        update_fields["unit"] = norm_unit
        current_qty = norm_qty

    if req.total_price is not None:
        if req.total_price < 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Price cannot be negative.")
        update_fields["total_price"] = round(req.total_price, 2)

    current_total = update_fields.get("total_price", existing["total_price"])
    if current_qty > 0:
        update_fields["unit_price"] = round(current_total / current_qty, 4)

    now = datetime.now(timezone.utc)
    update_fields["updated_at"] = now

    audit_entry = {
        "action": "updated",
        "user_id": user_id,
        "timestamp": now,
        "changes": {k: str(v) for k, v in update_fields.items() if k != "updated_at"},
    }

    updated_doc = await purchases_col.find_one_and_update(
        {"_id": existing["_id"]},
        {
            "$set": update_fields,
            "$push": {"audit_trail": audit_entry},
        },
        return_document=True,
    )
    return _serialize_purchase(updated_doc)


async def delete_purchase(
    society_id: str,
    round_id: str,
    purchase_id: str,
    user_id: str,
) -> Dict[str, str]:
    """Delete an unfinalized purchase record."""
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    bills_col = get_grocery_bills_collection()
    finalized_bill = await bills_col.find_one({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$in": [BillStatus.FINALIZED.value, BillStatus.PUBLISHED.value]},
    })
    if finalized_bill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete purchases after bills have been finalized.",
        )

    purchases_col = get_purchase_records_collection()
    res = await purchases_col.delete_one({
        "_id": ObjectId(purchase_id),
        "society_id": society_id,
        "round_id": round_id,
    })
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase record not found.")

    return {"status": "deleted", "purchase_id": purchase_id}


# ============================================================================
# 2. Purchase-to-Order Matching & Cost Allocation Engine
# ============================================================================

def _match_purchase_to_requested(
    item_norm_name: str,
    item_category: str,
    item_brand: Optional[str],
    item_variant: Optional[str],
    item_unit: str,
    purchases: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
    """Match a requested grocery item to recorded purchases.

    Matches strictly on (category, normalized_name, brand, variant, unit)
    OR through explicit substitution link.
    Never silently matches different brands or variants!
    """
    req_norm = item_norm_name.strip().lower()
    req_cat = item_category.strip().lower()
    req_brand = (item_brand or "").strip().lower()
    req_variant = (item_variant or "").strip().lower()
    req_unit = item_unit.strip().lower()

    direct_matches = []
    substitution_matches = []
    substitute_note = None

    for p in purchases:
        p_norm = p.get("normalized_name", p["item_name"]).strip().lower()
        p_cat = p.get("category", "").strip().lower()
        p_brand = (p.get("brand") or "").strip().lower()
        p_variant = (p.get("variant") or "").strip().lower()
        p_unit = p.get("unit", "").strip().lower()

        # Direct strict match:
        if (
            req_norm == p_norm
            and req_cat == p_cat
            and req_brand == p_brand
            and req_variant == p_variant
            and req_unit == p_unit
        ):
            direct_matches.append(p)
            continue

        # Explicit substitution match:
        if p.get("is_substitution"):
            sub_for_name = (p.get("substitute_for_item_name") or "").strip().lower()
            sub_for_brand = (p.get("substitute_for_brand") or "").strip().lower()
            sub_for_variant = (p.get("substitute_for_variant") or "").strip().lower()
            if (
                sub_for_name == req_norm
                and (not sub_for_brand or sub_for_brand == req_brand)
                and (not sub_for_variant or sub_for_variant == req_variant)
                and req_unit == p_unit
            ):
                substitution_matches.append(p)
                substitute_note = f"Substituted with {p.get('item_name')} ({p.get('brand') or 'standard'})"

    if direct_matches:
        return direct_matches, False, None
    if substitution_matches:
        return substitution_matches, True, substitute_note
    return [], False, None


async def calculate_allocation(
    society_id: str,
    round_id: str,
    user_id: str,
    shared_costs: Optional[List[SharedCostEntry]] = None,
    flat_allocations_override: Optional[List[FlatItemAllocationOverride]] = None,
) -> AllocationPreviewResponse:
    """Core cost-allocation engine calculating per-flat item costs from actual purchases.

    Supports:
    - Decimal-safe monetary arithmetic with paise precision.
    - Explicit physical flat-wise allocation overrides from volunteer packing breakdown.
    - Transparent distinction between unfulfilled resident orders and unallocated inventory.
    """
    # 1. Load compiled shopping list from Phase 6
    manifest = await shopping_list_service.get_shopping_list(society_id, round_id)
    if not manifest:
        # Attempt compile if not yet compiled
        manifest = await shopping_list_service.compile_shopping_list(society_id, round_id, user_id)

    # 2. Load all recorded purchases
    purchases_col = get_purchase_records_collection()
    cursor = purchases_col.find({"society_id": society_id, "round_id": round_id})
    purchases = await cursor.to_list(length=1000)

    # 3. Calculate total actual purchase cost using Decimal
    total_actual_purchase_cost_dec = _quantize_paise(
        sum((_to_decimal(p["total_price"]) for p in purchases), Decimal("0.00"))
    )
    total_actual_purchase_cost = float(total_actual_purchase_cost_dec)

    # 4. Build override lookup map if provided
    override_map: Dict[Tuple[str, str], float] = {}
    if flat_allocations_override:
        for ov in flat_allocations_override:
            f_num = ov.flat_number.strip().lower()
            i_name = ov.item_name.strip().lower()
            override_map[(f_num, i_name)] = float(ov.allocated_quantity)

    # 5. Map purchases by canonical key & aggregate quantities
    matching_summaries: List[PurchasedItemMatchingSummary] = []
    item_cost_map: Dict[str, Dict[str, Any]] = {}

    for cat_group in manifest.categories:
        for it in cat_group.items:
            matches, is_sub, sub_note = _match_purchase_to_requested(
                item_norm_name=it.normalized_name,
                item_category=it.category,
                item_brand=it.brand,
                item_variant=it.variant,
                item_unit=it.unit,
                purchases=purchases,
            )

            purchased_qty = sum(float(m["actual_quantity"]) for m in matches)
            purchased_total_cost_dec = _quantize_paise(
                sum((_to_decimal(m["total_price"]) for m in matches), Decimal("0.00"))
            )

            effective_unit_cost_dec = (
                _quantize_unit_cost(purchased_total_cost_dec / _to_decimal(purchased_qty))
                if purchased_qty > 0
                else Decimal("0.0000")
            )
            effective_unit_cost = float(effective_unit_cost_dec)

            # Check if this item has any flat allocation overrides
            norm_name_lower = it.normalized_name.strip().lower()
            relevant_overrides = {
                k[0]: v for k, v in override_map.items() if k[1] == norm_name_lower
            }

            if relevant_overrides:
                # Sum explicitly allocated quantities across flats
                fulfilled_qty = round(sum(relevant_overrides.values()), 3)
            else:
                fulfilled_qty = min(it.total_quantity, purchased_qty)

            unfulfilled_qty = max(0.0, round(it.total_quantity - fulfilled_qty, 3))

            # Default proportional ratio if no override exists
            ratio = min(1.0, (purchased_qty / it.total_quantity)) if it.total_quantity > 0 else 0.0

            item_cost_map[it.item_key] = {
                "matches": matches,
                "is_sub": is_sub,
                "sub_note": sub_note,
                "purchased_qty": purchased_qty,
                "purchased_total_cost_dec": purchased_total_cost_dec,
                "effective_unit_cost_dec": effective_unit_cost_dec,
                "effective_unit_cost": effective_unit_cost,
                "fulfillment_ratio": ratio,
            }

            matching_summaries.append(
                PurchasedItemMatchingSummary(
                    item_key=it.item_key,
                    item_name=it.normalized_name,
                    brand=it.brand,
                    variant=it.variant,
                    category=it.category,
                    unit=it.unit,
                    requested_quantity=it.total_quantity,
                    purchased_quantity=purchased_qty,
                    fulfilled_quantity=fulfilled_qty,
                    unfulfilled_quantity=unfulfilled_qty,
                    is_substituted=is_sub,
                    substitute_item_name=matches[0]["item_name"] if is_sub and matches else None,
                    effective_unit_cost=effective_unit_cost,
                    total_cost=float(_quantize_paise(_to_decimal(fulfilled_qty) * effective_unit_cost_dec)),
                )
            )

    # 6. Flat-wise item allocation
    flat_allocations: List[FlatAllocationPreview] = []
    total_allocated_flats_cost_dec = Decimal("0.00")

    shared_cost_sum_dec = _quantize_paise(sum((_to_decimal(sc.amount) for sc in (shared_costs or [])), Decimal("0.00")))
    shared_cost_sum = float(shared_cost_sum_dec)
    num_flats = len(manifest.packing_breakdown)

    if num_flats > 0:
        per_flat_shared_dec = _quantize_paise(shared_cost_sum_dec / Decimal(str(num_flats)))
        shared_residual_dec = shared_cost_sum_dec - (per_flat_shared_dec * Decimal(str(num_flats)))
    else:
        per_flat_shared_dec = Decimal("0.00")
        shared_residual_dec = Decimal("0.00")

    for flat_idx, flat in enumerate(manifest.packing_breakdown):
        allocated_items: List[ItemAllocationDetail] = []
        flat_items_subtotal_dec = Decimal("0.00")
        f_num_lower = flat.flat_number.strip().lower()

        for f_it in flat.items:
            norm_name = f_it.normalized_name
            norm_name_lower = norm_name.strip().lower()
            f_key = _build_aggregation_key(
                normalized_name=norm_name,
                brand=f_it.brand,
                variant=f_it.variant,
                normalized_unit=f_it.unit,
                category=f_it.category,
            )

            cost_info = item_cost_map.get(f_key)
            req_qty = float(f_it.quantity or 0.0)

            if not cost_info or cost_info["purchased_qty"] <= 0:
                # Completely unfulfilled item
                allocated_items.append(
                    ItemAllocationDetail(
                        item_name=norm_name,
                        normalized_name=norm_name,
                        brand=f_it.brand,
                        variant=f_it.variant,
                        category=f_it.category,
                        requested_quantity=req_qty,
                        allocated_quantity=0.0,
                        unit=f_it.unit,
                        unit_price=0.0,
                        item_total=0.0,
                        is_substituted=False,
                        is_unfulfilled=True,
                        unfulfilled_quantity=req_qty,
                    )
                )
            else:
                unit_cost_dec = cost_info["effective_unit_cost_dec"]
                unit_cost = cost_info["effective_unit_cost"]

                # Check if explicit physical allocation override exists for this flat & item
                override_key = (f_num_lower, norm_name_lower)
                if override_key in override_map:
                    alloc_qty = round(override_map[override_key], 3)
                else:
                    ratio = cost_info["fulfillment_ratio"]
                    alloc_qty = round(req_qty * ratio, 3)

                unfulfilled_qty = max(0.0, round(req_qty - alloc_qty, 3))
                item_total_dec = _quantize_paise(_to_decimal(alloc_qty) * unit_cost_dec)
                item_total = float(item_total_dec)
                flat_items_subtotal_dec += item_total_dec

                allocated_items.append(
                    ItemAllocationDetail(
                        item_name=norm_name,
                        normalized_name=norm_name,
                        brand=f_it.brand,
                        variant=f_it.variant,
                        category=f_it.category,
                        requested_quantity=req_qty,
                        allocated_quantity=alloc_qty,
                        unit=f_it.unit,
                        unit_price=float(_quantize_paise(unit_cost_dec)),
                        item_total=item_total,
                        is_substituted=cost_info["is_sub"],
                        substitute_notes=cost_info["sub_note"],
                        is_unfulfilled=(unfulfilled_qty > 0),
                        unfulfilled_quantity=unfulfilled_qty,
                    )
                )

        # Shared cost allocation (first flat deterministically receives any residual paise)
        this_shared_dec = per_flat_shared_dec
        if flat_idx == 0:
            this_shared_dec += shared_residual_dec
        this_shared = float(this_shared_dec)

        final_flat_total_dec = flat_items_subtotal_dec + this_shared_dec
        flat_items_subtotal = float(flat_items_subtotal_dec)
        final_flat_total = float(final_flat_total_dec)

        total_allocated_flats_cost_dec += flat_items_subtotal_dec

        flat_allocations.append(
            FlatAllocationPreview(
                flat_number=flat.flat_number,
                resident_name=flat.user_name,
                user_id=flat.user_id,
                order_id=flat.order_id,
                items=allocated_items,
                items_subtotal=flat_items_subtotal,
                shared_costs_allocated=this_shared,
                rounding_adjustment=0.0,
                final_amount_payable=final_flat_total,
            )
        )

    # 7. Financial Reconciliation Analysis
    # Actual Purchase Cost = Resident Allocations + Unallocated Inventory Cost
    total_allocated_flats_cost = float(total_allocated_flats_cost_dec)
    unallocated_cost_dec = max(Decimal("0.00"), total_actual_purchase_cost_dec - total_allocated_flats_cost_dec)
    unallocated_cost = float(unallocated_cost_dec)

    reconciled_sum_dec = total_allocated_flats_cost_dec + unallocated_cost_dec
    diff_dec = abs(total_actual_purchase_cost_dec - reconciled_sum_dec)
    is_reconciled = (diff_dec <= Decimal("0.02"))

    if is_reconciled:
        msg = (
            f"Reconciled: Total Purchase (Rs {total_actual_purchase_cost:.2f}) = "
            f"Allocated (Rs {total_allocated_flats_cost:.2f}) + "
            f"Unallocated Inventory (Rs {unallocated_cost:.2f})"
        )
    else:
        msg = (
            f"Discrepancy detected: Total Purchase Rs {total_actual_purchase_cost:.2f} differs "
            f"from reconciled sum Rs {float(reconciled_sum_dec):.2f} by Rs {float(diff_dec):.2f}."
        )

    can_finalize = is_reconciled and len(flat_allocations) > 0 and total_actual_purchase_cost > 0

    return AllocationPreviewResponse(
        society_id=society_id,
        round_id=round_id,
        round_number=manifest.round_number,
        matching_summaries=matching_summaries,
        flat_allocations=flat_allocations,
        total_actual_purchase_cost=total_actual_purchase_cost,
        total_allocated_flats_cost=total_allocated_flats_cost,
        total_shared_costs=shared_cost_sum,
        unallocated_cost=unallocated_cost,
        is_reconciled=is_reconciled,
        reconciliation_message=msg,
        can_finalize=can_finalize,
    )


# ============================================================================
# 3. Bill Finalization and Lifecycle
# ============================================================================

async def finalize_bills(
    society_id: str,
    round_id: str,
    user_id: str,
    req: FinalizeBillsRequest,
) -> List[GroceryBillResponse]:
    """Finalize itemized bills for all flats in the grocery round.

    Enforces reconciliation, creates immutable bill documents,
    and transitions status to 'finalized'.
    """
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    # Check for existing finalized bills
    bills_col = get_grocery_bills_collection()
    existing_bills = await bills_col.find({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$in": [BillStatus.FINALIZED.value, BillStatus.PUBLISHED.value]},
    }).to_list(length=1000)

    if existing_bills:
        logger.info("Bills already finalized for round %s; returning existing records.", round_id)
        return [_serialize_bill(b) for b in existing_bills]

    # Compute fresh allocation preview respecting physical allocations override
    preview = await calculate_allocation(
        society_id=society_id,
        round_id=round_id,
        user_id=user_id,
        shared_costs=req.shared_costs,
        flat_allocations_override=req.flat_allocations_override,
    )
    if not preview.is_reconciled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finalize bills: {preview.reconciliation_message}",
        )

    if not preview.flat_allocations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No confirmed flats found to bill for this round.",
        )

    # Load society name
    societies_col = get_societies_collection()
    soc = await societies_col.find_one({"_id": ObjectId(society_id)})
    soc_name = soc.get("name", "Society") if soc else "Society"

    now = datetime.now(timezone.utc)
    bill_docs = []

    for flat_alloc in preview.flat_allocations:
        shared_entries = []
        if flat_alloc.shared_costs_allocated > 0:
            shared_entries.append(
                SharedCostEntry(
                    name="Shared Round Expenses",
                    amount=flat_alloc.shared_costs_allocated,
                    notes="Proportional delivery / logistics share",
                )
            )

        bill_doc = {
            "society_id": society_id,
            "round_id": round_id,
            "round_number": preview.round_number,
            "society_name": soc_name,
            "user_id": flat_alloc.user_id,
            "flat_number": flat_alloc.flat_number,
            "resident_name": flat_alloc.resident_name,
            "order_id": flat_alloc.order_id,
            "status": BillStatus.FINALIZED.value,
            "bill_version": 1,
            "items": [it.model_dump() for it in flat_alloc.items],
            "shared_costs": [sc.model_dump() for sc in shared_entries],
            "items_subtotal": flat_alloc.items_subtotal,
            "shared_costs_total": flat_alloc.shared_costs_allocated,
            "rounding_adjustment": flat_alloc.rounding_adjustment,
            "total_amount": flat_alloc.final_amount_payable,
            "is_reconciled": True,
            "created_at": now,
            "updated_at": now,
            "finalized_at": now,
            "published_at": None,
            "previous_version_bill_id": None,
            "correction_notes": None,
        }
        bill_docs.append(bill_doc)

    # Insert bills into collection
    inserted = await bills_col.insert_many(bill_docs)
    for idx, inserted_id in enumerate(inserted.inserted_ids):
        bill_docs[idx]["_id"] = inserted_id

    # Update round status
    rounds_col = get_order_rounds_collection()
    await rounds_col.update_one(
        {"_id": ObjectId(round_id)},
        {"$set": {"bills_finalized": True, "bills_finalized_at": now, "updated_at": now}},
    )

    logger.info("Successfully finalized %d bills for round %s", len(bill_docs), round_id)
    return [_serialize_bill(b) for b in bill_docs]


async def get_round_bills(
    society_id: str,
    round_id: str,
    user_id: str,
) -> List[GroceryBillResponse]:
    """Get all bills for a round (Volunteer/Admin only)."""
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )
    bills_col = get_grocery_bills_collection()
    cursor = bills_col.find({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$ne": BillStatus.CANCELLED.value},
    }).sort("flat_number", 1)

    results = []
    async for doc in cursor:
        results.append(_serialize_bill(doc))
    return results


async def correct_bill(
    society_id: str,
    round_id: str,
    bill_id: str,
    user_id: str,
    correction_notes: str,
) -> GroceryBillResponse:
    """Create a corrected version of a finalized bill while preserving audit history.

    Uses atomic compare-and-swap (CAS) to prevent concurrent conflicting corrections
    from creating divergent version forks.
    """
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    bills_col = get_grocery_bills_collection()
    now = datetime.now(timezone.utc)

    # Atomic CAS: Match on _id, society_id, round_id, and active finalized/published status
    # and transition to CANCELLED in one atomic step.
    existing = await bills_col.find_one_and_update(
        {
            "_id": ObjectId(bill_id),
            "society_id": society_id,
            "round_id": round_id,
            "status": {"$in": [BillStatus.FINALIZED.value, BillStatus.PUBLISHED.value, BillStatus.CORRECTED.value]},
        },
        {"$set": {"status": BillStatus.CANCELLED.value, "updated_at": now}},
        return_document=False,
    )
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bill cannot be corrected: it is either already cancelled, modified by another user, or does not exist.",
        )

    # Create new corrected bill version
    new_doc = existing.copy()
    new_doc.pop("_id")
    new_doc["bill_version"] = existing.get("bill_version", 1) + 1
    new_doc["status"] = BillStatus.CORRECTED.value
    new_doc["previous_version_bill_id"] = str(existing["_id"])
    new_doc["correction_notes"] = correction_notes
    new_doc["created_at"] = now
    new_doc["updated_at"] = now

    res = await bills_col.insert_one(new_doc)
    new_doc["_id"] = res.inserted_id

    logger.info("Created corrected bill v%d for flat %s (previous bill: %s)", new_doc["bill_version"], new_doc["flat_number"], bill_id)
    return _serialize_bill(new_doc)


# ============================================================================
# 4. Nexconn Group Chat Bill Announcement (Privacy Preserved)
# ============================================================================

async def publish_bills_announcement(
    society_id: str,
    round_id: str,
    user_id: str,
) -> PublishBillsAnnouncementResponse:
    """Publish a generic, privacy-safe group chat announcement to Nexconn.

    STRICT PRIVACY: NEVER publishes individual flat numbers, resident names, or amounts!
    Concurrency-safe: atomically locks announcement state before dispatching to prevent duplicate messages.
    """
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    rounds_col = get_order_rounds_collection()
    round_doc = await rounds_col.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found.")

    round_number = round_doc.get("round_number", 1)

    # Verify bills are finalized
    bills_col = get_grocery_bills_collection()
    finalized_count = await bills_col.count_documents({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$in": [BillStatus.FINALIZED.value, BillStatus.PUBLISHED.value, BillStatus.CORRECTED.value]},
    })
    if finalized_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish announcement: No bills have been finalized for this round yet.",
        )

    # Check idempotency: if already successfully published, return cached status
    now = datetime.now(timezone.utc)
    ann_state = round_doc.get("bills_announcement", {})
    if ann_state.get("status") == "sent":
        logger.info("Bills announcement for round %s was already sent; returning existing record.", round_id)
        return PublishBillsAnnouncementResponse(
            society_id=society_id,
            round_id=round_id,
            round_number=round_number,
            group_id=f"society_{society_id}",
            message_text=ann_state.get("message_text", "Bills available announcement"),
            sent=True,
            delivery_status="sent",
            attempts=int(ann_state.get("attempts", 1)),
            published_at=_ensure_utc(ann_state.get("sent_at")),
        )

    # Generic privacy-safe announcement text:
    message_text = (
        f"📢 Society Cart: Shopping for Round #{round_number} is complete!\n\n"
        f"Your itemized grocery bill is now available in your personal Society Cart dashboard. "
        f"Please log in to view your flat's breakdown and verified bulk savings."
    )

    attempts = int(ann_state.get("attempts", 0)) + 1

    # Atomic CAS pre-lock: transition from failed/empty to "sending"
    locked_round = await rounds_col.find_one_and_update(
        {
            "_id": ObjectId(round_id),
            "society_id": society_id,
            "bills_announcement.status": {"$nin": ["sending", "sent"]},
        },
        {
            "$set": {
                "bills_announcement.status": "sending",
                "bills_announcement.last_attempt_at": now,
                "bills_announcement.attempts": attempts,
                "bills_announcement.message_text": message_text,
                "updated_at": now,
            }
        },
        return_document=True,
    )

    if not locked_round:
        # Another worker is currently dispatching or already completed
        fresh_round = await rounds_col.find_one({"_id": ObjectId(round_id)})
        curr_state = fresh_round.get("bills_announcement", {}) if fresh_round else {}
        if curr_state.get("status") == "sent":
            return PublishBillsAnnouncementResponse(
                society_id=society_id,
                round_id=round_id,
                round_number=round_number,
                group_id=f"society_{society_id}",
                message_text=curr_state.get("message_text", message_text),
                sent=True,
                delivery_status="sent",
                attempts=int(curr_state.get("attempts", 1)),
                published_at=_ensure_utc(curr_state.get("sent_at")),
            )
        elif curr_state.get("status") == "sending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Announcement is currently being dispatched by another worker.",
            )

    group_id = f"society_{society_id}"
    sent = False
    delivery_status = "failed"

    try:
        sent = await send_system_bot_message(
            group_id=group_id,
            text=message_text,
            extra={
                "type": "bills_announcement",
                "round_id": round_id,
                "round_number": round_number,
            },
        )
        delivery_status = "sent" if sent else "failed"
    except Exception as exc:
        logger.warning("Error dispatching Nexconn bills announcement: %s", exc)
        delivery_status = "failed"

    # Update round announcement final delivery state
    update_data = {
        "bills_announcement": {
            "status": delivery_status,
            "attempts": attempts,
            "sent_at": now if sent else None,
            "last_attempt_at": now,
            "message_text": message_text,
        },
        "updated_at": now,
    }
    await rounds_col.update_one({"_id": ObjectId(round_id)}, {"$set": update_data})

    # Update bills status to PUBLISHED if sent
    if sent:
        await bills_col.update_many(
            {
                "society_id": society_id,
                "round_id": round_id,
                "status": BillStatus.FINALIZED.value,
            },
            {"$set": {"status": BillStatus.PUBLISHED.value, "published_at": now, "updated_at": now}},
        )

    return PublishBillsAnnouncementResponse(
        society_id=society_id,
        round_id=round_id,
        round_number=round_number,
        group_id=group_id,
        message_text=message_text,
        sent=sent,
        delivery_status=delivery_status,
        attempts=attempts,
        published_at=now,
    )


# ============================================================================
# 5. Resident Billing Access
# ============================================================================

async def get_my_bills(user_id: str) -> List[GroceryBillResponse]:
    """Retrieve all grocery bills belonging strictly to the authenticated resident."""
    bills_col = get_grocery_bills_collection()
    cursor = bills_col.find({
        "user_id": user_id,
        "status": {"$ne": BillStatus.CANCELLED.value},
    }).sort("created_at", -1)

    results = []
    async for doc in cursor:
        results.append(_serialize_bill(doc))
    return results


async def get_my_bill_by_id(user_id: str, bill_id: str) -> GroceryBillResponse:
    """Retrieve a specific bill. Enforces that only the bill's owner can access it."""
    bills_col = get_grocery_bills_collection()
    bill = await bills_col.find_one({"_id": ObjectId(bill_id)})
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found.")

    if str(bill["user_id"]) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only access grocery bills for your own flat.",
        )

    return _serialize_bill(bill)


# ============================================================================
# 6. Society Spending Summary
# ============================================================================

async def get_society_spending_summary(
    society_id: str,
    round_id: str,
    user_id: str,
) -> SocietySpendingSummaryResponse:
    """Calculate and return society expenditure, allocation, and reconciliation summary.

    Uses Decimal-safe arithmetic to ensure mathematical identity:
    Actual Purchase Cost = Allocated Bill Costs + Shared Costs + Unallocated Cost
    """
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    rounds_col = get_order_rounds_collection()
    round_doc = await rounds_col.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found.")

    round_number = round_doc.get("round_number", 1)

    # 1. Total actual purchases (Decimal)
    purchases_col = get_purchase_records_collection()
    purchases = await purchases_col.find({"society_id": society_id, "round_id": round_id}).to_list(length=1000)
    total_purchase_cost_dec = _quantize_paise(sum(_to_decimal(p["total_price"]) for p in purchases))
    total_purchase_cost = float(total_purchase_cost_dec)

    # 2. Total allocated bills (Decimal)
    bills_col = get_grocery_bills_collection()
    bills = await bills_col.find({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$in": [BillStatus.FINALIZED.value, BillStatus.PUBLISHED.value, BillStatus.CORRECTED.value]},
    }).to_list(length=1000)

    total_allocated_dec = _quantize_paise(sum((_to_decimal(b["items_subtotal"]) for b in bills), Decimal("0.00")))
    total_allocated = float(total_allocated_dec)

    total_shared_dec = _quantize_paise(sum((_to_decimal(b.get("shared_costs_total", 0.0)) for b in bills), Decimal("0.00")))
    total_shared = float(total_shared_dec)

    unallocated_cost_dec = max(Decimal("0.00"), total_purchase_cost_dec - total_allocated_dec)
    unallocated_cost = float(unallocated_cost_dec)

    reconciled_sum_dec = total_allocated_dec + unallocated_cost_dec
    diff_dec = abs(total_purchase_cost_dec - reconciled_sum_dec)
    is_reconciled = (diff_dec <= Decimal("0.02"))

    discrepancies = []
    if not is_reconciled:
        discrepancies.append(
            f"Unresolved discrepancy: Total actual cost Rs {total_purchase_cost:.2f} does not match "
            f"allocated total Rs {total_allocated:.2f} + unallocated Rs {unallocated_cost:.2f}."
        )

    # Counts
    unfulfilled_items = sum(
        1 for b in bills for it in b.get("items", []) if it.get("is_unfulfilled")
    )
    substituted_items = sum(
        1 for b in bills for it in b.get("items", []) if it.get("is_substituted")
    )

    equation = (
        f"₹{total_purchase_cost:.2f} (Actual) = "
        f"₹{total_allocated:.2f} (Allocated) + "
        f"₹{total_shared:.2f} (Shared) + "
        f"₹{unallocated_cost:.2f} (Unallocated)"
    )

    return SocietySpendingSummaryResponse(
        society_id=society_id,
        round_id=round_id,
        round_number=round_number,
        total_actual_purchase_cost=total_purchase_cost,
        total_allocated_bill_costs=total_allocated,
        total_shared_costs=total_shared,
        total_unallocated_cost=unallocated_cost,
        is_reconciled=is_reconciled,
        reconciliation_equation=equation,
        total_purchased_items_count=len(purchases),
        total_flats_billed=len(bills),
        total_finalized_bills=len(bills),
        total_unfulfilled_items_count=unfulfilled_items,
        total_substituted_items_count=substituted_items,
        unresolved_discrepancies=discrepancies,
    )


# ============================================================================
# 7. Retail Benchmark Prices and Verified Savings Analysis
# ============================================================================

async def record_retail_benchmark(
    society_id: str,
    user_id: str,
    req: RecordBenchmarkRequest,
) -> RetailBenchmarkResponse:
    """Store verifiable individual retail benchmark price evidence.

    Initial state is 'pending' verification. An explicit verification workflow
    by an authorized volunteer or admin is required before it enters the savings engine.
    """
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    norm_size, norm_unit = normalize_unit_and_quantity(req.package_size, req.package_unit)
    if norm_size is None or norm_size <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid package size.")

    norm_size_dec = _to_decimal(norm_size)
    price_dec = _to_decimal(req.benchmark_price)
    benchmark_unit_price_dec = _quantize_unit_cost(price_dec / norm_size_dec)
    benchmark_unit_price = float(benchmark_unit_price_dec)

    now = datetime.now(timezone.utc)

    doc = {
        "society_id": society_id,
        "product_name": req.product_name.strip(),
        "brand": req.brand.strip() if req.brand else None,
        "variant": req.variant.strip() if req.variant else None,
        "package_size": norm_size,
        "package_unit": norm_unit,
        "benchmark_price": round(req.benchmark_price, 2),
        "benchmark_unit_price": benchmark_unit_price,
        "store_name": req.store_name.strip(),
        "source_type": req.source_type.strip(),
        "evidence_ref": req.evidence_ref.strip() if req.evidence_ref else None,
        "evidence_url": req.evidence_url.strip() if req.evidence_url else None,
        "evidence_date": _ensure_utc(req.evidence_date),
        "location": req.location.strip(),
        "verification_status": BenchmarkVerificationStatus.PENDING.value,
        "verified_by": None,
        "verified_at": None,
        "created_at": now,
        "updated_at": now,
    }

    col = get_retail_benchmarks_collection()
    res = await col.insert_one(doc)
    doc["_id"] = res.inserted_id
    logger.info("Recorded retail benchmark evidence %s for %s (status=pending)", res.inserted_id, req.product_name)
    return _serialize_benchmark(doc)


async def verify_retail_benchmark(
    society_id: str,
    round_id: str,
    benchmark_id: str,
    user_id: str,
    req: VerifyBenchmarkRequest,
) -> RetailBenchmarkResponse:
    """Explicitly verify or reject a retail benchmark price evidence record."""
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin"]
    )

    col = get_retail_benchmarks_collection()
    now = datetime.now(timezone.utc)

    updated = await col.find_one_and_update(
        {"_id": ObjectId(benchmark_id), "society_id": society_id},
        {
            "$set": {
                "verification_status": req.status.value,
                "verified_by": user_id,
                "verified_at": now,
                "verification_notes": req.notes.strip() if req.notes else None,
                "updated_at": now,
            }
        },
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retail benchmark not found.")

    logger.info(
        "Benchmark %s verification status updated to %s by user %s",
        benchmark_id, req.status.value, user_id
    )
    return _serialize_benchmark(updated)


async def list_retail_benchmarks(
    society_id: str,
    user_id: str,
) -> List[RetailBenchmarkResponse]:
    """List all retail benchmark prices recorded for a society."""
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin", "resident"]
    )
    col = get_retail_benchmarks_collection()
    cursor = col.find({"society_id": society_id}).sort("product_name", 1)
    results = []
    async for doc in cursor:
        results.append(_serialize_benchmark(doc))
    return results


async def calculate_society_savings(
    society_id: str,
    round_id: str,
    user_id: str,
) -> SocietySavingsSummaryResponse:
    """Calculate verified bulk savings against verified retail benchmark evidence.

    Comparability Rules:
    - Same product name, brand, variant, and normalized unit.
    - Strictly filters for 'verified' benchmarks; excludes pending or rejected benchmarks.
    - If benchmark evidence is missing or stale (>90 days old): marked as Unavailable.
    - Uses actual physical quantities allocated per flat.
    - NEVER extrapolates partial results to unbenchmarked items.
    - Zero or negative savings are presented honestly.
    """
    await membership_service.require_society_role(
        user_id, society_id, ["volunteer", "admin", "resident"]
    )

    rounds_col = get_order_rounds_collection()
    round_doc = await rounds_col.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found.")

    round_number = round_doc.get("round_number", 1)

    # 1. Fetch all allocated items from finalized bills or preview
    bills_col = get_grocery_bills_collection()
    bills = await bills_col.find({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$in": [BillStatus.FINALIZED.value, BillStatus.PUBLISHED.value, BillStatus.CORRECTED.value]},
    }).to_list(length=1000)

    # Aggregate total allocated quantities by item using Decimal
    allocated_by_item: Dict[str, Dict[str, Any]] = {}
    if bills:
        for b in bills:
            for it in b.get("items", []):
                alloc_qty = float(it.get("allocated_quantity", 0.0))
                if alloc_qty <= 0:
                    continue
                name = it["item_name"]
                brand = it.get("brand")
                variant = it.get("variant")
                unit = it["unit"]
                key = f"{name.lower()}__{str(brand or '').lower()}__{str(variant or '').lower()}__{unit.lower()}"
                if key not in allocated_by_item:
                    allocated_by_item[key] = {
                        "item_name": name,
                        "brand": brand,
                        "variant": variant,
                        "unit": unit,
                        "quantity": 0.0,
                        "bulk_cost_dec": Decimal("0.00"),
                        "unit_price": float(it.get("unit_price", 0.0)),
                    }
                allocated_by_item[key]["quantity"] = round(allocated_by_item[key]["quantity"] + alloc_qty, 3)
                allocated_by_item[key]["bulk_cost_dec"] += _to_decimal(it.get("item_total", 0.0))
    else:
        # Fall back to allocation preview
        preview = await calculate_allocation(society_id, round_id, user_id)
        for ms in preview.matching_summaries:
            if ms.fulfilled_quantity <= 0:
                continue
            key = f"{ms.item_name.lower()}__{str(ms.brand or '').lower()}__{str(ms.variant or '').lower()}__{ms.unit.lower()}"
            allocated_by_item[key] = {
                "item_name": ms.item_name,
                "brand": ms.brand,
                "variant": ms.variant,
                "unit": ms.unit,
                "quantity": ms.fulfilled_quantity,
                "bulk_cost_dec": _to_decimal(ms.total_cost),
                "unit_price": ms.effective_unit_cost,
            }

    # 2. Fetch strictly verified benchmarks
    benchmarks_col = get_retail_benchmarks_collection()
    benchmarks = await benchmarks_col.find({
        "society_id": society_id,
        "verification_status": BenchmarkVerificationStatus.VERIFIED.value,
    }).to_list(length=1000)

    now = datetime.now(timezone.utc)
    ninety_days_ago = now - timedelta(days=90)

    # 3. Compare items against verified benchmarks
    item_savings_list: List[ItemSavingsDetail] = []
    total_comparable_bulk_cost_dec = Decimal("0.00")
    total_individual_benchmark_cost_dec = Decimal("0.00")
    verified_benchmark_count = 0
    excluded_count = 0

    for key, data in allocated_by_item.items():
        name = data["item_name"].strip().lower()
        brand = (data["brand"] or "").strip().lower()
        variant = (data["variant"] or "").strip().lower()
        unit = data["unit"].strip().lower()
        qty = data["quantity"]
        bulk_cost_dec = _quantize_paise(data["bulk_cost_dec"])
        bulk_cost = float(bulk_cost_dec)
        bulk_unit_price = data["unit_price"]

        # Find matching verified benchmark
        matched_bench = None
        for b in benchmarks:
            b_name = b["product_name"].strip().lower()
            b_brand = (b.get("brand") or "").strip().lower()
            b_variant = (b.get("variant") or "").strip().lower()
            b_unit = b.get("package_unit", "").strip().lower()

            # Must match product, brand (where specified), variant, and unit
            if (
                b_name == name
                and (not brand or b_brand == brand)
                and (not variant or b_variant == variant)
                and b_unit == unit
            ):
                # Check for evidence freshness (<= 90 days)
                ev_date = _ensure_utc(b.get("evidence_date"))
                if ev_date < ninety_days_ago:
                    logger.warning("Benchmark %s is older than 90 days (stale evidence).", b["_id"])
                    continue
                matched_bench = b
                break

        if matched_bench:
            bench_unit_price_dec = _to_decimal(matched_bench.get("benchmark_unit_price", 0.0))
            bench_cost_dec = _quantize_paise(_to_decimal(qty) * bench_unit_price_dec)
            bench_cost = float(bench_cost_dec)
            item_savings_dec = _quantize_paise(bench_cost_dec - bulk_cost_dec)
            item_savings = float(item_savings_dec)

            savings_pct = (
                round(float((item_savings_dec / bench_cost_dec) * Decimal("100")), 1)
                if bench_cost_dec > 0
                else 0.0
            )

            total_comparable_bulk_cost_dec += bulk_cost_dec
            total_individual_benchmark_cost_dec += bench_cost_dec
            verified_benchmark_count += 1

            item_savings_list.append(
                ItemSavingsDetail(
                    item_name=data["item_name"],
                    brand=data["brand"],
                    variant=data["variant"],
                    quantity=qty,
                    unit=data["unit"],
                    bulk_cost=bulk_cost,
                    bulk_unit_price=bulk_unit_price,
                    has_benchmark=True,
                    benchmark_price=matched_bench["benchmark_price"],
                    benchmark_unit_price=float(bench_unit_price_dec),
                    benchmark_store=matched_bench["store_name"],
                    benchmark_date=_ensure_utc(matched_bench.get("evidence_date")),
                    benchmark_cost=bench_cost,
                    savings_amount=item_savings,
                    savings_percentage=savings_pct,
                    status_label="Verified Savings",
                    unavailability_reason=None,
                )
            )
        else:
            excluded_count += 1
            item_savings_list.append(
                ItemSavingsDetail(
                    item_name=data["item_name"],
                    brand=data["brand"],
                    variant=data["variant"],
                    quantity=qty,
                    unit=data["unit"],
                    bulk_cost=bulk_cost,
                    bulk_unit_price=bulk_unit_price,
                    has_benchmark=False,
                    benchmark_price=None,
                    benchmark_unit_price=None,
                    benchmark_store=None,
                    benchmark_date=None,
                    benchmark_cost=None,
                    savings_amount=None,
                    savings_percentage=None,
                    status_label="Benchmark Unavailable",
                    unavailability_reason="No verified retail benchmark price available for this brand/variant",
                )
            )

    verified_savings_amount_dec = _quantize_paise(
        total_individual_benchmark_cost_dec - total_comparable_bulk_cost_dec
    )
    verified_savings_amount = float(verified_savings_amount_dec)
    verified_savings_percentage = (
        round(
            float((verified_savings_amount_dec / total_individual_benchmark_cost_dec) * Decimal("100")),
            1,
        )
        if total_individual_benchmark_cost_dec > 0
        else 0.0
    )

    return SocietySavingsSummaryResponse(
        society_id=society_id,
        round_id=round_id,
        round_number=round_number,
        total_bulk_cost_comparable_items=float(total_comparable_bulk_cost_dec),
        total_individual_benchmark_cost=float(total_individual_benchmark_cost_dec),
        verified_savings_amount=verified_savings_amount,
        verified_savings_percentage=verified_savings_percentage,
        total_items_evaluated=len(allocated_by_item),
        items_with_verified_benchmarks=verified_benchmark_count,
        items_excluded_count=excluded_count,
        is_partial_coverage=(excluded_count > 0),
        label="Verified Savings",
        items=item_savings_list,
    )
