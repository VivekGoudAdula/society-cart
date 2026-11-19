"""Society creation, joining, and details schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.membership import MembershipResponse


class SocietyCreateRequest(BaseModel):
    """Schema for creating a new apartment society."""

    name: str = Field(..., min_length=3, max_length=150, description="Name of apartment society")
    address: str = Field(..., min_length=5, max_length=255, description="Street / locality address")
    city: str = Field(..., min_length=2, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: str = Field("India", max_length=100)
    total_flats: Optional[int] = Field(None, ge=1, le=10000)
    creator_flat_number: str = Field(..., min_length=1, max_length=20, description="Creator's flat number")


class SocietyJoinRequest(BaseModel):
    """Schema for joining an existing society using an invitation code."""

    invite_code: str = Field(..., min_length=4, max_length=30, description="Society invitation code")
    flat_number: str = Field(..., min_length=1, max_length=20, description="Resident's flat number")


class SocietyResponse(BaseModel):
    """Public society information schema."""

    id: str
    name: str
    address: str
    city: str
    state: Optional[str] = None
    country: str
    invite_code: str
    created_by: str
    created_at: datetime
    is_active: bool = True
    total_flats: Optional[int] = None


class UserSocietyMembershipResponse(BaseModel):
    """Combined society and active membership representation for the user."""

    society: SocietyResponse
    membership: MembershipResponse
