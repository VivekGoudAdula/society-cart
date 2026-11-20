"""Pydantic schemas for order rounds and grocery submissions.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator

RoundStatus = Literal["draft", "open", "closed", "cancelled"]
SubmissionStatus = Literal["reserved", "confirmed", "failed", "pending", "parsed"]

try:
    from zoneinfo import ZoneInfo
    KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    # Standard UTC+05:30 (India Standard Time) fallback for Windows systems without tzdata
    KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30))


class AnnouncementDeliveryState(BaseModel):
    """Structured delivery state for society announcements."""

    status: Literal["pending", "sent", "failed"] = Field("pending", description="Delivery status")
    attempts: int = Field(0, description="Total delivery attempts")
    last_attempt_at: Optional[datetime] = Field(None, description="Timestamp of last delivery attempt")
    sent_at: Optional[datetime] = Field(None, description="Timestamp of successful delivery")
    last_error: Optional[str] = Field(None, description="Error message if delivery failed")


class CreateRoundRequest(BaseModel):
    """Schema for creating a new grocery order round."""

    title: str = Field(..., min_length=2, max_length=120, description="Round title")
    description: Optional[str] = Field(None, max_length=500, description="Optional logistics note")
    deadline_at: datetime = Field(..., description="Order submission deadline (UTC)")
    shopping_date: Union[datetime, str] = Field(..., description="Expected shopping/delivery date")

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

    @field_validator("shopping_date")
    @classmethod
    def normalize_shopping_date(cls, v: Union[datetime, str]) -> str:
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=KOLKATA_TZ)
            return v.isoformat()
        clean = v.strip()
        if not clean:
            raise ValueError("Shopping date cannot be empty.")
        # Attempt to parse as ISO datetime if formatted as one
        try:
            parsed = datetime.fromisoformat(clean)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=KOLKATA_TZ)
            return parsed.isoformat()
        except (ValueError, TypeError):
            # Freeform string fallback (e.g. "Saturday 10:00 AM")
            return clean


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
    opening_announcement: Optional[AnnouncementDeliveryState] = Field(
        None, description="Opening announcement structured state"
    )
    closing_announcement: Optional[AnnouncementDeliveryState] = Field(
        None, description="Closing announcement structured state"
    )
    opening_announcement_sent: bool = Field(False, description="Backward compatibility boolean")
    closing_announcement_sent: bool = Field(False, description="Backward compatibility boolean")


class RoundListResponse(BaseModel):
    """Paginated list of grocery rounds for a society."""

    items: List[RoundResponse]
    total: int


class SubmissionReservationRequest(BaseModel):
    """Client request to reserve a submission before sending message to Nexconn."""

    submission_id: str = Field(..., min_length=1, max_length=100, description="Client-generated unique submission ID")
    raw_text: str = Field(..., min_length=1, max_length=2000, description="Resident's grocery text")


class SubmissionConfirmationRequest(BaseModel):
    """Client request to confirm submission once Nexconn delivers message ID."""

    message_id: str = Field(..., min_length=1, max_length=100, description="Real Nexconn message ID")


class SubmissionFailureRequest(BaseModel):
    """Client request to mark a reservation failed if Nexconn send fails."""

    reason: Optional[str] = Field(None, max_length=500, description="Optional reason for delivery failure")


class CreateSubmissionRequest(BaseModel):
    """Schema for linking a chat grocery message with an active round (legacy/direct)."""

    message_id: str = Field(..., min_length=1, max_length=100, description="Real Nexconn message ID")
    raw_text: str = Field(..., min_length=1, max_length=2000, description="Resident's grocery text")
    round_id: Optional[str] = Field(None, description="Optional target round ID (defaults to active round)")


class SubmissionResponse(BaseModel):
    """Representation of an order submission linked to a round."""

    id: str = Field(..., description="Submission ID")
    submission_id: str = Field(..., description="Client submission ID")
    society_id: str = Field(..., description="Society ID")
    round_id: str = Field(..., description="Round ID")
    round_number: int = Field(..., description="Round number")
    user_id: str = Field(..., description="Resident user ID")
    flat_number: str = Field(..., description="Resident apartment flat number")
    user_name: str = Field(..., description="Resident name")
    message_id: Optional[str] = Field(None, description="Nexconn message ID (None when reserved)")
    raw_text: str = Field(..., description="Raw text of grocery items")
    status: SubmissionStatus = Field("reserved", description="Status (reserved/confirmed/failed/pending/parsed)")
    reserved_at: Optional[datetime] = Field(None, description="Reservation acceptance timestamp (UTC)")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp (UTC)")
    created_at: datetime = Field(..., description="Submission creation timestamp (UTC)")
