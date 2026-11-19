"""Authentication service for registration, login, and credential validation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError
from app.core.database import get_users_collection
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.schemas.auth import RegisterRequest, LoginRequest
from app.schemas.user import UserResponse
from app.services.user_service import get_user_by_email, _serialize_user


async def register_user(request: RegisterRequest) -> Tuple[UserResponse, str, str]:
    """Register a new user account with unique email and hashed password.

    Args:
        request: Validated registration request.

    Returns:
        Tuple[UserResponse, str, str]: User profile, access token, and refresh token.

    Raises:
        HTTPException: 409 Conflict if email is already registered.
    """
    col = get_users_collection()
    normalized_email = request.email.strip().lower()

    # Check for existing email
    existing = await get_user_by_email(normalized_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    now = datetime.now(timezone.utc)
    user_doc = {
        "name": request.name.strip(),
        "email": normalized_email,
        "phone": request.phone.strip() if request.phone else None,
        "password_hash": hash_password(request.password),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = await col.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    user_resp = _serialize_user(user_doc)
    access_token = create_access_token(user_resp.id, user_resp.email)
    refresh_token = create_refresh_token(user_resp.id)

    return user_resp, access_token, refresh_token


async def authenticate_user(request: LoginRequest) -> Tuple[UserResponse, str, str]:
    """Validate credentials and return authenticated tokens.

    Args:
        request: Email and raw password.

    Returns:
        Tuple[UserResponse, str, str]: User profile, access token, and refresh token.

    Raises:
        HTTPException: 401 Unauthorized if credentials do not match or user is inactive.
    """
    normalized_email = request.email.strip().lower()
    user_doc = await get_user_by_email(normalized_email)

    if not user_doc or not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(request.password, user_doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user_resp = _serialize_user(user_doc)
    access_token = create_access_token(user_resp.id, user_resp.email)
    refresh_token = create_refresh_token(user_resp.id)

    return user_resp, access_token, refresh_token
