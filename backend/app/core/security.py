"""Supabase JWT verification and principal helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

import httpx
import jwt
from jwt import PyJWKClient

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError

Role = Literal["owner", "member"]


@dataclass(frozen=True, slots=True)
class AuthUser:
    user_id: str
    email: str | None
    claims: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    email: str | None
    organization_id: UUID
    workspace_id: UUID
    role: Role
    membership_id: UUID
    membership_status: str


class JWTVerifier:
    """Verifies Supabase access tokens via JWKS or shared secret."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jwks_client: PyJWKClient | None = None
        if settings.supabase_jwks_url:
            self._jwks_client = PyJWKClient(settings.supabase_jwks_url)

    def verify(self, token: str) -> AuthUser:
        if not token:
            raise UnauthorizedError("Missing bearer token")
        if not self._settings.has_jwt_verifier():
            raise UnauthorizedError("JWT verifier is not configured")

        try:
            claims = self._decode(token)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc

        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub:
            raise UnauthorizedError("Token missing subject")
        email = claims.get("email")
        return AuthUser(
            user_id=sub,
            email=email if isinstance(email, str) else None,
            claims=claims,
        )

    def _decode(self, token: str) -> dict[str, Any]:
        options = {"require": ["exp", "sub"]}
        audience = "authenticated"
        if self._jwks_client is not None:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256", "HS256"],
                audience=audience,
                options=options,
            )
        return jwt.decode(
            token,
            self._settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=audience,
            options=options,
        )


def pinecone_namespace(workspace_id: UUID | str) -> str:
    """Server-derived Pinecone namespace. Never accept from clients."""
    return f"ws_{workspace_id}"


def health_check_jwks(settings: Settings, *, timeout: float = 2.0) -> bool:
    if not settings.supabase_jwks_url:
        return bool(settings.supabase_jwt_secret)
    try:
        response = httpx.get(settings.supabase_jwks_url, timeout=timeout)
        return response.status_code == 200
    except httpx.HTTPError:
        return False
