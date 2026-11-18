"""Supabase Auth request/response schemas for Swagger-visible routes."""

from __future__ import annotations

from typing import Any

from pydantic import EmailStr, Field

from app.schemas.common import APIModel


class SignupRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(APIModel):
    refresh_token: str = Field(min_length=1)


class AuthSessionResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    expires_at: int | None = None
    user: dict[str, Any]


class AuthUserResponse(APIModel):
    id: str
    email: str | None = None
    role: str | None = None
    user_metadata: dict[str, Any] = Field(default_factory=dict)
