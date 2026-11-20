"""Pydantic schemas for AI-interpreted grocery orders and items.
"""

from datetime import datetime
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

GroceryCategory = Literal[
    "grains_rice",
    "pulses",
    "vegetables",
    "fruits",
    "dairy",
    "cooking_oils",
    "spices",
    "household_essentials",
    "personal_care",
    "other",
]

OrderStatus = Literal[
    "processing",
    "pending_review",
    "awaiting_confirmation",
    "needs_clarification",
    "confirmed",
    "rejected",
    "failed",
]


class GroceryItemSchema(BaseModel):
    """Schema representing an individual structured grocery item."""

    id: str = Field(..., description="Unique client or item identifier, e.g. item_1")
    original_name: str = Field(..., min_length=1, max_length=120, description="Item name in original language/script")
    normalized_name: str = Field(..., min_length=1, max_length=120, description="Standardized English grocery item name")
    quantity: Optional[float] = Field(None, description="Item quantity (positive number, or None if clarification needed)")
    unit: Optional[str] = Field(None, max_length=30, description="Measurement unit e.g. kg, g, L, ml, packet, piece")
    category: str = Field("other", description="Grocery item category")
    brand: Optional[str] = Field(None, max_length=80, description="Optional brand specified by resident")
    variant: Optional[str] = Field(None, max_length=80, description="Optional product variant (e.g. sunflower, whole-wheat)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    needs_clarification: bool = Field(False, description="Whether this item requires clarification from the resident")
    clarification_reason: Optional[str] = Field(None, max_length=300, description="Reason why clarification is requested")

    @field_validator("quantity")
    @classmethod
    def validate_positive_quantity(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be a positive number greater than 0.")
        return v

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Optional[str]) -> str:
        if not v:
            return "other"
        clean = str(v).strip().lower().replace("-", "_").replace(" ", "_")
        mapping = {
            "grains_and_rice": "grains_rice",
            "grains_rice": "grains_rice",
            "grains": "grains_rice",
            "grain": "grains_rice",
            "rice": "grains_rice",
            "cereal": "grains_rice",
            "flour": "grains_rice",
            "atta": "grains_rice",
            "pulses_and_lentils": "pulses",
            "pulses_lentils": "pulses",
            "pulses": "pulses",
            "lentils": "pulses",
            "dal": "pulses",
            "dals": "pulses",
            "vegetable": "vegetables",
            "vegetables": "vegetables",
            "produce": "vegetables",
            "herbs": "vegetables",
            "fruit": "fruits",
            "fruits": "fruits",
            "dairy": "dairy",
            "oil": "cooking_oils",
            "oils": "cooking_oils",
            "cooking_oil": "cooking_oils",
            "cooking_oils": "cooking_oils",
            "spice": "spices",
            "spices": "spices",
            "condiments": "spices",
            "household": "household_essentials",
            "household_essentials": "household_essentials",
            "cleaning": "household_essentials",
            "personal_care": "personal_care",
            "cosmetics": "personal_care",
            "bakery": "other",
        }
        canonical = mapping.get(clean, clean)
        valid = (
            "grains_rice",
            "pulses",
            "vegetables",
            "fruits",
            "dairy",
            "cooking_oils",
            "spices",
            "household_essentials",
            "personal_care",
            "other",
        )
        return canonical if canonical in valid else "other"

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = v.strip().lower()
        # Common unit normalization
        unit_map = {
            "kgs": "kg",
            "kilos": "kg",
            "kilo": "kg",
            "kilogram": "kg",
            "kilograms": "kg",
            "gms": "g",
            "gm": "g",
            "gram": "g",
            "grams": "g",
            "liters": "L",
            "litres": "L",
            "liter": "L",
            "litre": "L",
            "ltr": "L",
            "ltrs": "L",
            "l": "L",
            "milliliters": "ml",
            "millilitres": "ml",
            "packets": "packet",
            "pkt": "packet",
            "pkts": "packet",
            "pack": "packet",
            "packs": "packet",
            "pieces": "piece",
            "pcs": "piece",
            "pc": "piece",
            "bunches": "bunch",
            "dozens": "dozen",
            "dz": "dozen",
            "bottles": "bottle",
            "cans": "can",
            "boxes": "box",
        }
        return unit_map.get(clean, clean)


class AIExtractionOutput(BaseModel):
    """Direct validated output returned by the Groq AI extraction prompt."""

    detected_language: str = Field("en", description="Detected language code: en, te, hi, mixed")
    items: List[GroceryItemSchema] = Field(default_factory=list, description="Extracted grocery items")
    overall_status: Literal["pending_review", "awaiting_confirmation", "needs_clarification"] = Field(
        "pending_review", description="Overall interpretation readiness"
    )
    clarification_prompt: Optional[str] = Field(None, description="Clarification question for resident if needed")

    @field_validator("overall_status", mode="before")
    @classmethod
    def normalize_overall_status(cls, v: Any) -> str:
        if v == "awaiting_confirmation":
            return "pending_review"
        return str(v)


class ClarificationHistoryEntry(BaseModel):
    """Record of a resident clarification round."""

    prompt: str = Field(..., description="Clarification question asked to resident")
    resident_response: str = Field(..., description="Resident's clarification message")
    timestamp: datetime = Field(..., description="Timestamp of the clarification")


class GroceryOrderResponse(BaseModel):
    """Full public representation of a resident's structured grocery order."""

    id: str = Field(..., description="Order document ID")
    society_id: str = Field(..., description="Society ID")
    round_id: str = Field(..., description="Order round ID")
    round_number: int = Field(..., description="Round number")
    submission_id: str = Field(..., description="Associated submission reservation ID")
    message_id: str = Field(..., description="Nexconn group message ID")
    user_id: str = Field(..., description="Resident user ID")
    flat_number: str = Field(..., description="Resident flat number")
    user_name: str = Field(..., description="Resident name")
    raw_text: str = Field(..., description="Original raw grocery request (immutable)")
    detected_language: str = Field("en", description="Detected language: en, te, hi, mixed")
    items: List[GroceryItemSchema] = Field(default_factory=list, description="Structured grocery items")
    status: OrderStatus = Field("processing", description="Current order review/confirmation status")
    clarification_prompt: Optional[str] = Field(None, description="Active clarification prompt if any")
    clarification_history: List[ClarificationHistoryEntry] = Field(default_factory=list, description="Clarification log")
    ai_model: str = Field(..., description="Groq AI model used for extraction")
    prompt_version: str = Field("v1.0", description="Prompt template version")
    created_at: datetime = Field(..., description="Order creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Resident confirmation timestamp")
    recovery_attempts: int = Field(0, description="Number of recovery attempts following server restarts")
    processing_lease_id: Optional[str] = Field(None, description="Active lease ID if currently processing")
    processing_lease_until: Optional[datetime] = Field(None, description="Lease expiration timestamp")


class ClarifyOrderRequest(BaseModel):
    """Payload when resident provides additional context to clarify ambiguous items."""

    clarification_text: str = Field(..., min_length=1, max_length=1000, description="Resident clarification text")

    @field_validator("clarification_text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Clarification text cannot be empty.")
        return clean


class UpdateOrderItemsRequest(BaseModel):
    """Payload when resident manually adjusts or adds/removes items."""

    items: List[GroceryItemSchema] = Field(..., min_length=1, description="Updated list of grocery items")
