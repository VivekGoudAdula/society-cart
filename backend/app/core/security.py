"""Security utilities for password hashing and JWT token handling.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt
from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt.

    Args:
        password: Raw user password string.

    Returns:
        str: Securely hashed password.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a raw password against its stored bcrypt hash.

    Args:
        plain_password: Password entered by the user.
        hashed_password: Stored bcrypt hash string.

    Returns:
        bool: True if passwords match, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_token(payload: Dict[str, Any], expires_delta: timedelta) -> str:
    """Generate a signed JWT token with an expiration timestamp.

    Args:
        payload: Custom claims to embed in the token.
        expires_delta: Duration until expiration.

    Returns:
        str: Encoded JWT string.
    """
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(user_id: str, email: str) -> str:
    """Generate a short-lived access token for user authentication.

    Args:
        user_id: Unique user document ID.
        email: User email address.

    Returns:
        str: Signed JWT access token.
    """
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
    }
    return create_token(
        payload,
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    """Generate a long-lived refresh token for session continuation.

    Args:
        user_id: Unique user document ID.

    Returns:
        str: Signed JWT refresh token.
    """
    payload = {
        "sub": user_id,
        "type": "refresh",
    }
    return create_token(
        payload,
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a signed JWT token.

    Args:
        token: Signed JWT string.

    Returns:
        Optional[Dict[str, Any]]: Payload dict if valid, None if expired/invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None
