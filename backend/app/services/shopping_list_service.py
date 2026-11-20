"""Service for compiling, aggregating, persisting, and exporting society shopping lists.
"""

import csv
from datetime import datetime, timezone
import io
import logging
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.core.database import (
    get_grocery_orders_collection,
    get_order_rounds_collection,
    get_shopping_lists_collection,
    get_societies_collection,
)
from app.schemas.shopping_list import (
    CategoryGroup,
    CompiledShoppingListResponse,
    ConsolidatedItem,
    ContributingFlat,
    FlatPackingBreakdown,
    PackingFlatItem,
    ShoppingListSummary,
    UnresolvedOrderInfo,
)

logger = logging.getLogger(__name__)

# Canonical 10 categories with clean display titles
CATEGORY_METADATA: Dict[str, str] = {
    "grains_rice": "Rice & Grains",
    "pulses": "Pulses",
    "vegetables": "Vegetables",
    "fruits": "Fruits",
    "dairy": "Dairy",
    "cooking_oils": "Cooking Oils",
    "spices": "Spices",
    "household_essentials": "Household Essentials",
    "personal_care": "Personal Care",
    "other": "Other",
}

# Mass unit mappings to kg
MASS_GRAM_UNITS = {"g", "gram", "grams", "gm", "gms"}
MASS_KG_UNITS = {"kg", "kilogram", "kilograms", "kgs"}

# Volume unit mappings to L
VOLUME_ML_UNITS = {"ml", "millilitre", "millilitres", "milliliter", "milliliters"}
VOLUME_L_UNITS = {"l", "litre", "litres", "liter", "liters", "ltr", "ltrs"}

# Count / discrete unit normalizations
DISCRETE_UNIT_MAP = {
    "packet": "packet",
    "packets": "packet",
    "pkt": "packet",
    "pkts": "packet",
    "piece": "piece",
    "pieces": "piece",
    "pc": "piece",
    "pcs": "piece",
    "bunch": "bunch",
    "bunches": "bunch",
    "box": "box",
    "boxes": "box",
    "bottle": "bottle",
    "bottles": "bottle",
    "can": "can",
    "cans": "can",
    "dozen": "dozen",
    "dozens": "dozen",
    "loaf": "loaf",
    "loaves": "loaf",
    "bag": "bag",
    "bags": "bag",
    "jar": "jar",
    "jars": "jar",
    "bar": "bar",
    "bars": "bar",
}


def normalize_unit_and_quantity(
    raw_quantity: Optional[float],
    raw_unit: Optional[str],
) -> Tuple[Optional[float], str]:
    """Normalize compatible measurement units (e.g. grams to kg, ml to L).

    Returns:
        Tuple[Optional[float], str]: Normalized (quantity, unit).
    """
    if raw_unit is None or not raw_unit.strip():
        norm_unit = "item"
    else:
        norm_unit = raw_unit.strip().lower()

    if raw_quantity is None or raw_quantity <= 0:
        return (None, norm_unit)

    # 1. Mass normalization: convert grams to kg
    if norm_unit in MASS_GRAM_UNITS:
        return (round(raw_quantity / 1000.0, 3), "kg")
    if norm_unit in MASS_KG_UNITS:
        return (round(raw_quantity, 3), "kg")

    # 2. Volume normalization: convert ml to L
    if norm_unit in VOLUME_ML_UNITS:
        return (round(raw_quantity / 1000.0, 3), "L")
    if norm_unit in VOLUME_L_UNITS:
        return (round(raw_quantity, 3), "L")

    # 3. Discrete unit normalization
    if norm_unit in DISCRETE_UNIT_MAP:
        return (round(raw_quantity, 2), DISCRETE_UNIT_MAP[norm_unit])

    # Default fallback: preserve unit name cleaned
    return (round(raw_quantity, 2), norm_unit)


def _build_aggregation_key(
    normalized_name: str,
    brand: Optional[str],
    variant: Optional[str],
    normalized_unit: str,
    category: str,
) -> str:
    """Generate a deterministic aggregation key.

    Items combine ONLY when name, brand, variant, category, and normalized unit all match.
    """
    n_name = normalized_name.strip().lower()
    n_brand = (brand or "").strip().lower()
    n_variant = (variant or "").strip().lower()
    n_unit = normalized_unit.strip().lower()
    n_cat = category.strip().lower()
    return f"{n_cat}__{n_name}__{n_brand}__{n_variant}__{n_unit}"


