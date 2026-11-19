"""Authentication request and response schemas.
"""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserResponse
from app.schemas.society import UserSocietyMembershipResponse


class RegisterRequest(BaseModel):
    """User account registration schema."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)


class LoginRequest(BaseModel):
    """User authentication login schema."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token output schema returned upon successful login or refresh."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuthSessionResponse(BaseModel):
    """Complete authenticated session state including user and joined societies."""

    user: UserResponse
    societies: List[UserSocietyMembershipResponse]
