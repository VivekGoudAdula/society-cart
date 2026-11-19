"""Authentication dependencies extracting and validating current user from JWT.
"""

from typing import Optional
from fastapi import Cookie, Depends, Header, HTTPException, status
from app.core.security import decode_token
from app.schemas.user import UserResponse
from app.services.user_service import get_user_by_id


async def get_current_user(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
) -> UserResponse:
    """Extract and validate the current authenticated user.

    Supports Authorization header ('Bearer <token>') and HTTP-only access_token cookie.

    Args:
        authorization: Authorization header string.
        access_token: Cookie containing token.

    Returns:
        UserResponse: Authenticated user profile.

    Raises:
        HTTPException: 401 if missing, invalid, or expired token.
    """
    token: Optional[str] = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif access_token:
        token = access_token.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists or has been deactivated.",
        )

    return user


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Verify that the authenticated user is active.

    Args:
        current_user: Resolved authenticated user.

    Returns:
        UserResponse: Active user.

    Raises:
        HTTPException: 403 Forbidden if user is deactivated.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    return current_user
