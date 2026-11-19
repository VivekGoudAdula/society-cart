"""Chat endpoints for issuing Nexconn user tokens and managing society group channels.
"""

from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.database import get_societies_collection
from app.dependencies.auth import get_current_active_user
from app.dependencies.permissions import require_society_member
from app.schemas.auth import UserResponse
from app.schemas.chat import ChatTokenRequest, ChatTokenResponse
from app.services.membership_service import get_active_membership
from app.services.nexconn_service import (
    issue_nexconn_token,
    add_resident_to_group,
    send_system_bot_message,
)

router = APIRouter(prefix="/chat", tags=["Chat"])
settings = get_settings()


class SystemMessageRequest(BaseModel):
    """Schema for dispatching an automated bot/system message to a society group chat."""
    society_id: str = Field(..., description="ID of target apartment society")
    text: str = Field(..., min_length=1, max_length=1000, description="Broadcast message text")
    extra: Optional[dict] = Field(None, description="Optional metadata payload for future AI/rounds")


@router.post("/token", response_model=ChatTokenResponse)
async def get_chat_token(
    request: ChatTokenRequest,
    current_user: UserResponse = Depends(get_current_active_user),
) -> ChatTokenResponse:
    """Issue a user-specific Nexconn chat access token for an authenticated society member.

    Security guarantees:
    - Never accepts an arbitrary Nexconn user ID; derives identity strictly from authenticated user.
    - Strictly blocks non-members or cross-society eavesdropping (403 Forbidden).
    - Ensures user is added to the society's private group channel.
    - Never exposes the App Secret.
    """
    society_id = request.society_id.strip()

    # Verify active society membership
    membership = await get_active_membership(current_user.id, society_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this apartment society.",
        )

    # Fetch society details
    societies_col = get_societies_collection()
    society_oid = ObjectId(society_id) if ObjectId.is_valid(society_id) else society_id
    society_doc = await societies_col.find_one({"_id": society_oid, "is_active": True})

    if not society_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apartment society not found or inactive.",
        )

    group_id = society_doc.get("nexconn_group_id") or f"society_{society_id}"
    group_name = society_doc["name"]

    # Issue verified user access token from Nexconn Server API
    token = await issue_nexconn_token(
        user_id=current_user.id,
        display_name=current_user.name,
    )

    # Ensure resident is registered in the group channel
    await add_resident_to_group(current_user.id, group_id, group_name)

    return ChatTokenResponse(
        token=token,
        app_key=settings.nexconn_app_key,
        user_id=current_user.id,
        group_id=group_id,
        group_name=group_name,
    )


@router.post("/system-message")
async def dispatch_system_message(
    request: SystemMessageRequest,
    current_user: UserResponse = Depends(get_current_active_user),
) -> dict:
    """Publish a system bot message to the society group chat.

    Requires that the caller is an active member of the society.
    Prepares the foundation for future automated round opening/closing notifications.
    """
    society_id = request.society_id.strip()

    # Caller must be active member
    membership = await get_active_membership(current_user.id, society_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an active member of this society to dispatch notifications.",
        )

    societies_col = get_societies_collection()
    society_oid = ObjectId(society_id) if ObjectId.is_valid(society_id) else society_id
    society_doc = await societies_col.find_one({"_id": society_oid, "is_active": True})

    if not society_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apartment society not found.",
        )

    group_id = society_doc.get("nexconn_group_id") or f"society_{society_id}"

    success = await send_system_bot_message(
        group_id=group_id,
        text=request.text.strip(),
        extra=request.extra,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to publish system message to Nexconn group channel.",
        )

    return {"status": "ok", "message": "System notification published successfully"}
