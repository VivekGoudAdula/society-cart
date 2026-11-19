"""User request and response schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """Public user profile data schema."""

    id: str
    name: str
    email: str
    phone: Optional[str] = None
    is_active: bool = True
    created_at: datetime


class UserUpdateRequest(BaseModel):
    """Permitted user profile update fields.

    Only name and phone can be modified. Protected fields (id, email, password_hash,
    roles) are strictly rejected.
    """

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
