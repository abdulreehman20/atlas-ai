"""Thin proxy to Supabase Auth (GoTrue) for Swagger/dev convenience."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import AppError, UnauthorizedError


def _anon_key(settings: Settings) -> str:
    key = settings.supabase_anon_key or settings.supabase_publishable_key
    if not settings.supabase_url or not key:
        raise AppError(
            "Supabase Auth is not configured (SUPABASE_URL + SUPABASE_ANON_KEY)",
            code="supabase_auth_unconfigured",
            status_code=503,
        )
    return key


def _service_role_key(settings: Settings) -> str:
    key = settings.effective_supabase_key
    if not settings.supabase_url or not key:
        raise AppError(
            "Supabase Admin is not configured (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)",
            code="supabase_admin_unconfigured",
            status_code=503,
        )
    return key


def _headers(settings: Settings, *, access_token: str | None = None) -> dict[str, str]:
    key = _anon_key(settings)
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    else:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _service_headers(settings: Settings) -> dict[str, str]:
    key = _service_role_key(settings)
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _raise_from_response(response: httpx.Response) -> None:
    try:
        payload = response.json()
    except Exception:
        payload = {"message": response.text}
    message = (
        payload.get("error_description")
        or payload.get("msg")
        or payload.get("message")
        or payload.get("error")
        or "Supabase Auth request failed"
    )
    status = response.status_code
    if status in {401, 403}:
        raise UnauthorizedError(str(message))
    raise AppError(str(message), code="supabase_auth_error", status_code=status, details=payload)


def _session_from_token_payload(payload: dict[str, Any]) -> dict[str, Any]:
    user = payload.get("user") or {}
    return {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token") or "",
        "token_type": payload.get("token_type") or "bearer",
        "expires_in": payload.get("expires_in"),
        "expires_at": payload.get("expires_at"),
        "user": user,
    }


def signup(settings: Settings, *, email: str, password: str) -> dict[str, Any]:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/signup"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            headers=_headers(settings),
            json={"email": email, "password": password},
        )
    if response.status_code >= 400:
        _raise_from_response(response)
    payload = response.json()
    # Email-confirm flows may omit access_token until the user confirms.
    if "access_token" in payload:
        return _session_from_token_payload(payload)
    return {
        "access_token": "",
        "refresh_token": "",
        "token_type": "bearer",
        "expires_in": None,
        "expires_at": None,
        "user": payload.get("user") or payload,
    }


def login(settings: Settings, *, email: str, password: str) -> dict[str, Any]:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            params={"grant_type": "password"},
            headers=_headers(settings),
            json={"email": email, "password": password},
        )
    if response.status_code >= 400:
        _raise_from_response(response)
    return _session_from_token_payload(response.json())


def refresh(settings: Settings, *, refresh_token: str) -> dict[str, Any]:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            params={"grant_type": "refresh_token"},
            headers=_headers(settings),
            json={"refresh_token": refresh_token},
        )
    if response.status_code >= 400:
        _raise_from_response(response)
    return _session_from_token_payload(response.json())


def logout(settings: Settings, *, access_token: str) -> None:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/logout"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=_headers(settings, access_token=access_token))
    if response.status_code >= 400:
        _raise_from_response(response)


def get_user(settings: Settings, *, access_token: str) -> dict[str, Any]:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=_headers(settings, access_token=access_token))
    if response.status_code >= 400:
        _raise_from_response(response)
    user = response.json()
    return {
        "id": user.get("id") or "",
        "email": user.get("email"),
        "role": user.get("role"),
        "user_metadata": user.get("user_metadata") or {},
    }


def invite_user_by_email(
    settings: Settings,
    *,
    email: str,
    redirect_to: str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a Supabase Auth invite email (service role). Returns the invited user."""

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/invite"
    params: dict[str, str] = {}
    if redirect_to:
        params["redirect_to"] = redirect_to
    body: dict[str, Any] = {"email": email.strip().lower()}
    if data:
        body["data"] = data

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            params=params or None,
            headers=_service_headers(settings),
            json=body,
        )
    if response.status_code >= 400:
        _raise_from_response(response)
    user = response.json()
    return {
        "id": user.get("id") or "",
        "email": user.get("email") or email.strip().lower(),
        "user_metadata": user.get("user_metadata") or {},
        "email_sent": True,
    }
