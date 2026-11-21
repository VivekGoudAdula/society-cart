"""Nexconn service for user token issuance, group synchronization, and messaging.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import random
import time
from typing import Any, Dict, Optional
import httpx
from fastapi import HTTPException, status
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_configured() -> bool:
    """Check if valid Nexconn credentials are provided in configuration."""
    return bool(settings.nexconn_app_key and settings.nexconn_app_secret)


def _generate_auth_headers() -> Dict[str, str]:
    """Generate SHA1 cryptographic request headers required by the Nexconn/RongCloud API."""
    nonce = str(random.randint(100000, 999999))
    timestamp = str(int(time.time() * 1000))
    raw_sig = f"{settings.nexconn_app_secret}{nonce}{timestamp}"
    signature = hashlib.sha1(raw_sig.encode("utf-8")).hexdigest()

    return {
        "App-Key": settings.nexconn_app_key,
        "Nonce": nonce,
        "Timestamp": timestamp,
        "Signature": signature,
        "Content-Type": "application/x-www-form-urlencoded",
    }


async def issue_nexconn_token(user_id: str, display_name: str, avatar_url: str = "") -> str:
    """Issue a user-specific chat access token from the Nexconn Server API.

    Args:
        user_id: Stable Society Cart user ID.
        display_name: Resident full name.
        avatar_url: Optional resident profile photo.

    Returns:
        str: User access token for connecting from the Web SDK.
    """
    if not _is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nexconn chat integration is not configured. Missing App Key or App Secret.",
        )

    headers = _generate_auth_headers()
    url = f"{settings.nexconn_api_base_url}/user/getToken.json"
    data = {
        "userId": user_id,
        "name": display_name,
        "portraitUri": avatar_url or "",
    }

    max_attempts = 2
    last_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, data=data)
                resp_data = resp.json()

                if resp.status_code == 200 and resp_data.get("code") == 200:
                    token = resp_data.get("token")
                    if token:
                        return token

                logger.error(
                    "Failed to issue Nexconn token (attempt %d/%d): HTTP %s, Body: %s",
                    attempt, max_attempts, resp.status_code, resp.text
                )
                if attempt == max_attempts:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Nexconn token issuance failed: {resp_data.get('errorMessage', 'Unknown error')}",
                    )
        except httpx.RequestError as exc:
            last_error = exc
            logger.warning("Nexconn request error on attempt %d/%d: %s", attempt, max_attempts, exc)
            if attempt == max_attempts:
                logger.error("Nexconn network request error during token issuance: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Could not reach Nexconn chat network: {str(exc)}",
                )


async def create_nexconn_group(group_id: str, group_name: str, creator_user_id: str) -> bool:
    """Create a new group channel in the Nexconn network for an apartment society.

    Args:
        group_id: Stable group identifier (e.g. `society_<id>`).
        group_name: Apartment community name.
        creator_user_id: Society Cart admin user ID.

    Returns:
        bool: True if created or already exists.
    """
    if not _is_configured():
        logger.warning("Nexconn not configured; skipping group creation for %s", group_id)
        return False

    headers = _generate_auth_headers()
    url = f"{settings.nexconn_api_base_url}/group/create.json"
    data = {
        "userId": creator_user_id,
        "groupId": group_id,
        "groupName": group_name,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, data=data)
            resp_data = resp.json()
            if resp.status_code == 200 and resp_data.get("code") == 200:
                return True

            logger.warning("Nexconn group creation returned: %s", resp.text)
            return resp_data.get("code") == 200
    except Exception as exc:
        logger.error("Error creating Nexconn group %s: %s", group_id, exc)
        return False


async def add_resident_to_group(user_id: str, group_id: str, group_name: str) -> bool:
    """Add a resident user to the society's Nexconn group channel.

    Args:
        user_id: Resident user ID.
        group_id: Society Nexconn group ID.
        group_name: Society name.

    Returns:
        bool: True if successful.
    """
    if not _is_configured():
        return False

    headers = _generate_auth_headers()
    url = f"{settings.nexconn_api_base_url}/group/join.json"
    data = {
        "userId": user_id,
        "groupId": group_id,
        "groupName": group_name,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, data=data)
            resp_data = resp.json()
            return resp.status_code == 200 and resp_data.get("code") == 200
    except Exception as exc:
        logger.error("Error adding user %s to group %s: %s", user_id, group_id, exc)
        return False


async def remove_resident_from_group(user_id: str, group_id: str) -> bool:
    """Remove a deactivated resident from the society's Nexconn group channel.

    Args:
        user_id: User ID to remove.
        group_id: Society Nexconn group ID.

    Returns:
        bool: True if removed successfully.
    """
    if not _is_configured():
        return False

    headers = _generate_auth_headers()
    url = f"{settings.nexconn_api_base_url}/group/quit.json"
    data = {
        "userId": user_id,
        "groupId": group_id,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, data=data)
            resp_data = resp.json()
            return resp.status_code == 200 and resp_data.get("code") == 200
    except Exception as exc:
        logger.error("Error removing user %s from group %s: %s", user_id, group_id, exc)
        return False


async def send_system_bot_message(
    group_id: str,
    text: str,
    extra: Optional[Dict[str, Any]] = None,
) -> bool:
    """Publish an automated system/bot message to the society group chat.

    Args:
        group_id: Society Nexconn group channel ID.
        text: Plain-text broadcast message.
        extra: Optional metadata payload.

    Returns:
        bool: True if dispatched successfully.
    """
    if not _is_configured():
        return False

    headers = _generate_auth_headers()
    url = f"{settings.nexconn_api_base_url}/message/group/publish.json"

    content_payload = {"content": text}
    if extra:
        content_payload["extra"] = json.dumps(extra)

    data = {
        "fromUserId": "society_cart_bot",
        "toGroupId": group_id,
        "objectName": "RC:TxtMsg",
        "content": json.dumps(content_payload),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, data=data)
            resp_data = resp.json()
            return resp.status_code == 200 and resp_data.get("code") == 200
    except Exception as exc:
        logger.error("Error publishing bot message to group %s: %s", group_id, exc)
        return False