def _ensure_utc(dt: Optional[datetime]) -> datetime:
    """Ensure datetime is UTC-aware."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def compile_shopping_list(
    society_id: str,
    round_id: str,
    user_id: str,
) -> CompiledShoppingListResponse:
    """Compile or recompile the consolidated society shopping list from confirmed orders.

    Rules:
    - Only orders with status 'confirmed' enter the shopping list.
    - Excludes pending_review, needs_clarification, processing, failed, and rejected orders.
    - Safe unit normalization (g -> kg, ml -> L).
    - Incompatible units, different brands, and different variants remain separate entries.
    - Flat-wise packing breakdown generated for individual resident order fulfillment.
    - Unresolved orders tracked with diagnostics.
    - Atomically updates shopping_lists collection with incremented version.
    """
    # 1. Verify Society & Round existence
    rounds_col = get_order_rounds_collection()
    round_doc = await rounds_col.find_one({"_id": ObjectId(round_id), "society_id": society_id})
    if not round_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grocery order round not found in this society.",
        )

    round_number = int(round_doc.get("round_number", 1))
    round_title = round_doc.get("title", f"Grocery Round #{round_number}")
    shopping_date = str(round_doc.get("shopping_date", ""))

    # 2. Fetch all orders for this society round with captured read snapshot timestamp
    read_snapshot_at = datetime.now(timezone.utc)
    orders_col = get_grocery_orders_collection()
    cursor = orders_col.find({"society_id": society_id, "round_id": round_id})
    all_orders = await cursor.to_list(length=1000)

    # 3. Partition orders by eligibility & prevent duplicate source orders
    seen_order_ids = set()
    seen_sub_ids = set()
    confirmed_orders: List[Dict[str, Any]] = []
    unresolved_orders_list: List[UnresolvedOrderInfo] = []
    rejected_count = 0

    for order in all_orders:
        st = order.get("status", "processing")
        if st == "confirmed":
            oid = str(order["_id"])
            sub_id = str(order.get("submission_id", ""))
            # Strict duplicate order protection
            if oid in seen_order_ids or (sub_id and sub_id in seen_sub_ids):
                continue
            seen_order_ids.add(oid)
            if sub_id:
                seen_sub_ids.add(sub_id)
            confirmed_orders.append(order)
        elif st in ("pending_review", "awaiting_confirmation", "needs_clarification", "processing", "failed"):
            unresolved_orders_list.append(
                UnresolvedOrderInfo(
                    order_id=str(order["_id"]),
                    flat_number=str(order.get("flat_number", "Unknown")),
                    user_id=str(order.get("user_id", "")),
                    user_name=str(order.get("user_name", "Resident")),
                    status=st,
                    clarification_prompt=order.get("clarification_prompt"),
                    error_message=order.get("error_message"),
                    raw_text=order.get("raw_text", ""),
                    updated_at=_ensure_utc(order.get("updated_at")),
                )
            )
        elif st == "rejected":
            rejected_count += 1

    # 4. Aggregate confirmed grocery items
    # Map key -> ConsolidatedItem dict
    aggregated_items_map: Dict[str, Dict[str, Any]] = {}
    flat_packing_map: Dict[str, Dict[str, Any]] = {}
    total_item_rows = 0

    for order in confirmed_orders:
        order_id_str = str(order["_id"])
        flat_number = str(order.get("flat_number", "Unknown"))
        user_id_str = str(order.get("user_id", ""))
        user_name = str(order.get("user_name", "Resident"))

        if flat_number not in flat_packing_map:
            flat_packing_map[flat_number] = {
                "flat_number": flat_number,
                "user_id": user_id_str,
                "user_name": user_name,
                "order_id": order_id_str,
                "items": [],
            }

        order_items = order.get("items", [])
        for it in order_items:
            total_item_rows += 1
            raw_qty = it.get("quantity")
            raw_unit = it.get("unit")
            norm_name = it.get("normalized_name") or it.get("original_name") or "Item"
            orig_name = it.get("original_name", norm_name)
            brand = it.get("brand") or None
            variant = it.get("variant") or None
            category = it.get("category", "other")
            if category not in CATEGORY_METADATA:
                category = "other"

            norm_qty, norm_unit = normalize_unit_and_quantity(raw_qty, raw_unit)
            has_unspecified = (norm_qty is None)

            # Flat-wise packing item
            flat_packing_map[flat_number]["items"].append(
                PackingFlatItem(
                    item_id=str(it.get("id", f"item_{total_item_rows}")),
                    original_name=orig_name,
                    normalized_name=norm_name,
                    brand=brand,
                    variant=variant,
                    quantity=norm_qty,
                    unit=norm_unit,
                    category=category,
                )
            )

            # Build aggregation key
            agg_key = _build_aggregation_key(
                normalized_name=norm_name,
                brand=brand,
                variant=variant,
                normalized_unit=norm_unit,
                category=category,
            )

            add_qty = norm_qty if norm_qty is not None else 0.0

            if agg_key not in aggregated_items_map:
                aggregated_items_map[agg_key] = {
                    "item_key": agg_key,
                    "normalized_name": norm_name,
                    "brand": brand,
                    "variant": variant,
                    "category": category,
                    "total_quantity": add_qty,
                    "unit": norm_unit,
                    "contributing_flats": [
                        ContributingFlat(
                            flat_number=flat_number,
                            user_id=user_id_str,
                            user_name=user_name,
                            order_id=order_id_str,
                            quantity=add_qty,
                            unit=norm_unit,
                            notes=orig_name if orig_name != norm_name else None,
                        )
                    ],
                    "original_names": {orig_name},
                    "has_unspecified_quantity": has_unspecified,
                }
            else:
                aggregated_items_map[agg_key]["total_quantity"] += add_qty
                aggregated_items_map[agg_key]["total_quantity"] = round(
                    aggregated_items_map[agg_key]["total_quantity"], 3
                )
                aggregated_items_map[agg_key]["original_names"].add(orig_name)
                if has_unspecified:
                    aggregated_items_map[agg_key]["has_unspecified_quantity"] = True
                aggregated_items_map[agg_key]["contributing_flats"].append(
                    ContributingFlat(
                        flat_number=flat_number,
                        user_id=user_id_str,
                        user_name=user_name,
                        order_id=order_id_str,
                        quantity=add_qty,
                        unit=norm_unit,
                        notes=orig_name if orig_name != norm_name else None,
                    )
                )

    # 5. Group aggregated items into categories
    categories_dict: Dict[str, List[ConsolidatedItem]] = {cat: [] for cat in CATEGORY_METADATA.keys()}

    for item_data in aggregated_items_map.values():
        c_item = ConsolidatedItem(
            item_key=item_data["item_key"],
            normalized_name=item_data["normalized_name"],
            brand=item_data["brand"],
            variant=item_data["variant"],
            category=item_data["category"],
            total_quantity=round(item_data["total_quantity"], 3),
            unit=item_data["unit"],
            contributing_flats=item_data["contributing_flats"],
            contributing_flats_count=len(set(cf.flat_number for cf in item_data["contributing_flats"])),
            original_names=sorted(list(item_data["original_names"])),
            has_unspecified_quantity=item_data["has_unspecified_quantity"],
            is_purchased=False,
        )
        cat = item_data["category"]
        if cat in categories_dict:
            categories_dict[cat].append(c_item)
        else:
            categories_dict["other"].append(c_item)

    # Convert to CategoryGroup list, sorted with canonical category order
    category_groups: List[CategoryGroup] = []
    total_distinct_items = 0
    for cat_key, cat_title in CATEGORY_METADATA.items():
        items_in_cat = categories_dict.get(cat_key, [])
        # Sort items alphabetically by normalized_name, then brand
        items_in_cat.sort(key=lambda x: (x.normalized_name.lower(), (x.brand or "").lower()))
        total_distinct_items += len(items_in_cat)
        category_groups.append(
            CategoryGroup(
                category=cat_key,
                category_name=cat_title,
                items=items_in_cat,
                item_count=len(items_in_cat),
            )
        )

    # 6. Build Flat-wise packing breakdown list sorted by flat number
    flat_breakdown_list: List[FlatPackingBreakdown] = []
    for flat_num, f_data in sorted(flat_packing_map.items(), key=lambda x: x[0]):
        flat_breakdown_list.append(
            FlatPackingBreakdown(
                flat_number=f_data["flat_number"],
                user_id=f_data["user_id"],
                user_name=f_data["user_name"],
                order_id=f_data["order_id"],
                items=f_data["items"],
                total_items=len(f_data["items"]),
            )
        )

    # 7. Summary calculation
    confirmed_flats_set = set(o.get("flat_number") for o in confirmed_orders if o.get("flat_number"))
    unresolved_flats_set = set(u.flat_number for u in unresolved_orders_list)

    summary = ShoppingListSummary(
        total_confirmed_flats=len(confirmed_flats_set),
        total_confirmed_orders=len(confirmed_orders),
        total_distinct_items=total_distinct_items,
        total_items_count=total_item_rows,
        total_unresolved_flats=len(unresolved_flats_set),
        total_unresolved_orders=len(unresolved_orders_list),
        has_unresolved_orders=len(unresolved_orders_list) > 0,
        rejected_orders_count=rejected_count,
    )

    now = datetime.now(timezone.utc)
    shopping_lists_col = get_shopping_lists_collection()

    # 8. Safe Snapshot Concurrency Control & Versioning
    # Recompilation always calculates from fresh source confirmed orders
    upsert_doc = {
        "society_id": society_id,
        "round_id": round_id,
        "round_number": round_number,
        "round_title": round_title,
        "shopping_date": shopping_date,
        "compiled_at": now,
        "source_snapshot_at": read_snapshot_at,
        "compiled_by_user_id": user_id,
        "summary": summary.model_dump(),
        "categories": [cg.model_dump() for cg in category_groups],
        "packing_breakdown": [fb.model_dump() for fb in flat_breakdown_list],
        "unresolved_orders": [uo.model_dump() for uo in unresolved_orders_list],
        "confirmed_order_ids": [str(o["_id"]) for o in confirmed_orders],
        "updated_at": now,
    }

    # Optimistic concurrency check against source snapshot
    existing = await shopping_lists_col.find_one({"society_id": society_id, "round_id": round_id})
    if not existing:
        try:
            init_doc = {
                **upsert_doc,
                "version": 1,
                "created_at": now,
            }
            res = await shopping_lists_col.insert_one(init_doc)
            init_doc["_id"] = res.inserted_id
            return _serialize_shopping_list(init_doc)
        except Exception:
            # Another concurrent compilation inserted first
            existing = await shopping_lists_col.find_one({"society_id": society_id, "round_id": round_id})

    if existing:
        existing_snapshot = existing.get("source_snapshot_at")
        if existing_snapshot:
            # Ensure timezone comparability
            if existing_snapshot.tzinfo is None:
                existing_snapshot = existing_snapshot.replace(tzinfo=timezone.utc)
            # If a newer compilation already saved, discard this stale compilation
            if existing_snapshot > read_snapshot_at:
                logger.warning(
                    "Stale compilation snapshot for round %s (read at %s) superseded by newer compilation at %s. Discarding stale write.",
                    round_id,
                    read_snapshot_at,
                    existing_snapshot,
                )
                return _serialize_shopping_list(existing)

        # Atomic compare-and-swap: ensure source_snapshot_at has not advanced past our read_snapshot_at
        persisted = await shopping_lists_col.find_one_and_update(
            {
                "_id": existing["_id"],
                "$or": [
                    {"source_snapshot_at": {"$lte": read_snapshot_at}},
                    {"source_snapshot_at": None},
                ],
            },
            {
                "$set": upsert_doc,
                "$inc": {"version": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not persisted:
            logger.warning(
                "Concurrent compilation race detected for round %s. Stale write rejected.",
                round_id,
            )
            latest = await shopping_lists_col.find_one({"_id": existing["_id"]})
            return _serialize_shopping_list(latest or existing)
        return _serialize_shopping_list(persisted)

    return _serialize_shopping_list(upsert_doc)


async def get_shopping_list(
    society_id: str,
    round_id: str,
) -> Optional[CompiledShoppingListResponse]:
    """Retrieve an existing compiled shopping list for a society round."""
    shopping_lists_col = get_shopping_lists_collection()
    doc = await shopping_lists_col.find_one({"society_id": society_id, "round_id": round_id})
    if not doc:
        return None
    return _serialize_shopping_list(doc)


async def get_unresolved_orders(
    society_id: str,
    round_id: str,
) -> List[UnresolvedOrderInfo]:
    """Retrieve all unconfirmed orders awaiting resident action for a round."""
    orders_col = get_grocery_orders_collection()
    cursor = orders_col.find({
        "society_id": society_id,
        "round_id": round_id,
        "status": {"$in": ["pending_review", "awaiting_confirmation", "needs_clarification", "processing", "failed"]},
    })
    orders = await cursor.to_list(length=500)
    return [
        UnresolvedOrderInfo(
            order_id=str(o["_id"]),
            flat_number=str(o.get("flat_number", "Unknown")),
            user_id=str(o.get("user_id", "")),
            user_name=str(o.get("user_name", "Resident")),
            status=str(o.get("status", "processing")),
            clarification_prompt=o.get("clarification_prompt"),
            error_message=o.get("error_message"),
            raw_text=o.get("raw_text", ""),
            updated_at=_ensure_utc(o.get("updated_at")),
        )
        for o in orders
    ]


def export_shopping_list_csv(
    shopping_list: CompiledShoppingListResponse,
    export_type: str = "consolidated",
) -> str:
    """Generate RFC 4180 compliant CSV export for the compiled shopping list.

    Args:
        shopping_list: The compiled shopping list response.
        export_type: 'consolidated' for bulk purchasing or 'packing' for flat distribution.

    Returns:
        str: CSV string contents.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    if export_type == "packing":
        writer.writerow([
            "Flat Number",
            "Resident Name",
            "Category",
            "Item Name",
            "Brand",
            "Variant",
            "Quantity",
            "Unit",
        ])
        for flat in shopping_list.packing_breakdown:
            for item in flat.items:
                cat_title = CATEGORY_METADATA.get(item.category, item.category)
                writer.writerow([
                    flat.flat_number,
                    flat.user_name,
                    cat_title,
                    item.normalized_name,
                    item.brand or "",
                    item.variant or "",
                    item.quantity if item.quantity is not None else "",
                    item.unit or "",
                ])
    else:
        # Default: consolidated bulk shopping list
        writer.writerow([
            "Category",
            "Item Name",
            "Brand",
            "Variant",
            "Total Quantity",
            "Unit",
            "Contributing Flats Count",
            "Contributing Flats",
        ])
        for cg in shopping_list.categories:
            for item in cg.items:
                flats_str = ", ".join(sorted(set(cf.flat_number for cf in item.contributing_flats)))
                qty_val = (
                    "Unspecified"
                    if (item.has_unspecified_quantity and item.total_quantity == 0)
                    else str(item.total_quantity)
                )
                writer.writerow([
                    cg.category_name,
                    item.normalized_name,
                    item.brand or "",
                    item.variant or "",
                    qty_val,
                    item.unit,
                    item.contributing_flats_count,
                    flats_str,
                ])

    return output.getvalue()


