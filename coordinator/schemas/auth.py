"""
Pydantic schemas for authentication, token exchange, and API key management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from shared.constants import UserRole


class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="User password (min 8 chars)"
    )
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.USER, description="Requested role: user or provider")


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    balance_credits: float
    created_at: datetime


class APIKeyCreateRequest(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Friendly label for the API key"
    )
    scopes: list[str] = Field(default_factory=lambda: ["jobs:read", "jobs:write", "models:read"])
    expires_days: int | None = Field(default=90, ge=1, le=365)


class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    prefix: str
    scopes: list[str]
    is_revoked: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    # Returned only once upon initial creation
    raw_key: str | None = None
