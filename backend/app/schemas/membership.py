"""Society membership schemas and role definitions.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

MembershipRole = Literal["admin", "resident", "volunteer"]


class MembershipResponse(BaseModel):
    """Membership details connecting a user to a specific society and flat."""

    id: str
    user_id: str
    society_id: str
    flat_number: str
    role: MembershipRole
    joined_at: datetime
    is_active: bool = True
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class AssignRoleRequest(BaseModel):
    """Request schema for an admin assigning roles to society members."""

    role: Literal["resident", "volunteer"] = Field(
        ...,
        description="Role to assign: 'volunteer' or 'resident'. Only admins can perform this.",
    )
