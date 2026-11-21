"""Authentication endpoints for registration, login, logout, and session check.
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from app.core.config import get_settings
from app.core.security import decode_token, create_access_token, create_refresh_token
from app.dependencies.auth import get_current_active_user
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    AuthSessionResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import register_user, authenticate_user
from app.services.society_service import get_user_societies
from app.services.user_service import get_user_by_id

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set secure HTTP-only session cookies."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, response: Response) -> TokenResponse:
    """Register a new user account with email, name, and password."""
    user, access_token, refresh_token = await register_user(request)
    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(access_token=access_token, user=user)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, response: Response) -> TokenResponse:
    """Authenticate with email and password to begin a session."""
    user, access_token, refresh_token = await authenticate_user(request)
    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(access_token=access_token, user=user)


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Terminate the current session and clear authentication cookies."""
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    return {"message": "Logged out successfully", "status": "ok"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
) -> TokenResponse:
    """Issue a new access token using a valid HTTP-only refresh token."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is required.",
        )

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
        )

    user_id = payload.get("sub")
    user = await get_user_by_id(user_id) if user_id else None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer active.",
        )

    new_access_token = create_access_token(user.id, user.email)
    new_refresh_token = create_refresh_token(user.id)
    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return TokenResponse(access_token=new_access_token, user=user)


@router.get("/me", response_model=AuthSessionResponse)
async def get_my_session(
    current_user: UserResponse = Depends(get_current_active_user),
) -> AuthSessionResponse:
    """Restore and return the active authenticated session state with society memberships."""
    user_societies = await get_user_societies(current_user.id)
    return AuthSessionResponse(user=current_user, societies=user_societies)
