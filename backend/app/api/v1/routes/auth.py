"""Supabase Auth routes (visible in Swagger for signup/login/token flows)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import SettingsDep
from app.core.exceptions import UnauthorizedError
from app.schemas.auth import (
    AuthSessionResponse,
    AuthUserResponse,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
)
from app.services import supabase_auth

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


@router.post("/signup", response_model=AuthSessionResponse, summary="Supabase signup")
def signup(body: SignupRequest, settings: SettingsDep) -> AuthSessionResponse:
    payload = supabase_auth.signup(settings, email=str(body.email).lower(), password=body.password)
    return AuthSessionResponse.model_validate(payload)


@router.post("/login", response_model=AuthSessionResponse, summary="Supabase password login")
def login(body: LoginRequest, settings: SettingsDep) -> AuthSessionResponse:
    payload = supabase_auth.login(settings, email=str(body.email).lower(), password=body.password)
    return AuthSessionResponse.model_validate(payload)


@router.post("/refresh", response_model=AuthSessionResponse, summary="Refresh Supabase session")
def refresh(body: RefreshRequest, settings: SettingsDep) -> AuthSessionResponse:
    payload = supabase_auth.refresh(settings, refresh_token=body.refresh_token)
    return AuthSessionResponse.model_validate(payload)


@router.post("/logout", summary="Supabase logout")
def logout(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Bearer token required")
    supabase_auth.logout(settings, access_token=credentials.credentials)
    return {"status": "ok"}


@router.get("/user", response_model=AuthUserResponse, summary="Current Supabase user")
def current_user(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthUserResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Bearer token required")
    payload = supabase_auth.get_user(settings, access_token=credentials.credentials)
    return AuthUserResponse.model_validate(payload)