def _serialize_shopping_list(doc: Dict[str, Any]) -> CompiledShoppingListResponse:
    """Convert MongoDB raw shopping list document to response model."""
    summary_data = doc.get("summary", {})
    summary = ShoppingListSummary.model_validate(summary_data)

    categories = [
        CategoryGroup.model_validate(cg) for cg in doc.get("categories", [])
    ]
    packing_breakdown = [
        FlatPackingBreakdown.model_validate(pb) for pb in doc.get("packing_breakdown", [])
    ]
    unresolved_orders = [
        UnresolvedOrderInfo(
            order_id=str(uo.get("order_id", "")),
            flat_number=str(uo.get("flat_number", "")),
            user_id=str(uo.get("user_id", "")),
            user_name=str(uo.get("user_name", "")),
            status=str(uo.get("status", "")),
            clarification_prompt=uo.get("clarification_prompt"),
            error_message=uo.get("error_message"),
            raw_text=uo.get("raw_text", ""),
            updated_at=_ensure_utc(uo.get("updated_at")),
        )
        for uo in doc.get("unresolved_orders", [])
    ]

    return CompiledShoppingListResponse(
        id=str(doc.get("_id", "")),
        society_id=str(doc["society_id"]),
        round_id=str(doc["round_id"]),
        round_number=int(doc.get("round_number", 1)),
        round_title=doc.get("round_title"),
        shopping_date=doc.get("shopping_date"),
        version=int(doc.get("version", 1)),
        compiled_at=_ensure_utc(doc.get("compiled_at")),
        source_snapshot_at=_ensure_utc(doc.get("source_snapshot_at")) if doc.get("source_snapshot_at") else None,
        compiled_by_user_id=str(doc.get("compiled_by_user_id", "")),
        summary=summary,
        categories=categories,
        packing_breakdown=packing_breakdown,
        unresolved_orders=unresolved_orders,
    )
