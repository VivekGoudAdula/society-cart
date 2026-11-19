"""Chat schemas for Nexconn token issuance and group channel identity.
"""

from pydantic import BaseModel, Field


class ChatTokenRequest(BaseModel):
    """Request payload to retrieve a user-specific Nexconn token."""
    society_id: str = Field(..., description="ID of the society whose chat the user wants to access")


class ChatTokenResponse(BaseModel):
    """Response containing credentials to connect to the society's Nexconn group chat."""
    token: str = Field(..., description="User access token signed by Nexconn Server API")
    app_key: str = Field(..., description="Public Nexconn application key")
    user_id: str = Field(..., description="Stable user ID within Nexconn")
    group_id: str = Field(..., description="Nexconn group channel ID for this society")
    group_name: str = Field(..., description="Apartment society name")
