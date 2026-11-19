"""Pydantic schemas for order rounds and grocery submissions.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

RoundStatus = Literal["draft", "open", "closed", "cancelled"]


class CreateRoundRequest(BaseModel):
    """Schema for creating a new grocery order round."""

    title: str = Field(..., min_length=2, max_length=120, description="Round title")
    description: Optional[str] = Field(None, max_length=500, description="Optional logistics note")
    deadline_at: datetime = Field(..., description="Order submission deadline (UTC)")
    shopping_date: str = Field(..., min_length=2, max_length=60, description="Expected shopping/delivery date")

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Round title cannot be empty.")
        return clean

    @field_validator("deadline_at")
    @classmethod
    def validate_future_deadline(cls, v: datetime) -> datetime:
        # Normalize to UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        else:
            v = v.astimezone(timezone.utc)

        if v <= datetime.now(timezone.utc):
            raise ValueError("Round deadline must be in the future.")
        return v


class RoundResponse(BaseModel):
    """Public representation of an apartment grocery order round."""

    id: str = Field(..., description="Round document ID")
    society_id: str = Field(..., description="Apartment society ID")
    round_number: int = Field(..., description="Sequential round number within society")
    title: str = Field(..., description="Round title")
    description: Optional[str] = Field(None, description="Optional round description")
    status: RoundStatus = Field(..., description="Current round status")
    created_by: str = Field(..., description="User ID of creator")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    opened_at: Optional[datetime] = Field(None, description="Opening timestamp (UTC)")
    deadline_at: datetime = Field(..., description="Submission deadline (UTC)")
    shopping_date: str = Field(..., description="Expected shopping date")
    closed_at: Optional[datetime] = Field(None, description="Closure timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    submissions_count: int = Field(0, description="Total grocery submissions registered")


class RoundListResponse(BaseModel):
    """Paginated list of grocery rounds for a society."""

    items: List[RoundResponse]
    total: int


class CreateSubmissionRequest(BaseModel):
    """Schema for linking a chat grocery message with an active round."""

    message_id: str = Field(..., min_length=1, max_length=100, description="Real Nexconn message ID")
    raw_text: str = Field(..., min_length=1, max_length=2000, description="Resident's grocery text")
    round_id: Optional[str] = Field(None, description="Optional target round ID (defaults to active round)")


class SubmissionResponse(BaseModel):
    """Representation of an order submission linked to a round."""

    id: str = Field(..., description="Submission ID")
    society_id: str = Field(..., description="Society ID")
    round_id: str = Field(..., description="Round ID")
    round_number: int = Field(..., description="Round number")
    user_id: str = Field(..., description="Resident user ID")
    flat_number: str = Field(..., description="Resident apartment flat number")
    user_name: str = Field(..., description="Resident name")
    message_id: str = Field(..., description="Nexconn message ID")
    raw_text: str = Field(..., description="Raw text of grocery items")
    status: str = Field("pending", description="Processing status (pending/parsed)")
    created_at: datetime = Field(..., description="Submission timestamp (UTC)")
